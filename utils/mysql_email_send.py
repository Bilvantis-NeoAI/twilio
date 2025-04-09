#!/usr/bin/env python3
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mysql.connector
import logging
import openai
import os
from dotenv import load_dotenv
load_dotenv()
from utils.send_email import send_email_1
# --------------------------
# LOGGING CONFIGURATION
# --------------------------
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL="bhaskarrao.g@gmail.com" #os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
USE_SSL = "False" #os.getenv("USE_SSL", "false").lower() == "true"
SENDER_PASSWORD="wrmm fguv ptqv uqnk"



def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('employee_performance.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

load_dotenv()
logger = setup_logging()
logger.info("Logging setup complete")

# --------------------------
# CONFIGURATION
# --------------------------

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --------------------------
# MYSQL DATABASE FUNCTIONS
# --------------------------

def fetch_actionplan_by_phone(phone_number):
    """Fetch employee data by phone number from MySQL"""
    db_config = {
        'host': 'localhost',
        'user': 'root',  # Update with your MySQL username
        'password': 'gbr123',  # Update with your MySQL password
        'database': 'lendingkart_db'  # Your database name
    }

    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()

            select_query = """
            SELECT email, managers_email, group_manager_mail, actionplan, summary 
            FROM lendingkart_db WHERE phone = %s LIMIT 1
            """
            cursor.execute(select_query, (phone_number,))
            record = cursor.fetchone()

            if record:
                employee_data = {
                    'email': record[0],
                    'managers_email': record[1],
                    'group_manager_mail': record[2],
                    'actionplan': record[3],
                    'summary': record[4]
                }

                print(f"Found employee: {employee_data['email']}")
                return employee_data
            else:
                logger.warning(f"No employee found with phone: {phone_number}")
                return None
    except mysql.connector.Error as e:
        logger.error(f"MySQL error: {e}")
        return None
    finally:
        if 'connection' in locals():
            connection.close()

# --------------------------
# EMAIL FUNCTIONS
# --------------------------



def generate_performance_summary(employee_data: dict) -> str:
    """Generate Summary of conversation"""
    prompt = f"""
    Analyze this conversation and create:
    1. A 100-word  summary of the transcript
    2. Action Points 
    3. Takeaways
    
   
    Action Plan: {employee_data['actionplan']}
    Summary: {employee_data['summary']}
    
    Format:
    -  Summary: give like neatly [summary]

    - Action Items: 
                  1) [item1] 
                  2) [item2] 
                  3) [item3]

    - Takeaways: 1) [takeaway1]
                 2) [takeaway2]
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an HR analyst creating professional performance evaluations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        summary = response.choices[0].message.content.strip()
        logger.info("Successfully generated performance summary")
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return f"Error generating performance summary: {str(e)}"

# --------------------------
# MAIN WORKFLOW
# --------------------------

def process_employee_performance(phone_number: str):
    """Main workflow to process employee performance and send email"""
    logger.info(f"Processing employee with phone: {phone_number}")
    
    # 1. Get employee data from MySQL
    employee_data = fetch_actionplan_by_phone(phone_number)
    RECIPIENTS = ["dr.kp.latha@gmail.com", "bhaskarrao.gujju@gmail.com"]  # Replace with actual emails

    if not employee_data:
        logger.error(f"No employee found for phone: {phone_number}")
        return False

    # 2. Generate performance summary (using OpenAI or any logic)
    performance_summary = generate_performance_summary(employee_data)
    
    # 3. Prepare email content
    email_subject = "Follow-up summary"  # Use action plan in subject
    email_body = f"""
    Dear Collection Manager,

    Please find the follow-up email:

    {performance_summary}

    Best Regards,
    AI BOT
    Lendingkart
    """
    
    RECIPIENTS = [employee_data['email'],employee_data['managers_email'],employee_data['group_manager_mail']]  # Replace with actual emails
    print(RECIPIENTS)
    send_email_1(SENDER_EMAIL, SENDER_PASSWORD,RECIPIENTS, email_subject,email_body )
    return False


    

if __name__ == "__main__":
    phone_number="+919963029130"
    process_employee_performance(phone_number)
