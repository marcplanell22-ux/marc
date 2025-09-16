from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, File, UploadFile, Form
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
fs = AsyncIOMotorGridFSBucket(db)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

# Stripe Configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

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
    transaction_type: str  # 'subscription', 'tip', 'ppv'
    stripe_session_id: str
    payment_status: str = "pending"
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TipRequest(BaseModel):
    creator_id: str
    amount: float
    message: Optional[str] = None

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

# Payment Routes
@api_router.post("/payments/subscribe")
async def create_subscription_checkout(
    creator_id: str,
    plan_type: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if plan_type not in SUBSCRIPTION_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    creator = await db.creators.find_one({"id": creator_id})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    # Check if already subscribed
    existing_subscription = await db.subscriptions.find_one({
        "user_id": current_user.id,
        "creator_id": creator_id,
        "status": "active"
    })
    if existing_subscription:
        raise HTTPException(status_code=400, detail="Already subscribed to this creator")
    
    # Create Stripe checkout session
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    package = SUBSCRIPTION_PACKAGES[plan_type]
    success_url = f"{host_url}/subscription-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/creators/{creator_id}"
    
    checkout_request = CheckoutSessionRequest(
        amount=package["price"],
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "type": "subscription",
            "user_id": current_user.id,
            "creator_id": creator_id,
            "plan_type": plan_type
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Store payment transaction
    transaction = PaymentTransaction(
        user_id=current_user.id,
        creator_id=creator_id,
        amount=package["price"],
        transaction_type="subscription",
        stripe_session_id=session.session_id,
        metadata={
            "plan_type": plan_type,
            "creator_id": creator_id
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