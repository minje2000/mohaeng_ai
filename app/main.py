# app/main.py
from fastapi import FastAPI
from app.api import reco_router

app = FastAPI()

app.include_router(reco_router.router)