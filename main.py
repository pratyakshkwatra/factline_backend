import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, post, game

app = FastAPI(
    title="Factline API",
    description="Factline Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["Auth"])
app.include_router(post.router, tags=["Posts"])
app.include_router(game.router, tags=["Game"]) 

@app.get("/")
async def root():
    return {"message": "Welcome to the Factline API"}
