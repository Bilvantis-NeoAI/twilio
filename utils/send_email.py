import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "bhaskarrao.g@gmail.com"  # Replace with your Gmail address
#SENDER_PASSWORD = "your_app_password"  # Use App Password, not normal password
SENDER_PASSWORD="wrmm fguv ptqv uqnk"

RECIPIENTS = ["dr.kp.latha@gmail.com", "bhaskarrao.gujju@gmail.com"]  # Replace with actual emails

def send_email_1(sender, password, RECIPIENTS, subject,body):
    """Send an email from Gmail to two recipients."""
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(RECIPIENTS)
        msg["Subject"] = subject
        
        #body = "Hello,\n\nThis is a test email sent via Python SMTP.\n\nBest regards!"
        msg.attach(MIMEText(body, "plain"))

        # Establish SMTP connection
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()  # Upgrade to secure connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())

        logger.info("Email sent successfully to %s", ", ".join(RECIPIENTS))
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

# Run the function
if __name__ == "__main__":
    subject="Action plan for 9963029130"
    body = "Hello,\n\nThis is a test email sent via Python SMTP.\n\nBest regards!"
    send_email_1(SENDER_EMAIL, SENDER_PASSWORD, RECIPIENTS, subject, body)
