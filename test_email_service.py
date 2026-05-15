#!/usr/bin/env python3
"""
Email Service Troubleshooting & Testing Script

This script helps diagnose and fix email sending issues by:
1. Checking environment variable configuration
2. Testing SMTP server connectivity
3. Testing SMTP authentication
4. Sending test emails with full debugging output

Usage:
    python test_email_service.py

Requirements:
    - Create a .env file with SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER, SMTP_PORT
    For Gmail users:
        - Enable 2-Step Verification
        - Generate an App Password at https://myaccount.google.com/apppasswords
        - Use the 16-character app password (without spaces) as SENDER_PASSWORD
"""

import os
import sys
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pathlib import Path


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_success(message: str):
    """Print a success message in green (simulated)."""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message in red (simulated)."""
    print(f"✗ {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"ℹ {message}")


def check_environment():
    """Check if environment variables are properly configured."""
    print_section("STEP 1: Checking Environment Variables")
    
    # Load .env file
    env_file = Path('.env')
    if not env_file.exists():
        print_error("'.env' file not found!")
        print_info("Please create a .env file with the following content:")
        print("""
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
        """)
        return False
    
    load_dotenv()
    print_success("'.env' file loaded")
    
    # Check required variables
    sender_email = os.environ.get('SENDER_EMAIL', '').strip()
    sender_password = os.environ.get('SENDER_PASSWORD', '').strip()
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com').strip()
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    
    if not sender_email:
        print_error("SENDER_EMAIL is not set")
        return False
    print_success(f"SENDER_EMAIL: {sender_email}")
    
    if not sender_password:
        print_error("SENDER_PASSWORD is not set")
        return False
    print_success(f"SENDER_PASSWORD: {'*' * len(sender_password)} (hidden)")
    
    print_success(f"SMTP_SERVER: {smtp_server}")
    print_success(f"SMTP_PORT: {smtp_port}")
    
    return True


def test_smtp_connection():
    """Test SMTP server connectivity."""
    print_section("STEP 2: Testing SMTP Server Connection")
    
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    
    print_info(f"Connecting to {smtp_server}:{smtp_port}...")
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            print_success(f"✓ Connected to {smtp_server}:{smtp_port}")
            
            # Try to start TLS
            print_info("Starting TLS encryption...")
            try:
                server.starttls()
                print_success("✓ TLS encryption enabled")
                return True
            except smtplib.SMTPNotSupportedError:
                print_error("Server does not support TLS")
                return False
            except ssl.SSLError as e:
                print_error(f"SSL/TLS error: {str(e)}")
                return False
    
    except ConnectionRefusedError:
        print_error(f"Connection refused to {smtp_server}:{smtp_port}")
        print_info("Possible causes:")
        print("  - Firewall blocking the port")
        print("  - Wrong SMTP server or port")
        print("  - Network connectivity issue")
        return False
    
    except socket.timeout:
        print_error(f"Connection timeout to {smtp_server}:{smtp_port}")
        print_info("Possible causes:")
        print("  - Network is too slow")
        print("  - Server is not responding")
        return False
    
    except Exception as e:
        print_error(f"Connection error: {str(e)}")
        return False


def test_smtp_auth():
    """Test SMTP authentication."""
    print_section("STEP 3: Testing SMTP Authentication")
    
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    sender_email = os.environ.get('SENDER_EMAIL', '').strip()
    sender_password = os.environ.get('SENDER_PASSWORD', '').strip()
    
    print_info(f"Authenticating as: {sender_email}")
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            
            print_info("Sending login credentials...")
            server.login(sender_email, sender_password)
            print_success("✓ Authentication successful!")
            return True
    
    except smtplib.SMTPAuthenticationError:
        print_error("❌ Authentication FAILED!")
        print_info("\nCommon causes for Gmail:")
        print("  1. Using account password instead of App Password")
        print("     → Generate App Password at: https://myaccount.google.com/apppasswords")
        print("  2. 2-Step Verification not enabled")
        print("     → Enable at: https://myaccount.google.com/security")
        print("  3. App password used incorrectly (remove spaces if any)")
        print("  4. Account has login restrictions")
        print("     → Check: https://myaccount.google.com/security")
        return False
    
    except Exception as e:
        print_error(f"Authentication error: {str(e)}")
        return False


def send_test_email():
    """Send a test email to verify everything works."""
    print_section("STEP 4: Sending Test Email")
    
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    sender_email = os.environ.get('SENDER_EMAIL', '').strip()
    sender_password = os.environ.get('SENDER_PASSWORD', '').strip()
    
    # Get recipient email
    recipient_email = input("Enter recipient email address (for test email): ").strip()
    
    if not recipient_email or '@' not in recipient_email:
        print_error("Invalid email address")
        return False
    
    print_info(f"Sending test email to: {recipient_email}")
    
    try:
        # Create email
        message = MIMEMultipart('alternative')
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = "✓ Email Service Test - Professional Setup Verified"
        
        # Create HTML body
        html_body = """
        <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; background: #f5f5f5; padding: 20px; border-radius: 8px; }
                    .header { background: linear-gradient(135deg, #1a5c4f 0%, #0f3a2e 100%); color: white; padding: 20px; text-align: center; border-radius: 8px; }
                    .content { background: white; padding: 20px; margin-top: 10px; border-radius: 8px; }
                    .success { color: #28a745; font-weight: bold; }
                    .details { background: #f9f9f9; padding: 15px; border-left: 4px solid #28a745; margin: 15px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✓ Test Email Successful</h1>
                    </div>
                    <div class="content">
                        <p>Hello,</p>
                        <p class="success">✓ Your email service is properly configured and working!</p>
                        <div class="details">
                            <strong>Configuration Details:</strong><br>
                            SMTP Server: """ + smtp_server + """<br>
                            SMTP Port: """ + str(smtp_port) + """<br>
                            Sender Email: """ + sender_email + """<br>
                            Authentication: ✓ Successful
                        </div>
                        <p>
                            You can now use the email service to send application status notifications
                            with personalized resume analysis details (ATS score, resume status, etc.).
                        </p>
                        <p>
                            Best regards,<br>
                            <strong>AI Resume Screening System</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        html_part = MIMEText(html_body, 'html')
        message.attach(html_part)
        
        # Send email
        print_info("Connecting to SMTP server...")
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            print_success("Connected")
            
            print_info("Starting TLS encryption...")
            server.starttls()
            print_success("TLS enabled")
            
            print_info("Authenticating...")
            server.login(sender_email, sender_password)
            print_success("Authenticated")
            
            print_info("Sending email...")
            server.send_message(message)
            print_success("Email sent successfully!")
        
        return True
    
    except Exception as e:
        print_error(f"Failed to send email: {str(e)}")
        return False


def test_email_service_module():
    """Test the email service module directly."""
    print_section("STEP 5: Testing Email Service Module")
    
    try:
        from utils.email_service import send_applicant_status_email
        print_success("Email service module imported successfully")
        
        # Get test details
        recipient_email = input("Enter recipient email address: ").strip()
        recipient_name = input("Enter recipient name: ").strip()
        recipient_username = input("Enter recipient username: ").strip()
        status = input("Enter status (Selected/Rejected): ").strip()
        ats_score = input("Enter ATS score (0-100, optional): ").strip()
        resume_status = input("Enter resume status (e.g., ATS-Friendly, optional): ").strip()
        
        # Convert ats_score to float if provided
        ats_score = float(ats_score) if ats_score else None
        resume_status = resume_status if resume_status else None
        
        print_info(f"Sending application status email...")
        
        success, message = send_applicant_status_email(
            applicant_email=recipient_email,
            applicant_name=recipient_name,
            applicant_username=recipient_username,
            status=status,
            resume_status=resume_status,
            ats_score=ats_score,
            company_name="AI Resume Screening System"
        )
        
        if success:
            print_success(message)
            return True
        else:
            print_error(message)
            return False
    
    except ImportError as e:
        print_error(f"Could not import email service: {str(e)}")
        print_info("Make sure you're in the correct directory")
        return False
    
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("           EMAIL SERVICE TROUBLESHOOTING & TESTING TOOL")
    print("=" * 80)
    
    # Step 1: Check environment
    if not check_environment():
        return False
    
    # Step 2: Test SMTP connection
    if not test_smtp_connection():
        return False
    
    # Step 3: Test SMTP authentication
    if not test_smtp_auth():
        return False
    
    # Step 4: Send test email
    if not send_test_email():
        return False
    
    # Step 5: Test email service module
    test_email_service_module()
    
    print_section("✓ ALL TESTS PASSED!")
    print_success("Your email service is properly configured and ready to use!")
    print("\nYou can now use the email service in your Flask app:")
    print("  from utils.email_service import send_applicant_status_email")
    print("  send_applicant_status_email(email, name, username, status, resume_status, ats_score)")
    
    return True


if __name__ == '__main__':
    import socket
    success = main()
    sys.exit(0 if success else 1)
