import mysql.connector
from mysql.connector import Error
import hashlib  # For pbkdf2_hmac
import os  # For generating a secure salt
from hmac import compare_digest  # For securely comparing hashes

# --- 1. Connection Details ---
DB_HOST = "localhost"
DB_NAME = "pool_game_db"
DB_USER = "root"
# --- !!! UPDATE THIS PASSWORD !!! ---
DB_PASS = "Password"


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


def get_player_achievements(player_id):
    """
    Gets a set of all AchievementIDs a player has already earned.
    """
    conn = get_db_connection()
    if conn is None:
        return set()

    cursor = conn.cursor()
    earned_set = set()
    try:
        sql = "SELECT AchievementID FROM PlayerAchievement WHERE PlayerID = %s"
        cursor.execute(sql, (player_id,))
        results = cursor.fetchall()
        earned_set = {row[0] for row in results}

    except Error as e:
        print(f"Database error getting player achievements: {e}")
    finally:
        cursor.close()
        conn.close()

    return earned_set  # <--- FIXED: Moved outside finally


def grant_achievement(player_id, achievement_id):
    """
    Grants a *single* new achievement to a player, in real-time.
    """
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        sql = """
            INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned)
            VALUES (%s, %s, NOW())
        """
        cursor.execute(sql, (player_id, achievement_id))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Player {player_id} just earned achievement {achievement_id}!")

    except Error as e:
        print(f"Database error granting achievement: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def check_all_achievements(player_id, difficulty_id, timer, shots, fouls, did_win):
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    newly_earned = []

    try:
        cursor.execute(
            "CALL sp_CheckPlayerAchievements(%s,%s,%s,%s,%s,%s)",
            (player_id, difficulty_id, timer, shots, fouls, did_win)
        )
        newly_earned = cursor.fetchall()
        conn.commit()

    except Error as e:
        print("Database error checking achievements:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return newly_earned  # <--- FIXED: Moved outside finally


def get_achievement_name(achievement_id):
    conn = get_db_connection()
    if conn is None:
        return "Unknown Achievement"

    cursor = conn.cursor()
    try:
        sql = "SELECT Name FROM Achievement WHERE AchievementID = %s"
        cursor.execute(sql, (achievement_id,))
        result = cursor.fetchone()
        return result[0] if result else "Unknown Achievement"
    except Error as e:
        return "Unknown Achievement"
    finally:
        cursor.close()
        conn.close()


def get_all_achievements_list():
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    results = []
    try:
        cursor.execute("SELECT AchievementID, Name, Description FROM Achievement ORDER BY AchievementID")
        results = cursor.fetchall()
    except Error as e:
        print(f"Error fetching all achievements: {e}")
    finally:
        cursor.close()
        conn.close()

    return results  # <--- FIXED: Moved outside finally


def update_password(player_id, new_password):
    if not new_password:
        return {'success': False, 'message': "Password cannot be empty."}

    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), salt, 100000)
    salt_hex = salt.hex()
    hash_hex = password_hash.hex()

    conn = get_db_connection()
    if conn is None:
        return {'success': False, 'message': "Database connection failed."}

    cursor = conn.cursor()
    try:
        sql = "UPDATE Player SET PasswordHash=%s, Salt=%s WHERE PlayerID=%s"
        cursor.execute(sql, (hash_hex, salt_hex, player_id))
        conn.commit()
        return {'success': True, 'message': "Password changed successfully!"}
    except Error as e:
        return {'success': False, 'message': f"Database error: {e}"}
    finally:
        cursor.close()
        conn.close()


def register_player(username, password):
    if not username or not password:
        return {'success': False, 'message': 'Username and password cannot be empty.'}

    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    salt_hex = salt.hex()
    hash_hex = password_hash.hex()

    conn = get_db_connection()
    if conn is None:
        return {'success': False, 'message': 'Database connection failed.'}

    cursor = conn.cursor()
    try:
        sql = "INSERT INTO Player (Username, PasswordHash, Salt) VALUES (%s, %s, %s)"
        cursor.execute(sql, (username, hash_hex, salt_hex))
        conn.commit()
        return {'success': True, 'message': f"User '{username}' registered successfully!"}

    except Error as e:
        if e.errno == 1062:
            return {'success': False, 'message': f"Error: Username '{username}' already exists."}
        return {'success': False, 'message': f"Database error: {e}"}
    finally:
        cursor.close()
        conn.close()


def login_player(username, password):
    if not username or not password:
        return {'success': False, 'message': 'Username and password cannot be empty.'}

    conn = get_db_connection()
    if conn is None:
        return {'success': False, 'message': 'Database connection failed.'}

    cursor = conn.cursor(dictionary=True)
    try:
        sql = "SELECT PlayerID, PasswordHash, Salt FROM Player WHERE Username = %s"
        cursor.execute(sql, (username,))
        user_data = cursor.fetchone()

        if not user_data:
            return {'success': False, 'message': 'Login failed: Invalid username or password.'}

        stored_hash_hex = user_data['PasswordHash']
        stored_salt_hex = user_data['Salt']
        player_id = user_data['PlayerID']

        salt = bytes.fromhex(stored_salt_hex)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)

        if compare_digest(new_hash, bytes.fromhex(stored_hash_hex)):
            return {'success': True, 'message': f"Login successful! Welcome, {username}.", 'player_id': player_id}
        else:
            return {'success': False, 'message': 'Login failed: Invalid username or password.'}
    except Error as e:
        return {'success': False, 'message': f"Database error: {e}"}
    finally:
        cursor.close()
        conn.close()


def save_game_session(player_id, difficulty_id, score, did_win):
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        sql_session = "INSERT INTO GameSession (DifficultyID) VALUES (%s)"
        cursor.execute(sql_session, (difficulty_id,))
        game_session_id = cursor.lastrowid

        sql_participant = """
            INSERT INTO GameParticipant (GameSessionID, PlayerID, Score, IsWinner) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_participant, (game_session_id, player_id, int(score), did_win))
        conn.commit()
    except mysql.connector.Error as e:
        print(f"Database error saving game: {e}")
    finally:
        cursor.close()
        conn.close()


def get_top_scores():
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    top_scores = []
    try:
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

    return top_scores  # <--- FIXED: Moved outside finally


if __name__ == "__main__":
    # Simple test to check connection
    print(login_player("test_user", "test_pass"))