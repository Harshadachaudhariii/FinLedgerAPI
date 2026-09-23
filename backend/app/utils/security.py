import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from app.config import settings
from app.utils.logger import logger

# 1. Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def hash_password(password: str) -> str:
    logger.info("Hashing password for user authentication")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.info("Password verification result: %s", is_valid)
        return is_valid
    except Exception:
        logger.exception("Password verification failed")
        return False

# 2. JWT Functions (Notice we now use settings.SECRET_KEY)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.info("Access token created successfully for user claim")
        return encoded_jwt
    except Exception:
        logger.exception("Failed to create access token")
        raise

# 4. Function to CHECK the token (The Dependency)

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        # Decode the token using the secret key
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            logger.warning("Token payload missing 'sub' claim")
            raise HTTPException(status_code=401, detail="Invalid token payload")
        logger.info("Authenticated user: %s", user_id)
        return user_id

    except jwt.ExpiredSignatureError:
        logger.warning("Authentication failed: expired token")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        logger.warning("Authentication failed: invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")