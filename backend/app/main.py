import os
import logging
from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from app.schemas import SubscribeRequest, UnsubscribeRequest, DailyBriefGroup
from app.database import init_db, add_subscriber, remove_subscriber, read_history, get_subscribers
from app.email_dispatcher import dispatch_emails

logger = logging.getLogger("DailyDiff.api")

# Initialize database schema
init_db()

app = FastAPI(
    title="DailyDiff API",
    description="Autonomous Agentic Tech Intelligence Platform API",
    version="1.0.0"
)

# CORS configurations for cross-origin React frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set Vercel URL here in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
def get_status():
    """Verify backend system status."""
    return {"status": "online", "message": "DailyDiff API is fully operational"}

@app.post("/api/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe(request: SubscribeRequest):
    """Subscribe a new email address to receive briefs."""
    success = add_subscriber(request.email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already subscribed"
        )
    logger.info(f"New subscriber registered: {request.email}")
    return {"message": "Successfully subscribed to DailyDiff briefs"}

@app.post("/api/unsubscribe")
def unsubscribe(request: UnsubscribeRequest):
    """Unsubscribe an email address."""
    success = remove_subscriber(request.email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email address not found in subscription list"
        )
    logger.info(f"Subscriber removed: {request.email}")
    return {"message": "Successfully unsubscribed from DailyDiff briefs"}

@app.get("/api/briefs/latest", response_model=DailyBriefGroup)
def get_latest_brief():
    """Retrieve the most recent published brief group."""
    history = read_history()
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No briefs published yet"
        )
    # The last element in history represents the latest daily brief group
    return history[-1]

@app.get("/api/briefs/archive", response_model=List[DailyBriefGroup])
def get_archive(page: int = 1, limit: int = 10):
    """Retrieve historical briefs with pagination (newest first)."""
    history = read_history()
    if not history:
        return []
        
    # Reverse to get newest first
    reversed_history = list(reversed(history))
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    return reversed_history[start_idx:end_idx]

@app.get("/api/briefs/{date}", response_model=DailyBriefGroup)
def get_brief_by_date(date: str):
    """Retrieve the brief group for a specific date (Format: YYYY-MM-DD)."""
    history = read_history()
    brief = next((item for item in history if item.get("date") == date), None)
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No brief found for date: {date}"
        )
    return brief

@app.post("/api/notify-subscribers")
def notify_subscribers(brief_group: DailyBriefGroup, token: str = Header(None, alias="X-Auth-Token")):
    """Notify all active email subscribers about the new brief group."""
    secret_token = os.getenv("NOTIFY_SECRET_TOKEN")
    
    # Simple token validation to prevent public abuse of the email dispatcher
    if secret_token and token != secret_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid notification authorization token"
        )
        
    try:
        emails = get_subscribers()
    except Exception as db_err:
        logger.error(f"Database error in notify_subscribers: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection or query failed: {db_err}"
        )
        
    if not emails:
        return {"message": "No active subscribers found. Dispatch skipped."}
        
    try:
        dispatch_emails(emails, brief_group)
    except Exception as mail_err:
        logger.error(f"Mailing dispatch failed: {mail_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email delivery operation failed: {mail_err}"
        )
        
    return {"message": f"Successfully queued notification emails to {len(emails)} subscribers"}
