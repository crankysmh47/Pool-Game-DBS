import socket
import threading
import json
import auth
import datetime
import struct

# Configuration
HOST = '127.0.0.1'
PORT = 65432

from decimal import Decimal 

# Helper to serialize Dates AND Decimals for JSON
def json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, Decimal): 
        return int(obj)          # Convert Decimal to Int
    raise TypeError(f"Type {type(obj)} not serializable")

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    try:
        while True:
            # Receive data (up to 8KB buffer)
            data = conn.recv(8192).decode('utf-8')
            if not data: break

            try:
                request = json.loads(data)
                cmd = request.get('command')
                p = request.get('payload', {})
                response = {"status": "error", "message": "Unknown command"}

                # --- ROUTING LOGIC ---
                if cmd == "LOGIN":
                    response = auth.login_player(p['username'], p['password'])

                elif cmd == "REGISTER":
                    response = auth.register_player(p['username'], p['password'])

                elif cmd == "CHANGE_PASSWORD":
                    response = auth.update_password(p['player_id'], p['new_password'])

                elif cmd == "GET_ACHIEVEMENTS":
                    # Convert SET to LIST for JSON
                    ach_set = auth.get_player_achievements(p['player_id'])
                    response = {"status": "success", "data": list(ach_set)}

                elif cmd == "GET_ALL_ACHIEVEMENTS":
                    data = auth.get_all_achievements_list()
                    response = {"status": "success", "data": data}

                elif cmd == "GET_HISTORY":
                    data = auth.get_full_game_history(p['player_id'])
                    response = {"status": "success", "data": data}

                elif cmd == "GRANT_ACHIEVEMENT":
                    auth.grant_achievement(p['player_id'], p['achievement_id'])
                    response = {"status": "success"}

                elif cmd == "SAVE_SESSION":
                    sid = auth.save_game_session(p['pid'], p['diff'], p['score'], p['win'])
                    response = {"status": "success", "session_id": sid}

                elif cmd == "SAVE_EVENTS":
                    # Reconstruct list of tuples from list of lists
                    events = [tuple(x) for x in p['events']] 
                    auth.save_event_log(p['session_id'], events)
                    response = {"status": "success"}

                elif cmd == "CHECK_ACHIEVEMENTS":
                    new_achs = auth.check_all_achievements(
                        p['pid'], p['diff'], p['timer'], p['shots'], p['fouls'], p['win']
                    )
                    response = {"status": "success", "data": new_achs}

                
                elif cmd == "GET_ALL_USERS":
                    # In a real app, verify p['requester_role'] == 'ADMIN' here
                    data = auth.get_all_users_for_admin()
                    response = {"status": "success", "data": data}

                elif cmd == "PROMOTE_USER":
                    success = auth.promote_user(p['target_id'])
                    msg = "User Promoted!" if success else "Database Error"
                    response = {"status": "success" if success else "error", "message": msg}


                elif cmd == "GET_PLAYER_HIGH_SCORES":
                    data = auth.get_player_high_scores(p['player_id'])
                    response = {"status": "success", "data": data}

                elif cmd == "REVOKE_ADMIN":
                    success = auth.revoke_admin(p['target_id'])
                    t_id = p.get('target_id')
                    print(f"[SERVER DEBUG] Received REVOKE request for ID: {t_id} (Type: {type(t_id)})")
                    msg = "Admin Revoked" if success else "DB Error"
                    response = {"status": "success" if success else "error", "message": msg}


                elif cmd == "BAN_USER":
                    success = auth.ban_user(p['target_id'])
                    msg = "User Banned/Deleted" if success else "DB Error"
                    response = {"status": "success" if success else "error", "message": msg}

                
                # Send Response (using custom serializer for dates)
                json_data = json.dumps(response, default=json_serial).encode('utf-8')
                    
                    # 2. Pack the length of the data into 4 bytes (Big Endian integer)
                msg_length = struct.pack('>I', len(json_data))
                    
                    # 3. Send Length + Data
                conn.sendall(msg_length + json_data)

            except json.JSONDecodeError:
                print(f"[{addr}] JSON Error")
            except Exception as e:
                print(f"[{addr}] Logic Error: {e}")
                conn.sendall(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

    except ConnectionResetError:
        pass
    finally:
        conn.close()
        print(f"[DISCONNECTED] {addr}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()