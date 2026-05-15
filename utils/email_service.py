"""
Email Service Module for Applicant Status Notifications

This module provides functionality to send professional email notifications
to applicants about their application status (Selected/Rejected) with detailed
resume scoring and assessment information.

Features:
- Secure credential handling via environment variables
- Professional HTML email templates with resume analysis details
- Comprehensive error handling and debugging
- Detailed logging of email operations and SMTP diagnostics
- Batch email sending capability
- Support for applicant details: username, resume status, score, decision
"""

import os
from dotenv import load_dotenv
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, Dict, List, Optional
from datetime import datetime

# Load environment variables from a .env file automatically, if present
# This ensures SENDER_EMAIL and SENDER_PASSWORD are available when the module
# is imported. Users should still explicitly set these variables in production
# or via deployment configuration.
load_dotenv()

# Configure logging with detailed format for debugging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output for debugging
        logging.FileHandler('email_service.log')  # File log for persistence
    ]
)


class EmailService:
    """Service for sending applicant status notification emails with resume analysis details."""
    
    def __init__(self):
        """Initialize email service with SMTP configuration from environment variables."""
        logger.info("=" * 80)
        logger.info("Initializing EmailService...")
        logger.info("=" * 80)
        
        self.sender_email = os.environ.get('SENDER_EMAIL', '').strip()
        self.sender_password = os.environ.get('SENDER_PASSWORD', '').strip()
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com').strip()
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        
        # Log configuration (mask password for security)
        logger.info(f"SMTP Server: {self.smtp_server}")
        logger.info(f"SMTP Port: {self.smtp_port}")
        logger.info(f"Sender Email: {self.sender_email if self.sender_email else 'NOT SET'}")
        logger.info(f"Password Set: {'Yes' if self.sender_password else 'NO - This will cause failures!'}")
        logger.info("=" * 80)
        
        # Validate required configurations
        if not self.sender_email or not self.sender_password:
            logger.error(
                '[CRITICAL] Email service NOT properly configured!\n'
                'Required environment variables missing:\n'
                f'  - SENDER_EMAIL: {self.sender_email or "NOT SET"}\n'
                f'  - SENDER_PASSWORD: {"NOT SET" if not self.sender_password else "SET"}\n\n'
                'Please create a .env file with these values and load it before running.'
            )
    
    def _create_email_body(
        self,
        applicant_name: str,
        applicant_username: str,
        status: str,
        resume_status: Optional[str] = None,
        ats_score: Optional[float] = None,
        company_name: str = "AI Resume Screening System"
    ) -> str:
        """
        Create a professional HTML email body with resume analysis details.
        
        Args:
            applicant_name: Full name of the applicant
            applicant_username: Username/profile name of applicant
            status: Application status ('Selected' or 'Rejected')
            resume_status: Resume analysis status (e.g., 'ATS-Friendly', 'Needs Improvement')
            ats_score: Numeric ATS score (0-100)
            company_name: Name of the company/system
            
        Returns:
            HTML formatted email body
        """
        status_lower = status.lower()
        is_selected = status_lower == 'selected'
        
        # Color coding: Green for selected, Red for rejected
        status_color = '#28a745' if is_selected else '#dc3545'
        status_icon = '✓' if is_selected else '✗'
        
        # Conditional message based on status
        if is_selected:
            main_message = (
                f"Congratulations, {applicant_name}! We are pleased to inform you that "
                "your application has been <strong>SELECTED</strong>.<br/><br/>"
                "Your qualifications impressed our team, and we would like to move forward "
                "with the next steps of our hiring process."
            )
            next_steps = (
                "We will be in touch shortly with details about the next phase of our "
                "recruitment process. Please keep an eye on your inbox for further updates."
            )
        else:
            main_message = (
                f"Dear {applicant_name},<br/><br/>"
                "Thank you for your interest in our organization and for taking the time "
                "to submit your application. We appreciate the effort you put into your submission.<br/><br/>"
                "Unfortunately, we regret to inform you that your application has <strong>NOT BEEN SELECTED</strong> "
                "for this position."
            )
            next_steps = (
                "While you were not selected this time, we encourage you to apply for other positions that may be "
                "a better fit for your skills and experience in the future. "
                "We wish you the best in your career endeavors."
            )
        
        # Build resume analysis section if score is provided
        resume_analysis = ""
        if ats_score is not None or resume_status:
            ats_score_display = f"{ats_score:.1f}/100" if ats_score is not None else "N/A"
            resume_status_display = resume_status or "Assessment Pending"
            
            resume_analysis = f"""
                    <div class="analysis-section">
                        <h3 style="color: #1a5c4f; margin-bottom: 15px;">📋 Resume Analysis</h3>
                        <table class="analysis-table">
                            <tr>
                                <td class="analysis-label">ATS Score:</td>
                                <td class="analysis-value">{ats_score_display}</td>
                            </tr>
                            <tr>
                                <td class="analysis-label">Resume Status:</td>
                                <td class="analysis-value">{resume_status_display}</td>
                            </tr>
                            <tr>
                                <td class="analysis-label">Username:</td>
                                <td class="analysis-value">{applicant_username}</td>
                            </tr>
                        </table>
                    </div>
            """
        
        html_body = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #1a5c4f 0%, #0f3a2e 100%);
                        color: #ffffff;
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 28px;
                    }}
                    .status-badge {{
                        display: inline-block;
                        background-color: {status_color};
                        color: white;
                        padding: 10px 20px;
                        border-radius: 5px;
                        font-weight: bold;
                        margin-top: 10px;
                        font-size: 18px;
                    }}
                    .content {{
                        padding: 30px 20px;
                    }}
                    .greeting {{
                        font-size: 16px;
                        margin-bottom: 20px;
                        color: #333;
                    }}
                    .main-message {{
                        font-size: 15px;
                        margin-bottom: 20px;
                        line-height: 1.8;
                        color: #555;
                    }}
                    .analysis-section {{
                        background-color: #f9f9f9;
                        border: 1px solid #e0e0e0;
                        border-radius: 6px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .analysis-table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    .analysis-table tr {{
                        border-bottom: 1px solid #e0e0e0;
                    }}
                    .analysis-table tr:last-child {{
                        border-bottom: none;
                    }}
                    .analysis-label {{
                        font-weight: 600;
                        color: #1a5c4f;
                        padding: 8px 0;
                        width: 40%;
                    }}
                    .analysis-value {{
                        color: #555;
                        padding: 8px 0;
                    }}
                    .next-steps {{
                        font-size: 14px;
                        line-height: 1.8;
                        color: #666;
                        background-color: #f9f9f9;
                        padding: 15px;
                        border-left: 4px solid {status_color};
                        margin: 20px 0;
                    }}
                    .footer {{
                        background-color: #f5f5f5;
                        padding: 20px;
                        text-align: center;
                        font-size: 12px;
                        color: #999;
                        border-top: 1px solid #e0e0e0;
                    }}
                    .company-name {{
                        color: #1a5c4f;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Application Status Update</h1>
                        <div class="status-badge">{status_icon} {status.upper()}</div>
                    </div>
                    
                    <div class="content">
                        <p class="greeting">Dear {applicant_name},</p>
                        
                        <p class="main-message">
                            {main_message}
                        </p>
                        
                        {resume_analysis}
                        
                        <div class="next-steps">
                            <strong>Next Steps:</strong><br/>
                            {next_steps}
                        </div>
                        
                        <p>
                            If you have any questions or would like to learn more about our organization,
                            please don't hesitate to reach out to our HR team.
                        </p>
                        
                        <p>
                            Best regards,<br/>
                            <span class="company-name">{company_name}</span><br/>
                            Human Resources Team
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>
                            This is an automated notification. Please do not reply to this email.
                            For inquiries, contact our HR team directly.
                        </p>
                        <p>© {datetime.now().year} {company_name}. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        return html_body
    
    def send_status_email(
        self,
        applicant_email: str,
        applicant_name: str,
        applicant_username: str,
        status: str,
        resume_status: Optional[str] = None,
        ats_score: Optional[float] = None,
        company_name: str = "AI Resume Screening System"
    ) -> Tuple[bool, str]:
        """
        Send application status email to applicant with resume analysis details.
        
        Args:
            applicant_email: Recipient email address
            applicant_name: Full name of applicant
            applicant_username: Username/profile name of applicant
            status: Application status ('Selected' or 'Rejected')
            resume_status: Resume analysis status (e.g., 'ATS-Friendly', 'Needs Improvement')
            ats_score: Numeric ATS score (0-100)
            company_name: Name of the company/system sending the email
            
        Returns:
            Tuple of (success: bool, message: str)
            - success: True if email sent successfully, False otherwise
            - message: Status message or error description
        """
        logger.debug("-" * 80)
        logger.debug(f"Processing email for: {applicant_name} ({applicant_email})")
        logger.debug("-" * 80)
        
        # Validate inputs
        applicant_email = applicant_email.strip()
        if not applicant_email or '@' not in applicant_email:
            error_msg = f"❌ Invalid email address: {applicant_email}"
            logger.error(error_msg)
            return False, error_msg
        
        if status.lower() not in ['selected', 'rejected']:
            error_msg = f"❌ Invalid status: {status}. Must be 'Selected' or 'Rejected'"
            logger.error(error_msg)
            return False, error_msg
        
        # Check if email credentials are configured
        if not self.sender_email or not self.sender_password:
            error_msg = (
                "❌ Email service NOT configured!\n"
                "Missing environment variables:\n"
                f"  - SENDER_EMAIL: {self.sender_email or 'NOT SET'}\n"
                f"  - SENDER_PASSWORD: {'NOT SET' if not self.sender_password else 'SET'}\n"
                "Please set these variables before sending emails."
            )
            logger.error(error_msg)
            return False, error_msg
        
        try:
            logger.debug("Creating email message...")
            
            # Create email message
            message = MIMEMultipart('alternative')
            message['From'] = self.sender_email
            message['To'] = applicant_email
            message['Subject'] = f"Application Status - {applicant_name}"
            
            logger.debug(f"  From: {self.sender_email}")
            logger.debug(f"  To: {applicant_email}")
            logger.debug(f"  Subject: {message['Subject']}")
            logger.debug(f"  Status: {status}")
            if ats_score is not None:
                logger.debug(f"  ATS Score: {ats_score}")
            if resume_status:
                logger.debug(f"  Resume Status: {resume_status}")
            
            # Create email body
            logger.debug("Generating HTML email body...")
            html_body = self._create_email_body(
                applicant_name,
                applicant_username,
                status,
                resume_status,
                ats_score,
                company_name
            )
            
            # Attach HTML content
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
            logger.debug("✓ HTML body attached")
            
            # Send email via SMTP
            logger.info(f"Connecting to SMTP server at {self.smtp_server}:{self.smtp_port}...")
            
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                    logger.debug("✓ SMTP connection established")
                    
                    # Enable TLS encryption for secure connection
                    logger.debug("Starting TLS encryption...")
                    server.starttls()
                    logger.debug("✓ TLS encryption enabled")
                    
                    # Authenticate with credentials
                    logger.debug("Authenticating with SMTP server...")
                    server.login(self.sender_email, self.sender_password)
                    logger.debug("✓ SMTP authentication successful")
                    
                    # Send the message
                    logger.debug("Sending message...")
                    server.send_message(message)
                    logger.debug("✓ Message sent successfully to SMTP server")
                    
                success_msg = f"✓ Email successfully sent to {applicant_email} ({status})"
                logger.info(success_msg)
                logger.debug("-" * 80)
                return True, success_msg
            
            except smtplib.SMTPAuthenticationError as e:
                error_msg = (
                    "❌ SMTP Authentication FAILED\n"
                    "Possible causes:\n"
                    "  1. Incorrect SENDER_EMAIL or SENDER_PASSWORD\n"
                    "  2. For Gmail: Using account password instead of App Password\n"
                    "     → Enable 2FA and generate an App Password: https://myaccount.google.com/apppasswords\n"
                    "  3. Account has 2FA enabled but no App Password generated\n"
                    "  4. Email account has login restrictions enabled\n"
                    f"Error details: {str(e)}"
                )
                logger.error(error_msg)
                logger.debug("-" * 80)
                return False, error_msg
            
            except smtplib.SMTPServerDisconnected as e:
                error_msg = (
                    "❌ SMTP Server disconnected unexpectedly\n"
                    "Possible causes:\n"
                    "  1. Server closed connection before TLS negotiation\n"
                    "  2. Network connectivity issue\n"
                    "  3. Firewall blocking the connection\n"
                    f"Error details: {str(e)}"
                )
                logger.error(error_msg)
                logger.debug("-" * 80)
                return False, error_msg
            
            except smtplib.SMTPNotSupportedError as e:
                error_msg = (
                    "❌ SMTP server does not support TLS\n"
                    "Verify SMTP_SERVER and SMTP_PORT are correct\n"
                    f"Error details: {str(e)}"
                )
                logger.error(error_msg)
                logger.debug("-" * 80)
                return False, error_msg
            
            except smtplib.SMTPException as e:
                error_msg = f"❌ SMTP Error: {str(e)}"
                logger.error(error_msg)
                logger.debug("-" * 80)
                return False, error_msg
        
        except Exception as e:
            error_msg = f"❌ Unexpected error: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            logger.debug("-" * 80)
            return False, error_msg
    
    def send_batch_status_emails(
        self,
        applicants: List[Dict[str, any]],
        company_name: str = "AI Resume Screening System"
    ) -> Dict[str, dict]:
        """
        Send status emails to multiple applicants.
        
        Args:
            applicants: List of dictionaries with keys:
                - 'name': Applicant full name (required)
                - 'username': Applicant username (required)
                - 'email': Applicant email (required)
                - 'status': Application status (required)
                - 'resume_status': Resume analysis status (optional)
                - 'ats_score': ATS score 0-100 (optional)
            company_name: Name of the company/system
            
        Returns:
            Dictionary with results for each applicant:
            {
                'email@example.com': {
                    'success': bool,
                    'message': str,
                    'name': str,
                    'username': str,
                    'status': str
                }
            }
        """
        logger.info("=" * 80)
        logger.info(f"Starting BATCH EMAIL sending for {len(applicants)} applicants")
        logger.info("=" * 80)
        
        results = {}
        
        if not applicants:
            logger.warning("No applicants provided for batch email sending")
            return results
        
        for idx, applicant in enumerate(applicants, 1):
            logger.info(f"\n[{idx}/{len(applicants)}] Processing applicant...")
            
            try:
                email = applicant.get('email', '').strip()
                name = applicant.get('name', 'Applicant').strip()
                username = applicant.get('username', '').strip()
                status = applicant.get('status', '').strip()
                resume_status = applicant.get('resume_status', None)
                ats_score = applicant.get('ats_score', None)
                
                success, message = self.send_status_email(
                    email,
                    name,
                    username,
                    status,
                    resume_status,
                    ats_score,
                    company_name
                )
                
                results[email] = {
                    'success': success,
                    'message': message,
                    'name': name,
                    'username': username,
                    'status': status
                }
            
            except Exception as e:
                email = applicant.get('email', 'unknown')
                error_msg = f"Error processing applicant: {str(e)}"
                logger.error(error_msg)
                logger.exception("Full traceback:")
                results[email] = {
                    'success': False,
                    'message': error_msg,
                    'name': applicant.get('name', 'Unknown'),
                    'username': applicant.get('username', 'Unknown'),
                    'status': applicant.get('status', 'Unknown')
                }
        
        # Log summary
        successful = sum(1 for r in results.values() if r['success'])
        failed = len(results) - successful
        logger.info("\n" + "=" * 80)
        logger.info(f"BATCH EMAIL SUMMARY: {successful}/{len(applicants)} successful, {failed} failed")
        logger.info("=" * 80)
        
        return results


# Create a singleton instance
email_service = EmailService()


def send_applicant_status_email(
    applicant_email: str,
    applicant_name: str,
    applicant_username: str,
    status: str,
    resume_status: Optional[str] = None,
    ats_score: Optional[float] = None,
    company_name: str = "AI Resume Screening System"
) -> Tuple[bool, str]:
    """
    Convenience function to send a status email to an applicant.
    
    Args:
        applicant_email: Recipient email address
        applicant_name: Full name of applicant
        applicant_username: Username/profile name of applicant
        status: Application status ('Selected' or 'Rejected')
        resume_status: Resume analysis status (e.g., 'ATS-Friendly')
        ats_score: Numeric ATS score (0-100)
        company_name: Name of the company/system
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    return email_service.send_status_email(
        applicant_email,
        applicant_name,
        applicant_username,
        status,
        resume_status,
        ats_score,
        company_name
    )


def send_batch_applicant_emails(
    applicants: List[Dict[str, any]],
    company_name: str = "AI Resume Screening System"
) -> Dict[str, dict]:
    """
    Convenience function to send status emails to multiple applicants.
    
    Args:
        applicants: List of applicant dictionaries with:
            - 'name': Applicant full name
            - 'username': Applicant username
            - 'email': Applicant email
            - 'status': Application status
            - 'resume_status': (optional) Resume status
            - 'ats_score': (optional) ATS score
        company_name: Name of the company/system
        
    Returns:
        Dictionary with results for each applicant
    """
    return email_service.send_batch_status_emails(applicants, company_name)
