import mysql.connector
import random
from datetime import datetime, timedelta

# Function to generate random dates
def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

# Function to generate random phone numbers
def random_phone_number():
    return f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

# Function to generate random email
def random_email(name):
    domains = ["example.com", "test.com", "demo.com"]
    return f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"

# Function to generate random policyholder data
def generate_policyholder_data(id):
    name = f"Policyholder {id}"
    return {
        "Policyholder_ID": id,
        "Name": name,
        "Address": f"{random.randint(100, 999)} Main St",
        "City": random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
        "State": random.choice(["NY", "CA", "IL", "TX", "AZ"]),
        "Pincode": f"{random.randint(10000, 99999)}",
        "Phone_Number": random_phone_number(),
        "Email": random_email(name),
        "Date_of_Birth": random_date(datetime(1950, 1, 1), datetime(2000, 1, 1)).strftime('%Y-%m-%d'),
        "Gender": random.choice(["Male", "Female"]),
        "PAN_Number": f"ABCDE{random.randint(1000, 9999)}F",
        "Aadhaar_Number": f"{random.randint(100000000000, 999999999999)}",
        "Bank_Account_Number": f"{random.randint(1000000000, 9999999999)}",
        "Bank_Name": random.choice(["Example Bank", "Test Bank", "Demo Bank"]),
        "IFSC_Code": f"EXMP{random.randint(1000, 9999)}",
        "Nominee_Name": f"Nominee {id}",
        "Nominee_Relationship": random.choice(["Spouse", "Child", "Parent"]),
        "Nominee_Contact_Number": random_phone_number(),
        "Policy_ID": f"POL{random.randint(100000, 999999)}",
        "Policy_Type": random.choice(["Term", "Endowment", "ULIP"]),
        "Policy_Start_Date": random_date(datetime(2010, 1, 1), datetime(2023, 1, 1)).strftime('%Y-%m-%d'),
        "Policy_Maturity_Date": random_date(datetime(2030, 1, 1), datetime(2050, 1, 1)).strftime('%Y-%m-%d'),
        "Premium_Amount": random.randint(1000, 10000),
        "Premium_Payment_Frequency": random.choice(["Monthly", "Quarterly", "Yearly"]),
        "Policy_Status": random.choice(["Active", "Lapsed", "Surrendered"]),
        "Sum_Assured": random.randint(100000, 1000000),
        "Bonus_Amount": random.randint(1000, 10000),
        "Surrender_Value": random.randint(1000, 50000),
        "Loan_Against_Policy": random.randint(0, 100000),
        "Policy_Documents_Received": random.choice(["Yes", "No"]),
        "Policy_Documents_Received_Date": random_date(datetime(2020, 1, 1), datetime(2023, 1, 1)).strftime('%Y-%m-%d'),
        "Policy_Assignment_Status": random.choice(["Assigned", "Unassigned"]),
        "Policy_Revival_Date": None,
        "Policy_Cancellation_Date": None,
        "Policy_Cancellation_Reason": None,
        "Complaint_ID": id,
        "Complaint_Date": random_date(datetime(2023, 1, 1), datetime(2023, 10, 1)).strftime('%Y-%m-%d'),
        "Complaint_Type": random.choice(["Delay in Claim Settlement", "Non-receipt of Policy Documents", "Incorrect Premium Deduction"]),
        "Complaint_Description": f"Complaint description for {name}",
        "Complaint_Status": random.choice(["Open", "In Progress", "Resolved"]),
        "Resolution_Date": None,
        "Resolution_Details": None,
        "Grievance_Officer_Name": f"Officer {id}",
        "Grievance_Officer_Contact": random_phone_number(),
        "Escalation_Level": random.choice(["Level 1", "Level 2", "Level 3"]),
        "Claim_ID": f"CLM{random.randint(100000, 999999)}",
        "Claim_Type": random.choice(["Maturity", "Death", "Survival Benefit"]),
        "Claim_Amount": random.randint(100000, 1000000),
        "Claim_Submission_Date": random_date(datetime(2023, 1, 1), datetime(2023, 10, 1)).strftime('%Y-%m-%d'),
        "Claim_Settlement_Date": None,
        "Claim_Status": random.choice(["Pending", "Approved", "Rejected"]),
        "Claim_Rejection_Reason": None,
        "Claim_Documents_Submitted": random.choice(["Yes", "No"]),
        "Claim_Documents_Verified": random.choice(["Yes", "No"]),
        "Premium_Payment_ID": f"PREM{random.randint(100000, 999999)}",
        "Premium_Due_Date": random_date(datetime(2023, 1, 1), datetime(2023, 10, 1)).strftime('%Y-%m-%d'),
        "Premium_Paid_Date": random_date(datetime(2023, 1, 1), datetime(2023, 10, 1)).strftime('%Y-%m-%d'),
        "Premium_Payment_Mode": random.choice(["Online", "Offline", "Auto-Debit"]),
        "Premium_Payment_Status": random.choice(["Paid", "Unpaid"]),
        "Premium_Receipt_Received": random.choice(["Yes", "No"]),
        "Premium_Receipt_Date": random_date(datetime(2023, 1, 1), datetime(2023, 10, 1)).strftime('%Y-%m-%d'),
        "Auto_Debit_Failure_Reason": None,
        "Premium_Notice_Sent_Date": random_date(datetime(2023, 1, 1), datetime(2023, 10, 1)).strftime('%Y-%m-%d'),
        "Premium_Notice_Received": random.choice(["Yes", "No"]),
        "Agent_ID": f"AGT{random.randint(100000, 999999)}",
        "Agent_Name": f"Agent {id}",
        "Agent_Contact_Number": random_phone_number(),
        "Agent_Email": random_email(f"Agent {id}"),
        "Agent_Branch": random.choice(["New York Branch", "Los Angeles Branch", "Chicago Branch"]),
        "Agent_Commission": random.randint(100, 1000),
        "Agent_Misconduct_Reported": random.choice(["Yes", "No"]),
        "Agent_Misconduct_Details": None,
        "Agent_Complaint_Resolution_Status": None,
        "Customer_Service_ID": f"CS{random.randint(100000, 999999)}",
        "Customer_Service_Representative_Name": f"CS Rep {id}",
        "Customer_Service_Contact_Number": random_phone_number(),
        "Customer_Service_Email": random_email(f"CS Rep {id}"),
        "Customer_Service_Response_Time": f"{random.randint(1, 48)} hours",
        "Customer_Service_Feedback_Rating": random.randint(1, 5),
        "Customer_Service_Feedback_Comments": f"Feedback for {name}",
        "Website_Login_ID": f"user{id}",
        "Website_Password": f"password{id}",
        "Website_Complaint_Submission_Date": random_date(datetime(2023, 1, 1), datetime(2023, 10, 1)).strftime('%Y-%m-%d'),
        "Website_Complaint_Status": random.choice(["Open", "Resolved"]),
        "Website_User_Experience_Rating": random.randint(1, 5),
        "Website_User_Feedback": f"User feedback for {name}",
        "Social_Media_Complaint_Submitted": random.choice(["Yes", "No"]),
        "Social_Media_Platform_Name": random.choice(["Twitter", "Facebook", "Instagram"]) if random.choice([True, False]) else None,
        "Social_Media_Complaint_Status": random.choice(["Open", "Resolved"]) if random.choice([True, False]) else None,
        "Social_Media_Response_Time": f"{random.randint(1, 48)} hours" if random.choice([True, False]) else None
    }

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="myuser",
    password="Abcd@1234",
    database="lic_complaints_management",
    port=3306
)
cursor = conn.cursor()

# Create the table
create_table_query = """
CREATE TABLE IF NOT EXISTS policyholder_complaints (
    Policyholder_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Address VARCHAR(255),
    City VARCHAR(255),
    State VARCHAR(255),
    Pincode VARCHAR(10),
    Phone_Number VARCHAR(15),
    Email VARCHAR(255),
    Date_of_Birth DATE,
    Gender VARCHAR(10),
    PAN_Number VARCHAR(20),
    Aadhaar_Number VARCHAR(20),
    Bank_Account_Number VARCHAR(20),
    Bank_Name VARCHAR(255),
    IFSC_Code VARCHAR(20),
    Nominee_Name VARCHAR(255),
    Nominee_Relationship VARCHAR(50),
    Nominee_Contact_Number VARCHAR(15),
    Policy_ID VARCHAR(20),
    Policy_Type VARCHAR(50),
    Policy_Start_Date DATE,
    Policy_Maturity_Date DATE,
    Premium_Amount DECIMAL(10,2),
    Premium_Payment_Frequency VARCHAR(20),
    Policy_Status VARCHAR(20),
    Sum_Assured DECIMAL(10,2),
    Bonus_Amount DECIMAL(10,2),
    Surrender_Value DECIMAL(10,2),
    Loan_Against_Policy DECIMAL(10,2),
    Policy_Documents_Received VARCHAR(3),
    Policy_Documents_Received_Date DATE,
    Policy_Assignment_Status VARCHAR(20),
    Policy_Revival_Date DATE,
    Policy_Cancellation_Date DATE,
    Policy_Cancellation_Reason TEXT,
    Complaint_ID INT,
    Complaint_Date DATE,
    Complaint_Type VARCHAR(255),
    Complaint_Description TEXT,
    Complaint_Status VARCHAR(20),
    Resolution_Date DATE,
    Resolution_Details TEXT,
    Grievance_Officer_Name VARCHAR(255),
    Grievance_Officer_Contact VARCHAR(15),
    Escalation_Level VARCHAR(20),
    Claim_ID VARCHAR(20),
    Claim_Type VARCHAR(50),
    Claim_Amount DECIMAL(10,2),
    Claim_Submission_Date DATE,
    Claim_Settlement_Date DATE,
    Claim_Status VARCHAR(20),
    Claim_Rejection_Reason TEXT,
    Claim_Documents_Submitted VARCHAR(3),
    Claim_Documents_Verified VARCHAR(3),
    Premium_Payment_ID VARCHAR(20),
    Premium_Due_Date DATE,
    Premium_Paid_Date DATE,
    Premium_Payment_Mode VARCHAR(20),
    Premium_Payment_Status VARCHAR(20),
    Premium_Receipt_Received VARCHAR(3),
    Premium_Receipt_Date DATE,
    Auto_Debit_Failure_Reason TEXT,
    Premium_Notice_Sent_Date DATE,
    Premium_Notice_Received VARCHAR(3),
    Agent_ID VARCHAR(20),
    Agent_Name VARCHAR(255),
    Agent_Contact_Number VARCHAR(15),
    Agent_Email VARCHAR(255),
    Agent_Branch VARCHAR(255),
    Agent_Commission DECIMAL(10,2),
    Agent_Misconduct_Reported VARCHAR(3),
    Agent_Misconduct_Details TEXT,
    Agent_Complaint_Resolution_Status TEXT,
    Customer_Service_ID VARCHAR(20),
    Customer_Service_Representative_Name VARCHAR(255),
    Customer_Service_Contact_Number VARCHAR(15),
    Customer_Service_Email VARCHAR(255),
    Customer_Service_Response_Time VARCHAR(20),
    Customer_Service_Feedback_Rating INT,
    Customer_Service_Feedback_Comments TEXT,
    Website_Login_ID VARCHAR(255),
    Website_Password VARCHAR(255),
    Website_Complaint_Submission_Date DATE,
    Website_Complaint_Status VARCHAR(20),
    Website_User_Experience_Rating INT,
    Website_User_Feedback TEXT,
    Social_Media_Complaint_Submitted VARCHAR(3),
    Social_Media_Platform_Name VARCHAR(255),
    Social_Media_Complaint_Status VARCHAR(20),
    Social_Media_Response_Time VARCHAR(20)
);
"""
cursor.execute(create_table_query)
conn.commit()

# Insert 1000 rows
for i in range(1, 1001):
    data = generate_policyholder_data(i)
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    insert_query = f"INSERT INTO policyholder_complaints ({columns}) VALUES ({placeholders})"
    cursor.execute(insert_query, list(data.values()))

conn.commit()
print("1000 rows inserted successfully!")

# Close the connection
cursor.close()
conn.close()