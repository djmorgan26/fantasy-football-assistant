from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_database
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate
from app.schemas.auth import Token
from app.core.auth import auth_service, get_current_active_user
from app.models.user import User
from app.utils.encryption import ESPNCredentialManager

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await auth_service.register_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        # Store ESPN credentials if provided
        if user_data.espn_s2 or user_data.espn_swid:
            user_id = result["user"]["id"]
            user = await auth_service.get_user_by_id(db, user_id)
            
            if user_data.espn_s2:
                user.espn_s2_encrypted = ESPNCredentialManager.encrypt_espn_s2(user_data.espn_s2)
            if user_data.espn_swid:
                user.espn_swid_encrypted = ESPNCredentialManager.encrypt_espn_swid(user_data.espn_swid)
            
            await db.commit()
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_database)
):
    try:
        result = await auth_service.login_user(
            db=db,
            email=login_data.email,
            password=login_data.password
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
):
    try:
        # Update basic profile information
        updated_user = await auth_service.update_user_profile(
            db=db,
            user_id=current_user.id,
            full_name=user_update.full_name,
            current_password=user_update.current_password,
            new_password=user_update.new_password
        )
        
        # Update ESPN credentials if provided
        if user_update.espn_s2 is not None:
            if user_update.espn_s2:
                updated_user.espn_s2_encrypted = ESPNCredentialManager.encrypt_espn_s2(user_update.espn_s2)
            else:
                updated_user.espn_s2_encrypted = None
        
        if user_update.espn_swid is not None:
            if user_update.espn_swid:
                updated_user.espn_swid_encrypted = ESPNCredentialManager.encrypt_espn_swid(user_update.espn_swid)
            else:
                updated_user.espn_swid_encrypted = None
        
        await db.commit()
        await db.refresh(updated_user)
        
        return UserResponse.from_orm(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )