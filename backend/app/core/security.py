import hmac
import hashlib
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.session import get_db

# HTTP Bearer authentication scheme
security_bearer = HTTPBearer(auto_error=False)


def generate_node_id() -> str:
    """Generate a unique, cryptographically random node identifier."""
    rand_hex = secrets.token_hex(8)
    return f"node_{rand_hex}"


def generate_node_token() -> str:
    """Generate a high-entropy secret token for node authentication."""
    rand_bytes = secrets.token_urlsafe(32)
    return f"cnx_tok_{rand_bytes}"


def hash_node_token(token: str) -> str:
    """
    Hash node authentication token using HMAC-SHA256 with the backend secret.
    Stores only the hash in PostgreSQL so raw tokens cannot be leaked from DB dumps.
    """
    return hmac.new(
        settings.NODE_TOKEN_SECRET.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_node_token(plain_token: str, token_hash: str) -> bool:
    """Constant-time verification of node token."""
    expected_hash = hash_node_token(plain_token)
    return hmac.compare_digest(expected_hash, token_hash)


def mask_token(token: Optional[str]) -> str:
    """Safely redact tokens for structured logging."""
    if not token:
        return "[NONE]"
    if len(token) <= 8:
        return "[REDACTED]"
    return f"{token[:7]}...[REDACTED]"


async def get_current_authenticated_node(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency to authenticate the node from Authorization: Bearer <token>.
    """
    from backend.app.models.node import Node  # Local import to avoid circular dependencies

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credential required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = credentials.credentials.strip()
    calculated_hash = hash_node_token(raw_token)

    query = select(Node).where(Node.token_hash == calculated_hash)
    result = await db.execute(query)
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid node credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if node.status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Node is suspended",
        )

    return node


def verify_node_ownership(target_node_id: str, current_node) -> None:
    """
    Authorization check: ensure that Node A cannot view/modify Node B.
    """
    if current_node.node_id != target_node_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized: Authenticated node ({current_node.node_id}) cannot access target node ({target_node_id})",
        )
