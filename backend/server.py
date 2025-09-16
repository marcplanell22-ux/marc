from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, File, UploadFile, Form, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from bson import ObjectId
import json
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import io
import gridfs
import asyncio
from cryptography.fernet import Fernet
import base64
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
fs = AsyncIOMotorGridFSBucket(db)

# Configuration
PLATFORM_COMMISSION_RATE = 0.099  # 9.9% commission rate
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

# Stripe Configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# Encryption Configuration
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key().decode())

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except:
                # Connection might be closed, remove it
                self.disconnect(user_id)
    
    async def broadcast_to_conversation(self, message: dict, user_ids: List[str]):
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()

# Create the main app
app = FastAPI(title="Creator Subscription Platform", version="1.0.0")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Subscription Packages
SUBSCRIPTION_PACKAGES = {
    "basic": {"price": 9.99, "name": "Basic Plan", "description": "Access to basic content"},
    "premium": {"price": 19.99, "name": "Premium Plan", "description": "Access to all content + exclusive perks"},
    "vip": {"price": 49.99, "name": "VIP Plan", "description": "All access + direct messaging + custom content"}
}

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    username: str
    full_name: str
    is_creator: bool = False
    is_verified: bool = False
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    subscription_plan: Optional[str] = None
    stripe_customer_id: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    is_creator: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Creator(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    display_name: str
    bio: str
    category: str
    tags: List[str] = []
    subscription_price: float
    follower_count: int = 0
    content_count: int = 0
    rating: float = 0.0
    is_verified: bool = False
    banner_url: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CreatorCreate(BaseModel):
    display_name: str
    bio: str
    category: str
    tags: List[str] = []
    subscription_price: float

class Content(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    title: str
    description: str
    content_type: str  # 'image', 'video', 'text', 'audio'
    file_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_premium: bool = False
    is_ppv: bool = False  # Pay-per-view
    ppv_price: Optional[float] = None
    tags: List[str] = []
    likes: int = 0
    views: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContentCreate(BaseModel):
    title: str
    description: str
    is_premium: bool = False
    is_ppv: bool = False
    ppv_price: Optional[float] = None
    tags: List[str] = []

class ScheduledContent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    title: str
    description: str
    content_type: str  # 'image', 'video', 'text', 'audio'
    file_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_premium: bool = False
    is_ppv: bool = False
    ppv_price: Optional[float] = None
    tags: List[str] = []
    scheduled_date: datetime
    is_recurring: bool = False
    recurrence_type: Optional[str] = None  # 'weekly', 'monthly', 'daily'
    recurrence_end_date: Optional[datetime] = None
    status: str = "scheduled"  # 'scheduled', 'published', 'cancelled'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None

class ScheduledContentCreate(BaseModel):
    title: str
    description: str
    scheduled_date: datetime
    is_premium: bool = False
    is_ppv: bool = False
    ppv_price: Optional[float] = None
    tags: List[str] = []
    is_recurring: bool = False
    recurrence_type: Optional[str] = None
    recurrence_end_date: Optional[datetime] = None

class ContentTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    name: str
    title_template: str
    description_template: str
    tags: List[str] = []
    is_premium: bool = False
    is_ppv: bool = False
    ppv_price: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContentTemplateCreate(BaseModel):
    name: str
    title_template: str
    description_template: str
    tags: List[str] = []
    is_premium: bool = False
    is_ppv: bool = False
    ppv_price: Optional[float] = None

class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    creator_id: str
    plan_type: str
    status: str  # 'active', 'cancelled', 'expired'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    stripe_subscription_id: Optional[str] = None

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    creator_id: Optional[str] = None
    amount: float
    currency: str = "usd"
    transaction_type: str  # 'subscription', 'tip', 'ppv', 'message_ppv'
    stripe_session_id: str
    payment_status: str = "pending"
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Messaging Models
class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    fan_id: str
    is_blocked: bool = False
    blocked_by: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    sender_id: str
    sender_type: str  # 'creator' or 'fan'
    message_type: str  # 'text', 'image', 'video', 'audio', 'tip'
    content: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    is_ppv: bool = False
    ppv_price: Optional[float] = None
    ppv_preview: Optional[str] = None  # Preview text or thumbnail
    is_tip: bool = False
    tip_amount: Optional[float] = None
    is_read: bool = False
    is_encrypted: bool = False
    encryption_key: Optional[str] = None
    auto_destruct_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read_at: Optional[datetime] = None

class MessageCreate(BaseModel):
    conversation_id: str
    message_type: str = "text"
    content: Optional[str] = None
    is_ppv: bool = False
    ppv_price: Optional[float] = None
    ppv_preview: Optional[str] = None
    is_tip: bool = False
    tip_amount: Optional[float] = None
    auto_destruct_minutes: Optional[int] = None

class ConversationSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    allow_messages: bool = True
    require_subscription: bool = False
    message_price: Optional[float] = None  # Price per message for non-subscribers
    auto_response_enabled: bool = False
    auto_response_message: Optional[str] = None
    max_messages_per_day: Optional[int] = None
    blocked_users: List[str] = []
    vip_users: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MessagePayment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str
    payer_id: str
    amount: float
    payment_status: str = "pending"  # 'pending', 'paid', 'failed'
    stripe_session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    paid_at: Optional[datetime] = None

class TipRequest(BaseModel):
    creator_id: str
    amount: float
    message: Optional[str] = None

class SubscriptionRequest(BaseModel):
    creator_id: str
    plan_type: str

# Utility Functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(data: dict):
    expires_delta = timedelta(days=30)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

# Auth Routes
@api_router.post("/auth/register", response_model=dict)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"email": user_data.email}, {"username": user_data.username}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create user
    hashed_password = hash_password(user_data.password)
    user = User(**user_data.dict(), id=str(uuid.uuid4()))
    user_dict = user.dict()
    user_dict['password_hash'] = hashed_password
    
    await db.users.insert_one(user_dict)
    
    # Create JWT token
    token = create_jwt_token({"sub": user.id})
    
    return {"access_token": token, "token_type": "bearer", "user": user}

@api_router.post("/auth/login", response_model=dict)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_jwt_token({"sub": user['id']})
    user_obj = User(**{k: v for k, v in user.items() if k != 'password_hash'})
    
    return {"access_token": token, "token_type": "bearer", "user": user_obj}

@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Creator Routes
@api_router.post("/creators", response_model=Creator)
async def create_creator_profile(creator_data: CreatorCreate, current_user: User = Depends(get_current_user)):
    if not current_user.is_creator:
        raise HTTPException(status_code=403, detail="User is not registered as a creator")
    
    # Check if creator profile already exists
    existing_creator = await db.creators.find_one({"user_id": current_user.id})
    if existing_creator:
        raise HTTPException(status_code=400, detail="Creator profile already exists")
    
    creator = Creator(**creator_data.dict(), user_id=current_user.id)
    await db.creators.insert_one(creator.dict())
    
    return creator

@api_router.get("/creators", response_model=List[Creator])
async def get_creators(skip: int = 0, limit: int = 20, category: Optional[str] = None, search: Optional[str] = None):
    filters = {}
    if category:
        filters["category"] = category
    if search:
        filters["$or"] = [
            {"display_name": {"$regex": search, "$options": "i"}},
            {"bio": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}}
        ]
        
    creators = await db.creators.find(filters).skip(skip).limit(limit).to_list(length=None)
    return [Creator(**creator) for creator in creators]

@api_router.get("/creators/{creator_id}", response_model=Creator)
async def get_creator(creator_id: str):
    creator = await db.creators.find_one({"id": creator_id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    return Creator(**creator)

# Content Routes
@api_router.post("/content")
async def create_content(
    title: str = Form(...),
    description: str = Form(...),
    is_premium: bool = Form(False),
    is_ppv: bool = Form(False),
    ppv_price: Optional[float] = Form(None),
    tags: str = Form(""),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    # Get creator profile
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    content_data = {
        "title": title,
        "description": description,
        "is_premium": is_premium,
        "is_ppv": is_ppv,
        "ppv_price": ppv_price,
        "tags": tags.split(",") if tags else []
    }
    
    file_path = None
    content_type = "text"
    
    if file:
        # Store file in GridFS
        file_content = await file.read()
        file_id = await fs.upload_from_stream(
            file.filename,
            io.BytesIO(file_content),
            metadata={"content_type": file.content_type}
        )
        file_path = str(file_id)
        
        # Determine content type
        if file.content_type.startswith("image"):
            content_type = "image"
        elif file.content_type.startswith("video"):
            content_type = "video"
        elif file.content_type.startswith("audio"):
            content_type = "audio"
    
    content = Content(
        **content_data,
        creator_id=creator['id'],
        content_type=content_type,
        file_path=file_path
    )
    
    await db.content.insert_one(content.dict())
    
    # Update creator content count
    await db.creators.update_one(
        {"id": creator['id']},
        {"$inc": {"content_count": 1}}
    )
    
    return {"message": "Content created successfully", "content_id": content.id}

@api_router.get("/content", response_model=List[Content])
async def get_content(skip: int = 0, limit: int = 20, creator_id: Optional[str] = None, category: Optional[str] = None):
    filters = {}
    if creator_id:
        filters["creator_id"] = creator_id
    
    content = await db.content.find(filters).sort("created_at", -1).skip(skip).limit(limit).to_list(length=None)
    return [Content(**item) for item in content]

@api_router.get("/content/{content_id}/file")
async def get_content_file(content_id: str, current_user: User = Depends(get_current_user)):
    content = await db.content.find_one({"id": content_id})
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if not content.get('file_path'):
        raise HTTPException(status_code=404, detail="No file associated with this content")
    
    # Check access permissions
    if content['is_premium'] or content['is_ppv']:
        # Check if user has subscription or has paid for PPV
        subscription = await db.subscriptions.find_one({
            "user_id": current_user.id,
            "creator_id": content['creator_id'],
            "status": "active"
        })
        
        if not subscription and content['is_ppv']:
            # Check if user has paid for this specific content
            payment = await db.payment_transactions.find_one({
                "user_id": current_user.id,
                "metadata.content_id": content_id,
                "payment_status": "paid"
            })
            if not payment:
                raise HTTPException(status_code=403, detail="Payment required to access this content")
    
    # Get file from GridFS
    try:
        file_id = ObjectId(content['file_path'])
        grid_out = await fs.open_download_stream(file_id)
        file_data = await grid_out.read()
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=grid_out.metadata.get('content_type', 'application/octet-stream'),
            headers={"Content-Disposition": f"inline; filename={grid_out.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")

# Scheduled Content Routes
@api_router.post("/content/schedule")
async def schedule_content(
    title: str = Form(...),
    description: str = Form(...),
    scheduled_date: str = Form(...),
    is_premium: bool = Form(False),
    is_ppv: bool = Form(False),
    ppv_price: Optional[float] = Form(None),
    tags: str = Form(""),
    is_recurring: bool = Form(False),
    recurrence_type: Optional[str] = Form(None),
    recurrence_end_date: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    # Get creator profile
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    try:
        scheduled_datetime = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
        if scheduled_datetime <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Scheduled date must be in the future")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    file_path = None
    content_type = "text"
    
    if file:
        # Store file in GridFS
        file_content = await file.read()
        file_id = await fs.upload_from_stream(
            file.filename,
            io.BytesIO(file_content),
            metadata={"content_type": file.content_type}
        )
        file_path = str(file_id)
        
        # Determine content type
        if file.content_type.startswith("image"):
            content_type = "image"
        elif file.content_type.startswith("video"):
            content_type = "video"
        elif file.content_type.startswith("audio"):
            content_type = "audio"
    
    # Parse recurrence end date if provided
    recurrence_end_datetime = None
    if recurrence_end_date:
        try:
            recurrence_end_datetime = datetime.fromisoformat(recurrence_end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid recurrence end date format")
    
    scheduled_content = ScheduledContent(
        creator_id=creator['id'],
        title=title,
        description=description,
        content_type=content_type,
        file_path=file_path,
        is_premium=is_premium,
        is_ppv=is_ppv,
        ppv_price=ppv_price,
        tags=tags.split(",") if tags else [],
        scheduled_date=scheduled_datetime,
        is_recurring=is_recurring,
        recurrence_type=recurrence_type,
        recurrence_end_date=recurrence_end_datetime
    )
    
    await db.scheduled_content.insert_one(scheduled_content.dict())
    
    return {"message": "Content scheduled successfully", "scheduled_content_id": scheduled_content.id}

@api_router.get("/content/scheduled", response_model=List[ScheduledContent])
async def get_scheduled_content(
    skip: int = 0, 
    limit: int = 50,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    filters = {"creator_id": creator['id']}
    if status:
        filters["status"] = status
    
    scheduled_content = await db.scheduled_content.find(filters).sort("scheduled_date", 1).skip(skip).limit(limit).to_list(length=None)
    return [ScheduledContent(**item) for item in scheduled_content]

@api_router.delete("/content/scheduled/{scheduled_id}")
async def cancel_scheduled_content(scheduled_id: str, current_user: User = Depends(get_current_user)):
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    scheduled_content = await db.scheduled_content.find_one({
        "id": scheduled_id,
        "creator_id": creator['id']
    })
    
    if not scheduled_content:
        raise HTTPException(status_code=404, detail="Scheduled content not found")
    
    if scheduled_content['status'] == 'published':
        raise HTTPException(status_code=400, detail="Cannot cancel already published content")
    
    await db.scheduled_content.update_one(
        {"id": scheduled_id},
        {"$set": {"status": "cancelled"}}
    )
    
    return {"message": "Scheduled content cancelled successfully"}

@api_router.put("/content/scheduled/{scheduled_id}")
async def update_scheduled_content(
    scheduled_id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    scheduled_date: Optional[str] = Form(None),
    is_premium: Optional[bool] = Form(None),
    is_ppv: Optional[bool] = Form(None),
    ppv_price: Optional[float] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    scheduled_content = await db.scheduled_content.find_one({
        "id": scheduled_id,
        "creator_id": creator['id'],
        "status": "scheduled"
    })
    
    if not scheduled_content:
        raise HTTPException(status_code=404, detail="Scheduled content not found or already published")
    
    update_data = {}
    
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if scheduled_date is not None:
        try:
            scheduled_datetime = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
            if scheduled_datetime <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="Scheduled date must be in the future")
            update_data["scheduled_date"] = scheduled_datetime
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    if is_premium is not None:
        update_data["is_premium"] = is_premium
    if is_ppv is not None:
        update_data["is_ppv"] = is_ppv
    if ppv_price is not None:
        update_data["ppv_price"] = ppv_price
    if tags is not None:
        update_data["tags"] = tags.split(",") if tags else []
    
    if update_data:
        await db.scheduled_content.update_one(
            {"id": scheduled_id},
            {"$set": update_data}
        )
    
    return {"message": "Scheduled content updated successfully"}

# Content Templates Routes
@api_router.post("/content/templates", response_model=ContentTemplate)
async def create_content_template(template_data: ContentTemplateCreate, current_user: User = Depends(get_current_user)):
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    template = ContentTemplate(**template_data.dict(), creator_id=creator['id'])
    await db.content_templates.insert_one(template.dict())
    
    return template

@api_router.get("/content/templates", response_model=List[ContentTemplate])
async def get_content_templates(current_user: User = Depends(get_current_user)):
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    templates = await db.content_templates.find({"creator_id": creator['id']}).to_list(length=None)
    return [ContentTemplate(**template) for template in templates]

@api_router.delete("/content/templates/{template_id}")
async def delete_content_template(template_id: str, current_user: User = Depends(get_current_user)):
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    result = await db.content_templates.delete_one({
        "id": template_id,
        "creator_id": creator['id']
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}

# Auto-publish scheduled content (this would be called by a cron job)
@api_router.post("/content/publish-scheduled")
async def publish_scheduled_content():
    """
    This endpoint should be called periodically by a cron job to publish scheduled content
    """
    current_time = datetime.now(timezone.utc)
    
    # Find content that should be published now
    scheduled_content = await db.scheduled_content.find({
        "scheduled_date": {"$lte": current_time},
        "status": "scheduled"
    }).to_list(length=None)
    
    published_count = 0
    
    for content_data in scheduled_content:
        try:
            # Create the actual content
            content = Content(
                creator_id=content_data['creator_id'],
                title=content_data['title'],
                description=content_data['description'],
                content_type=content_data['content_type'],
                file_path=content_data.get('file_path'),
                thumbnail_url=content_data.get('thumbnail_url'),
                is_premium=content_data['is_premium'],
                is_ppv=content_data['is_ppv'],
                ppv_price=content_data.get('ppv_price'),
                tags=content_data['tags']
            )
            
            await db.content.insert_one(content.dict())
            
            # Update scheduled content status
            await db.scheduled_content.update_one(
                {"id": content_data['id']},
                {
                    "$set": {
                        "status": "published",
                        "published_at": current_time
                    }
                }
            )
            
            # Update creator content count
            await db.creators.update_one(
                {"id": content_data['creator_id']},
                {"$inc": {"content_count": 1}}
            )
            
            # Handle recurring content
            if content_data.get('is_recurring') and content_data.get('recurrence_type'):
                next_date = calculate_next_recurrence_date(
                    content_data['scheduled_date'], 
                    content_data['recurrence_type']
                )
                
                # Check if we should create next occurrence
                if (not content_data.get('recurrence_end_date') or 
                    next_date <= content_data['recurrence_end_date']):
                    
                    next_scheduled = ScheduledContent(
                        creator_id=content_data['creator_id'],
                        title=content_data['title'],
                        description=content_data['description'],
                        content_type=content_data['content_type'],
                        file_path=content_data.get('file_path'),
                        is_premium=content_data['is_premium'],
                        is_ppv=content_data['is_ppv'],
                        ppv_price=content_data.get('ppv_price'),
                        tags=content_data['tags'],
                        scheduled_date=next_date,
                        is_recurring=True,
                        recurrence_type=content_data['recurrence_type'],
                        recurrence_end_date=content_data.get('recurrence_end_date')
                    )
                    
                    await db.scheduled_content.insert_one(next_scheduled.dict())
            
            published_count += 1
            
        except Exception as e:
            logging.error(f"Error publishing scheduled content {content_data['id']}: {str(e)}")
            # Mark as failed
            await db.scheduled_content.update_one(
                {"id": content_data['id']},
                {"$set": {"status": "failed"}}
            )
    
    return {"message": f"Published {published_count} scheduled content items"}

def calculate_next_recurrence_date(current_date: datetime, recurrence_type: str) -> datetime:
    """Calculate the next occurrence date based on recurrence type"""
    if isinstance(current_date, str):
        current_date = datetime.fromisoformat(current_date.replace('Z', '+00:00'))
    
    if recurrence_type == 'daily':
        return current_date + timedelta(days=1)
    elif recurrence_type == 'weekly':
        return current_date + timedelta(weeks=1)
    elif recurrence_type == 'monthly':
        # Add one month (approximate)
        if current_date.month == 12:
            return current_date.replace(year=current_date.year + 1, month=1)
        else:
            try:
                return current_date.replace(month=current_date.month + 1)
            except ValueError:
                # Handle case where day doesn't exist in next month (e.g., Jan 31 -> Feb 28)
                import calendar
                next_month = current_date.month + 1 if current_date.month < 12 else 1
                next_year = current_date.year if current_date.month < 12 else current_date.year + 1
                max_day = calendar.monthrange(next_year, next_month)[1]
                return current_date.replace(
                    year=next_year,
                    month=next_month,
                    day=min(current_date.day, max_day)
                )
    else:
        return current_date + timedelta(days=1)  # Default to daily

# Payment Routes
@api_router.post("/payments/subscribe")
async def create_subscription_checkout(
    subscription_data: SubscriptionRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if subscription_data.plan_type not in SUBSCRIPTION_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    creator = await db.creators.find_one({"id": subscription_data.creator_id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    # Check if already subscribed
    existing_subscription = await db.subscriptions.find_one({
        "user_id": current_user.id,
        "creator_id": subscription_data.creator_id,
        "status": "active"
    })
    if existing_subscription:
        raise HTTPException(status_code=400, detail="Already subscribed to this creator")
    
    # Create Stripe checkout session
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    package = SUBSCRIPTION_PACKAGES[subscription_data.plan_type]
    success_url = f"{host_url}/subscription-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/creators/{subscription_data.creator_id}"
    
    checkout_request = CheckoutSessionRequest(
        amount=package["price"],
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "type": "subscription",
            "user_id": current_user.id,
            "creator_id": subscription_data.creator_id,
            "plan_type": subscription_data.plan_type
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Store payment transaction
    transaction = PaymentTransaction(
        user_id=current_user.id,
        creator_id=subscription_data.creator_id,
        amount=package["price"],
        transaction_type="subscription",
        stripe_session_id=session.session_id,
        metadata={
            "plan_type": subscription_data.plan_type,
            "creator_id": subscription_data.creator_id
        }
    )
    await db.payment_transactions.insert_one(transaction.dict())
    
    return {"checkout_url": session.url, "session_id": session.session_id}

@api_router.post("/payments/tip")
async def create_tip_checkout(
    tip_data: TipRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    creator = await db.creators.find_one({"id": tip_data.creator_id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    if tip_data.amount < 1.0:
        raise HTTPException(status_code=400, detail="Minimum tip amount is $1.00")
    
    # Create Stripe checkout session
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    success_url = f"{host_url}/tip-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/creators/{tip_data.creator_id}"
    
    checkout_request = CheckoutSessionRequest(
        amount=tip_data.amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "type": "tip",
            "user_id": current_user.id,
            "creator_id": tip_data.creator_id,
            "message": tip_data.message or ""
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Store payment transaction
    transaction = PaymentTransaction(
        user_id=current_user.id,
        creator_id=tip_data.creator_id,
        amount=tip_data.amount,
        transaction_type="tip",
        stripe_session_id=session.session_id,
        metadata={
            "message": tip_data.message,
            "creator_id": tip_data.creator_id
        }
    )
    await db.payment_transactions.insert_one(transaction.dict())
    
    return {"checkout_url": session.url, "session_id": session.session_id}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, current_user: User = Depends(get_current_user)):
    # Get payment transaction
    transaction = await db.payment_transactions.find_one({"stripe_session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check Stripe status
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    status_response = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction status if changed
    if status_response.payment_status != transaction['payment_status']:
        await db.payment_transactions.update_one(
            {"stripe_session_id": session_id},
            {"$set": {"payment_status": status_response.payment_status}}
        )
        
        # Process successful payment
        if status_response.payment_status == "paid" and transaction['payment_status'] != "paid":
            await process_successful_payment(transaction, status_response.metadata)
    
    return {
        "payment_status": status_response.payment_status,
        "amount": status_response.amount_total / 100,  # Convert from cents
        "currency": status_response.currency
    }

async def process_successful_payment(transaction: dict, metadata: dict):
    if transaction['transaction_type'] == 'subscription':
        # Create subscription
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        subscription = Subscription(
            user_id=transaction['user_id'],
            creator_id=transaction['creator_id'],
            plan_type=transaction['metadata']['plan_type'],
            status="active",
            expires_at=expires_at
        )
        await db.subscriptions.insert_one(subscription.dict())
        
        # Update creator follower count
        await db.creators.update_one(
            {"id": transaction['creator_id']},
            {"$inc": {"follower_count": 1}}
        )

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    try:
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Process webhook event
        if webhook_response.event_type == "checkout.session.completed":
            transaction = await db.payment_transactions.find_one({
                "stripe_session_id": webhook_response.session_id
            })
            
            if transaction and transaction['payment_status'] != "paid":
                await db.payment_transactions.update_one(
                    {"stripe_session_id": webhook_response.session_id},
                    {"$set": {"payment_status": "paid"}}
                )
                
                await process_successful_payment(transaction, webhook_response.metadata)
        
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

# Dashboard Routes
@api_router.get("/dashboard/creator/stats")
async def get_creator_stats(current_user: User = Depends(get_current_user)):
    creator = await db.creators.find_one({"user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=403, detail="User is not a creator")
    
    # Get statistics
    total_subscribers = await db.subscriptions.count_documents({
        "creator_id": creator['id'],
        "status": "active"
    })
    
    total_revenue = await db.payment_transactions.aggregate([
        {"$match": {
            "creator_id": creator['id'],
            "payment_status": "paid"
        }},
        {"$group": {
            "_id": None,
            "total": {"$sum": "$amount"}
        }}
    ]).to_list(1)
    
    revenue = total_revenue[0]['total'] if total_revenue else 0
    
    return {
        "subscriber_count": total_subscribers,
        "content_count": creator['content_count'],
        "total_revenue": revenue,
        "follower_count": creator['follower_count']
    }

# Include router
app.include_router(api_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()