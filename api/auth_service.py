"""
Authentication service
Handles user registration, login, password hashing, and JWT token generation
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import jwt
from loguru import logger
from fastapi import HTTPException, status
from open_notebook.database.repository import repo_query, repo_update
from open_notebook.domain.user import (
    User, UserCreate, UserLogin, UserResponse, Token,
    PasswordResetRequest, PasswordReset
)


# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
RESET_TOKEN_EXPIRE_MINUTES = 60  # 1 hour


class AuthService:
    """
    Service for handling authentication operations
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    @staticmethod
    def create_access_token(user_id: str, username: str) -> str:
        """Create a JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": user_id,
            "username": username,
            "exp": expire
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    async def signup(self, user_data: UserCreate) -> Token:
        """Register a new user"""
        # Check if username already exists
        existing_user = await repo_query(
            "SELECT * FROM users WHERE username = $username LIMIT 1",
            {"username": user_data.username}
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = await repo_query(
            "SELECT * FROM users WHERE email = $email LIMIT 1",
            {"email": user_data.email}
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash the password
        password_hash = self.hash_password(user_data.password)
        
        # Insert into database
        result = await repo_query(
            """
            CREATE users CONTENT {
                username: $username,
                email: $email,
                password_hash: $password_hash,
                created_at: time::now(),
                updated_at: time::now(),
                is_active: true
            }
            """,
            {
                "username": user_data.username,
                "email": user_data.email,
                "password_hash": password_hash
            }
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        created_user = result[0]
        user_id = created_user["id"]
        
        # Generate JWT token
        access_token = self.create_access_token(user_id, user_data.username)
        
        # Return token and user info
        # SurrealDB returns datetime objects directly, not strings
        created_at = created_user["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        user_response = UserResponse(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            created_at=created_at,
            is_active=True
        )
        
        return Token(access_token=access_token, user=user_response)
    
    async def login(self, credentials: UserLogin) -> Token:
        """Authenticate a user and return a token"""
        # Find user by username
        result = await repo_query(
            "SELECT * FROM users WHERE username = $username LIMIT 1",
            {"username": credentials.username}
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        user_data = result[0]
        
        # Verify password
        if not self.verify_password(credentials.password, user_data["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if account is active
        if not user_data.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Update last login time - using raw query without parameters
        user_id = user_data["id"]
        # Extract table and id from the full record ID (e.g., "users:abc123")
        if ":" in user_id:
            table_name, record_id = user_id.split(":", 1)
        else:
            table_name = "users"
            record_id = user_id
        
        # Use repo_update which handles the UPDATE query properly
        from open_notebook.database.repository import repo_update
        await repo_update(table_name, record_id, {"last_login": datetime.utcnow()})
        
        # Generate JWT token
        access_token = self.create_access_token(user_data["id"], user_data["username"])
        
        # Return token and user info
        # SurrealDB returns datetime objects directly, not strings
        created_at = user_data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        last_login = user_data.get("last_login")
        if last_login and isinstance(last_login, str):
            last_login = datetime.fromisoformat(last_login)
        
        user_response = UserResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            created_at=created_at,
            is_active=user_data["is_active"],
            last_login=last_login
        )
        
        return Token(access_token=access_token, user=user_response)
    
    async def get_current_user(self, token: str) -> UserResponse:
        """Get current user from JWT token"""
        payload = self.decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Fetch user from database
        # Use direct record ID in query (not as parameter)
        result = await repo_query(
            f"SELECT * FROM {user_id}"
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Debug: Check what we got
        logger.debug(f"get_current_user result type: {type(result)}, value: {result}")
        
        # Handle if result is a string (error message)
        if isinstance(result, str):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {result}"
            )
        
        user_data = result[0]
        
        # Handle datetime conversion
        created_at = user_data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        last_login = user_data.get("last_login")
        if last_login and isinstance(last_login, str):
            last_login = datetime.fromisoformat(last_login)
        
        return UserResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            created_at=created_at,
            is_active=user_data["is_active"],
            last_login=last_login
        )

    
    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure random token for password reset"""
        return secrets.token_urlsafe(32)
    
    async def request_password_reset(self, request: PasswordResetRequest) -> dict:
        """
        Request a password reset token
        In production, this should send an email with the reset link
        For now, we'll return the token directly (for development/testing)
        """
        # Find user by email
        result = await repo_query(
            "SELECT * FROM users WHERE email = $email LIMIT 1",
            {"email": request.email}
        )
        
        if not result:
            # Don't reveal if email exists or not (security best practice)
            logger.info(f"Password reset requested for non-existent email: {request.email}")
            return {
                "message": "If the email exists, a password reset link has been sent"
            }
        
        user_data = result[0]
        user_id = user_data["id"]
        
        # Generate reset token
        reset_token = self.generate_reset_token()
        reset_token_expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
        
        # Store reset token in database
        # Extract table and id from the full record ID
        if ":" in user_id:
            table_name, record_id = user_id.split(":", 1)
        else:
            table_name = "users"
            record_id = user_id
        
        await repo_update(
            table_name,
            record_id,
            {
                "reset_token": reset_token,
                "reset_token_expires": reset_token_expires
            }
        )
        
        logger.info(f"Password reset token generated for user: {user_data['username']}")
        
        # TODO: In production, send email with reset link
        # For now, return the token directly (development only)
        return {
            "message": "If the email exists, a password reset link has been sent",
            "reset_token": reset_token,  # Remove this in production!
            "expires_in_minutes": RESET_TOKEN_EXPIRE_MINUTES
        }
    
    async def reset_password(self, reset_data: PasswordReset) -> dict:
        """Reset password using a valid reset token"""
        # Find user with this reset token
        result = await repo_query(
            "SELECT * FROM users WHERE reset_token = $reset_token LIMIT 1",
            {"reset_token": reset_data.token}
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        user_data = result[0]
        
        # Check if token has expired
        reset_token_expires = user_data.get("reset_token_expires")
        if not reset_token_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Convert to datetime if it's a string and make it timezone-aware
        if isinstance(reset_token_expires, str):
            reset_token_expires = datetime.fromisoformat(reset_token_expires)
        
        # Make current time timezone-aware if reset_token_expires is timezone-aware
        from datetime import timezone
        current_time = datetime.now(timezone.utc) if reset_token_expires.tzinfo else datetime.utcnow()
        
        if current_time > reset_token_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Hash the new password
        new_password_hash = self.hash_password(reset_data.new_password)
        
        # Update password and clear reset token
        user_id = user_data["id"]
        if ":" in user_id:
            table_name, record_id = user_id.split(":", 1)
        else:
            table_name = "users"
            record_id = user_id
        
        await repo_update(
            table_name,
            record_id,
            {
                "password_hash": new_password_hash,
                "reset_token": None,
                "reset_token_expires": None,
                "updated_at": datetime.utcnow()
            }
        )
        
        logger.info(f"Password reset successful for user: {user_data['username']}")
        
        return {
            "message": "Password has been reset successfully"
        }
