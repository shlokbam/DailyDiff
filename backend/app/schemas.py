from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

class SubscribeRequest(BaseModel):
    email: EmailStr = Field(..., description="The email address of the subscriber")

class UnsubscribeRequest(BaseModel):
    email: EmailStr = Field(..., description="The email address to unsubscribe")

class BriefItem(BaseModel):
    category: str = Field(..., description="E.g., Worth Knowing, Hidden Gem, Research Idea, Something Changed, Keep an Eye On This")
    title: str = Field(..., description="Headline of the update")
    description: str = Field(..., description="Description of what happened")
    why_it_matters: str = Field(..., description="Rationale for importance")
    who_cares: str = Field(..., description="Target audience group descriptions")
    verdict: str = Field(..., description="Actionable recommendation verdict (WATCH, INTEGRATE, READ, IGNORE)")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score out of 100")
    source_url: Optional[str] = Field(None, description="Primary link or reference URL")

class DailyBriefGroup(BaseModel):
    date: str = Field(..., description="ISO Date string YYYY-MM-DD")
    published_at: str = Field(..., description="ISO Timestamp of publication")
    briefs: List[BriefItem] = Field(..., description="List of the 5 curated briefs for this day")
