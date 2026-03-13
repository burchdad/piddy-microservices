"""
Email Service Integration

Handles all email delivery for notifications.
Supports multiple providers with fallback.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import asyncio
import os
from datetime import datetime

# Email providers
class EmailProvider:
    """Base email provider."""
    
    async def send(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        raise NotImplementedError


class SMTPEmailProvider(EmailProvider):
    """SMTP email provider (SendGrid, AWS SES, etc)."""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    async def send(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = to
            
            mime_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, mime_type))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"✗ SMTP send failed: {e}")
            return False


class SendGridProvider(EmailProvider):
    """SendGrid email provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def send(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            mail = Mail(
                from_email=Email("noreply@piddy.ai"),
                to_emails=To(to),
                subject=subject,
                plain_text_content=body if not html else None,
                html_content=body if html else None
            )
            
            sg = sendgrid.SendGridAPIClient(self.api_key)
            response = sg.send(mail)
            
            return response.status_code in [200, 202]
        except Exception as e:
            print(f"✗ SendGrid send failed: {e}")
            return False


class MultiProviderEmailService:
    """Email service with multiple providers and fallback."""
    
    def __init__(self):
        self.providers: List[EmailProvider] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize providers from environment."""
        # Primary: SendGrid
        sendgrid_key = os.getenv("SENDGRID_API_KEY")
        if sendgrid_key:
            self.providers.append(SendGridProvider(sendgrid_key))
        
        # Fallback: SMTP
        smtp_config = {
            'smtp_host': os.getenv("SMTP_HOST", "smtp.gmail.com"),
            'smtp_port': int(os.getenv("SMTP_PORT", 587)),
            'username': os.getenv("SMTP_USERNAME", ""),
            'password': os.getenv("SMTP_PASSWORD", "")
        }
        
        if smtp_config['username']:
            self.providers.append(SMTPEmailProvider(**smtp_config))
    
    async def send_email_async(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        retry_count: int = 0
    ) -> bool:
        """Send email with provider fallback."""
        
        for i, provider in enumerate(self.providers):
            try:
                success = await provider.send(to, subject, body, html)
                if success:
                    print(f"✓ Email sent via provider {i+1}: {to}")
                    return True
            except Exception as e:
                print(f"✗ Provider {i+1} failed: {e}")
                continue
        
        if retry_count < 3:
            # Retry with exponential backoff
            await asyncio.sleep(2 ** retry_count)
            return await self.send_email_async(to, subject, body, html, retry_count + 1)
        
        print(f"✗ All providers failed for: {to}")
        return False
    
    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email template."""
        subject = "Welcome to Piddy!"
        body = f"""
        <h1>Welcome, {user_name}!</h1>
        <p>Thank you for joining Piddy.</p>
        <p>Your account is now active and ready to use.</p>
        <a href="https://app.piddy.ai/onboarding">Complete Setup</a>
        """
        return await self.send_email_async(user_email, subject, body, html=True)
    
    async def send_password_reset_email(self, user_email: str, reset_token: str) -> bool:
        """Send password reset email."""
        subject = "Reset Your Piddy Password"
        body = f"""
        <h3>Password Reset Request</h3>
        <p>Click the link below to reset your password:</p>
        <a href="https://app.piddy.ai/reset?token={reset_token}">
            Reset Password
        </a>
        <p>This link expires in 24 hours.</p>
        """
        return await self.send_email_async(user_email, subject, body, html=True)
    
    async def send_notification_email(
        self,
        user_email: str,
        subject: str,
        message: str
    ) -> bool:
        """Send notification email."""
        body = f"""
        <h3>{subject}</h3>
        <p>{message}</p>
        <p>Manage your notification preferences in your account settings.</p>
        """
        return await self.send_email_async(user_email, subject, body, html=True)


# Global instance
email_service = MultiProviderEmailService()


async def send_email_async(to: str, subject: str, body: str, html: bool = False) -> bool:
    """Convenience function."""
    return await email_service.send_email_async(to, subject, body, html)
