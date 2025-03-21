import datetime
import base64
from sqlalchemy import Column, Integer, String, Boolean, DateTime, LargeBinary
from pydantic import BaseModel, EmailStr
from app.database import Base

# Constants for Dummy Default Values
DEFAULT_NAME = "Anonymous User"
DEFAULT_GENDER = "Unknown"
DEFAULT_ANONYMOUS_NAME = "HiddenUser"
DEFAULT_COUNTRY = "Unknown"
DEFAULT_CITY = "Unknown"
DEFAULT_PROFILE_IMAGE = b'default_profile.jpg'

# SQLAlchemy User Model
class User(Base):
    __tablename__ = "Users"
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), default=DEFAULT_NAME)
    age = Column(Integer, default=0)
    gender = Column(String(10), default=DEFAULT_GENDER)
    anonymous_name = Column(String(100), default=DEFAULT_ANONYMOUS_NAME)
    country = Column(String(100), default=DEFAULT_COUNTRY)
    city = Column(String(100), default=DEFAULT_CITY)
    profile_image = Column(LargeBinary, default=DEFAULT_PROFILE_IMAGE)
    hide_info = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# Pydantic Schemas
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

class UserUpdate(BaseModel):
    username: str | None = None
    password_hash: str | None = None
    phone_number: str | None = None
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    anonymous_name: str | None = None
    country: str | None = None
    city: str | None = None
    hide_info: bool | None = None
    profile_image: str | None = None  # Expect Base64-encoded string if updating image

# Helper Functions
def user_to_response(user: User) -> dict:
    """Converts a User instance to a response dictionary."""
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
        "profile_image": (
            base64.b64encode(user.profile_image).decode("utf-8")
            if user.profile_image and user.profile_image != DEFAULT_PROFILE_IMAGE else ""
        ),
    }

def user_to_post_response(user: User) -> dict:
    """
    Converts a User instance to a response dictionary for the POST endpoint.
    Dummy default values are returned as empty strings.
    """
    return {
        "user_id": user.user_id,
        "email": user.email,
        "username": user.username,
        "phone_number": user.phone_number,
        "name": "" if user.name == DEFAULT_NAME else user.name,
        "age": user.age,
        "gender": "" if user.gender == DEFAULT_GENDER else user.gender,
        "anonymous_name": "" if user.anonymous_name == DEFAULT_ANONYMOUS_NAME else user.anonymous_name,
        "country": "" if user.country == DEFAULT_COUNTRY else user.country,
        "city": "" if user.city == DEFAULT_CITY else user.city,
        "hide_info": user.hide_info,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "profile_image": (
            "" if user.profile_image == DEFAULT_PROFILE_IMAGE else base64.b64encode(user.profile_image).decode("utf-8")
        ),
    }
