import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("heimdall.email")

def send_reset_password_email(email: str, token: str) -> None:
    """
    Sends a stylized password reset email to the user.
    If SMTP credentials are not configured, prints the email body directly to the logs/console.
    """
    reset_url = f"{settings.FRONTEND_URL}/#/reset-password?token={token}"
    
    # ── HTML Email Template (Premium Norse Watchtower Theme) ──
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Heimdall Password Reset</title>
        <style>
            body {{
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background-color: #0A0A14;
                color: #E8E8F0;
                margin: 0;
                padding: 40px 20px;
            }}
            .container {{
                max-width: 500px;
                margin: 0 auto;
                background-color: #12121F;
                border: 1px solid #1E1E35;
                border-radius: 12px;
                padding: 32px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
                text-align: center;
            }}
            .logo-placeholder {{
                display: inline-block;
                width: 64px;
                height: 64px;
                background-color: #4F8EF7;
                color: #FFFFFF;
                border-radius: 50%;
                font-size: 32px;
                line-height: 64px;
                margin-bottom: 20px;
                font-weight: bold;
                text-shadow: 0 0 10px rgba(79, 142, 247, 0.6);
            }}
            h2 {{
                color: #E8E8F0;
                font-size: 22px;
                margin-top: 0;
                letter-spacing: 0.5px;
            }}
            p {{
                color: #9C9CB0;
                font-size: 15px;
                line-height: 1.6;
                margin: 16px 0;
            }}
            .btn-container {{
                margin: 28px 0;
            }}
            .btn {{
                background-color: #4F8EF7;
                color: #FFFFFF;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: 700;
                font-size: 15px;
                display: inline-block;
                box-shadow: 0 4px 12px rgba(79, 142, 247, 0.3);
                transition: background-color 0.2s ease;
            }}
            .btn:hover {{
                background-color: #3A7DE3;
            }}
            .warning-text {{
                font-size: 12px;
                color: #6B6B8A;
                border-top: 1px solid #1E1E35;
                padding-top: 20px;
                margin-top: 24px;
            }}
            .warning-text a {{
                color: #4F8EF7;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo-placeholder">👁</div>
            <h2>Heimdall Password Reset</h2>
            <p>We received a request to reset the password for your Heimdall account.</p>
            <p>Click the button below to secure your credentials. This link will expire in <strong>30 minutes</strong>.</p>
            
            <div class="btn-container">
                <a href="{reset_url}" class="btn" target="_blank">Reset Password</a>
            </div>
            
            <p style="font-size: 13px; color: #6B6B8A;">
                Or copy and paste this URL into your browser:<br>
                <a href="{reset_url}" style="color: #4F8EF7; word-break: break-all;">{reset_url}</a>
            </p>
            
            <div class="warning-text">
                <strong>Security Warning:</strong> If you did not request this password reset, please ignore this message. Your password will remain unchanged, but you may want to review your account details.
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = (
        f"Heimdall Password Reset\n\n"
        f"We received a request to reset your password. Use the following link to set a new password:\n"
        f"{reset_url}\n\n"
        f"This link will expire in 30 minutes.\n\n"
        f"Security Warning: If you did not request this reset, you can safely ignore this email."
    )

    # Check if SMTP is configured
    if not settings.SMTP_HOST:
        logger.info("=== [SMTP OFFLINE - PASSWORD RESET DETAILS] ===")
        logger.info(f"Recipient: {email}")
        logger.info(f"Reset Link: {reset_url}")
        logger.info("===============================================")
        # Print directly to stdout to ensure developers see it immediately in dev server logs
        print("\n" + "="*50)
        print(f"PASSWORD RESET REQUEST RECEIVED FOR: {email}")
        print(f"RESET LINK: {reset_url}")
        print("="*50 + "\n", flush=True)
        return

    # Dispatch via SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Heimdall — Password Reset Request"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email
        
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, email, msg.as_string())
        logger.info(f"Successfully dispatched password reset email to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        # Even if sending fails, we log it to console as fallback so the session is not blocked
        print(f"\n[SMTP ERROR FALLBACK] RESET LINK FOR {email}: {reset_url}\n", flush=True)
