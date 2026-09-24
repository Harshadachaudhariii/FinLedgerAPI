import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from app.config import settings
from app.utils.logger import logger
import time
from collections import defaultdict

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
# --- NEW: Token Blocklist & Rate Limiting ---
token_blocklist = set()
login_attempts = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_ATTEMPTS = 5

def add_token_to_blocklist(token: str):
    token_blocklist.add(token)

def is_token_blocked(token: str) -> bool:
    return token in token_blocklist

def check_rate_limit(username: str) -> bool:
    current_time = time.time()
    login_attempts[username] = [t for t in login_attempts[username] if current_time - t < RATE_LIMIT_WINDOW]
    if len(login_attempts[username]) >= MAX_ATTEMPTS:
        return False
    login_attempts[username].append(current_time)
    return True
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
        logger.info("Authentication attempt started")
        # Check if token is blocked
        if is_token_blocked(token):
            logger.warning("Authentication failed: token has been revoked")
            raise HTTPException(status_code=401,detail="Token has been revoked")
        logger.info("Token is not blocked")
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        logger.info("JWT token decoded successfully")
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Authentication failed: token payload missing 'sub'")
            raise HTTPException(status_code=401,detail="Invalid token payload")
        logger.info("User authenticated successfully: %s", user_id)
        return user_id
    except jwt.ExpiredSignatureError:
        logger.warning("Authentication failed: token has expired")
        raise HTTPException(status_code=401,detail="Token has expired")
    except jwt.InvalidTokenError:
        logger.warning("Authentication failed: invalid token")
        raise HTTPException(status_code=401,detail="Invalid token")