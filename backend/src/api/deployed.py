"""
Dynamic API Router for deployed flows
Flow: External Request -> Route to deployment -> Execute flow -> Return response
"""

from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.core.database import get_db
from src.services.deployment_service import deployment_service

router = APIRouter(prefix="/api/deployed", tags=["deployed-apis"])


class ApiResponse(BaseModel):
    """Standard API response format."""
    success: bool
    data: Dict[str, Any]
    message: str = ""
    execution_id: str = ""


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def execute_deployed_api(
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> ApiResponse:
    """Execute a deployed flow via dynamic API endpoint."""
    
    # Construct full endpoint path
    endpoint_path = f"/{path}"
    
    # Get request data based on method
    if request.method in ["POST", "PUT"]:
        try:
            request_data = await request.json()
        except Exception:
            request_data = {}
    else:
        # For GET/DELETE, use query parameters
        request_data = dict(request.query_params)
    
    try:
        # Execute the deployed flow
        result = await deployment_service.execute_deployed_flow(
            endpoint_path=endpoint_path,
            request_data=request_data,
            request=request,
            db=db
        )
        
        return ApiResponse(
            success=True,
            data=result,
            message="Flow executed successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )