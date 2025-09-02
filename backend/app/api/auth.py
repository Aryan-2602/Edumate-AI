from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth
from app.database import get_db, User
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize Firebase Admin SDK
try:
    if not firebase_admin._apps:
        if settings.firebase_private_key:
            # Use service account credentials
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "private_key_id": settings.firebase_private_key_id,
                "private_key": settings.firebase_private_key.replace('\\n', '\n'),
                "client_email": settings.firebase_client_email,
                "client_id": settings.firebase_client_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.firebase_client_email}"
            })
            firebase_admin.initialize_app(cred)
        else:
            # Use default credentials (GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app()
except Exception as e:
    logger.warning(f"Firebase Admin SDK initialization failed: {e}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Verify Firebase token and return current user"""
    try:
        # Verify Firebase token
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        
        # Get user UID
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        display_name = decoded_token.get('name', '')
        
        # Check if user exists in database
        user = db.query(User).filter(User.id == uid).first()
        
        if not user:
            # Create new user
            user = User(
                id=uid,
                email=email,
                display_name=display_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {uid}")
        
        return user
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh user session (Firebase handles token refresh automatically)"""
    return {
        "message": "Token refreshed successfully",
        "user_id": current_user.id
    }


@router.delete("/logout")
async def logout():
    """Logout user (client-side token invalidation)"""
    return {"message": "Logged out successfully"}


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth"}
