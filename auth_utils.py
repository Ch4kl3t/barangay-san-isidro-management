"""
Authentication and Authorization Utilities
"""

import secrets
from functools import wraps
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import session, redirect, url_for, flash, g, abort
from html import escape
from email_config import GMAIL_CONFIG, send_gmail_message

def require_role(*allowed_roles):
    """Decorator to check user role for route access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.get('identity'):
                flash('Please log in first', 'danger')
                return redirect(url_for('login'))
            
            user_role = g.identity['role']
            if user_role not in allowed_roles:
                abort(403, description='You do not have permission to access this page')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_admin():
    """Check if current user is admin"""
    return session.get('role') == 'admin'

def is_user():
    """Check if current user is regular user"""
    return session.get('role') == 'user'

def generate_reset_token():
    """Generate a secure reset token"""
    return secrets.token_urlsafe(32)

def send_password_reset_email(to_email, username, reset_link):
    """
    Send password reset email via the configured email API.
    Args:
        to_email: Recipient email
        username: Username for personalization
        reset_link: Full URL for reset link
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Barangay Household Information Management System - Password Reset Request'
        msg['From'] = GMAIL_CONFIG['sender_email']
        msg['To'] = to_email

        text = f"""
Hello {username},

You requested to reset your password for the Barangay Household Information Management System.
Click the link below to reset your password:

{reset_link}

This link will expire in 1 hour.

If you did not request this, please ignore this email.

Best regards,
Barangay Household Information Management System
        """

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #1B3A57;">Password Reset Request</h2>
                    <p>Hello <strong>{escape(username)}</strong>,</p>
                    <p>You requested to reset your password for the Barangay Household Information Management System.</p>
                    <p>
                        <a href="{escape(reset_link, quote=True)}"
                           style="display: inline-block; padding: 12px 24px; background-color: #2e86c1;
                                  color: white; text-decoration: none; border-radius: 4px; margin: 20px 0;">
                            Reset Your Password
                        </a>
                    </p>
                    <p style="color: #7a93aa; font-size: 12px;">
                        <strong>Link expires in:</strong> 1 hour
                    </p>
                    <p style="color: #7a93aa; font-size: 12px;">
                        If you did not request this, please ignore this email and your password will remain unchanged.
                    </p>
                    <hr style="border: none; border-top: 1px solid #dde3ed; margin: 30px 0;">
                    <p style="color: #7a93aa; font-size: 11px;">
                        Barangay Household Information Management System<br>
                        Municipality of Bongabong, Oriental Mindoro
                    </p>
                </div>
            </body>
        </html>
        """

        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        return send_gmail_message(msg)
    except Exception as exc:
        print('Password recovery message could not be prepared')
        return False, 'Unable to prepare recovery email'


def send_admin_notification(admin_email, username, action):
    """
    Send notification to admin about password reset
    Args:
        admin_email: Admin email address
        username: User who reset password
        action: Action description
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Password Reset Activity - Barangay Household Information Management System'
        msg['From'] = GMAIL_CONFIG['sender_email']
        msg['To'] = admin_email
        
        text = f"""
Admin Alert,

User '{username}' reset their password.
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please review in the audit log if needed.

Barangay Household Information Management System
        """
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #1B3A57;">Admin Alert</h2>
                    <p>User <strong>'{username}'</strong> has reset their password.</p>
                    <p>
                        <strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        <strong>Action:</strong> {action}
                    </p>
                    <p>Review the password reset activity in the audit log.</p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        return send_gmail_message(msg)
    except Exception as exc:
        print('Administrator notification could not be prepared')
        return False, 'Unable to prepare notification'
