import mysql.connector
from faker import Faker
import random

# Database Connection
DB_NAME = "lendingkart_db"
DB_USER = "root"
DB_PASSWORD = "Erenyeager2018!"
DB_HOST = "localhost"

fake = Faker()

def create_insurance_table():
    connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = connection.cursor()
    
    create_table_query = """
    CREATE TABLE IF NOT EXISTS Insurance (
        Policyholder_ID INT AUTO_INCREMENT PRIMARY KEY,
        Name VARCHAR(255),
        Address TEXT,
        City VARCHAR(100),
        State VARCHAR(100),
        Pincode VARCHAR(10),
        Phone_Number VARCHAR(255),
        Email VARCHAR(255),
        Date_of_Birth DATE,
        Gender ENUM('Male', 'Female', 'Other'),
        PAN_Number VARCHAR(10),
        Aadhaar_Number VARCHAR(12),
        Bank_Account_Number VARCHAR(20),
        Bank_Name VARCHAR(255),
        IFSC_Code VARCHAR(20),
        Nominee_Name VARCHAR(255),
        Nominee_Relationship VARCHAR(50),
        Nominee_Contact_Number VARCHAR(255),
        Policy_ID VARCHAR(50),
        Policy_Type VARCHAR(50),
        Policy_Start_Date DATE,
        Policy_Maturity_Date DATE,
        Premium_Amount DECIMAL(10,2),
        Premium_Payment_Frequency ENUM('Monthly', 'Quarterly', 'Annually'),
        Policy_Status ENUM('Active', 'Lapsed', 'Surrendered'),
        Sum_Assured DECIMAL(15,2),
        Bonus_Amount DECIMAL(10,2),
        Surrender_Value DECIMAL(15,2),
        Loan_Against_Policy DECIMAL(15,2),
        Policy_Documents_Received ENUM('Yes', 'No'),
        Policy_Documents_Received_Date DATE,
        Claim_ID VARCHAR(50),
        Claim_Type VARCHAR(50),
        Claim_Amount DECIMAL(15,2),
        Claim_Submission_Date DATE,
        Claim_Status ENUM('Pending', 'Approved', 'Rejected'),
        Claim_Rejection_Reason TEXT
    )"""
    
    cursor.execute(create_table_query)
    connection.commit()
    cursor.close()
    connection.close()
    print("Insurance table created successfully.")

def insert_fake_data(n=100):
    connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = connection.cursor()
    
    insert_query = """
    INSERT INTO Insurance (Name, Address, City, State, Pincode, Phone_Number, Email, Date_of_Birth, Gender, PAN_Number, Aadhaar_Number, 
        Bank_Account_Number, Bank_Name, IFSC_Code, Nominee_Name, Nominee_Relationship, Nominee_Contact_Number, 
        Policy_ID, Policy_Type, Policy_Start_Date, Policy_Maturity_Date, Premium_Amount, Premium_Payment_Frequency, 
        Policy_Status, Sum_Assured, Bonus_Amount, Surrender_Value, Loan_Against_Policy, Policy_Documents_Received, 
        Policy_Documents_Received_Date, Claim_ID, Claim_Type, Claim_Amount, Claim_Submission_Date, Claim_Status, Claim_Rejection_Reason) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    for _ in range(n):
        data = (
            fake.name(), fake.address(), fake.city(), fake.state(), fake.zipcode(), fake.phone_number(), fake.email(),
            fake.date_of_birth(minimum_age=18, maximum_age=80), random.choice(['Male', 'Female', 'Other']),
            fake.bothify(text='?????####?'), fake.bothify(text='############'),
            fake.bban(), fake.company(), fake.swift(), fake.name(), random.choice(['Spouse', 'Parent', 'Sibling', 'Child']), fake.phone_number(),
            fake.uuid4(), random.choice(['Term', 'Endowment', 'Whole Life']), fake.date_this_decade(), fake.future_date(end_date='+20y'),
            round(random.uniform(5000, 100000), 2), random.choice(['Monthly', 'Quarterly', 'Annually']),
            random.choice(['Active', 'Lapsed', 'Surrendered']), round(random.uniform(100000, 5000000), 2),
            round(random.uniform(5000, 50000), 2), round(random.uniform(10000, 500000), 2), round(random.uniform(0, 100000), 2),
            random.choice(['Yes', 'No']), fake.date_this_year(),
            fake.uuid4(), random.choice(['Death', 'Maturity', 'Accidental']), round(random.uniform(50000, 5000000), 2), fake.date_this_year(),
            random.choice(['Pending', 'Approved', 'Rejected']), fake.sentence()
        )
        
        cursor.execute(insert_query, data)
    
    connection.commit()
    cursor.close()
    connection.close()
    print(f"{n} fake records inserted successfully.")

# Usage
if __name__ == "__main__":
    create_insurance_table()
    insert_fake_data(100)
