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



# --- NEW FUNCTION (for real-time cache) ---
def get_player_achievements(player_id):
    """
    Gets a set of all AchievementIDs a player has already earned.
    This is used to cache achievements at the start of a game.
    """
    conn = get_db_connection()
    if conn is None:
        return set() # Return an empty set on failure

    cursor = conn.cursor()
    earned_set = set()
    try:
        sql = "SELECT AchievementID FROM PlayerAchievement WHERE PlayerID = %s"
        cursor.execute(sql, (player_id,))
        results = cursor.fetchall()
        
        # Unpack the list of tuples into a simple set
        earned_set = {row[0] for row in results}
        
    except Error as e:
        print(f"Database error getting player achievements: {e}")
    finally:
        cursor.close()
        conn.close()
        return earned_set

# --- NEW FUNCTION (for real-time grant) ---
def grant_achievement(player_id, achievement_id):
    """
    Grants a *single* new achievement to a player, in real-time.
    Uses INSERT IGNORE to be safe if it's called by mistake.
    """
    conn = get_db_connection()
    if conn is None:
        print("Could not grant achievement. DB connection failed.")
        return

    cursor = conn.cursor()
    try:
        sql = """
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (%s, %s, NOW())
        """
        cursor.execute(sql, (player_id, achievement_id))
        conn.commit()
        
        # We can check if a row was actually inserted
        if cursor.rowcount > 0:
            print(f"Player {player_id} just earned achievement {achievement_id}!")
        
    except Error as e:
        print(f"Database error granting achievement: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# --- This is your existing Stored Procedure call (for end-of-game) ---
# --- This is your existing Stored Procedure call (for end-of-game) ---
def check_all_achievements(player_id, difficulty_id, timer, shots, fouls, did_win):
    """
    Calls the master stored procedure to check all end-of-game achievements
    and returns a list of newly granted achievements.
    """
    conn = get_db_connection()
    if conn is None:
        print("Could not check achievements. DB connection failed.")
        return [] # <-- Return an empty list

    # --- NEW: We must use dictionary=True to read the results ---
    cursor = conn.cursor(dictionary=True)
    newly_earned = [] # <-- List to store achievements
    try:
        args = (player_id, difficulty_id, timer, shots, fouls, did_win)
        
        # callproc returns an iterator of result sets
        results_iterator = cursor.callproc('sp_CheckPlayerAchievements', args)
        
        # --- NEW: Loop to read the results ---
        # Our procedure returns one (1) result set, so we read it.
        for result in results_iterator:
            if result.with_rows:
                newly_earned = result.fetchall()

        conn.commit()
        print(f"Successfully checked for end-of-game achievements. {len(newly_earned)} new.")
        
    except Error as e:
        print(f"Database error checking achievements: {e}")
        conn.rollback() 
    finally:
        cursor.close()
        conn.close()
        # --- NEW: Return the list of achievements ---
        return newly_earned









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






# --- Database Functions (Unchanged) ---

def save_game_session(player_id, difficulty_id, score, did_win):
    """
    Saves the completed game to the database.
    This replaces updateScoresFile().
    """
    conn = get_db_connection()  # Use the centralized connection function
    if conn is None:
        print("Could not save score. DB connection failed.")
        return

    cursor = conn.cursor()
    try:
        # 1. Create the GameSession
        sql_session = "INSERT INTO GameSession (DifficultyID) VALUES (%s)"
        cursor.execute(sql_session, (difficulty_id,))
        game_session_id = cursor.lastrowid  # Get the ID of the new session
        
        # 2. Link the Player to the session
        sql_participant = """
            INSERT INTO GameParticipant (GameSessionID, PlayerID, Score, IsWinner) 
            VALUES (%s, %s, %s, %s)
        """
        values = (game_session_id, player_id, int(score), did_win)
        cursor.execute(sql_participant, values)
        
        conn.commit()
        print(f"Game session {game_session_id} saved for player {player_id} with score {score}.")
    except mysql.connector.Error as e:
        print(f"Database error saving game: {e}")
    finally:
        cursor.close()
        conn.close()

def get_top_scores():
    """
    Gets the top 5 scores from the database.
    This replaces getTopScore().
    """
    conn = get_db_connection()  # Use the centralized connection function
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    top_scores = []
    try:
        # Join Player and GameParticipant, order by score, get top 5
        sql = """
            SELECT p.Username, gp.Score, d.LevelName
            FROM GameParticipant gp
            JOIN Player p ON p.PlayerID = gp.PlayerID
            JOIN GameSession gs ON gs.GameSessionID = gp.GameSessionID
            JOIN Difficultylevel d ON d.DifficultyID = gs.DifficultyID
            ORDER BY gp.Score DESC
            LIMIT 5
        """
        cursor.execute(sql)
        top_scores = cursor.fetchall()

    except mysql.connector.Error as e:
        print(f"Database error getting top scores: {e}")
    finally:
        cursor.close()
        conn.close()
        return top_scores

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

