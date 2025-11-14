import mysql.connector
from mysql.connector import Error

def connect_and_test():
    """
    Connects to the pool_game_db database and
    runs a test query on the DifficultyLevel table.
    """
    
    # --- 1. Connection Details ---
    # Replace these with your MySQL Workbench credentials
    db_host = "localhost"
    db_name = "pool_game_db"
    db_user = "root"
    db_pass = "roo123"  # The password you set for MySQL

    conn = None
    cursor = None
    
    try:
        # --- 2. Open a Connection ---
        print("Connecting to database...")
        conn = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        print("Connection successful!")

        # --- 3. Execute a Test Query ---
        # A "cursor" is an object that runs queries and fetches results
        cursor = conn.cursor()

        print("Running test query on 'DifficultyLevel' table...")
        sql_query = "SELECT DifficultyID, LevelName FROM DifficultyLevel"
        cursor.execute(sql_query)

        # --- 4. Process the Results ---
        # .fetchall() grabs all rows from the query result
        results = cursor.fetchall()
        
        for row in results:
            # Data is returned as a tuple (id, name)
            id = row[0]
            name = row[1]
            print(f"  > ID: {id}, Name: {name}")

        print("Query finished. All data printed.")

    except Error as e:
        # Handle errors
        print(f"Error connecting to MySQL: {e}")
        if str(e)._contains_("Access denied"):
            print("HINT: Check your 'db_user' and 'db_pass' variables.")

    finally:
        # --- 5. Always Close Resources ---
        # This block runs whether there was an error or not
        print("Closing resources...")
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            
    print("Goodbye!")


# --- This makes the script runnable ---
if __name__ == "__main__":
    connect_and_test()