import mysql.connector
import pandas as pd
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'cs@123',
    'database': 'smart_attendance'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM login_credentials WHERE username=%s AND password=%s", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

def register_student(regno, name, dept, whatsapp, encoding, username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Convert numpy encoding to JSON for storage
        encoding_blob = encoding.tobytes()
        
        # 1. Insert into students_info
        cursor.execute("""
            INSERT INTO students_info (RegNo, Name, Department, Parent_WhatsApp, Face_Encoding)
            VALUES (%s, %s, %s, %s, %s)
        """, (regno, name, dept, whatsapp, encoding_blob))
        
        # 2. Insert into login_credentials
        cursor.execute("""
            INSERT INTO login_credentials (name, username, password, designation)
            VALUES (%s, %s, %s, 'Student')
        """, (name, username, password))
        
        # 3. Initialize in attendance table
        cursor.execute("INSERT INTO attendance (RegNo, Name) VALUES (%s, %s)", (regno, name))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def ensure_date_column_exists(date_str):
    """Creates a new column for today's date if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"ALTER TABLE attendance ADD COLUMN `{date_str}` INT DEFAULT 0")
        conn.commit()
    except mysql.connector.Error as err:
        # Error 1060 indicates duplicate column name (column already exists)
        if err.errno != 1060:
            raise err
    finally:
        conn.close()

def mark_student_present(regno, date_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE attendance SET `{date_str}` = 1 WHERE RegNo = %s", (regno,))
    conn.commit()
    conn.close()

def get_absentees_for_date(date_str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = f"""
        SELECT a.RegNo, a.Name, s.Parent_WhatsApp 
        FROM attendance a
        JOIN students_info s ON a.RegNo = s.RegNo
        WHERE a.`{date_str}` = 0
    """
    cursor.execute(query)
    absentees = cursor.fetchall()
    conn.close()
    return absentees