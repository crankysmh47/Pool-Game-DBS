import mysql.connector
from mysql.connector import Error
import hashlib  # For pbkdf2_hmac
import os       # For generating a secure salt
from hmac import compare_digest # For securely comparing hashes

# --- 1. Connection Details ---
DB_HOST = "localhost"
DB_NAME = "pool_game_db"
DB_USER = "root"
DB_PASS = "roo123"  # <-- !!! REMEMBER to change this !!!

def get_db_connection():
    """Helper function to create a database connection."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def register_player(username, password):
    """
    Securely registers a new player.
    Generates a salt, hashes the password, and stores it.
    Returns a dictionary with success status and message.
    """
    if not username or not password:
        # Return a dictionary
        return {'success': False, 'message': 'Username and password cannot be empty.'}

    salt = os.urandom(16) # 16 bytes of random data
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    
    salt_hex = salt.hex()
    hash_hex = password_hash.hex()
    
    conn = get_db_connection()
    if conn is None:
        # Return a dictionary
        return {'success': False, 'message': 'Database connection failed.'}

    cursor = conn.cursor()
    
    try:
        sql = "INSERT INTO Player (Username, PasswordHash, Salt) VALUES (%s, %s, %s)"
        values = (username, hash_hex, salt_hex)
        
        cursor.execute(sql, values)
        conn.commit()
        
        # Return a dictionary
        return {'success': True, 'message': f"User '{username}' registered successfully!"}
        
    except Error as e:
        if e.errno == 1062:
            # Return a dictionary
            return {'success': False, 'message': f"Error: Username '{username}' already exists."}
        # Return a dictionary
        return {'success': False, 'message': f"Database error: {e}"}
        
    finally:
        cursor.close()
        conn.close()


def login_player(username, password):
    """
    Securely logs in a player.
    Returns a dictionary with success, message, and player_id (on success).
    """
    if not username or not password:
        # Return a dictionary
        return {'success': False, 'message': 'Username and password cannot be empty.'}

    conn = get_db_connection()
    if conn is None:
        # Return a dictionary
        return {'success': False, 'message': 'Database connection failed.'}

    cursor = conn.cursor(dictionary=True)
    
    try:
        sql = "SELECT PlayerID, PasswordHash, Salt FROM Player WHERE Username = %s"
        cursor.execute(sql, (username,))
        user_data = cursor.fetchone()
        
        if not user_data:
            # Return a dictionary
            return {'success': False, 'message': 'Login failed: Invalid username or password.'}
            
        stored_hash_hex = user_data['PasswordHash']
        stored_salt_hex = user_data['Salt']
        player_id = user_data['PlayerID']
        
        salt = bytes.fromhex(stored_salt_hex)
        
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        
        if compare_digest(new_hash, bytes.fromhex(stored_hash_hex)):
            # Return a dictionary
            return {'success': True, 'message': f"Login successful! Welcome, {username}.", 'player_id': player_id}
        else:
            # Return a dictionary
            return {'success': False, 'message': 'Login failed: Invalid username or password.'}
            
    except Error as e:
        # Return a dictionary
        return {'success': False, 'message': f"Database error: {e}"}
        
    finally:
        cursor.close()
        conn.close()

# --- This makes the script runnable for testing ---
if __name__ == "__main__":
    
    # Test Registration
    print("Testing Registration...")
    # NOTE: You may need to change the username "danyal" to a new one if he's already in the DB
    print(register_player("danyal_test", "mySecurePass123"))
    
    # Test Login (Successful)
    print("\nTesting Successful Login...")
    print(login_player("danyal_test", "mySecurePass123"))
    
    # Test Login (Wrong Password)
    print("\nTesting Failed Login (Wrong Pass)...")
    print(login_player("danyal_test", "wrong_password"))