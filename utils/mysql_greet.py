import mysql.connector
from mysql.connector import Error

def fetch_explanation_by_phone(phone_number):
    # Database connection parameters
    db_config = {
        'host': 'localhost',  # Change if your MySQL server is not localhost
        'user': 'root',  # Update with your MySQL username
        'password': 'Erenyeager2018!',  # Update with your MySQL password
        'database': 'twilio',  # Your database name
        'auth_plugin': 'mysql_native_password' 
    }
    ret=""

    try:
        # Establishing the connection
        connection = mysql.connector.connect(**db_config)

        if connection.is_connected():
            cursor = connection.cursor()

            # SQL query to fetch the actionplan by phone number
            select_query = """
            SELECT greeting_text FROM Greetings WHERE number = %s LIMIT 1
            """
            cursor.execute(select_query, (phone_number,))

            # Fetch the record
            record = cursor.fetchone()

            # Check if a record was found
            if record:
                result_explanation = record[0]  # Get the actionplan from the first column
                print(f"Action Plan for phone number {phone_number}: {result_explanation}")
                ret=result_explanation
            else:
                print(f"No employee found with the phone number: {phone_number}")

    except Error as e:
        print(f"Error: {e}")

    finally:
        if connection is not None and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed.")
    return ret  

# Example usage
ret= fetch_explanation_by_phone("+17043693803")
print(ret)