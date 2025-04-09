import mysql.connector
from mysql.connector import Error

def insert_employee_record():
    # Database connection parameters
    db_config = {
        'host': 'localhost',  # Change if your MySQL server is not localhost
        'user': 'root',  # Update with your MySQL username
        'password': 'Erenyeager2018!',  # Update with your MySQL password
        'database': 'lendingkart_db',
        'auth_plugin': 'mysql_native_password' 
        
    }

    # Employee details to be inserted
    employee_data = (
        'Varun',
        '+17043693803',
        'varuninmail@gmail.com',
        '+17043693803',
        'varun.t@bilvantis.io',
        'varun.t@gmail.com',
        '2025-04-01',  # Date in YYYY-MM-DD format
        50000,
        40000,
        "I need to focus on contacting key customers who are into retail business. They were available as yesterday was Ramadan.",
        "All appears good. Target is 20% away. Lets focus on key customers",
        '09:30:00',  # Time in HH:MM:SS format
        100,
        "All appears good. Target is 20% away. Lets focus on key customers"
    )

    connection = None 

    try:
        # Establishing the connection
        connection = mysql.connector.connect(**db_config)

        if connection.is_connected():
            cursor = connection.cursor()

            # SQL query to insert the employee record
            insert_query = """
            INSERT INTO lendingkart_db 
            (name, phone, email, manager_phone_no, managers_email, group_manager_mail, date, target, result, 
            actionplan, result_explanation, meeting_time, meeting_duration, summary) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Executing the insert query
            cursor.execute(insert_query, employee_data)

            # Commit the changes to the database
            connection.commit()
            print("Employee record inserted successfully.")
    
    except Error as e:
        print(f"Error: {e}")

    finally:
        if connection is not None and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed.")

# Call the function
insert_employee_record()