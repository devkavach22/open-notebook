"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from open_notebook.domain.user import UserResponse
from api.auth_service import AuthService


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """Dependency to get the current authenticated user"""
    auth_service = AuthService()
    token = credentials.credentials
    user = await auth_service.get_current_user(token)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_user_id(
    current_user: UserResponse = Depends(get_current_user)
) -> str:
    """Dependency to get just the user ID"""
    return current_user.id
