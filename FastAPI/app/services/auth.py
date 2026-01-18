from sqlalchemy.orm import Session
from app.utils.security import create_access_token, create_refresh_token, decode_token
from app.services.user import authenticate_user, get_user_by_id
from app.schemas.auth import Token
from app.models.user import User


def login_user(db: Session, email: str, password: str) -> Token | None:
    """
    Authenticate user and return access and refresh tokens.
    """
    user = authenticate_user(db, email, password)
    
    if not user:
        return None
    
    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user
    )


def refresh_access_token(db: Session, refresh_token: str) -> Token | None:
    """
    Validate refresh token and return new access token.
    """
    payload = decode_token(refresh_token)
    
    if not payload:
        return None
    
    # Verify token type
    if payload.get("type") != "refresh":
        return None
    
    # Get user ID
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # Verify user exists and is active
    user = get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        return None
    
    # Create new tokens
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )
