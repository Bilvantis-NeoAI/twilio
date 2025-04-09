import mysql.connector
from mysql.connector import Error
import random
from faker import Faker

# Function to create the table and add dummy records
def create_table_and_insert_dummy_records():
    connection = None
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(
            host='localhost',         # Change if your MySQL server is not localhost
            user='root',     # Update with your MySQL username
            password='Erenyeager2018!',  # Update with your MySQL password
            database='lendingkart_db',  # Update with your target database
            auth_plugin='mysql_native_password'
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Create the table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS LENDINGKART_DB (
                emp_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                phone VARCHAR(255),
                email VARCHAR(255),
                manager_phone_no VARCHAR(255),
                managers_email VARCHAR(255),
                group_manager_mail VARCHAR(255),
                date DATE,
                target INT,
                result INT,
                actionplan TEXT,
                result_explanation TEXT,
                meeting_time TIME,
                meeting_duration INT,
                summary TEXT
            )
            """
            cursor.execute(create_table_query)
            print("Table 'employees' created successfully.")

            # Generate and insert dummy records
            fake = Faker()
            insert_query = """
            INSERT INTO LENDINGKART_DB (name, phone, email, manager_phone_no, managers_email, group_manager_mail, date, target, result, 
            actionplan, result_explanation, meeting_time, meeting_duration, summary) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            records_to_insert = []
            for _ in range(100):
                name = fake.name()
                phone = fake.phone_number()
                email = fake.email()
                manager_phone_no = fake.phone_number()
                managers_email = fake.email()
                group_manager_mail = fake.email()
                date = fake.date()
                target = random.randint(50, 150)  # Random target between 50 and 150
                result = random.randint(0, target)  # Result cannot be greater than target
                actionplan = fake.sentence()
                result_explanation = fake.paragraph()
                meeting_time = fake.time()
                meeting_duration = random.randint(30, 120)  # Meeting duration in minutes
                summary = fake.text()

                records_to_insert.append((name, phone, email, manager_phone_no, managers_email, group_manager_mail, date, 
                                           target, result, actionplan, result_explanation, meeting_time, 
                                           meeting_duration, summary))

            cursor.executemany(insert_query, records_to_insert)
            connection.commit()
            print("100 dummy records inserted successfully.")

    except Error as e:
        print(f"GGGG Error: {e}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed.")

# Call the function
create_table_and_insert_dummy_records()
