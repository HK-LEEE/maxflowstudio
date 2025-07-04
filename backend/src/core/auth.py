"""
┌──────────────────────────────────────────────────────────────┐
│                    Authentication Flow                      │
│                                                              │
│  [Request] → [Middleware] → [Extract] → [DB] → [User]      │
│      ↓          ↓            ↓         ↓       ↓           │
│   HTTP요청    인증미들웨어    사용자추출   DB조회  사용자반환  │
│                                                              │
│  Auth Flow: Token → Validate → User Data → DB Sync → User  │
│  Error Handling: Invalid Token → HTTP 401 → Client         │
└──────────────────────────────────────────────────────────────┘

Authentication module for MAX Flowstudio
Flow: HTTP request → Middleware auth → User extraction → Database sync → User object
"""

from typing import Optional
from fastapi import Depends, HTTPException, Request, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import json
from urllib.parse import parse_qs

from ..models.user import User
from .database import get_db

logger = structlog.get_logger()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from request.
    
    Authentication Flow:
    1. extract_user_from_request() → Get user data from middleware
    2. lookup_or_create_user() → Find/create user in database
    3. validate_user_permissions() → Check user status
    4. return_user_object() → Provide User model instance
    
    Args:
        request: FastAPI request object (populated by auth middleware)
        db: Database session dependency
        
    Returns:
        User: Authenticated user model instance
        
    Raises:
        HTTPException: 401 if user not authenticated or invalid
    """
    # Extract user data from request state (set by auth middleware)
    user_data = getattr(request.state, 'user', None)
    
    if not user_data:
        logger.warning("No user data found in request state")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Get user ID from OAuth userinfo (sub field)
    user_id = user_data.get('sub') or user_data.get('id') or user_data.get('user_id')
    if not user_id:
        logger.warning("No user ID found in user data", user_data=user_data)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data"
        )
    
    # Look up user in database
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    
    # If user doesn't exist in local DB, create from OAuth userinfo data
    if not user:
        logger.info("Creating new user from OAuth userinfo", user_id=user_id)
        
        # Extract group info from OAuth userinfo groups array
        groups = user_data.get('groups', [])
        group_id = groups[0].get('id') if groups else None
        
        user = User(
            id=user_id,
            email=user_data.get('email', ''),
            username=user_data.get('display_name', user_data.get('username', '')),
            full_name=user_data.get('real_name', user_data.get('full_name', '')),
            is_active=user_data.get('is_active', True),
            is_superuser=user_data.get('is_admin', user_data.get('is_superuser', False)),
            group_id=group_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Validate user is active
    if not user.is_active:
        logger.warning("Inactive user attempted access", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    logger.debug("User authenticated successfully", 
                user_id=user_id, 
                username=user.username)
    
    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current superuser.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Superuser model instance
        
    Raises:
        HTTPException: 403 if user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning("Non-superuser attempted admin access", 
                      user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return current_user


# Optional: User info extraction for compatibility
def get_user_from_request(request: Request) -> Optional[dict]:
    """
    Extract user data from request state (set by middleware).
    
    Args:
        request: FastAPI request object
        
    Returns:
        dict: User data if available, None otherwise
    """
    return getattr(request.state, 'user', None)


async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession
) -> Optional[User]:
    """
    Get current authenticated user from WebSocket connection.
    
    WebSocket doesn't have the same request lifecycle as HTTP,
    so we need to extract auth info from query params or headers.
    
    Args:
        websocket: FastAPI WebSocket object
        db: Database session
        
    Returns:
        User: Authenticated user model instance or None
    """
    try:
        # Try to get token from query params first
        query_params = parse_qs(websocket.scope.get("query_string", b"").decode())
        token = query_params.get("token", [None])[0]
        
        if not token:
            # Try to get from headers
            headers = dict(websocket.headers)
            auth_header = headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            logger.warning("No token provided for WebSocket auth")
            return None
            
        # Validate token with auth server
        try:
            import httpx
            from ..config.settings import get_settings
            settings = get_settings()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.AUTH_SERVER_URL}/api/oauth/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5.0,
                )
                
                if response.status_code != 200:
                    logger.warning("Token validation failed for WebSocket", status=response.status_code)
                    return None
                    
                user_data = response.json()
                user_id = user_data.get('sub') or user_data.get('id') or user_data.get('user_id')
                
                if not user_id:
                    logger.warning("No user ID in OAuth userinfo response for WebSocket")
                    return None
                    
                # Look up user in database
                result = await db.execute(select(User).filter(User.id == user_id))
                user = result.scalar_one_or_none()
                
                # If user doesn't exist in local DB, create from OAuth userinfo data
                if not user:
                    logger.info("Creating new user from WebSocket OAuth userinfo", user_id=user_id)
                    
                    # Extract group info from OAuth userinfo groups array
                    groups = user_data.get('groups', [])
                    group_id = groups[0].get('id') if groups else None
                    
                    user = User(
                        id=user_id,
                        email=user_data.get('email', ''),
                        username=user_data.get('display_name', user_data.get('username', '')),
                        full_name=user_data.get('real_name', user_data.get('full_name', '')),
                        is_active=user_data.get('is_active', True),
                        is_superuser=user_data.get('is_admin', user_data.get('is_superuser', False)),
                        group_id=group_id
                    )
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)
                
                # Validate user is active
                if not user.is_active:
                    logger.warning("Inactive user attempted WebSocket access", user_id=user_id)
                    return None
                    
                logger.debug("WebSocket user authenticated successfully", user_id=user_id)
                return user
                
        except Exception as auth_error:
            logger.error("Auth server error for WebSocket", error=str(auth_error))
            return None
        
    except Exception as e:
        logger.error("WebSocket authentication failed", error=str(e))
        return None