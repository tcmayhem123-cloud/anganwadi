"""
Authentication Endpoints: Login, Me, Demo Accounts, Account Lockout.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User, UserRole, JurisdictionType
from ..schemas.all_schemas import LoginRequest, LoginResponse, UserResponse
from ..auth.security import verify_password, create_access_token
from ..auth.rbac import get_current_user, handle_failed_login, reset_failed_login, log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    # Check lockout
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.locked_until and user.locked_until > now:
        minutes_left = int((user.locked_until - now).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to consecutive failed attempts. Please retry in {minutes_left} minute(s)."
        )

    # Verify password
    if not verify_password(req.password, user.password_hash):
        failed_count, is_locked = handle_failed_login(user, db)
        log_audit_event(db, user, "LOGIN_FAILED", "User", str(user.id), after_val={"failed_attempts": failed_count})
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account has been locked for 15 minutes due to 5 consecutive failed login attempts."
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid username or password. Attempt {failed_count}/5 before temporary lockout."
        )

    # Successful login
    reset_failed_login(user, db)
    log_audit_event(db, user, "LOGIN_SUCCESS", "User", str(user.id))

    token = create_access_token(data={
        "sub": user.username,
        "role": user.role.value,
        "jurisdiction_type": user.jurisdiction_type.value,
        "jurisdiction_id": user.jurisdiction_id
    })

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.get("/demo-users")
def get_demo_users(db: Session = Depends(get_db)):
    """Provides sample pre-seeded test accounts for instant role demonstration."""
    users = db.query(User).all()
    return [
        {
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role.value,
            "jurisdiction": f"{u.jurisdiction_type.value} #{u.jurisdiction_id or 'ALL'}",
            "sample_password": "password123"
        }
        for u in users
    ]
