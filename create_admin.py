import mysql.connector
import os
import hashlib

# Configuration
DB_HOST = "localhost"
DB_NAME = "pool_game_db"
DB_USER = "root"
DB_PASS = "roo123" 

def create_super_admin(username, password):
    conn = mysql.connector.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
    )
    cursor = conn.cursor()

    # 1. Generate Hash
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    
    try:
        conn.start_transaction()
        
        # 2. Insert into User as ADMIN
        print(f"Creating User '{username}'...")
        sql_user = "INSERT INTO User (Username, PasswordHash, Salt, Role) VALUES (%s, %s, %s, 'ADMIN')"
        cursor.execute(sql_user, (username, password_hash.hex(), salt.hex()))
        new_id = cursor.lastrowid

        # 3. Insert into Admin table
        print(f"Linking to Admin table with ID {new_id}...")
        sql_admin = "INSERT INTO Admin (AdminID) VALUES (%s)"
        cursor.execute(sql_admin, (new_id,))

        conn.commit()
        print("Success! Admin created.")
        
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"Error: {e}")
        print("Tip: If the error is 'Duplicate entry', delete the user from the DB first.")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_super_admin("admin", "admin123")