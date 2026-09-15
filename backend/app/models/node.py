import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Float,
    DateTime,
    JSON,
    func,
    Uuid,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from backend.app.db.base import Base


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    node_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    owner_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    sdk_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    device_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="REGISTERING",
        index=True,
    )
    health_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="HEALTHY",
        index=True,
    )
    capabilities: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    observed_public_ip: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    download_mbps: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    upload_mbps: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_nodes_status_last_heartbeat", "status", "last_heartbeat_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "node_id": self.node_id,
            "owner_id": self.owner_id,
            "platform": self.platform,
            "sdk_version": self.sdk_version,
            "device_name": self.device_name,
            "status": self.status,
            "health_status": self.health_status,
            "capabilities": self.capabilities,
            "observed_public_ip": self.observed_public_ip,
            "download_mbps": self.download_mbps,
            "upload_mbps": self.upload_mbps,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
