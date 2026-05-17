from sqlalchemy import String, Boolean, Integer, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    VENDOR = "vendor"
    CUSTOMER = "customer"

class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.CUSTOMER)

    # Relationships to profiles
    admin_profile: Mapped["AdminProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    vendor_profile: Mapped["VendorProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    customer_profile: Mapped["CustomerProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")

class AdminProfile(Base):
    __tablename__ = "admin_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True)
    permissions: Mapped[str] = mapped_column(String, default="all")
    
    user: Mapped["User"] = relationship(back_populates="admin_profile")

class VendorProfile(Base):
    __tablename__ = "vendor_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True)
    company_name: Mapped[str] = mapped_column(String, nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String, default="basic")
    api_key: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    
    user: Mapped["User"] = relationship(back_populates="vendor_profile")

class CustomerProfile(Base):
    __tablename__ = "customer_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    preferences: Mapped[dict] = mapped_column(JSON, default={})
    
    user: Mapped["User"] = relationship(back_populates="customer_profile")
