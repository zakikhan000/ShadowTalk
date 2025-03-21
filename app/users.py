from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from .database import get_db
from .models import User
import datetime
import base64

router = APIRouter()

# ---------------------------
# Pydantic Models for Responses
# ---------------------------
class UserResponse(BaseModel):
    user_id: int
    email: str
    username: str
    phone_number: str
    name: str
    age: int
    gender: str
    anonymous_name: str
    country: str
    city: str
    hide_info: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    profile_image: str  # Base64-encoded string

    class Config:
        from_attributes = True


# ---------------------------
# Helper Functions
# ---------------------------
def user_to_response(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "username": user.username,
        "phone_number": user.phone_number,
        "name": user.name,
        "age": user.age,
        "gender": user.gender,
        "anonymous_name": user.anonymous_name,
        "country": user.country,
        "city": user.city,
        "hide_info": user.hide_info,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "profile_image": base64.b64encode(user.profile_image).decode('utf-8') if user.profile_image else "",
    }


# ---------------------------
# API Endpoints
# ---------------------------

# GET: Retrieve all non-deleted users
@router.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_deleted == False).all()
    return [user_to_response(user) for user in users]


# GET: Retrieve a user by email
@router.get("/users/{email}", response_model=UserResponse)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_response(user)


# POST: Create a new user with optional profile image upload
@router.post("/users", response_model=UserResponse)
async def create_user(
        email: EmailStr = Form(...),
        username: str = Form(...),
        phone_number: str = Form(...),
        password_hash: str = Form(...),
        name: str = Form(None),
        age: int = Form(0),
        gender: str = Form(None),
        anonymous_name: str = Form(None),
        country: str = Form(None),
        city: str = Form(None),
        hide_info: bool = Form(False),
        profile_image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with given email or username already exists")

    image_data = await profile_image.read() if profile_image else None

    new_user = User(
        email=email,
        username=username,
        password_hash=password_hash,
        phone_number=phone_number,
        name=name or "Anonymous User",
        age=age,
        gender=gender or "Unknown",
        anonymous_name=anonymous_name or "HiddenUser",
        country=country or "Unknown",
        city=city or "Unknown",
        hide_info=hide_info,
        profile_image=image_data
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return user_to_response(new_user)


# PUT: Update a user by email
@router.put("/users/{email}", response_model=UserResponse)
def update_user(email: str, user_update: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in user_update.items():
        if field == "profile_image" and value is not None:
            try:
                value = base64.b64decode(value)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid profile_image data")
        setattr(user, field, value)

    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user_to_response(user)


# DELETE: Soft delete a user by email
@router.delete("/users/{email}")
def delete_user(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_deleted = True
    user.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"detail": "User soft-deleted successfully"}
