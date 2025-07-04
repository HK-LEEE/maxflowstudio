"""
API Deployment model
Flow: Flow -> API Deployment -> Public Endpoint
"""

from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, DateTime, Text, Boolean, ForeignKey, func, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from .flow import Flow
    from .user import User
    from .api_key import ApiKey


class DeploymentStatus(str, Enum):
    """API deployment status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class ApiDeployment(Base):
    """API Deployment model - represents deployed flow as REST API."""
    
    __tablename__ = "api_deployments"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Associated flow
    flow_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("flows.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Owner
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # API metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    endpoint_path: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    # Deployment configuration
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    status: Mapped[DeploymentStatus] = mapped_column(
        SQLEnum(DeploymentStatus), 
        default=DeploymentStatus.PENDING
    )
    
    # API settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit: Mapped[int | None] = mapped_column()  # requests per minute
    
    # Input/Output schema
    input_schema: Mapped[dict | None] = mapped_column(JSON)
    output_schema: Mapped[dict | None] = mapped_column(JSON)
    
    # Usage tracking
    total_requests: Mapped[int] = mapped_column(default=0)
    last_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Deployment metadata
    deployment_config: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    flow: Mapped["Flow"] = relationship("Flow")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<ApiDeployment(id={self.id}, name={self.name}, status={self.status})>"