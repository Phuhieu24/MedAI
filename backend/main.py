import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from limiter import limiter

from api.routes_admin import router as admin_router
from api.routes_diagnosis import router as diagnosis_router
from config import settings
from database import init_db, SessionLocal
from services.graph_db import graph_manager


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hệ thống AI gợi ý chẩn đoán sức khỏe sơ cấp tại tuyến cơ sở",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnosis_router)
app.include_router(admin_router)


@app.on_event("startup")
def startup():
    init_db()
    os.makedirs(settings.ML_MODELS_DIR, exist_ok=True)
    
    db = SessionLocal()
    try:
        graph_manager.build_medical_graph(db)
    except Exception as e:
        print(f"Error building medical graph: {e}")
    finally:
        db.close()


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
