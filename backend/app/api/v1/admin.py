from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.api.deps import RoleChecker
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.api.v1.auth import UserOut, UserCreate

router = APIRouter()

# Protect all routes in this router for Admin only
admin_required = RoleChecker([UserRole.ADMIN])

@router.get("/users", response_model=List[UserOut])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required)
) -> Any:
    """
    Retrieve all users. Admin only.
    """
    result = await db.execute(
        select(User).options(
            selectinload(User.admin_profile),
            selectinload(User.vendor_profile),
            selectinload(User.customer_profile)
        )
    )
    users = result.scalars().all()
    
    # Format response to include profile snippets
    formatted_users = []
    for user in users:
        profile_data = {}
        if user.role == UserRole.ADMIN and user.admin_profile:
            profile_data = {"permissions": user.admin_profile.permissions}
        elif user.role == UserRole.VENDOR and user.vendor_profile:
            profile_data = {
                "company_name": user.vendor_profile.company_name,
                "tier": user.vendor_profile.subscription_tier
            }
        elif user.role == UserRole.CUSTOMER and user.customer_profile:
            profile_data = {"phone": user.customer_profile.phone}
            
        formatted_users.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "profile": profile_data
        })
    return formatted_users

@router.post("/users", response_model=UserOut)
async def create_user_by_admin(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(admin_required)
) -> Any:
    """
    Create a new user with a specific role. Admin only.
    """
    user = await AuthService.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = await AuthService.create_user(
        db, 
        full_name=user_in.full_name, 
        email=user_in.email, 
        password=user_in.password,
        role=user_in.role
    )
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: int,
    current_user: User = Depends(admin_required)
) -> None:
    """
    Delete a user. Admin only.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return None
