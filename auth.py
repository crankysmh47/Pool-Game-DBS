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


# --- UPDATE THIS FUNCTION ---
def save_game_session(player_id, difficulty_id, score, did_win):
    """
    Saves the session and RETURNS the new GameSessionID.
    """
    conn = get_db_connection()
    if conn is None:
        return None

    cursor = conn.cursor()
    game_session_id = None  # Store the ID here

    try:
        # 1. Create Session
        sql_session = "INSERT INTO GameSession (DifficultyID) VALUES (%s)"
        cursor.execute(sql_session, (difficulty_id,))
        game_session_id = cursor.lastrowid  # <--- CAPTURE THE ID

        # 2. Create Participant Entry
        sql_participant = """
            INSERT INTO GameParticipant (GameSessionID, PlayerID, Score, IsWinner) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_participant, (game_session_id, player_id, int(score), did_win))

        conn.commit()
        return game_session_id  # <--- RETURN IT

    except mysql.connector.Error as e:
        print(f"Database error saving game: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# --- ADD THIS NEW FUNCTION ---
def save_event_log(game_session_id, event_list):
    """
    Bulk inserts the buffered game events into the GameEvent table.
    event_list should be a list of tuples: (PlayerID, PocketID, BallPotted, EventType)
    """
    if not event_list or game_session_id is None:
        return

    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        sql = """
            INSERT INTO GameEvent (GameSessionID, PlayerID, PocketID, BallPotted, EventType)
            VALUES (%s, %s, %s, %s, %s)
        """

        # Prepare data: Add GameSessionID to every event tuple
        data_to_insert = []
        for event in event_list:
            # event is (PlayerID, PocketID, BallPotted, EventType)
            # We add game_session_id to the front
            full_row = (game_session_id,) + event
            data_to_insert.append(full_row)

        cursor.executemany(sql, data_to_insert)
        conn.commit()
        print(f"Successfully logged {len(data_to_insert)} events.")

    except mysql.connector.Error as e:
        print(f"Database error saving events: {e}")
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


def get_full_game_history(player_id):
    """
    Fetches the last 10 games for a player, including ALL detailed events
    (Shots, Pots, Fouls) for those games.
    Returns a list of dictionaries, where each dictionary is a full game summary.
    """
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    history_data = []

    try:
        # 1. Get the last 10 Game Sessions for this player
        sql_sessions = """
            SELECT gs.GameSessionID, gs.StartTime, gp.Score, gp.IsWinner, dl.LevelName
            FROM GameSession gs
            JOIN GameParticipant gp ON gs.GameSessionID = gp.GameSessionID
            JOIN DifficultyLevel dl ON gs.DifficultyID = dl.DifficultyID
            WHERE gp.PlayerID = %s
            ORDER BY gs.StartTime DESC
            LIMIT 10
        """
        cursor.execute(sql_sessions, (player_id,))
        sessions = cursor.fetchall()

        # 2. For EACH session, get the detailed Event Log
        for session in sessions:
            sid = session['GameSessionID']

            sql_events = """
                SELECT EventType, BallPotted, PocketID, EventTime
                FROM GameEvent
                WHERE GameSessionID = %s
                ORDER BY EventTime ASC
            """
            cursor.execute(sql_events, (sid,))
            events = cursor.fetchall()

            # Combine session info with its specific events
            session_summary = {
                "info": session,  # Contains Date, Score, Win/Loss
                "events": events  # Contains the list of shots/pots
            }
            history_data.append(session_summary)

    except Error as e:
        print(f"Error fetching history: {e}")
    finally:
        cursor.close()
        conn.close()

    return history_data

if __name__ == "__main__":
    # Simple test to check connection
    print(login_player("test_user", "test_pass"))