from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import upload, auth, admin, search
from app.db.session import engine
from app.db.base_class import Base
# Import models to ensure they are registered with Base
from app.models.user import User 

app = FastAPI(
    title="Floor Plan Intelligence API",
    description="AI-powered floor plan understanding and 3D reconstruction engine",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin Management"])
app.include_router(upload.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(search.router, prefix="/api/v1/search", tags=["AI Discovery"])

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # For development reset
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"message": "Welcome to the Floor Plan Intelligence API", "status": "active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
