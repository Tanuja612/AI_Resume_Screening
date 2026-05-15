#!/usr/bin/env python3
"""
Email Service Usage Examples

This script demonstrates how to use the enhanced email service to send:
1. Single applicant status emails with resume analysis
2. Batch emails to multiple applicants
3. Sample usage patterns for Flask integration
"""

from utils.email_service import send_applicant_status_email, send_batch_applicant_emails
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_1_single_selected():
    """Example 1: Send a SELECTED status email with full resume analysis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Send SELECTED Status Email with Resume Analysis")
    print("=" * 80 + "\n")
    
    success, message = send_applicant_status_email(
        applicant_email="john.doe@example.com",
        applicant_name="John Doe",
        applicant_username="johndoe123",
        status="Selected",
        resume_status="ATS-Friendly",  # Resume passed ATS analysis
        ats_score=92.5,  # High ATS score
        company_name="Acme Corporation"
    )
    
    print(f"Result: {message}")
    return success


def example_2_single_rejected():
    """Example 2: Send a REJECTED status email with resume analysis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Send REJECTED Status Email with Resume Analysis")
    print("=" * 80 + "\n")
    
    success, message = send_applicant_status_email(
        applicant_email="jane.smith@example.com",
        applicant_name="Jane Smith",
        applicant_username="janesmith456",
        status="Rejected",
        resume_status="Needs Improvement",  # Resume didn't pass ATS thresholds
        ats_score=45.3,  # Lower ATS score
        company_name="Tech Innovations Inc"
    )
    
    print(f"Result: {message}")
    return success


def example_3_simple_email():
    """Example 3: Send email without resume analysis (basic usage)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Send Basic Status Email (Without Resume Analysis)")
    print("=" * 80 + "\n")
    
    success, message = send_applicant_status_email(
        applicant_email="bob.johnson@example.com",
        applicant_name="Bob Johnson",
        applicant_username="bobjohnson789",
        status="Selected"
        # No resume_status or ats_score provided - optional fields
    )
    
    print(f"Result: {message}")
    return success


def example_4_batch_emails():
    """Example 4: Send emails to multiple applicants in batch."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Send Batch Emails to Multiple Applicants")
    print("=" * 80 + "\n")
    
    # List of applicants with resume analysis data
    applicants = [
        {
            # Selected applicant with excellent resume
            'name': 'Alice Williams',
            'username': 'alicew2024',
            'email': 'alice.williams@example.com',
            'status': 'Selected',
            'resume_status': 'Excellent Match',
            'ats_score': 95.8
        },
        {
            # Selected applicant with good resume
            'name': 'Charlie Brown',
            'username': 'charlieb88',
            'email': 'charlie.brown@example.com',
            'status': 'Selected',
            'resume_status': 'ATS-Friendly',
            'ats_score': 88.5
        },
        {
            # Rejected applicant - low score
            'name': 'Diana Prince',
            'username': 'dprince_2024',
            'email': 'diana.prince@example.com',
            'status': 'Rejected',
            'resume_status': 'Low Match',
            'ats_score': 35.2
        },
        {
            # Rejected - missing key skills
            'name': 'Evan Davis',
            'username': 'evan_d',
            'email': 'evan.davis@example.com',
            'status': 'Rejected',
            'resume_status': 'Missing Key Skills',
            'ats_score': 42.0
        },
        {
            # Another selected applicant
            'name': 'Fiona Garcia',
            'username': 'fiona_g2024',
            'email': 'fiona.garcia@example.com',
            'status': 'Selected',
            'resume_status': 'Strong Candidate',
            'ats_score': 91.3
        }
    ]
    
    print(f"Sending emails to {len(applicants)} applicants...\n")
    
    # Send batch emails
    results = send_batch_applicant_emails(
        applicants=applicants,
        company_name="Global Tech Solutions"
    )
    
    # Display results summary
    successful = sum(1 for r in results.values() if r['success'])
    failed = len(results) - successful
    
    print(f"\nBatch Results:")
    print(f"  Total: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print("\nDetailed Results:")
    print("-" * 100)
    
    for email, result in results.items():
        status_icon = "✓" if result['success'] else "✗"
        print(f"{status_icon} {result['name']} ({email})")
        print(f"   Username: {result.get('username', 'N/A')}")
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message'][:60]}...")
        print()
    
    return failed == 0


def example_5_database_to_email():
    """
    Example 5: Simulate reading from database and sending emails.
    This shows how to integrate with your Flask app's database.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Database Integration Pattern")
    print("=" * 80 + "\n")
    
    print("""
# This example shows how you'd use the email service with database records
# In your Flask app, you might have something like:

from flask import Flask
from utils.db import get_db_connection
from utils.email_service import send_applicant_status_email

# In your admin dashboard or processing route:
db = get_db_connection()
cursor = db.cursor()

# Get applicant records with resume analysis
cursor.execute('''
    SELECT username, email, name, status, ats_score, resume_analysis
    FROM applicants
    WHERE status IN ('Selected', 'Rejected')
    AND email_sent = 0
''')

applicants = cursor.fetchall()

# Send emails for each applicant
for applicant in applicants:
    username, email, name, status, ats_score, resume_status = applicant
    
    success, message = send_applicant_status_email(
        applicant_email=email,
        applicant_name=name,
        applicant_username=username,
        status=status,
        resume_status=resume_status,
        ats_score=float(ats_score),
        company_name="AI Resume Screening System"
    )
    
    if success:
        # Mark email as sent in database
        cursor.execute('UPDATE applicants SET email_sent = 1 WHERE email = ?', (email,))
        db.commit()
    
    print(f"{message}")
    """)


def example_6_environment_variables():
    """Show how to set up environment variables."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Environment Variable Configuration")
    print("=" * 80 + "\n")
    
    print("Create a .env file in your project root with:\n")
    print("""
# Email Service Configuration
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Flask Configuration
FLASK_SECRET=your_secret_key_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
    """)
    
    print("\n⚠️  IMPORTANT for Gmail Users:")
    print("────────────────────────────────")
    print("""
1. Enable 2-Step Verification on your Google Account:
   https://myaccount.google.com/security

2. Generate an App Password (not your regular password):
   https://myaccount.google.com/apppasswords
   
   - Select 'Mail' and 'Windows Computer' (or your OS)
   - Google will generate a 16-character password
   - Use this password in SENDER_PASSWORD (without spaces)

3. Example:
   SENDER_EMAIL=myemail@gmail.com
   SENDER_PASSWORD=abcd efgh ijkl mnop  (copy exactly as shown, with spaces)
    """)


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  EMAIL SERVICE USAGE EXAMPLES".center(78) + "║")
    print("║" + "  Enhanced with Resume Analysis (Username, ATS Score, Status)".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Check if .env is configured
    if not os.environ.get('SENDER_EMAIL') or not os.environ.get('SENDER_PASSWORD'):
        print("\n⚠️  WARNING: Environment variables not configured!")
        print("Please see Example 6 for setup instructions.\n")
        example_6_environment_variables()
        print("\nOnce configured, uncomment the examples below to run them.\n")
        return
    
    # Run examples (comment/uncomment as needed)
    print("\nRunning examples with production credentials...\n")
    
    # Uncomment the examples you want to run:
    
    # example_1_single_selected()
    # example_2_single_rejected()
    # example_3_simple_email()
    # example_4_batch_emails()
    example_5_database_to_email()
    example_6_environment_variables()
    
    print("\n" + "=" * 80)
    print("Examples completed! Review the code for more details.")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()
