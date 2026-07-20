import os
import logging
from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
from app.schemas import SubscribeRequest, UnsubscribeRequest, DailyBriefGroup
from app.database import init_db, add_subscriber, remove_subscriber, read_history, get_subscribers
from app.email_dispatcher import dispatch_emails, dispatch_unsubscribe_confirmation

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
    
    # Send polite unsubscribe confirmation email
    try:
        dispatch_unsubscribe_confirmation(request.email)
    except Exception as e:
        logger.error(f"Error triggering unsubscribe confirmation email: {e}")
        
    return {"message": "Successfully unsubscribed from DailyDiff briefs"}

@app.get("/api/unsubscribe", response_class=HTMLResponse)
def unsubscribe_via_link(email: str):
    """Handle unsubscribe requests from email links (GET)."""
    success = remove_subscriber(email)
    if not success:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Unsubscribe Error | DailyDiff</title>
            <style>
                body { background-color: #0c0d12; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 40px; text-align: center; }
                .container { background-color: #141620; border: 1px solid #ef4444; border-radius: 8px; padding: 40px; display: inline-block; max-width: 450px; box-shadow: 0 4px 20px rgba(239, 68, 68, 0.1); margin-top: 10vh; }
                h2 { color: #ef4444; margin: 0 0 15px 0; font-size: 22px; }
                p { font-size: 14px; color: #9ca3af; line-height: 1.5; margin: 0 0 20px 0; }
                a { color: #60a5fa; text-decoration: none; font-weight: 500; font-size: 14px; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Unsubscribe Error</h2>
                <p>This email address was not found in our active subscriber directory.</p>
                <a href="https://dailydiff.in">Go to DailyDiff Dashboard &rarr;</a>
            </div>
        </body>
        </html>
        """
        
    logger.info(f"Subscriber removed via email link: {email}")
    
    # Send polite unsubscribe confirmation email
    try:
        dispatch_unsubscribe_confirmation(email)
    except Exception as e:
        logger.error(f"Error triggering unsubscribe confirmation email: {e}")
        
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Unsubscribed Successfully | DailyDiff</title>
        <style>
            body { background-color: #0c0d12; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 40px; text-align: center; }
            .container { background-color: #141620; border: 1px solid #1f2937; border-radius: 8px; padding: 40px; display: inline-block; max-width: 450px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); margin-top: 10vh; }
            h2 { color: #10b981; margin: 0 0 15px 0; font-size: 22px; }
            p { font-size: 14px; color: #9ca3af; line-height: 1.5; margin: 0 0 20px 0; }
            a { color: #60a5fa; text-decoration: none; font-weight: 500; font-size: 14px; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>You Have Been Unsubscribed</h2>
            <p>We are sorry to see you go! You have been successfully removed from our thrice-weekly Tech Curation briefings.</p>
            <p style="font-size: 13px; color: #6b7280; margin-bottom: 25px;">A confirmation email has been sent to your inbox.</p>
            <a href="https://dailydiff.in">Back to DailyDiff Dashboard &rarr;</a>
        </div>
    </body>
    </html>
    """


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
