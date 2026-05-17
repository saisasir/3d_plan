from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole, AdminProfile, VendorProfile, CustomerProfile
from app.core.security import get_password_hash, verify_password

class AuthService:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    @staticmethod
    async def create_user(db: AsyncSession, *, full_name: str, email: str, password: str, role: UserRole = UserRole.CUSTOMER) -> User:
        db_obj = User(
            full_name=full_name,
            email=email,
            hashed_password=get_password_hash(password),
            role=role
        )
        db.add(db_obj)
        await db.flush()  # Get the ID before committing
        
        # Create specialized profile based on role
        if role == UserRole.ADMIN:
            profile = AdminProfile(user_id=db_obj.id)
            db.add(profile)
        elif role == UserRole.VENDOR:
            profile = VendorProfile(user_id=db_obj.id)
            db.add(profile)
        else:
            profile = CustomerProfile(user_id=db_obj.id)
            db.add(profile)
            
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def authenticate(db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        user = await AuthService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
