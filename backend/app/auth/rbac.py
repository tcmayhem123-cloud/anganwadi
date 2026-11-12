"""
Role-Based Access Control (RBAC), Jurisdiction Scoping, and Audit Logging.
Complies with FR-AUTH-02, FR-AUTH-03, FR-AUTH-04.
"""
from datetime import datetime, timedelta, timezone
import json
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from .security import decode_access_token
from ..models.user import User, UserRole, JurisdictionType
from ..models.hierarchy import AWC, Sector, Block, District
from ..models.audit import AuditLog

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Extracts and verifies current user from JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject"
        )
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated"
        )
    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory that restricts endpoint to specific roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.ADMIN:
            return current_user  # Admin has access to all operations
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires one of roles {[r.value for r in allowed_roles]}, user has {current_user.role.value}"
            )
        return current_user
    return role_checker


def get_user_accessible_awc_ids(user: User, db: Session) -> Optional[List[int]]:
    """Returns list of AWC IDs accessible by this user.
    Returns None if user has GLOBAL access (Admin).
    """
    if user.role == UserRole.ADMIN or user.jurisdiction_type == JurisdictionType.GLOBAL:
        return None  # Unrestricted

    if user.jurisdiction_type == JurisdictionType.AWC:
        return [user.jurisdiction_id] if user.jurisdiction_id else []

    elif user.jurisdiction_type == JurisdictionType.SECTOR:
        awcs = db.query(AWC.id).filter(AWC.sector_id == user.jurisdiction_id).all()
        return [a[0] for a in awcs]

    elif user.jurisdiction_type == JurisdictionType.BLOCK:
        sectors = db.query(Sector.id).filter(Sector.block_id == user.jurisdiction_id).all()
        sector_ids = [s[0] for s in sectors]
        awcs = db.query(AWC.id).filter(AWC.sector_id.in_(sector_ids)).all()
        return [a[0] for a in awcs]

    elif user.jurisdiction_type == JurisdictionType.DISTRICT:
        blocks = db.query(Block.id).filter(Block.district_id == user.jurisdiction_id).all()
        block_ids = [b[0] for b in blocks]
        sectors = db.query(Sector.id).filter(Sector.block_id.in_(block_ids)).all()
        sector_ids = [s[0] for s in sectors]
        awcs = db.query(AWC.id).filter(AWC.sector_id.in_(sector_ids)).all()
        return [a[0] for a in awcs]

    return []


def assert_awc_access(user: User, awc_id: int, db: Session):
    """Enforces that the user has permission to access the target AWC."""
    allowed_ids = get_user_accessible_awc_ids(user, db)
    if allowed_ids is not None and awc_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: AWC #{awc_id} is outside user's jurisdiction ({user.jurisdiction_type.value}:{user.jurisdiction_id})"
        )


def handle_failed_login(user: User, db: Session) -> Tuple[int, bool]:
    """FR-AUTH-03: Increments failed login count and locks account if threshold reached."""
    user.failed_attempts = (user.failed_attempts or 0) + 1
    locked = False
    if user.failed_attempts >= settings.LOCKOUT_MAX_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
        locked = True
    db.commit()
    return user.failed_attempts, locked


def reset_failed_login(user: User, db: Session):
    """Resets failed attempts upon successful authentication."""
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()


def log_audit_event(
    db: Session,
    user: Optional[User],
    action: str,
    entity: str,
    entity_id: Optional[str] = None,
    before_val: Optional[dict] = None,
    after_val: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """FR-AUTH-04, NFR-11: Writes an immutable audit entry."""
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "SYSTEM",
        role=user.role.value if user else "SYSTEM",
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        before_val=json.dumps(before_val, default=str) if before_val else None,
        after_val=json.dumps(after_val, default=str) if after_val else None,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(entry)
    db.commit()
