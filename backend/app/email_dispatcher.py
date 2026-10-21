import os
import logging
import httpx
from pathlib import Path
from typing import List, Dict, Any
from app.schemas import DailyBriefGroup

logger = logging.getLogger("DailyDiff.email")

def build_email_html(brief_group: DailyBriefGroup) -> str:
    """Compile the daily briefs into a beautiful, clean, responsive HTML email layout."""
    import html as _html
    import re as _re

    date = brief_group.date
    briefs = brief_group.briefs

    category_colors = {
        "Tech Shift": "#f97316",
        "Cool Tool": "#a855f7",
        "Career & Learning": "#06b6d4",
        "Ecosystem Update": "#eab308",
        "Watchlist": "#ec4899",
    }

    def _fmt(value) -> str:
        """Escape text, turn **bold** / `code` markdown into real HTML, keep line breaks."""
        text = _html.escape(str(value if value is not None else "").strip())
        text = _re.sub(r"\*\*(.+?)\*\*", r"<strong style=\"color:#ffffff;\">\1</strong>", text, flags=_re.DOTALL)
        text = _re.sub(
            r"`([^`]+)`",
            r"<code style=\"background-color:#0c0d12; color:#e5e7eb; padding:1px 5px; border-radius:3px; font-family:Consolas,'Courier New',monospace; font-size:13px;\">\1</code>",
            text,
        )
        return text.replace("\n", "<br>")

    show_conf = os.getenv("SHOW_CONFIDENCE", "false").lower() == "true"

    items_html = ""
    for item in briefs:
        color = category_colors.get(item.category, "#3b82f6")
        source_link = (
            f'<tr><td class="card-pad" style="padding: 4px 20px 18px 20px;">'
            f'<a href="{_html.escape(str(item.source_url), quote=True)}" '
            f'style="color: #60a5fa; text-decoration: none; font-weight: 500; font-size: 14px;">'
            f'View Source Reference &rarr;</a></td></tr>'
            if item.source_url else ""
        )

        conf_str = f" | Confidence: {item.confidence}%" if (show_conf and item.confidence is not None) else ""

        items_html += f"""
        <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation" style="margin-bottom: 24px; background-color: #1e2130; border-left: 4px solid {color}; border-radius: 4px;">
            <tr>
                <td class="card-pad" style="padding: 18px 20px 6px 20px;">
                    <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
                        <tr>
                            <td align="left" valign="middle" style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: {color};">
                                <span style="background-color: rgba(255,255,255,0.04); padding: 3px 8px; border-radius: 3px; white-space: nowrap;">{_html.escape(str(item.category))}</span>
                            </td>
                            <td align="right" valign="middle" style="font-size: 12px; color: #9ca3af; line-height: 1.4;">
                                Verdict: <strong style="color: #e5e7eb;">{_html.escape(str(item.verdict))}</strong>{_html.escape(conf_str)}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td class="card-pad" style="padding: 8px 20px 4px 20px;">
                    <h3 style="margin: 0; font-size: 19px; line-height: 1.35; color: #ffffff; font-weight: 700;">{_fmt(item.title)}</h3>
                </td>
            </tr>
            <tr>
                <td class="card-pad" style="padding: 10px 20px 0 20px; font-size: 14px; line-height: 1.65; color: #d1d5db;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #9ca3af; margin-bottom: 3px;">What Happened</div>
                    {_fmt(item.description)}
                </td>
            </tr>
            <tr>
                <td class="card-pad" style="padding: 14px 20px 0 20px; font-size: 14px; line-height: 1.65; color: #d1d5db;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #9ca3af; margin-bottom: 3px;">Why It Matters</div>
                    {_fmt(item.why_it_matters)}
                </td>
            </tr>
            <tr>
                <td class="card-pad" style="padding: 14px 20px 14px 20px; font-size: 14px; line-height: 1.65; color: #d1d5db;">
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #9ca3af; margin-bottom: 3px;">Who Cares</div>
                    {_fmt(item.who_cares)}
                </td>
            </tr>
            {source_link}
        </table>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="color-scheme" content="dark">
        <meta name="supported-color-schemes" content="dark">
        <title>DailyDiff Tech Intelligence</title>
        <style>
            body {{ margin: 0; padding: 0; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
            table {{ border-collapse: collapse; }}
            @media only screen and (max-width: 620px) {{
                .outer-pad {{ padding: 12px 8px !important; }}
                .container {{ width: 100% !important; }}
                .container-pad {{ padding: 20px 14px !important; }}
                .card-pad {{ padding-left: 14px !important; padding-right: 14px !important; }}
            }}
        </style>
    </head>
    <body style="background-color: #0c0d12; color: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation" style="background-color: #0c0d12;">
            <tr>
                <td align="center" class="outer-pad" style="padding: 20px 10px;">
                    <table class="container" width="600" border="0" cellspacing="0" cellpadding="0" role="presentation" style="width: 100%; max-width: 600px; background-color: #141620; border: 1px solid #1f2937; border-radius: 8px; text-align: left;">
                        <tr>
                            <td class="container-pad" style="padding: 32px 28px;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0" role="presentation">
                                    <tr>
                                        <td align="center" style="padding-bottom: 26px; border-bottom: 1px solid #1f2937;">
                                            <h1 style="margin: 0 0 5px 0; font-size: 28px; font-weight: 700; color: #60a5fa; letter-spacing: -0.02em;">DailyDiff</h1>
                                            <p style="margin: 0; font-size: 12px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.1em; line-height: 1.5;">We scan the noise. Five things survive.</p>
                                            <p style="margin: 5px 0 0 0; font-size: 11px; color: #6b7280;">Published on {date}</p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 26px;">
                                            {items_html}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center" style="padding-top: 24px; border-top: 1px solid #1f2937; font-size: 12px; color: #6b7280; line-height: 1.6;">
                                            <p style="margin: 0 0 6px 0;">You received this because you subscribed to DailyDiff Tech Intelligence.</p>
                                            <p style="margin: 0;">If you want to unsubscribe, visit our website at <a href="https://dailydiff.in?mode=unsubscribe" style="color: #60a5fa; text-decoration: underline;">dailydiff.in</a> and click on the <strong>Unsubscribe</strong> button.</p>
                                        </td>
                                    </tr>
                                </table>
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
    from app.config import BREVO_API_KEY, SMTP_EMAIL, SMTP_PASSWORD
    
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
                payload = {
                    "sender": sender,
                    "to": [{"email": recipient}],
                    "subject": f"[DailyDiff] Tech Intelligence Brief for {brief_group.date}",
                    "htmlContent": html_content
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
            
    # 3. Try Resend API sending if configured
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
            
    # 4. Fallback to local files if both delivery methods are unavailable or failed
    logger.warning("No active email delivery method succeeded. Logging output to local file...")
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"email_dispatch_{brief_group.date}.html"
    with open(log_path, "w") as f:
        f.write(html_content)
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

