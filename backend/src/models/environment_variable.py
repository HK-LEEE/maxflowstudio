"""
Environment Variable Model
Unified system for managing all types of configuration and sensitive data
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from src.core.database import Base


class EnvironmentVariableType(PyEnum):
    """Environment variable types"""
    STRING = "string"
    SECRET = "secret"  # Encrypted storage
    URL = "url"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class EnvironmentVariableCategory(PyEnum):
    """Environment variable categories for organized management"""
    DATABASE = "database"           # DB connection settings
    AUTHENTICATION = "authentication"  # JWT, auth settings
    LLM_API = "llm_api"            # AI model API settings
    INFRASTRUCTURE = "infrastructure"  # Redis, RabbitMQ, etc.
    APPLICATION = "application"     # App basic settings
    CUSTOM = "custom"              # User-defined variables


class EnvironmentVariableScope(PyEnum):
    """Environment variable scope levels"""
    SYSTEM = "system"      # System-wide (managed by admin)
    USER = "user"          # User-specific
    WORKSPACE = "workspace"  # Workspace-specific


class EnvironmentVariable(Base):
    """Unified Environment Variable model for all configuration and sensitive data"""
    
    __tablename__ = "environment_variables"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Variable identification
    key = Column(String(255), nullable=False, index=True)
    value = Column(Text, nullable=True)  # Can be encrypted for secrets
    description = Column(Text, nullable=True)
    
    # Variable metadata
    var_type = Column(Enum(EnvironmentVariableType), default=EnvironmentVariableType.STRING)
    category = Column(Enum(EnvironmentVariableCategory), default=EnvironmentVariableCategory.CUSTOM)
    scope = Column(Enum(EnvironmentVariableScope), default=EnvironmentVariableScope.USER)
    
    # Security settings
    is_secret = Column(Boolean, default=False)  # Whether value should be encrypted
    is_encrypted = Column(Boolean, default=False)  # Whether value is currently encrypted
    is_system_managed = Column(Boolean, default=False)  # System vs user managed
    
    # Ownership and scope (nullable for system-wide variables)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=True)
    
    # Ordering and grouping
    sort_order = Column(Integer, default=0)  # For custom ordering within categories
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="environment_variables")
    workspace = relationship("Workspace", back_populates="environment_variables")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<EnvironmentVariable {self.key}={self.get_display_value()} ({self.category.value})>"
    
    def get_display_value(self) -> str:
        """Get display value (masked for secrets)"""
        if self.is_secret and self.value:
            if self.var_type == EnvironmentVariableType.URL:
                # For URLs, show protocol and domain structure
                return "https://••••••••.••••••••/••••••••"
            else:
                # For other secrets, show fixed mask
                return "••••••••••••••••••••••••••••••••"
        return self.value or ""
    
    def get_actual_value(self) -> str:
        """Get actual value (decrypted if needed)"""
        if not self.value:
            return ""
            
        if self.is_encrypted:
            try:
                from src.services.encryption_service import encryption_service
                return encryption_service.decrypt(self.value)
            except Exception:
                # If decryption fails, return empty string for security
                return ""
        
        return self.value
    
    def set_value(self, value: str) -> None:
        """Set value (encrypt if needed)"""
        if not value:
            self.value = value
            self.is_encrypted = False
            return
            
        if self.is_secret:
            try:
                from src.services.encryption_service import encryption_service
                encrypted_value, is_encrypted = encryption_service.encrypt_if_needed(
                    value, should_encrypt=True
                )
                self.value = encrypted_value
                self.is_encrypted = is_encrypted
            except Exception:
                # If encryption fails, store as plain text but log warning
                self.value = value
                self.is_encrypted = False
        else:
            self.value = value
            self.is_encrypted = False
    
    def is_system_variable(self) -> bool:
        """Check if this is a system-managed variable"""
        return self.is_system_managed or self.scope == EnvironmentVariableScope.SYSTEM
    
    def can_be_modified_by_user(self, user_id: str, is_admin: bool = False) -> bool:
        """Check if variable can be modified by given user"""
        # System variables can only be modified by admins
        if self.is_system_variable() and not is_admin:
            return False
            
        # User variables can be modified by owner or admin
        if self.scope == EnvironmentVariableScope.USER:
            return self.user_id == user_id or is_admin
            
        # Workspace variables can be modified by workspace members or admin
        if self.scope == EnvironmentVariableScope.WORKSPACE:
            # TODO: Check workspace membership
            return self.user_id == user_id or is_admin
            
        return is_admin
    
    def get_category_display_name(self) -> str:
        """Get human-readable category name"""
        category_names = {
            EnvironmentVariableCategory.DATABASE: "데이터베이스",
            EnvironmentVariableCategory.AUTHENTICATION: "인증",
            EnvironmentVariableCategory.LLM_API: "AI 모델 API",
            EnvironmentVariableCategory.INFRASTRUCTURE: "인프라",
            EnvironmentVariableCategory.APPLICATION: "애플리케이션",
            EnvironmentVariableCategory.CUSTOM: "사용자 정의",
        }
        return category_names.get(self.category, self.category.value)
    
    def get_scope_display_name(self) -> str:
        """Get human-readable scope name"""
        scope_names = {
            EnvironmentVariableScope.SYSTEM: "시스템",
            EnvironmentVariableScope.USER: "사용자",
            EnvironmentVariableScope.WORKSPACE: "워크스페이스",
        }
        return scope_names.get(self.scope, self.scope.value)