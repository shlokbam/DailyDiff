import os
import logging
from typing import List, Dict, Any
from app.schemas import DailyBriefGroup

logger = logging.getLogger("DailyDiff.email")

def build_email_html(brief_group: DailyBriefGroup) -> str:
    """Compile the daily briefs into a beautiful, clean, responsive HTML email layout."""
    date = brief_group.date
    briefs = brief_group.briefs
    
    category_colors = {
        "Worth Knowing": "#f97316",
        "Hidden Gem": "#a855f7",
        "Research Idea": "#06b6d4",
        "Something Changed": "#eab308",
        "Keep an Eye On This": "#ec4899",
    }
    
    items_html = ""
    for item in briefs:
        color = category_colors.get(item.category, "#3b82f6")
        source_link = f'<p style="margin-top: 10px;"><a href="{item.source_url}" style="color: #60a5fa; text-decoration: none; font-weight: 500;">View Source Reference &rarr;</a></p>' if item.source_url else ""
        
        items_html += f"""
        <div style="margin-bottom: 30px; padding: 20px; border-left: 4px solid {color}; background-color: #1e2130; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: {color}; background-color: rgba(255,255,255,0.04); padding: 3px 8px; border-radius: 3px;">
                    {item.category}
                </span>
                <span style="font-size: 12px; color: #9ca3af;">
                    Verdict: <strong>{item.verdict}</strong> | Confidence: {item.confidence}%
                </span>
            </div>
            <h3 style="margin: 0 0 10px 0; font-size: 18px; color: #ffffff;">{item.title}</h3>
            <p style="margin: 0 0 12px 0; font-size: 14px; line-height: 1.6; color: #d1d5db;">
                <strong>What Happened:</strong> {item.description}
            </p>
            <p style="margin: 0 0 12px 0; font-size: 14px; line-height: 1.6; color: #d1d5db;">
                <strong>Why It Matters:</strong> {item.why_it_matters}
            </p>
            <p style="margin: 0 0 12px 0; font-size: 14px; line-height: 1.6; color: #d1d5db;">
                <strong>Who Cares:</strong> {item.who_cares}
            </p>
            {source_link}
        </div>
        """
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>DailyDiff Tech Intelligence</title>
    </head>
    <body style="background-color: #0c0d12; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0c0d12; padding: 20px 0;">
            <tr>
                <td align="center">
                    <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #141620; border: 1px solid #1f2937; border-radius: 8px; padding: 40px; text-align: left;">
                        <tr>
                            <td align="center" style="padding-bottom: 30px; border-bottom: 1px solid #1f2937;">
                                <h1 style="margin: 0 0 5px 0; font-size: 28px; font-weight: 700; color: #60a5fa; letter-spacing: -0.02em;">DailyDiff</h1>
                                <p style="margin: 0; font-size: 12px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.1em;">We scan the noise. Five things survive.</p>
                                <p style="margin: 5px 0 0 0; font-size: 11px; color: #6b7280;">Published on {date}</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding-top: 30px;">
                                {items_html}
                            </td>
                        </tr>
                        <tr>
                            <td align="center" style="padding-top: 30px; border-top: 1px solid #1f2937; font-size: 12px; color: #6b7280;">
                                <p style="margin: 0 0 5px 0;">You received this because you subscribed to DailyDiff Tech Intelligence.</p>
                                <p style="margin: 0;"><a href="https://daily-diff-pi.vercel.app" style="color: #60a5fa; text-decoration: none;">View Dashboard</a> | <a href="#" style="color: #6b7280; text-decoration: underline;">Unsubscribe</a></p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html

def dispatch_emails(emails: List[str], brief_group: DailyBriefGroup):
    """Dispatch daily email briefs using Gmail SMTP, Resend API, or local HTML log fallback."""
    if not emails:
        logger.info("No active subscribers to notify.")
        return

    html_content = build_email_html(brief_group)
    
    # 1. Try Gmail SMTP sending if configured
    from app.config import SMTP_EMAIL, SMTP_PASSWORD
    if SMTP_EMAIL and SMTP_PASSWORD:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            logger.info(f"Connecting to Gmail SMTP server to send briefs to {len(emails)} subscribers...")
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            
            for recipient in emails:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[DailyDiff] Tech Intelligence Brief for {brief_group.date}"
                msg["From"] = f"DailyDiff <{SMTP_EMAIL}>"
                msg["To"] = recipient
                
                # Attach responsive HTML brief content
                part = MIMEText(html_content, "html")
                msg.attach(part)
                
                server.sendmail(SMTP_EMAIL, recipient, msg.as_string())
                
            server.quit()
            logger.info("Gmail SMTP email dispatch completed successfully.")
            return
        except Exception as e:
            logger.error(f"Failed to dispatch emails via SMTP: {e}. Trying Resend fallback...")
            
    # 2. Try Resend API sending if configured
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key and not resend_key.startswith("your_"):
        try:
            import resend
            resend.api_key = resend_key
            logger.info(f"Dispatching email briefs to {len(emails)} subscribers via Resend...")
            
            for recipient in emails:
                resend.Emails.send({
                    "from": "DailyDiff <briefs@dailydiff.dev>" if "onboarding" not in resend_key else "DailyDiff <onboarding@resend.dev>",
                    "to": recipient,
                    "subject": f"[DailyDiff] Curated brief for {brief_group.date}",
                    "html": html_content
                })
            logger.info("Resend email dispatch completed.")
            return
        except Exception as e:
            logger.error(f"Failed to dispatch emails via Resend: {e}")
            
    # 3. Fallback to local files if both delivery methods are unavailable or failed
    logger.warning("No active email delivery method succeeded. Logging output to local file...")
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"email_dispatch_{brief_group.date}.html"
    with open(log_path, "w") as f:
        f.write(html_content)
    logger.info(f"Saved simulated email HTML to {log_path} for manual verification.")

