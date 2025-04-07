import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import sqlite3
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings (store these in environment variables in production)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-for-development-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

class User(BaseModel):
    id: int
    username: str
    email: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

def verify_password(plain_password, hashed_password):
    """Verify the password against the hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Generate password hash"""
    return pwd_context.hash(password)

def create_user(username: str, email: str, password: str, role: str = "user") -> bool:
    """Create a new user in the database"""
    try:
        conn = sqlite3.connect('db/memory.sqlite')
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            conn.close()
            return False
        
        # Create new user
        hashed_password = get_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, role)
        )
        conn.commit()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user and return user data if valid"""
    try:
        conn = sqlite3.connect('db/memory.sqlite')
        cursor = conn.cursor()
        
        # Get user data
        cursor.execute(
            "SELECT id, username, email, password_hash, role FROM users WHERE username = ?", 
            (username,)
        )
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            return None
        
        user_id, username, email, password_hash, role = user_data
        
        if not verify_password(password, password_hash):
            return None
        
        return User(id=user_id, username=username, email=email, role=role)
    
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_from_token(token: str) -> Optional[User]:
    """Get user information from a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        
        if username is None:
            return None
        
        token_data = TokenData(username=username, role=role)
        
        conn = sqlite3.connect('db/memory.sqlite')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, email, role FROM users WHERE username = ?", 
            (token_data.username,)
        )
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            return None
        
        user_id, username, email, role = user_data
        return User(id=user_id, username=username, email=email, role=role)
    
    except JWTError:
        return None
    except Exception as e:
        print(f"Error getting user from token: {e}")
        return None