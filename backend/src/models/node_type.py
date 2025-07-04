"""
NodeType model
Flow: Node type definitions for the flow designer
"""

from datetime import datetime
from typing import Any

from sqlalchemy import String, DateTime, Text, Boolean, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class NodeType(Base):
    """NodeType model - represents available node types in the flow designer."""
    
    __tablename__ = "node_types"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Node category (e.g., "llm", "input", "output", "logic", "data")
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Node configuration schema (JSON Schema)
    config_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Default configuration values
    default_config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # UI metadata
    icon: Mapped[str | None] = mapped_column(String(50))  # Icon name
    color: Mapped[str | None] = mapped_column(String(7))  # Hex color
    
    # Input/Output port definitions
    input_ports: Mapped[list[dict]] = mapped_column(JSON, default=list)
    output_ports: Mapped[list[dict]] = mapped_column(JSON, default=list)
    
    # Node behavior
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Implementation details
    implementation_class: Mapped[str] = mapped_column(String(255), nullable=False)
    
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
    
    def __repr__(self) -> str:
        return f"<NodeType(id={self.id}, name={self.name}, category={self.category})>"