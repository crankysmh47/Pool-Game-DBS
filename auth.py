import mysql
from mysql.connector import *
import hashlib
import os

from hmac import compare_digest

# --- 1. Connection Details ---
DB_HOST = "localhost"
DB_NAME = "pool_game_db"
DB_USER = "root"
DB_PASS = "roo123" # !!! UPDATE THIS !!!

def get_db_connection():
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

# --- AUTHENTICATION FUNCTIONS (UPDATED FOR USER/PLAYER SPLIT) ---

def register_player(username, password):
    """
    Transactional Registration:
    1. Insert into User (Supertype)
    2. Insert into Player (Subtype)
    """
    if not username or not password:
        return {'success': False, 'message': 'Username and password cannot be empty.'}

    # Generate Hash
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    salt_hex = salt.hex()
    hash_hex = password_hash.hex()

    conn = get_db_connection()
    if conn is None:
        return {'success': False, 'message': 'Database connection failed.'}

    cursor = conn.cursor()
    try:
        # Start Transaction
        conn.start_transaction()

        # 1. Insert into USER table
        sql_user = "INSERT INTO User (Username, PasswordHash, Salt, Role) VALUES (%s, %s, %s, 'PLAYER')"
        cursor.execute(sql_user, (username, hash_hex, salt_hex))
        
        # Get the new ID
        new_user_id = cursor.lastrowid

        # 2. Insert into PLAYER table
        sql_player = "INSERT INTO Player (PlayerID) VALUES (%s)"
        cursor.execute(sql_player, (new_user_id,))
        # sql_admin = 'INSERT INTO admin (AdminID) Values (%s)'
        # cursor.execute(sql_admin, (new_user_id,))

        # Commit logic
        conn.commit()
        return {'success': True, 'message': f"User '{username}' registered successfully!"}

    except Error as e:
        conn.rollback() # Undo changes if anything fails
        if e.errno == 1062: # Duplicate entry code
            return {'success': False, 'message': f"Error: Username '{username}' already exists."}
        return {'success': False, 'message': f"Database error: {e}"}
    finally:
        cursor.close()
        conn.close()




      




def login_player(username, password):
    if not username or not password:
        return {'success': False, 'message': 'Field Empty.'}

    conn = get_db_connection()
    if conn is None:
        return {'success': False, 'message': 'Database connection failed.'}

    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Fetch User Data including Role
        sql = "SELECT UserID, PasswordHash, Salt, Role FROM User WHERE Username = %s"
        cursor.execute(sql, (username,))
        user_data = cursor.fetchone()
        
        if not user_data:
            return {'success': False, 'message': 'Login failed: Invalid username or password.'}

        stored_hash_hex = user_data['PasswordHash']
        stored_salt_hex = user_data['Salt']
        user_id = user_data['UserID']
        role = user_data['Role']

        # 2. Verify Password
        salt = bytes.fromhex(stored_salt_hex)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)

        if not compare_digest(new_hash, bytes.fromhex(stored_hash_hex)):
            return {'success': False, 'message': 'Login failed: Invalid username or password.'}

        # 3. CONDITIONAL SELF-HEALING
        # ONLY check for Player record if the user is actually a PLAYER.
        # Admins are NOT supposed to be in the Player table in your architecture.
        if role == 'PLAYER':
            sql_check = "SELECT PlayerID FROM Player WHERE PlayerID = %s"
            cursor.execute(sql_check, (user_id,))
            if not cursor.fetchone():
                print(f"Self-healed Player record for UserID {user_id}")
                cursor.execute("INSERT INTO Player (PlayerID) VALUES (%s)", (user_id,))
                conn.commit()

        # 4. Return Success
        return {
            'success': True, 
            'message': f"Welcome, {username}.", 
            'player_id': user_id,
            'role': role
        }

    except Error as e:
        return {'success': False, 'message': f"Database error: {e}"}
    finally:
        cursor.close()
        conn.close()


def get_all_users_for_admin():
    """Fetches list of all users and their basic aggregate stats."""
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    try:
        # Left join to get stats even if they haven't played
        sql = """
            SELECT u.UserID, u.Username, u.Role,
                   COUNT(gp.GameSessionID) as GamesPlayed,
                   SUM(CASE WHEN gp.IsWinner = 1 THEN 1 ELSE 0 END) as Wins
            FROM User u
            LEFT JOIN Player p ON u.UserID = p.PlayerID
            LEFT JOIN GameParticipant gp ON p.PlayerID = gp.PlayerID
            GROUP BY u.UserID
            ORDER BY u.Username ASC
        """
        cursor.execute(sql)
        return cursor.fetchall()
    except Error as e:
        print(f"DB Error: {e}")
        return []
    finally:
        cursor.close(); conn.close()





def ban_user(target_user_id):
    """Deletes a user from the database completely."""
    conn = get_db_connection()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        # ON DELETE CASCADE in your schema ensures Player/Game data is also deleted
        sql = "DELETE FROM User WHERE UserID = %s"
        cursor.execute(sql, (target_user_id,))
        conn.commit()
        return True
    except Error as e:
        print(f"DB Error: {e}")
        return False
    finally:
        cursor.close(); conn.close()

def promote_user(target_user_id):
    """
    Moves a user from PLAYER table to ADMIN table.
    WARNING: Deleting from Player table will WIPE all game history/stats 
    due to Foreign Key Cascades.
    """
    conn = get_db_connection()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        conn.start_transaction()

        # 1. Add to Admin Table
        sql_add_admin = "INSERT IGNORE INTO Admin (AdminID) VALUES (%s)"
        cursor.execute(sql_add_admin, (target_user_id,))

        # 2. Update User Role Label
        sql_update_role = "UPDATE User SET Role = 'ADMIN' WHERE UserID = %s"
        cursor.execute(sql_update_role, (target_user_id,))

        # 3. REMOVE from Player Table (Clean up)
        # This prevents them from being in both tables.
        sql_delete_player = "DELETE FROM Player WHERE PlayerID = %s"
        cursor.execute(sql_delete_player, (target_user_id,))

        conn.commit()
        print(f"User {target_user_id} promoted to Admin (Player stats wiped).")
        return True

    except Error as e:
        conn.rollback()
        print(f"DB Error during promote: {e}")
        return False
    finally:
        cursor.close(); conn.close()

def revoke_admin(target_user_id):
    """
    Moves a user from ADMIN table to PLAYER table.
    Forces Safe Updates OFF and ensures robust error handling.
    """
    # 1. Cast to INT to prevent any string/number mismatches
    try:
        t_id = int(target_user_id)
    except ValueError:
        print(f"[ERROR] Invalid User ID format: {target_user_id}")
        return False

    print(f"[DEBUG] Revoking Admin ID: {t_id}")
    
    conn = get_db_connection()
    if conn is None: 
        print("[DEBUG] DB Connection failed")
        return False
        
    cursor = conn.cursor()
    try:
        # 2. DISABLE SAFE UPDATES for this session
        cursor.execute("SET SQL_SAFE_UPDATES = 0;")
        
        conn.start_transaction()

        # 3. Add to Player Table
        # We use ON DUPLICATE KEY UPDATE as a safer alternative to INSERT IGNORE
        # This ensures the record exists in Player table no matter what.
        print(f"[DEBUG] Moving User {t_id} to Player Table...")
        sql_ensure_player = """
            INSERT INTO Player (PlayerID) VALUES (%s) 
            ON DUPLICATE KEY UPDATE PlayerID = PlayerID
        """
        cursor.execute(sql_ensure_player, (t_id,))

        # 4. Update Role in User Table
        print(f"[DEBUG] Updating User Role to PLAYER...")
        sql_update_role = "UPDATE User SET Role = 'PLAYER' WHERE UserID = %s"
        cursor.execute(sql_update_role, (t_id,))

        # 5. Remove from Admin Table
        print(f"[DEBUG] Removing from Admin Table...")
        sql_delete_admin = "DELETE FROM Admin WHERE AdminID = %s"
        cursor.execute(sql_delete_admin, (t_id,))

        conn.commit()
        print(f"[SUCCESS] User {t_id} is now a Player.")
        return True

    except Error as e:
        conn.rollback()
        print(f"[CRITICAL DB ERROR] Revoke Failed: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_player_high_scores(player_id):
    """Fetches the top 10 highest scores for a specific player."""
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT gs.StartTime, dl.LevelName, gp.Score, gp.IsWinner
            FROM GameParticipant gp
            JOIN GameSession gs ON gs.GameSessionID = gp.GameSessionID
            JOIN DifficultyLevel dl ON gs.DifficultyID = dl.DifficultyID
            WHERE gp.PlayerID = %s
            ORDER BY gp.Score DESC
            LIMIT 10
        """
        cursor.execute(sql, (player_id,))
        return cursor.fetchall()
    except Error as e:
        print(f"DB Error: {e}")
        return []
    finally:
        cursor.close(); conn.close()



def update_password(player_id, new_password):
    """
    Updates password in the USER table.
    """
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
        # UPDATED: Update User table
        sql = "UPDATE User SET PasswordHash=%s, Salt=%s WHERE UserID=%s"
        cursor.execute(sql, (hash_hex, salt_hex, player_id))
        conn.commit()
        return {'success': True, 'message': "Password changed successfully!"}
    except Error as e:
        return {'success': False, 'message': f"Database error: {e}"}
    finally:
        cursor.close()
        conn.close()

def get_top_scores():
    
    conn = get_db_connection()
    if conn is None: return []

    cursor = conn.cursor(dictionary=True)
    top_scores = []
    try:
        # UPDATED SQL JOIN
        sql = """
            SELECT u.Username, gp.Score, d.LevelName
            FROM GameParticipant gp
            JOIN Player p ON p.PlayerID = gp.PlayerID
            JOIN User u ON u.UserID = p.PlayerID
            JOIN GameSession gs ON gs.GameSessionID = gp.GameSessionID
            JOIN DifficultyLevel d ON d.DifficultyID = gs.DifficultyID
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

# --- GAMEPLAY FUNCTIONS (These remain mostly the same) ---

def get_player_achievements(player_id):
    conn = get_db_connection()
    if conn is None: return set()
    cursor = conn.cursor()
    earned_set = set()
    try:
        sql = "SELECT AchievementID FROM PlayerAchievement WHERE PlayerID = %s"
        cursor.execute(sql, (player_id,))
        results = cursor.fetchall()
        earned_set = {row[0] for row in results}
    except Error as e:
        print(f"DB Error: {e}")
    finally:
        cursor.close(); conn.close()
    return earned_set

def grant_achievement(player_id, achievement_id):
    conn = get_db_connection()
    if conn is None: return
    cursor = conn.cursor()
    try:
        sql = "INSERT IGNORE INTO PlayerAchievement (PlayerID, AchievementID, DateEarned) VALUES (%s, %s, NOW())"
        cursor.execute(sql, (player_id, achievement_id))
        conn.commit()
    except Error as e:
        print(f"DB Error: {e}"); conn.rollback()
    finally:
        cursor.close(); conn.close()

def check_all_achievements(player_id, difficulty_id, timer, shots, fouls, did_win):
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    newly_earned = []
    try:
        cursor.execute("CALL sp_CheckPlayerAchievements(%s,%s,%s,%s,%s,%s)", 
                       (player_id, difficulty_id, timer, shots, fouls, did_win))
        newly_earned = cursor.fetchall()
        while cursor.nextset(): pass # Consume results
        conn.commit()
    except Error as e:
        print("DB Error:", e); conn.rollback()
    finally:
        cursor.close(); conn.close()
    return newly_earned

def get_all_achievements_list():
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    results = []
    try:
        cursor.execute("SELECT AchievementID, Name, Description FROM Achievement ORDER BY AchievementID")
        results = cursor.fetchall()
    except Error as e:
        print(f"DB Error: {e}")
    finally:
        cursor.close(); conn.close()
    return results

def save_game_session(player_id, difficulty_id, score, did_win):
    conn = get_db_connection()
    if conn is None: return None
    cursor = conn.cursor()
    sid = None
    try:
        cursor.execute("INSERT INTO GameSession (DifficultyID) VALUES (%s)", (difficulty_id,))
        sid = cursor.lastrowid
        cursor.execute("INSERT INTO GameParticipant (GameSessionID, PlayerID, Score, IsWinner) VALUES (%s, %s, %s, %s)", 
                       (sid, player_id, int(score), did_win))
        conn.commit()
    except Error as e:
        print(f"DB Error: {e}")
    finally:
        cursor.close(); conn.close()
    return sid

def save_event_log(game_session_id, event_list):
    if not event_list or game_session_id is None: return
    conn = get_db_connection()
    if conn is None: return
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO GameEvent (GameSessionID, PlayerID, PocketID, BallPotted, EventType) VALUES (%s, %s, %s, %s, %s)"
        data = [(game_session_id,) + tuple(e) for e in event_list]
        cursor.executemany(sql, data)
        conn.commit()
    except Error as e:
        print(f"DB Error: {e}")
    finally:
        cursor.close(); conn.close()

def get_full_game_history(player_id):
    # This remains the same because it queries GameSession/Participant which still link to PlayerID
    conn = get_db_connection()
    if conn is None: return []
    cursor = conn.cursor(dictionary=True)
    history_data = []
    try:
        sql_sessions = """
            SELECT gs.GameSessionID, gs.StartTime, gp.Score, gp.IsWinner, dl.LevelName
            FROM GameSession gs
            JOIN GameParticipant gp ON gs.GameSessionID = gp.GameSessionID
            JOIN DifficultyLevel dl ON gs.DifficultyID = dl.DifficultyID
            WHERE gp.PlayerID = %s
            ORDER BY gs.StartTime DESC LIMIT 10
        """
        cursor.execute(sql_sessions, (player_id,))
        sessions = cursor.fetchall()
        for session in sessions:
            sid = session['GameSessionID']
            cursor.execute("SELECT EventType, BallPotted, PocketID, EventTime FROM GameEvent WHERE GameSessionID = %s ORDER BY EventTime ASC", (sid,))
            events = cursor.fetchall()
            history_data.append({"info": session, "events": events})
    except Error as e:
        print(f"DB Error: {e}")
    finally:
        cursor.close(); conn.close()
    return history_data