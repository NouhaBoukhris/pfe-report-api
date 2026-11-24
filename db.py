import os
import mysql.connector
from dotenv import load_dotenv

# Load the variables from .env
load_dotenv()


# Function to connect to MySQL
def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    return connection


# Test the database connection
if __name__ == "__main__":
    try:
        connection = get_db_connection()
        print("Successfully connected to MySQL!")
        print("Database:", connection.database)
        connection.close()

    except mysql.connector.Error as error:
        print("Connection failed:", error)
