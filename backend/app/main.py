from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import products, shopping_list, stores, auth

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Coins - Kenya Price Comparison",
    description="Compare grocery prices across Naivas, Carrefour, and Quickmart",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(shopping_list.router)
app.include_router(stores.router)


@app.get("/")
async def root():
    return {
        "name": "Coins API",
        "description": "Kenya grocery price comparison",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
