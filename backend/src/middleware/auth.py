"""
Authentication middleware for JWT token validation
Flow: Request -> Extract Token -> Validate with Auth Server -> Set User Context
"""

from typing import Optional

import httpx
from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from src.config.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
}


async def auth_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Middleware to validate JWT tokens with auth server."""
    
    # Skip auth for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Skip auth for public paths
    if any(request.url.path.startswith(path) for path in PUBLIC_PATHS):
        return await call_next(request)
    
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header", path=request.url.path)
        response = Response(content="Unauthorized", status_code=401)
        # Add CORS headers for error responses
        origin = request.headers.get("Origin")
        if origin and origin in settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    
    token = auth_header.split(" ")[1]
    
    # Validate token with OAuth 2.0 userinfo endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.AUTH_SERVER_URL}/api/oauth/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # Store user data in request state
                request.state.user = user_data
                logger.info("User authenticated", user_id=user_data.get("id"))
            else:
                logger.warning("Token validation failed", status=response.status_code)
                response = Response(content="Unauthorized", status_code=401)
                # Add CORS headers for error responses
                origin = request.headers.get("Origin")
                if origin and origin in settings.CORS_ORIGINS:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                return response
                
    except Exception as e:
        logger.error("Auth server error", error=str(e))
        response = Response(content="Authentication service unavailable", status_code=503)
        # Add CORS headers for error responses
        origin = request.headers.get("Origin")
        if origin and origin in settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    
    # Process request
    response = await call_next(request)
    return response


def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from request state."""
    return getattr(request.state, "user", None)