import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, products, checkout, orders, agent, seller

app = FastAPI(
    title="Fashion Marketplace API",
    description="Cohesive backend service for buyers, sellers, and AI-assisted workflows.",
    version="1.0.0"
)

raw_origins = os.getenv("ALLOWED_ORIGINS", "")
custom_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
allowed_origins = custom_origins if custom_origins else default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(checkout.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(seller.router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Welcome to the Fashion Marketplace API",
        "docs_url": "/docs"
    }