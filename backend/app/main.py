from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import students, products, enrollments, chat, analytics

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Every Student Database", version="1.0.0")

# CORS — allow the React frontend (dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(students.router)
app.include_router(products.router)
app.include_router(enrollments.router)
app.include_router(chat.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"message": "Every Student Database API", "docs": "/docs"}
