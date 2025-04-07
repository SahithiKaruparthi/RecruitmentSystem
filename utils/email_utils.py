import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3

class EmailService:
    def __init__(self):
        """Initialize the email service with SMTP credentials"""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_username)
        
        # Check if SMTP credentials are set
        if not all([self.smtp_username, self.smtp_password]):
            print("Warning: SMTP credentials are not set. Email sending will not work.")
    
    def send_email(self, recipient: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send an email to a recipient"""
        if not all([self.smtp_username, self.smtp_password]):
            print("Error: SMTP credentials are not set.")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient
            
            # Add plain text part
            text_part = MIMEText(body, "plain")
            message.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                message.attach(html_part)
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            # Send email
            server.sendmail(self.sender_email, recipient, message.as_string())
            server.quit()
            
            return True
        
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_interview_invitation(self, candidate_email: str, candidate_name: str, 
                                  job_title: str, company: str, interview_date: datetime,
                                  job_id: str, resume_id: str) -> bool:
        """Send interview invitation to a candidate"""
        # Format date for display
        formatted_date = interview_date.strftime("%A, %B %d, %Y at %I:%M %p")
        
        subject = f"Interview Invitation: {job_title} at {company}"
        
        body = f"""
Hello {candidate_name},

We are pleased to inform you that your application for the position of {job_title} at {company} has been shortlisted.

We would like to invite you for an interview on {formatted_date}.

Please confirm your attendance by replying to this email.

Best regards,
{company} Recruitment Team
"""
        
        html_body = f"""
<html>
<body>
    <p>Hello {candidate_name},</p>
    
    <p>We are pleased to inform you that your application for the position of <strong>{job_title}</strong> at <strong>{company}</strong> has been shortlisted.</p>
    
    <p>We would like to invite you for an interview on <strong>{formatted_date}</strong>.</p>
    
    <p>Please confirm your attendance by replying to this email.</p>
    
    <p>Best regards,<br>
    {company} Recruitment Team</p>
</body>
</html>
"""
        
        # Send email
        if self.send_email(candidate_email, subject, body, html_body):
            # Update interview record in the database
            try:
                conn = sqlite3.connect('db/memory.sqlite')
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT INTO interviews (resume_id, job_id, interview_date, status)
                VALUES (?, ?, ?, ?)
                """, (resume_id, job_id, interview_date.isoformat(), "scheduled"))
                
                conn.commit()
                conn.close()
                
                return True
            
            except Exception as e:
                print(f"Error updating interview record: {e}")
                return False
        
        return False
    
    def send_shortlist_notification(self, candidate_email: str, candidate_name: str, 
                                   job_title: str, company: str, match_score: float) -> bool:
        """Send notification to candidate about being shortlisted"""
        subject = f"Your application for {job_title} at {company} has been shortlisted"
        
        body = f"""
Hello {candidate_name},

We are pleased to inform you that your application for the position of {job_title} at {company} has been shortlisted.

Your profile has a {match_score:.1f}% match with our requirements.

We will be in touch soon with further details about the interview process.

Best regards,
{company} Recruitment Team
"""
        
        html_body = f"""
<html>
<body>
    <p>Hello {candidate_name},</p>
    
    <p>We are pleased to inform you that your application for the position of <strong>{job_title}</strong> at <strong>{company}</strong> has been shortlisted.</p>
    
    <p>Your profile has a <strong>{match_score:.1f}%</strong> match with our requirements.</p>
    
    <p>We will be in touch soon with further details about the interview process.</p>
    
    <p>Best regards,<br>
    {company} Recruitment Team</p>
</body>
</html>
"""
        
        return self.send_email(candidate_email, subject, body, html_body)