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

# API Configuration
API = os.environ.get('API_BASE_URL', 'http://localhost:8000/api')

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
    avatar_url: Optional[str] = None
    welcome_video_url: Optional[str] = None
    welcome_message: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    custom_sections: Optional[List[Dict[str, Any]]] = None
    subscription_tiers: Optional[List[Dict[str, Any]]] = None
    profile_settings: Optional[Dict[str, Any]] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    total_likes: int = 0
    content_stats: Optional[Dict[str, int]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CreatorCreate(BaseModel):
    display_name: str
    bio: str
    category: str
    tags: List[str] = []
    subscription_price: float

class CreatorUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    subscription_price: Optional[float] = None
    welcome_message: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    custom_sections: Optional[List[Dict[str, Any]]] = None
    subscription_tiers: Optional[List[Dict[str, Any]]] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None

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

def encrypt_message(content: str) -> tuple[str, str]:
    """Encrypt message content and return encrypted content and key"""
    fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    encrypted_content = fernet.encrypt(content.encode())
    return base64.b64encode(encrypted_content).decode(), ENCRYPTION_KEY

def decrypt_message(encrypted_content: str, key: str) -> str:
    """Decrypt message content"""
    try:
        fernet = Fernet(key.encode() if isinstance(key, str) else key)
        encrypted_bytes = base64.b64decode(encrypted_content.encode())
        decrypted_content = fernet.decrypt(encrypted_bytes)
        return decrypted_content.decode()
    except:
        return "[Message could not be decrypted]"

def generate_file_hash(file_content: bytes) -> str:
    """Generate SHA-256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if isinstance(doc, dict):
        return {k: serialize_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc

async def can_send_message(sender_id: str, recipient_id: str) -> tuple[bool, str]:
    """Check if sender can send message to recipient"""
    # Check if conversation exists and is not blocked
    conversation = await db.conversations.find_one({
        "$or": [
            {"creator_id": recipient_id, "fan_id": sender_id},
            {"creator_id": sender_id, "fan_id": recipient_id}
        ]
    })
    
    if conversation and conversation.get('is_blocked'):
        return False, "Conversation is blocked"
    
    # Check if recipient is a creator and has messaging restrictions
    creator = await db.creators.find_one({"user_id": recipient_id})
    if creator:
        settings = await db.conversation_settings.find_one({"creator_id": creator['id']})
        if settings:
            if not settings.get('allow_messages', True):
                return False, "Creator is not accepting messages"
            
            if sender_id in settings.get('blocked_users', []):
                return False, "You are blocked by this creator"
            
            if settings.get('require_subscription', False):
                # Check if sender is subscribed
                subscription = await db.subscriptions.find_one({
                    "user_id": sender_id,
                    "creator_id": creator['id'],
                    "status": "active"
                })
                if not subscription:
                    return False, "Subscription required to send messages"
    
    return True, "OK"

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

@api_router.get("/creators/{creator_id}", response_model=Dict)
async def get_creator(creator_id: str):
    # Try to find by creator ID first
    creator = await db.creators.find_one({"id": creator_id})
    
    # If not found, try to find by username (for SEO-friendly URLs)
    if not creator:
        user = await db.users.find_one({"username": creator_id})
        if user and user['is_creator']:
            creator = await db.creators.find_one({"user_id": user['id']})
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    # Get user info
    user = await db.users.find_one({"id": creator['user_id']})
    
    # Get public content (free samples and previews)
    public_content = await db.content.find({
        "creator_id": creator['id'],
        "is_premium": False,
        "is_ppv": False
    }).sort("created_at", -1).limit(10).to_list(length=None)
    
    # Get content statistics
    content_stats = await db.content.aggregate([
        {"$match": {"creator_id": creator['id']}},
        {"$group": {
            "_id": "$content_type",
            "count": {"$sum": 1}
        }}
    ]).to_list(length=None)
    
    stats_dict = {stat['_id']: stat['count'] for stat in content_stats}
    
    # Get recent activity metrics
    recent_content_count = await db.content.count_documents({
        "creator_id": creator['id'],
        "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}
    })
    
    # Calculate total likes
    total_likes = await db.content.aggregate([
        {"$match": {"creator_id": creator['id']}},
        {"$group": {"_id": None, "total_likes": {"$sum": "$likes"}}}
    ]).to_list(1)
    
    total_likes_count = total_likes[0]['total_likes'] if total_likes else 0
    
    # Enhanced creator response
    enhanced_creator = {
        **creator,
        "user_info": {
            "username": user['username'],
            "full_name": user['full_name'],
            "avatar_url": user.get('avatar_url'),
            "created_at": user['created_at']
        },
        "public_content": [Content(**content) for content in public_content],
        "content_stats": stats_dict,
        "recent_activity": {
            "posts_this_month": recent_content_count,
            "posting_frequency": "Regular" if recent_content_count > 4 else "Occasional"
        },
        "total_likes": total_likes_count,
        "profile_completion": calculate_profile_completion(creator)
    }
    
    return enhanced_creator

def calculate_profile_completion(creator: dict) -> int:
    """Calculate profile completion percentage"""
    fields = [
        creator.get('display_name'),
        creator.get('bio'),
        creator.get('banner_url'),
        creator.get('avatar_url'),
        creator.get('welcome_message'),
        creator.get('social_links'),
        creator.get('tags')
    ]
    
    completed = sum(1 for field in fields if field)
    return int((completed / len(fields)) * 100)

@api_router.put("/creators/{creator_id}")
async def update_creator_profile(
    creator_id: str,
    creator_data: CreatorUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update creator profile"""
    creator = await db.creators.find_one({"id": creator_id, "user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found or access denied")
    
    update_data = {k: v for k, v in creator_data.dict().items() if v is not None}
    
    if update_data:
        await db.creators.update_one(
            {"id": creator_id},
            {"$set": update_data}
        )
    
    return {"message": "Profile updated successfully"}

@api_router.post("/creators/{creator_id}/upload-banner")
async def upload_creator_banner(
    creator_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload creator banner image"""
    creator = await db.creators.find_one({"id": creator_id, "user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found or access denied")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Read and validate file size (max 5MB)
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    
    # Store file in GridFS
    file_id = await fs.upload_from_stream(
        f"banner_{creator_id}_{file.filename}",
        io.BytesIO(file_content),
        metadata={
            "content_type": file.content_type,
            "creator_id": creator_id,
            "type": "banner"
        }
    )
    
    # Update creator with banner URL
    banner_url = f"{API}/creators/{creator_id}/banner/{file_id}"
    await db.creators.update_one(
        {"id": creator_id},
        {"$set": {"banner_url": banner_url}}
    )
    
    return {"message": "Banner uploaded successfully", "banner_url": banner_url}

@api_router.get("/creators/{creator_id}/banner/{file_id}")
async def get_creator_banner(creator_id: str, file_id: str):
    """Get creator banner image"""
    try:
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        file_data = await grid_out.read()
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=grid_out.metadata.get('content_type', 'image/jpeg'),
            headers={"Cache-Control": "max-age=86400"}  # Cache for 24 hours
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Banner not found")

@api_router.post("/creators/{creator_id}/upload-welcome-video")
async def upload_welcome_video(
    creator_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload creator welcome video"""
    creator = await db.creators.find_one({"id": creator_id, "user_id": current_user.id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found or access denied")
    
    # Validate file type
    if not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="Only video files are allowed")
    
    # Read and validate file size (max 50MB)
    file_content = await file.read()
    if len(file_content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Store file in GridFS
    file_id = await fs.upload_from_stream(
        f"welcome_video_{creator_id}_{file.filename}",
        io.BytesIO(file_content),
        metadata={
            "content_type": file.content_type,
            "creator_id": creator_id,
            "type": "welcome_video"
        }
    )
    
    # Update creator with video URL
    video_url = f"{API}/creators/{creator_id}/welcome-video/{file_id}"
    await db.creators.update_one(
        {"id": creator_id},
        {"$set": {"welcome_video_url": video_url}}
    )
    
    return {"message": "Welcome video uploaded successfully", "video_url": video_url}

@api_router.get("/creators/{creator_id}/welcome-video/{file_id}")
async def get_welcome_video(creator_id: str, file_id: str):
    """Get creator welcome video"""
    try:
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        file_data = await grid_out.read()
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=grid_out.metadata.get('content_type', 'video/mp4'),
            headers={"Cache-Control": "max-age=3600"}  # Cache for 1 hour
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Welcome video not found")

@api_router.get("/creators/{creator_id}/public-feed")
async def get_creator_public_feed(
    creator_id: str,
    skip: int = 0,
    limit: int = 20
):
    """Get creator's public feed with free samples"""
    creator = await db.creators.find_one({"id": creator_id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    # Get public content
    public_content = await db.content.find({
        "creator_id": creator_id,
        "is_premium": False,
        "is_ppv": False
    }).sort("created_at", -1).skip(skip).limit(limit).to_list(length=None)
    
    # Get premium content previews (with watermarks)
    premium_previews = await db.content.find({
        "creator_id": creator_id,
        "$or": [{"is_premium": True}, {"is_ppv": True}]
    }).sort("created_at", -1).limit(5).to_list(length=None)
    
    # Add watermark indicator to premium previews
    for preview in premium_previews:
        preview['is_preview'] = True
        ppv_price = preview.get('ppv_price', 0)
        if preview['is_premium']:
            preview['preview_text'] = "Vista previa - Premium"
        else:
            preview['preview_text'] = f"Vista previa - PPV ${ppv_price}"
    
    return {
        "public_content": [Content(**content) for content in public_content],
        "premium_previews": [Content(**preview) for preview in premium_previews],
        "total_public": len(public_content),
        "has_premium": len(premium_previews) > 0
    }

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

# Messaging Routes
@api_router.get("/conversations", response_model=List[Dict])
async def get_conversations(current_user: User = Depends(get_current_user)):
    """Get all conversations for the current user"""
    conversations = await db.conversations.find({
        "$or": [
            {"creator_id": current_user.id},
            {"fan_id": current_user.id}
        ]
    }).sort("last_message_at", -1).to_list(length=None)
    
    # Enrich conversations with participant info and last message
    enriched_conversations = []
    for conv in conversations:
        # Get other participant info
        other_user_id = conv['fan_id'] if conv['creator_id'] == current_user.id else conv['creator_id']
        other_user = await db.users.find_one({"id": other_user_id})
        
        # Get creator info if needed
        creator_info = None
        if conv['creator_id'] != current_user.id:
            creator_info = await db.creators.find_one({"user_id": conv['creator_id']})
        
        # Get last message
        last_message = await db.messages.find_one(
            {"conversation_id": conv['id']},
            sort=[("created_at", -1)]
        )
        
        # Count unread messages
        unread_count = await db.messages.count_documents({
            "conversation_id": conv['id'],
            "sender_id": {"$ne": current_user.id},
            "is_read": False
        })
        
        enriched_conversations.append({
            **conv,
            "other_user": {
                "id": other_user['id'],
                "username": other_user['username'],
                "full_name": other_user['full_name'],
                "avatar_url": other_user.get('avatar_url'),
                "is_creator": other_user['is_creator']
            },
            "creator_info": creator_info,
            "last_message": last_message,
            "unread_count": unread_count
        })
    
    return enriched_conversations

@api_router.post("/conversations")
async def create_conversation(
    recipient_id: str,
    current_user: User = Depends(get_current_user)
):
    """Create or get existing conversation with another user"""
    if recipient_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")
    
    # Check if recipient exists
    recipient = await db.users.find_one({"id": recipient_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Determine creator and fan roles
    creator_id = recipient_id if recipient['is_creator'] else current_user.id
    fan_id = current_user.id if recipient['is_creator'] else recipient_id
    
    # Check if conversation already exists
    existing_conv = await db.conversations.find_one({
        "creator_id": creator_id,
        "fan_id": fan_id
    })
    
    if existing_conv:
        return {"conversation_id": existing_conv['id'], "exists": True}
    
    # Check if can send message
    can_send, reason = await can_send_message(current_user.id, recipient_id)
    if not can_send:
        raise HTTPException(status_code=403, detail=reason)
    
    # Create new conversation
    conversation = Conversation(
        creator_id=creator_id,
        fan_id=fan_id
    )
    
    await db.conversations.insert_one(conversation.dict())
    
    return {"conversation_id": conversation.id, "exists": False}

@api_router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get messages from a conversation"""
    # Verify user is part of conversation
    conversation = await db.conversations.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if current_user.id not in [conversation['creator_id'], conversation['fan_id']]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get messages
    messages = await db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=None)
    
    # Decrypt messages if encrypted
    decrypted_messages = []
    for msg in messages:
        if msg.get('is_encrypted') and msg.get('encryption_key'):
            if msg.get('content'):
                msg['content'] = decrypt_message(msg['content'], msg['encryption_key'])
        
        # Remove encryption key from response
        if 'encryption_key' in msg:
            del msg['encryption_key']
        
        decrypted_messages.append(msg)
    
    # Mark messages as read
    await db.messages.update_many(
        {
            "conversation_id": conversation_id,
            "sender_id": {"$ne": current_user.id},
            "is_read": False
        },
        {
            "$set": {
                "is_read": True,
                "read_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {"messages": list(reversed(decrypted_messages))}

@api_router.post("/messages/send")
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Send a message in a conversation"""
    # Verify conversation exists and user is part of it
    conversation = await db.conversations.find_one({"id": message_data.conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if current_user.id not in [conversation['creator_id'], conversation['fan_id']]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if conversation is blocked
    if conversation.get('is_blocked'):
        raise HTTPException(status_code=403, detail="Conversation is blocked")
    
    # Determine recipient
    recipient_id = conversation['fan_id'] if current_user.id == conversation['creator_id'] else conversation['creator_id']
    
    # Check if can send message
    can_send, reason = await can_send_message(current_user.id, recipient_id)
    if not can_send:
        raise HTTPException(status_code=403, detail=reason)
    
    # Determine sender type
    sender_type = "creator" if current_user.id == conversation['creator_id'] else "fan"
    
    # Encrypt message if requested
    content = message_data.content
    encryption_key = None
    is_encrypted = False
    
    if content and len(content) > 0:
        # Always encrypt sensitive messages
        content, encryption_key = encrypt_message(content)
        is_encrypted = True
    
    # Set auto-destruct time if specified
    auto_destruct_at = None
    if message_data.auto_destruct_minutes:
        auto_destruct_at = datetime.now(timezone.utc) + timedelta(minutes=message_data.auto_destruct_minutes)
    
    # Create message
    message = Message(
        conversation_id=message_data.conversation_id,
        sender_id=current_user.id,
        sender_type=sender_type,
        message_type=message_data.message_type,
        content=content,
        is_ppv=message_data.is_ppv,
        ppv_price=message_data.ppv_price,
        ppv_preview=message_data.ppv_preview,
        is_tip=message_data.is_tip,
        tip_amount=message_data.tip_amount,
        is_encrypted=is_encrypted,
        encryption_key=encryption_key,
        auto_destruct_at=auto_destruct_at
    )
    
    await db.messages.insert_one(message.dict())
    
    # Update conversation last message time
    await db.conversations.update_one(
        {"id": message_data.conversation_id},
        {"$set": {"last_message_at": datetime.now(timezone.utc)}}
    )
    
    # Prepare message for real-time sending (without encryption key)
    message_for_send = message.dict()
    if message_for_send.get('encryption_key'):
        del message_for_send['encryption_key']
    
    # Decrypt content for real-time sending
    if is_encrypted and encryption_key:
        message_for_send['content'] = decrypt_message(content, encryption_key)
    
    # Send real-time message
    await manager.broadcast_to_conversation(
        {
            "type": "new_message",
            "message": message_for_send
        },
        [conversation['creator_id'], conversation['fan_id']]
    )
    
    return {"message": "Message sent successfully", "message_id": message.id}

@api_router.post("/messages/upload")
async def upload_message_file(
    conversation_id: str = Form(...),
    message_type: str = Form(...),
    is_ppv: bool = Form(False),
    ppv_price: Optional[float] = Form(None),
    ppv_preview: Optional[str] = Form(None),
    auto_destruct_minutes: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload file and send as message"""
    # Verify conversation
    conversation = await db.conversations.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if current_user.id not in [conversation['creator_id'], conversation['fan_id']]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate file type
    allowed_types = {
        'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'video': ['video/mp4', 'video/quicktime', 'video/x-msvideo'],
        'audio': ['audio/mpeg', 'audio/wav', 'audio/ogg']
    }
    
    if message_type not in allowed_types or file.content_type not in allowed_types[message_type]:
        raise HTTPException(status_code=400, detail="Invalid file type for message type")
    
    # Read and validate file
    file_content = await file.read()
    if len(file_content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Store file in GridFS
    file_id = await fs.upload_from_stream(
        file.filename,
        io.BytesIO(file_content),
        metadata={
            "content_type": file.content_type,
            "message_type": message_type,
            "uploaded_by": current_user.id,
            "file_hash": generate_file_hash(file_content)
        }
    )
    
    # Determine sender type
    sender_type = "creator" if current_user.id == conversation['creator_id'] else "fan"
    
    # Set auto-destruct time if specified
    auto_destruct_at = None
    if auto_destruct_minutes:
        auto_destruct_at = datetime.now(timezone.utc) + timedelta(minutes=auto_destruct_minutes)
    
    # Create message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        sender_type=sender_type,
        message_type=message_type,
        file_path=str(file_id),
        file_type=file.content_type,
        file_size=len(file_content),
        is_ppv=is_ppv,
        ppv_price=ppv_price,
        ppv_preview=ppv_preview,
        auto_destruct_at=auto_destruct_at
    )
    
    await db.messages.insert_one(message.dict())
    
    # Update conversation last message time
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"last_message_at": datetime.now(timezone.utc)}}
    )
    
    # Send real-time message
    await manager.broadcast_to_conversation(
        {
            "type": "new_message",
            "message": message.dict()
        },
        [conversation['creator_id'], conversation['fan_id']]
    )
    
    return {"message": "File uploaded and sent successfully", "message_id": message.id}

@api_router.get("/messages/{message_id}/file")
async def get_message_file(message_id: str, current_user: User = Depends(get_current_user)):
    """Get file from message"""
    message = await db.messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Verify user is part of conversation
    conversation = await db.conversations.find_one({"id": message['conversation_id']})
    if current_user.id not in [conversation['creator_id'], conversation['fan_id']]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if message is PPV and user has paid
    if message.get('is_ppv') and message['sender_id'] != current_user.id:
        payment = await db.message_payments.find_one({
            "message_id": message_id,
            "payer_id": current_user.id,
            "payment_status": "paid"
        })
        if not payment:
            raise HTTPException(status_code=402, detail="Payment required to view this content")
    
    # Get file from GridFS
    try:
        file_id = ObjectId(message['file_path'])
        grid_out = await fs.open_download_stream(file_id)
        file_data = await grid_out.read()
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=message['file_type'],
            headers={"Content-Disposition": f"inline; filename={grid_out.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")

@api_router.post("/messages/{message_id}/pay")
async def pay_for_message(
    message_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Pay for PPV message"""
    message = await db.messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if not message.get('is_ppv'):
        raise HTTPException(status_code=400, detail="Message is not pay-per-view")
    
    if message['sender_id'] == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot pay for your own message")
    
    # Check if already paid
    existing_payment = await db.message_payments.find_one({
        "message_id": message_id,
        "payer_id": current_user.id,
        "payment_status": "paid"
    })
    
    if existing_payment:
        raise HTTPException(status_code=400, detail="Already paid for this message")
    
    # Create Stripe checkout session
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    success_url = f"{host_url}/messages/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/messages/{message_id}"
    
    checkout_request = CheckoutSessionRequest(
        amount=message['ppv_price'],
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "type": "message_ppv",
            "message_id": message_id,
            "payer_id": current_user.id,
            "creator_id": message['sender_id']
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Store payment record
    payment = MessagePayment(
        message_id=message_id,
        payer_id=current_user.id,
        amount=message['ppv_price'],
        stripe_session_id=session.session_id
    )
    await db.message_payments.insert_one(payment.dict())
    
    # Store transaction record
    transaction = PaymentTransaction(
        user_id=current_user.id,
        creator_id=message['sender_id'],
        amount=message['ppv_price'],
        transaction_type="message_ppv",
        stripe_session_id=session.session_id,
        metadata={
            "message_id": message_id
        }
    )
    await db.payment_transactions.insert_one(transaction.dict())
    
    return {"checkout_url": session.url, "session_id": session.session_id}

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            message_data = json.loads(data)
            
            # Echo back for connection testing
            await manager.send_personal_message({
                "type": "pong",
                "data": message_data
            }, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)

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