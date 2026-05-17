import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import engine
from app.models.user import User, UserRole, AdminProfile, VendorProfile, CustomerProfile
from app.models.scene import Scene
from app.core.security import get_password_hash

async def seed_data():
    async_session = AsyncSession(engine)
    async with async_session as db:
        print("[SEED] Seeding Proficient Database...")

        # 1. Create Super Admin
        admin_email = "admin@flux3d.com"
        result = await db.execute(select(User).where(User.email == admin_email))
        admin = result.scalars().first()
        if not admin:
            admin = User(
                full_name="System Administrator",
                email=admin_email,
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                is_superuser=True
            )
            db.add(admin)
            await db.flush()
            db.add(AdminProfile(user_id=admin.id, permissions="all"))
            print("[SUCCESS] Admin Created: admin@flux3d.com / admin123")

        # 2. Create Premium Vendor
        vendor_email = "design_studio@vendor.com"
        result = await db.execute(select(User).where(User.email == vendor_email))
        vendor = result.scalars().first()
        if not vendor:
            vendor = User(
                full_name="Elite Interiors Studio",
                email=vendor_email,
                hashed_password=get_password_hash("vendor123"),
                role=UserRole.VENDOR
            )
            db.add(vendor)
            await db.flush()
            db.add(VendorProfile(
                user_id=vendor.id, 
                company_name="Elite Interiors Ltd", 
                subscription_tier="pro",
                api_key="FLUX_PRO_778899"
            ))
            print("[SUCCESS] Vendor Created: design_studio@vendor.com / vendor123")

        # 3. Create Sample Customer
        customer_email = "john.doe@gmail.com"
        result = await db.execute(select(User).where(User.email == customer_email))
        customer = result.scalars().first()
        if not customer:
            customer = User(
                full_name="John Doe",
                email=customer_email,
                hashed_password=get_password_hash("customer123"),
                role=UserRole.CUSTOMER
            )
            db.add(customer)
            await db.flush()
            db.add(CustomerProfile(
                user_id=customer.id, 
                phone="+1 555 0199",
                preferences={"style": "minimalist", "favorite_color": "indigo"}
            ))
            print("[SUCCESS] Customer Created: john.doe@gmail.com / customer123")

        # 4. Create Sample Scene for Vendor
        if vendor and customer:
            sample_scene = Scene(
                name="Luxury Penthouse Suite",
                vendor_id=vendor.id,
                customer_id=customer.id,
                data={
                    "metadata": {"name": "Luxury Penthouse Suite"},
                    "rooms": [
                        {"id": "r1", "type": "class_1", "polygon": [[0,0], [10,0], [10,10], [0,10]]}
                    ],
                    "walls": [
                        {"points": [[0,0], [10,0]]},
                        {"points": [[10,0], [10,10]]},
                        {"points": [[10,10], [0,10]]},
                        {"points": [[0,10], [0,0]]}
                    ],
                    "furniture": [
                        {"id": "f1", "type": "sofa", "position": [5, 0, 5], "rotation": 0}
                    ]
                }
            )
            db.add(sample_scene)
        
        await db.commit()
        print("[DONE] Database Seeded Successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
