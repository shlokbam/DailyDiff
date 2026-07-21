import os
import logging
import httpx
from pathlib import Path
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
                                <p style="margin: 0;"><a href="https://dailydiff.in" style="color: #60a5fa; text-decoration: none;">View Dashboard</a> | <a href="{{UNSUBSCRIBE_URL}}" style="color: #6b7280; text-decoration: underline;">Unsubscribe</a></p>
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
    """Dispatch daily email briefs using Brevo API, Gmail SMTP, Resend API, or local HTML log fallback."""
    if not emails:
        logger.info("No active subscribers to notify.")
        return

    html_content = build_email_html(brief_group)
    
    # 1. Try Brevo HTTP API sending if configured (Best for Render Free Tier)
    from app.config import BREVO_API_KEY, SMTP_EMAIL, SMTP_PASSWORD, BACKEND_API_URL
    base_url = BACKEND_API_URL if BACKEND_API_URL else "https://dailydiff.onrender.com"
    
    if BREVO_API_KEY:
        try:
            logger.info(f"Dispatching email briefs to {len(emails)} subscribers via Brevo HTTP API...")
            headers = {
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
                "accept": "application/json"
            }
            sender_email = SMTP_EMAIL if SMTP_EMAIL else "briefs@dailydiff.in"
            sender = {
                "name": "DailyDiff",
                "email": sender_email
            }
            
            for recipient in emails:
                unsub_url = f"{base_url}/api/unsubscribe?email={recipient}"
                personalized_html = html_content.replace("{{UNSUBSCRIBE_URL}}", unsub_url)
                payload = {
                    "sender": sender,
                    "to": [{"email": recipient}],
                    "subject": f"[DailyDiff] Tech Intelligence Brief for {brief_group.date}",
                    "htmlContent": personalized_html
                }
                response = httpx.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=15)
                if response.status_code != 201 and response.status_code != 200:
                    logger.error(f"Brevo API failed for {recipient}: Status {response.status_code} - {response.text}")
                    raise Exception(f"Brevo API error: {response.text}")
                    
            logger.info("Brevo HTTP API email dispatch completed successfully.")
            return
        except Exception as e:
            logger.error(f"Failed to dispatch emails via Brevo: {e}. Trying SMTP fallback...")

    # 2. Try Gmail SMTP sending if configured
    if SMTP_EMAIL and SMTP_PASSWORD:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            logger.info(f"Connecting to Gmail SMTP server to send briefs to {len(emails)} subscribers...")
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            
            for recipient in emails:
                unsub_url = f"{base_url}/api/unsubscribe?email={recipient}"
                personalized_html = html_content.replace("{{UNSUBSCRIBE_URL}}", unsub_url)
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[DailyDiff] Tech Intelligence Brief for {brief_group.date}"
                msg["From"] = f"DailyDiff <{SMTP_EMAIL}>"
                msg["To"] = recipient
                
                # Attach responsive HTML brief content
                part = MIMEText(personalized_html, "html")
                msg.attach(part)
                
                server.sendmail(SMTP_EMAIL, recipient, msg.as_string())
                
            server.quit()
            logger.info("Gmail SMTP email dispatch completed successfully.")
            return
        except Exception as e:
            logger.error(f"Failed to dispatch emails via SMTP: {e}. Trying Resend fallback...")
            
    # 3. Try Resend API sending if configured
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key and not resend_key.startswith("your_"):
        try:
            import resend
            resend.api_key = resend_key
            logger.info(f"Dispatching email briefs to {len(emails)} subscribers via Resend...")
            
            for recipient in emails:
                unsub_url = f"{base_url}/api/unsubscribe?email={recipient}"
                personalized_html = html_content.replace("{{UNSUBSCRIBE_URL}}", unsub_url)
                resend.Emails.send({
                    "from": "DailyDiff <briefs@dailydiff.dev>" if "onboarding" not in resend_key else "DailyDiff <onboarding@resend.dev>",
                    "to": recipient,
                    "subject": f"[DailyDiff] Curated brief for {brief_group.date}",
                    "html": personalized_html
                })
            logger.info("Resend email dispatch completed.")
            return
        except Exception as e:
            logger.error(f"Failed to dispatch emails via Resend: {e}")
            
    # 4. Fallback to local files if both delivery methods are unavailable or failed
    logger.warning("No active email delivery method succeeded. Logging output to local file...")
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"email_dispatch_{brief_group.date}.html"
    unsub_url = f"{base_url}/api/unsubscribe?email=test_subscriber@example.com"
    personalized_html = html_content.replace("{{UNSUBSCRIBE_URL}}", unsub_url)
    with open(log_path, "w") as f:
        f.write(personalized_html)
    logger.info(f"Saved simulated email HTML to {log_path} for manual verification.")

def dispatch_unsubscribe_confirmation(email: str):
    """Send a polite unsubscribe confirmation email to the user."""
    logger.info(f"Preparing to send unsubscribe confirmation email to: {email}")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Unsubscribed from DailyDiff</title>
    </head>
    <body style="background-color: #0c0d12; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0c0d12; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table width="550" border="0" cellspacing="0" cellpadding="0" style="background-color: #141620; border: 1px solid #1f2937; border-radius: 8px; padding: 40px; text-align: left;">
                        <tr>
                            <td align="center" style="padding-bottom: 25px; border-bottom: 1px solid #1f2937;">
                                <h1 style="margin: 0 0 5px 0; font-size: 24px; font-weight: 700; color: #6b7280; letter-spacing: -0.02em;">DailyDiff</h1>
                                <p style="margin: 0; font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.15em;">Subscription Service</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 30px 0; font-size: 15px; line-height: 1.6; color: #d1d5db;">
                                <p style="margin-top: 0;">Hello,</p>
                                <p>This email confirms that you have been successfully unsubscribed from the <strong>DailyDiff Tech Intelligence Briefing</strong>. You will no longer receive our thrice-weekly newsletters in your inbox.</p>
                                <p>We are sorry to see you go! If this was an accident, or if you ever change your mind and want to stay updated with simplified tech tools, home-servers, and coding guides, you can resubscribe at any time on our website.</p>
                                <p style="margin-bottom: 0;">Thank you for reading with us,<br><em style="color: #60a5fa;">The DailyDiff Team</em></p>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" style="padding-top: 25px; border-top: 1px solid #1f2937; font-size: 12px; color: #6b7280;">
                                <p style="margin: 0;"><a href="https://dailydiff.in" style="color: #60a5fa; text-decoration: none; font-weight: 500;">Visit Dashboard</a></p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # 1. Try Brevo HTTP API sending if configured (Best for Render Free Tier)
    from app.config import BREVO_API_KEY, SMTP_EMAIL, SMTP_PASSWORD
    if BREVO_API_KEY:
        try:
            logger.info(f"Sending unsubscribe confirmation to {email} via Brevo HTTP API...")
            headers = {
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
                "accept": "application/json"
            }
            sender_email = SMTP_EMAIL if SMTP_EMAIL else "briefs@dailydiff.in"
            sender = {
                "name": "DailyDiff",
                "email": sender_email
            }
            payload = {
                "sender": sender,
                "to": [{"email": email}],
                "subject": "[DailyDiff] Unsubscribe Confirmation",
                "htmlContent": html_content
            }
            response = httpx.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=15)
            if response.status_code == 201 or response.status_code == 200:
                logger.info("Unsubscribe confirmation email sent successfully via Brevo.")
                return
            else:
                logger.error(f"Brevo API failed: Status {response.status_code} - {response.text}")
                raise Exception(f"Brevo API error: {response.text}")
        except Exception as e:
            logger.error(f"Failed to send unsubscribe confirmation email via Brevo: {e}. Trying SMTP fallback...")

    # 2. Try Gmail SMTP sending if configured
    if SMTP_EMAIL and SMTP_PASSWORD:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            logger.info(f"Connecting to Gmail SMTP server to send unsubscribe confirmation to {email}...")
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "[DailyDiff] Unsubscribe Confirmation"
            msg["From"] = f"DailyDiff <{SMTP_EMAIL}>"
            msg["To"] = email
            
            part = MIMEText(html_content, "html")
            msg.attach(part)
            
            server.sendmail(SMTP_EMAIL, email, msg.as_string())
            server.quit()
            logger.info("Unsubscribe confirmation email sent successfully via SMTP.")
            return
        except Exception as e:
            logger.error(f"Failed to send unsubscribe confirmation email via SMTP: {e}. Trying Resend fallback...")
            
    # 2. Try Resend API sending if configured
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key and not resend_key.startswith("your_"):
        try:
            import resend
            resend.api_key = resend_key
            logger.info(f"Sending unsubscribe confirmation to {email} via Resend...")
            resend.Emails.send({
                "from": "DailyDiff <briefs@dailydiff.dev>" if "onboarding" not in resend_key else "DailyDiff <onboarding@resend.dev>",
                "to": email,
                "subject": "[DailyDiff] Unsubscribe Confirmation",
                "html": html_content
            })
            logger.info("Unsubscribe confirmation email sent successfully via Resend.")
            return
        except Exception as e:
            logger.error(f"Failed to send unsubscribe confirmation email via Resend: {e}")
            
    # 3. Fallback to local files if both delivery methods are unavailable
    logger.warning("No active email delivery method succeeded. Logging output to local file...")
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"unsubscribe_confirm_{email.replace('@', '_at_')}.html"
    with open(log_path, "w") as f:
        f.write(html_content)
    logger.info(f"Saved simulated unsubscribe confirmation email HTML to {log_path} for manual verification.")

