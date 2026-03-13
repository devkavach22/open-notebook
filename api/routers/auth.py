"""
Authentication API routes
Provides endpoints for signup, login, password reset, and getting current user info
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from open_notebook.domain.user import (
    UserCreate, UserLogin, Token, UserResponse,
    PasswordResetRequest, PasswordReset
)
from api.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


def get_auth_service() -> AuthService:
    """Dependency to get auth service instance"""
    return AuthService()


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account
    
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (minimum 8 characters)
    
    Returns JWT token and user information
    """
    return await auth_service.signup(user_data)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login with username and password
    
    - **username**: Your username
    - **password**: Your password
    
    Returns JWT token and user information
    """
    return await auth_service.login(credentials)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get current authenticated user information
    
    Requires: Bearer token in Authorization header
    """
    token = credentials.credentials
    return await auth_service.get_current_user(token)


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client should delete token)
    
    Since we're using JWT, logout is handled client-side by deleting the token
    """
    return {"message": "Logged out successfully"}


@router.get("/status")
async def auth_status():
    """
    Check if authentication is enabled
    
    Returns whether the API requires authentication
    """
    # For now, authentication is always enabled with JWT
    return {"auth_enabled": True}



@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request a password reset token
    
    - **email**: Email address of the account
    
    Returns a success message. In production, this would send an email.
    For development, the token is returned in the response.
    """
    return await auth_service.request_password_reset(request)


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Reset password using a valid reset token
    
    - **token**: The reset token received via email (or from forgot-password endpoint in dev)
    - **new_password**: New password (minimum 8 characters)
    
    Returns success message if password was reset
    """
    return await auth_service.reset_password(reset_data)
