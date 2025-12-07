import pygame
import math
import sys
import socket
import json

# --- NETWORK HELPER CLASS ---
class NetworkClient:
    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 65432

    def send(self, command, payload={}):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                msg = json.dumps({"command": command, "payload": payload})
                s.sendall(msg.encode('utf-8'))
                
                # Receive response (increase buffer for history data)
                data = s.recv(16384).decode('utf-8')
                return json.loads(data)
        except Exception as e:
            print(f"Network Error: {e}")
            return {"status": "error", "message": "Server Offline"}

# Initialize Network Global
net = NetworkClient()

# --- Pygame Setup ---
pygame.init()
pygame.mixer.init()

# --- 1. VIRTUAL RESOLUTION SETTINGS ---
V_WIDTH = 1200
V_HEIGHT = 650
screen = pygame.display.set_mode((V_WIDTH, V_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Pool Game (Client-Server Architecture)")
canvas = pygame.Surface((V_WIDTH, V_HEIGHT))

# Scale tracking
scale_x = 1.0
scale_y = 1.0
clock = pygame.time.Clock()

# --- Fonts ---
main_font = pygame.font.SysFont("Arial", 25)
title_font = pygame.font.SysFont("Arial", 35)
foul_font = pygame.font.SysFont("Arial", 50)
achievement_font = pygame.font.SysFont("Arial", 20, bold=True)

# --- Constants & Colors ---
TABLE_START_X = V_WIDTH // 4
FELT_BLUE = (0, 51, 102)
CUSHION_DARK = (0, 40, 80)
RAIL_WOOD = (60, 40, 20)
DIAMOND_MARKER = (220, 220, 220)
SHADOW_COLOR = (0, 0, 0, 80)
SKYBLUE = (135, 206, 235)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 128, 0)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
DARKPURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
DARKGREEN = (0, 100, 0)
PINK = (255, 192, 203)
GOLD = (255, 215, 0)

# ---- Load Ball Images ----
try:
    ball_images = {
        1: pygame.image.load("assets/ball1.png"), 2: pygame.image.load("assets/ball2.png"),
        3: pygame.image.load("assets/ball3.png"), 4: pygame.image.load("assets/ball4.png"),
        5: pygame.image.load("assets/ball5.png"), 6: pygame.image.load("assets/ball6.png"),
        7: pygame.image.load("assets/ball7.png"), 8: pygame.image.load("assets/ball8.png"),
        9: pygame.image.load("assets/ball9.png"), 0: pygame.image.load("assets/cue.png")
    }
except:
    # Fallback if assets missing
    ball_images = {}

BALL_NAMES = {
    0: "Cue Ball", 1: "Ball#1", 2: "Ball#2", 3: "Ball#3",
    4: "Ball#4", 5: "Ball#5", 6: "Ball#6", 7: "Ball#7",
    8: "Ball#8", 9: "Ball#9"
}

# --- Sound Setup ---
try:
    bg_music = pygame.mixer.music.load("assets/sound/bgm.mp3")
    collision_sound = pygame.mixer.Sound("assets/sound/collision.wav")
    potting_sound = pygame.mixer.Sound("assets/sound/ball_pocket.wav")
except FileNotFoundError:
    print("Sound files not found. Game will run without sound.")
    collision_sound = None; potting_sound = None

# --- Helper Functions ---
def get_virtual_mouse_pos():
    mx, my = pygame.mouse.get_pos()
    current_w, current_h = screen.get_size()
    ratio_x = V_WIDTH / current_w
    ratio_y = V_HEIGHT / current_h
    return mx * ratio_x, my * ratio_y

def play_sound(sound):
    if sound: sound.play()

def draw_text(text, font, color, x, y):
    text_surface = font.render(text, True, color)
    canvas.blit(text_surface, (x, y))

def get_safe_cue_spawn_pos(target_x, target_y, cue_radius, other_balls):
    safe_x, safe_y = target_x, target_y
    is_unsafe = True; attempts = 0
    while is_unsafe and attempts < 50:
        is_unsafe = False
        for ball in other_balls:
            if not ball.did_go:
                dx = safe_x - ball.x; dy = safe_y - ball.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < (cue_radius + ball.radius + 2):
                    is_unsafe = True; break
        if is_unsafe: safe_x += (cue_radius * 2) + 5; attempts += 1
    return safe_x, safe_y

def check_collision_circles(pos1, r1, pos2, r2):
    dx = pos1[0] - pos2[0]; dy = pos1[1] - pos2[1]
    return math.sqrt(dx * dx + dy * dy) < r1 + r2

def handle_collision(ball1, ball):
    dx = ball.x - ball1.x; dy = ball.y - ball1.y
    distance = math.sqrt(dx * dx + dy * dy)
    if distance < 1e-6:
        dx = 0.01; dy = 0.01
        ball.x += dx; ball.y += dy
        dx = ball.x - ball1.x; dy = ball.y - ball1.y
        distance = math.sqrt(dx * dx + dy * dy)
    nx = dx / distance; ny = dy / distance
    relative_speed_x = ball.speedx - ball1.speedx
    relative_speed_y = ball.speedy - ball1.speedy
    impact_speed = relative_speed_x * nx + relative_speed_y * ny
    if impact_speed > 0: return
    restitution = 0.8
    impulse = -(1 + restitution) * impact_speed / 2.0
    ball1.speedx -= impulse * nx; ball1.speedy -= impulse * ny
    ball.speedx += impulse * nx; ball.speedy += impulse * ny

def draw_pool_table(holes):
    # Simplified drawing for brevity (Logic remains same as original)
    pygame.draw.rect(canvas, (25, 25, 25), (0, 0, TABLE_START_X, V_HEIGHT))
    RAIL_THICKNESS = 50
    PLAY_TOP = RAIL_THICKNESS
    PLAY_BOTTOM = V_HEIGHT - RAIL_THICKNESS
    PLAY_LEFT = TABLE_START_X + RAIL_THICKNESS
    PLAY_RIGHT = V_WIDTH - RAIL_THICKNESS
    PLAY_WIDTH = PLAY_RIGHT - PLAY_LEFT
    PLAY_HEIGHT = PLAY_BOTTOM - PLAY_TOP
    pygame.draw.rect(canvas, FELT_BLUE, (PLAY_LEFT - 20, PLAY_TOP - 20, PLAY_WIDTH + 40, PLAY_HEIGHT + 40))
    pygame.draw.rect(canvas, CUSHION_DARK, (PLAY_LEFT - 15, PLAY_TOP, 15, PLAY_HEIGHT))
    pygame.draw.rect(canvas, CUSHION_DARK, (PLAY_RIGHT, PLAY_TOP, 15, PLAY_HEIGHT))
    pygame.draw.rect(canvas, CUSHION_DARK, (PLAY_LEFT, PLAY_TOP - 15, PLAY_WIDTH, 15))
    pygame.draw.rect(canvas, CUSHION_DARK, (PLAY_LEFT, PLAY_BOTTOM, PLAY_WIDTH, 15))
    for hole in holes:
        pygame.draw.circle(canvas, BLACK, (int(hole.x), int(hole.y)), hole.radius)
        pygame.draw.circle(canvas, (20, 20, 20), (int(hole.x), int(hole.y)), hole.radius - 2, 2)
    head_line_x = PLAY_LEFT + (PLAY_WIDTH * 0.25)
    pygame.draw.line(canvas, (150, 180, 220), (int(head_line_x), PLAY_TOP), (int(head_line_x), PLAY_BOTTOM), 2)
    # Rails
    pygame.draw.rect(canvas, RAIL_WOOD, (PLAY_LEFT - 50, PLAY_TOP, 50, PLAY_HEIGHT))
    pygame.draw.rect(canvas, RAIL_WOOD, (PLAY_RIGHT, PLAY_TOP, 50, PLAY_HEIGHT))
    pygame.draw.rect(canvas, RAIL_WOOD, (PLAY_LEFT, PLAY_TOP - 50, PLAY_WIDTH, 50))
    pygame.draw.rect(canvas, RAIL_WOOD, (PLAY_LEFT, PLAY_BOTTOM, PLAY_WIDTH, 50))
    
    draw_text("POOL GAME AD", achievement_font, (255, 255, 255), PLAY_LEFT + PLAY_WIDTH / 2 - 60, PLAY_TOP + PLAY_HEIGHT / 2 - 10)

class Ball:
    def __init__(self, x, y, color):
        self.x = x; self.y = y
        self.radius = 20
        self.speedx = 0; self.speedy = 0
        self.color = color; self.is_moving = False
        self.did_go = False; self.angle = 0; self.ball_id = 0

    def draw(self):
        if not self.did_go:
            # Shadow
            shadow_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(shadow_surf, SHADOW_COLOR, (self.radius, self.radius), self.radius - 2)
            canvas.blit(shadow_surf, (self.x - self.radius + 3, self.y - self.radius + 3))
            
            # Use image if available, else circle
            if self.ball_id in ball_images:
                img = ball_images[self.ball_id]
                img = pygame.transform.scale(img, (40, 40))
                rotated_img = pygame.transform.rotate(img, self.angle) if self.is_moving else img
                rect = rotated_img.get_rect(center=(int(self.x), int(self.y)))
                canvas.blit(rotated_img, rect)
            else:
                pygame.draw.circle(canvas, self.color, (int(self.x), int(self.y)), self.radius)

class Hole:
    def __init__(self, x, y):
        self.x = x; self.y = y
        self.radius = 30

# --- Screens ---
def post_login_menu(player_id, username, role):
    menu_font = pygame.font.SysFont("arial", 30)
    running = True
    btn_width = 300; btn_height = 60
    center_x = 450; start_y = 200; gap = 70
    
    play_btn = pygame.Rect(center_x, start_y, btn_width, btn_height)
    achieve_btn = pygame.Rect(center_x, start_y + gap, btn_width, btn_height)
    history_btn = pygame.Rect(center_x, start_y + gap * 2, btn_width, btn_height)
    pass_btn = pygame.Rect(center_x, start_y + gap * 3, btn_width, btn_height)
    logout_btn = pygame.Rect(center_x, start_y + gap * 4, btn_width, btn_height)

    while running:
        canvas.fill((30, 30, 30))
        draw_text("Welcome, " + username, title_font, WHITE, 450, 120)
        draw_text("Main Menu", title_font, GOLD, 500, 160)
        
        pygame.draw.rect(canvas, BLUE, play_btn)
        draw_text("PLAY GAME", menu_font, WHITE, play_btn.x + 70, play_btn.y + 15)
        pygame.draw.rect(canvas, GREEN, achieve_btn)
        draw_text("ACHIEVEMENTS", menu_font, WHITE, achieve_btn.x + 45, achieve_btn.y + 15)
        pygame.draw.rect(canvas, ORANGE, history_btn)
        draw_text("GAME HISTORY", menu_font, BLACK, history_btn.x + 50, history_btn.y + 15)
        pygame.draw.rect(canvas, (150, 50, 50), pass_btn)
        draw_text("CHANGE PASSWORD", menu_font, WHITE, pass_btn.x + 15, pass_btn.y + 15)
        pygame.draw.rect(canvas, RED, logout_btn)
        draw_text("LOGOUT", menu_font, WHITE, logout_btn.x + 90, logout_btn.y + 15)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                if play_btn.collidepoint((mx, my)): return "play"
                if achieve_btn.collidepoint((mx, my)): return "achievements"
                if history_btn.collidepoint((mx, my)): return "history"
                if pass_btn.collidepoint((mx, my)): change_password_screen(player_id, username)
                if logout_btn.collidepoint((mx, my)): return "logout"
        
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()
    return role

def history_screen(player_id, username):
    running = True
    # NETWORK CALL
    res = net.send("GET_HISTORY", {"player_id": player_id})
    games = res.get('data', [])
    
    scroll_y = 0; scroll_speed = 30
    start_x = 100; content_start_y = 120
    return_btn = pygame.Rect(20, 20, 150, 50)

    while running:
        canvas.fill((20, 20, 20))
        pygame.draw.rect(canvas, (20, 20, 20), (0, 0, V_WIDTH, 100))
        draw_text(f"Last 10 Games History", title_font, GOLD, 400, 30)
        pygame.draw.rect(canvas, RED, return_btn, border_radius=8)
        draw_text("RETURN", main_font, WHITE, return_btn.x + 25, return_btn.y + 10)

        current_y = content_start_y + scroll_y
        if not games: draw_text("No games played yet!", main_font, WHITE, 450, 300)

        for game in games:
            info = game['info']; events = game['events']
            header_color = (0, 100, 0) if info['IsWinner'] else (100, 0, 0)
            if -200 < current_y < V_HEIGHT:
                pygame.draw.rect(canvas, header_color, (start_x, current_y, 1000, 40), border_radius=5)
                header_text = f"Date: {info['StartTime']} | Level: {info['LevelName']} | Score: {info['Score']} | {'WIN' if info['IsWinner'] else 'LOSS'}"
                draw_text(header_text, pygame.font.SysFont("Arial", 20, bold=True), WHITE, start_x + 10, current_y + 8)
            current_y += 50
            
            for event in events:
                if -50 < current_y < V_HEIGHT:
                    # --- FIX START: Use Dictionary Keys, not Indices ---
                    evt_type = event['EventType'] 
                    details = ""
                    txt_color = WHITE
                    
                    if evt_type == "SHOT": 
                        details = "Shot taken."
                        txt_color = (150, 150, 150)
                    elif evt_type == "POTTED": 
                        details = f"Potted {event['BallPotted']} (Pocket {event['PocketID']})"
                        txt_color = GOLD
                    elif evt_type == "FOUL": 
                        details = "FOUL! Penalty applied."
                        txt_color = RED
                    elif evt_type == "COMBO": 
                        details = f"COMBO: {event['BallPotted']}"
                        txt_color = SKYBLUE
                    # --- FIX END ---

                    draw_text(f"  > {details}", pygame.font.SysFont("Consolas", 18), txt_color, start_x + 20, current_y)
                current_y += 25
            current_y += 40
        
        total_content_height = (current_y - scroll_y) - content_start_y
        min_scroll = min(0, -total_content_height + (V_HEIGHT - 150))
        if scroll_y > 0: scroll_y = 0
        if scroll_y < min_scroll: scroll_y = min_scroll

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                if return_btn.collidepoint((mx, my)): return
            if event.type == pygame.MOUSEWHEEL: scroll_y += event.y * scroll_speed
        
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()
def achievements_screen(player_id, username):
    running = True
    # NETWORK CALLS
    res_earned = net.send("GET_ACHIEVEMENTS", {"player_id": player_id})
    earned = set(res_earned.get('data', [])) # Convert list back to set
    res_all = net.send("GET_ALL_ACHIEVEMENTS", {})
    all_achievements = res_all.get('data', [])

    unlocked_color = (60, 180, 75); locked_color = (70, 70, 70)
    x, start_y = 150, 150; scroll_offset = 0; scroll_speed = 25
    return_btn = pygame.Rect(20, 20, 150, 50)

    while running:
        canvas.fill((25, 25, 25))
        draw_text(f"{username}'s Achievements", title_font, GOLD, 350, 70)
        pygame.draw.rect(canvas, (200, 50, 50), return_btn, border_radius=8)
        draw_text("RETURN", main_font, WHITE, return_btn.x + 20, return_btn.y + 10)

        y = start_y + scroll_offset
        for ach in all_achievements:
            ach_id = int(ach["AchievementID"])
            is_unlocked = ach_id in earned
            color = unlocked_color if is_unlocked else locked_color
            if -100 < y < V_HEIGHT:
                pygame.draw.rect(canvas, color, (x, y, 1000, 80), border_radius=12)
                status_text = ach["Name"] if is_unlocked else f"{ach['Name']} (Locked)"
                draw_text(status_text, main_font, WHITE if is_unlocked else (200, 200, 200), x + 15, y + 10)
                draw_text(ach["Description"], pygame.font.SysFont("Arial", 18), WHITE if is_unlocked else (170, 170, 170), x + 15, y + 45)
            y += 100

        content_height = len(all_achievements) * 100
        visible_height = V_HEIGHT - start_y - 30
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                if return_btn.collidepoint((mx, my)): return
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset += event.y * scroll_speed
                min_scroll = -(content_height - visible_height) if content_height > visible_height else 0
                scroll_offset = max(min(scroll_offset, 0), min_scroll)
        
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()

def difficulty_screen():
    while True:
        center_x = V_WIDTH // 2
        easy_button = pygame.Rect(center_x - 125, V_HEIGHT * 0.3, 250, 70)
        medium_button = pygame.Rect(center_x - 125, V_HEIGHT * 0.5, 250, 70)
        hard_button = pygame.Rect(center_x - 125, V_HEIGHT * 0.7, 250, 70)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                if easy_button.collidepoint((mx, my)): return 1
                elif medium_button.collidepoint((mx, my)): return 2
                elif hard_button.collidepoint((mx, my)): return 3

        canvas.fill(BLACK)
        draw_text("Select Difficulty", title_font, WHITE, center_x - 100, V_HEIGHT * 0.1)
        pygame.draw.rect(canvas, GREEN, easy_button)
        draw_text("Easy", title_font, BLACK, easy_button.x + 90, easy_button.y + 15)
        pygame.draw.rect(canvas, YELLOW, medium_button)
        draw_text("Medium", title_font, BLACK, medium_button.x + 70, medium_button.y + 15)
        pygame.draw.rect(canvas, RED, hard_button)
        draw_text("Hard", title_font, BLACK, hard_button.x + 90, hard_button.y + 15)
        
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()

def login_register_screen():
    username, password = "", ""; message = "Enter Username & Password"
    active_field = "username"
    
    while True:
        center_x = V_WIDTH // 2
        input_box_user = pygame.Rect(center_x - 200, V_HEIGHT * 0.3, 400, 50)
        input_box_pass = pygame.Rect(center_x - 200, V_HEIGHT * 0.45, 400, 50)
        button_login = pygame.Rect(center_x - 200, V_HEIGHT * 0.6, 180, 50)
        button_register = pygame.Rect(center_x + 20, V_HEIGHT * 0.6, 180, 50)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                if input_box_user.collidepoint((mx, my)): active_field = "username"
                elif input_box_pass.collidepoint((mx, my)): active_field = "password"
                elif button_login.collidepoint((mx, my)):
                    # NETWORK CALL
                    res = net.send("LOGIN", {"username": username, "password": password})
                    message = res.get('message', "Error")
                    if res.get('success'): 
                        return res['player_id'], username, res.get('role', 'PLAYER')
                elif button_register.collidepoint((mx, my)):
                    # NETWORK CALL
                    res = net.send("REGISTER", {"username": username, "password": password})
                    message = res.get('message', "Error")

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    if active_field == "username": username = username[:-1]
                    else: password = password[:-1]
                else:
                    if active_field == "username": username += event.unicode
                    else: password += event.unicode

        canvas.fill(BLACK)
        draw_text("Pool Game Login", title_font, WHITE, center_x - 120, V_HEIGHT * 0.1)
        draw_text(message, main_font, RED, center_x - 150, V_HEIGHT * 0.8)
        pygame.draw.rect(canvas, WHITE if active_field == "username" else (200,200,200), input_box_user, 2)
        draw_text(username, main_font, WHITE, input_box_user.x + 5, input_box_user.y + 5)
        pygame.draw.rect(canvas, WHITE if active_field == "password" else (200,200,200), input_box_pass, 2)
        draw_text('*' * len(password), main_font, WHITE, input_box_pass.x + 5, input_box_pass.y + 5)
        pygame.draw.rect(canvas, GREEN, button_login)
        draw_text("Login", main_font, BLACK, button_login.x + 60, button_login.y + 10)
        pygame.draw.rect(canvas, BLUE, button_register)
        draw_text("Register", main_font, BLACK, button_register.x + 40, button_register.y + 10)
        
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()

def change_password_screen(player_id, username):
    current_pass, new_pass, msg = "", "", ""
    active = "current"
    input_box_current = pygame.Rect(450, 250, 300, 50)
    input_box_new = pygame.Rect(450, 330, 300, 50)
    save_button = pygame.Rect(450, 420, 300, 60)
    return_button = pygame.Rect(450, 500, 300, 60)

    while True:
        canvas.fill((20, 20, 20))
        draw_text("Change Password", title_font, GOLD, 450, 150)
        draw_text("New Password:", main_font, WHITE, 300, 340)
        pygame.draw.rect(canvas, WHITE, input_box_new, 2)
        draw_text('*' * len(new_pass), main_font, WHITE, input_box_new.x + 5, input_box_new.y + 5)
        pygame.draw.rect(canvas, GREEN, save_button)
        draw_text("SAVE PASSWORD", main_font, BLACK, save_button.x + 40, save_button.y + 15)
        pygame.draw.rect(canvas, BLUE, return_button)
        draw_text("RETURN", main_font, WHITE, return_button.x + 95, return_button.y + 15)
        draw_text(msg, main_font, RED, 450, 500)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                if input_box_new.collidepoint((mx, my)): active = "new"
                elif save_button.collidepoint((mx, my)):
                    # NETWORK CALL
                    res = net.send("CHANGE_PASSWORD", {"player_id": player_id, "new_password": new_pass})
                    msg = res.get('message', "Error")
                    if res.get('success'): new_pass = ""
                elif return_button.collidepoint((mx, my)): return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE: new_pass = new_pass[:-1]
                else: new_pass += event.unicode
        
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()


def admin_screen(admin_id, admin_username):
    running = True
    
    # 1. Fetch Data
    res = net.send("GET_ALL_USERS", {})
    users = res.get('data', [])
    current_idx = 0
    
    # UI Layout
    panel_rect = pygame.Rect(V_WIDTH//2 - 300, 100, 600, 450)
    prev_btn = pygame.Rect(panel_rect.x + 20, panel_rect.y + 100, 50, 50)
    next_btn = pygame.Rect(panel_rect.right - 70, panel_rect.y + 100, 50, 50)
    promote_btn = pygame.Rect(panel_rect.x + 150, panel_rect.y + 350, 300, 60)
    return_btn = pygame.Rect(20, 20, 150, 50)
    
    status_msg = "Ready"
    msg_color = WHITE

    while running:
        canvas.fill((10, 10, 10))
        draw_text(f"Admin Panel: {admin_username}", title_font, GOLD, 20, 80)
        
        # Return Button
        pygame.draw.rect(canvas, RED, return_btn, border_radius=8)
        draw_text("RETURN", main_font, WHITE, return_btn.x + 25, return_btn.y + 10)

        # Draw Main Panel
        pygame.draw.rect(canvas, (30, 30, 30), panel_rect, border_radius=15)
        pygame.draw.rect(canvas, WHITE, panel_rect, 2, border_radius=15)

        if users:
            user = users[current_idx]
            
            # --- "DROPDOWN" / SELECTOR ---
            # Prev Arrow
            pygame.draw.rect(canvas, BLUE, prev_btn)
            draw_text("<", title_font, WHITE, prev_btn.x + 15, prev_btn.y + 5)
            # Next Arrow
            pygame.draw.rect(canvas, BLUE, next_btn)
            draw_text(">", title_font, WHITE, next_btn.x + 15, next_btn.y + 5)
            
            # Display Selected User Data
            cx = panel_rect.centerx
            draw_text(f"User: {user['Username']}", title_font, WHITE, cx - 100, panel_rect.y + 40)
            draw_text(f"ID: {user['UserID']}", main_font, (150,150,150), cx - 100, panel_rect.y + 110)
            
            role_color = GREEN if user['Role'] == 'ADMIN' else YELLOW
            draw_text(f"Role: {user['Role']}", main_font, role_color, cx - 100, panel_rect.y + 150)
            
            draw_text(f"Games Played: {user['GamesPlayed']}", main_font, WHITE, cx - 100, panel_rect.y + 200)
            draw_text(f"Wins: {user['Wins']}", main_font, WHITE, cx - 100, panel_rect.y + 240)

            # Promote Button (Only if not already admin)
            if user['Role'] != 'ADMIN':
                pygame.draw.rect(canvas, GREEN, promote_btn, border_radius=10)
                draw_text("MAKE ADMIN", title_font, BLACK, promote_btn.x + 50, promote_btn.y + 10)
            else:
                draw_text("User is already Admin", main_font, GREEN, cx - 100, promote_btn.y + 20)

        else:
            draw_text("No users found.", title_font, RED, panel_rect.x + 200, panel_rect.y + 200)

        # Status Message
        draw_text(status_msg, main_font, msg_color, panel_rect.x + 20, panel_rect.bottom + 20)

        # Event Loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                
                if return_btn.collidepoint((mx, my)): return
                
                if users:
                    if prev_btn.collidepoint((mx, my)):
                        current_idx = (current_idx - 1) % len(users)
                        status_msg = "Ready"; msg_color = WHITE
                    
                    if next_btn.collidepoint((mx, my)):
                        current_idx = (current_idx + 1) % len(users)
                        status_msg = "Ready"; msg_color = WHITE
                        
                    if users[current_idx]['Role'] != 'ADMIN' and promote_btn.collidepoint((mx, my)):
                        # Network Call to Promote
                        res = net.send("PROMOTE_USER", {"target_id": users[current_idx]['UserID']})
                        if res.get('status') == 'success':
                            users[current_idx]['Role'] = 'ADMIN' # Update local cache immediately
                            status_msg = f"Promoted {users[current_idx]['Username']}!"; msg_color = GREEN
                        else:
                            status_msg = "Error promoting user."; msg_color = RED

        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()

def admin_dashboard_screen(win, net):
    run = True
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("comicsans", 40)

    while run:
        win.fill((30, 30, 30)) # Dark grey background
        text = font.render("ADMIN DASHBOARD (Press ESC to quit)", 1, (255, 255, 255))
        win.blit(text, (100, 300))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    run = False
        
        clock.tick(60)



def main_game(player_id, username, difficulty_id):
    game_over = False; game_over_saved = False; did_win = False
    show_message = False; message_timer = 0; timer = 0.0
    foul_waiting_for_stop = False; game_events = []

    # NETWORK CALL: Cache achievements
    res = net.send("GET_ACHIEVEMENTS", {"player_id": player_id})
    earned_achievements_cache = set(res.get('data', []))
    
    achievement_popup_queue = []
    FIRST_POT_ID = 8; COMBO_ACHIEVEMENT_ID = 7

    if difficulty_id == 1:
        countdown_time = 500; aiming_level = 'easy'; hole_radius_change = 5; difficulty_factor = 1.0
    elif difficulty_id == 2:
        countdown_time = 400; aiming_level = 'medium'; hole_radius_change = 0; difficulty_factor = 1.35
    else:
        countdown_time = 300; aiming_level = 'hard'; hole_radius_change = -5; difficulty_factor = 1.75

    score = 0.0; shots = 0; fouls = 0
    balls_potted_this_shot = 0; total_balls_potted_game = 0

    # Table & Balls Setup
    RAIL_THICKNESS = 50
    PLAY_TOP = RAIL_THICKNESS; PLAY_BOTTOM = V_HEIGHT - RAIL_THICKNESS
    PLAY_LEFT = TABLE_START_X + RAIL_THICKNESS; PLAY_RIGHT = V_WIDTH - RAIL_THICKNESS
    PLAY_WIDTH = PLAY_RIGHT - PLAY_LEFT; PLAY_HEIGHT = PLAY_BOTTOM - PLAY_TOP

    startX = PLAY_LEFT + (PLAY_WIDTH * 0.75); startY = PLAY_TOP + (PLAY_HEIGHT / 2)
    cue_startX = PLAY_LEFT + (PLAY_WIDTH * 0.25); cue_startY = startY
    cue = Ball(cue_startX, cue_startY, WHITE); cue.ball_id = 0

    spacing_factor = 1.1
    balls = [
        Ball(startX - 60 * spacing_factor, startY, YELLOW), Ball(startX - 20 * spacing_factor, startY + 75 * spacing_factor, BLUE),
        Ball(startX + 20 * spacing_factor, startY, RED), Ball(startX - 40 * spacing_factor, startY - 37 * spacing_factor, DARKPURPLE),
        Ball(startX, startY - 37 * spacing_factor, ORANGE), Ball(startX - 20 * spacing_factor, startY - 75 * spacing_factor, DARKGREEN),
        Ball(startX - 40 * spacing_factor, startY + 37 * spacing_factor, BROWN), Ball(startX, startY + 37 * spacing_factor, BLACK),
        Ball(startX - 20 * spacing_factor, startY, PINK)
    ]
    for i, ball in enumerate(balls, start=1): ball.ball_id = i

    holes = [
        Hole(PLAY_LEFT, PLAY_TOP), Hole(PLAY_LEFT + PLAY_WIDTH / 2, PLAY_TOP - 5), Hole(PLAY_RIGHT, PLAY_TOP),
        Hole(PLAY_LEFT, PLAY_BOTTOM), Hole(PLAY_LEFT + PLAY_WIDTH / 2, PLAY_BOTTOM + 5), Hole(PLAY_RIGHT, PLAY_BOTTOM)
    ]
    for hole in holes: hole.radius = 30 + (hole_radius_change if difficulty_id == 1 else 0)

    def is_near_hole(ball):
        for hole in holes:
            if math.sqrt((ball.x - hole.x)**2 + (ball.y - hole.y)**2) < 50: return True
        return False

    is_aiming = False; running = True; music_playing = False; countdown_finished = False

    while running:
        delta_time = clock.tick(60) / 1000.0

        if foul_waiting_for_stop:
            if all(not b.is_moving for b in balls):
                respawn_x, respawn_y = get_safe_cue_spawn_pos(cue_startX, cue_startY, cue.radius, balls)
                cue.x = respawn_x; cue.y = respawn_y; cue.speedx = 0; cue.speedy = 0
                cue.is_moving = False; foul_waiting_for_stop = False

        if shots == 0 and not music_playing:
            if bg_music: pygame.mixer.music.play(-1); music_playing = True
        elif shots > 0 and music_playing:
            pygame.mixer.music.stop(); music_playing = False

        col_snd = False; pot_snd = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if not cue.is_moving and not game_over and not foul_waiting_for_stop:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    is_aiming = True; balls_potted_this_shot = 0
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if is_aiming:
                        is_aiming = False
                        mx, my = get_virtual_mouse_pos()
                        cue.speedx = (cue.x - mx) * 2.5; cue.speedy = (cue.y - my) * 2.5
                        cue.is_moving = True; shots += 1; col_snd = True
                        game_events.append((player_id, None, None, "SHOT"))

        # Physics Loop (simplified)
        if not foul_waiting_for_stop:
            cue.x += cue.speedx * delta_time; cue.y += cue.speedy * delta_time
            cue.speedx *= 0.99; cue.speedy *= 0.99
            if abs(cue.speedx) < 5 and abs(cue.speedy) < 5: cue.speedx, cue.speedy = 0, 0; cue.is_moving = False
            else: cue.is_moving = True
            if not is_near_hole(cue):
                if cue.x < PLAY_LEFT or cue.x > PLAY_RIGHT: cue.speedx *= -1; cue.x = max(PLAY_LEFT + 20, min(cue.x, PLAY_RIGHT - 20))
                if cue.y < PLAY_TOP or cue.y > PLAY_BOTTOM: cue.speedy *= -1; cue.y = max(PLAY_TOP + 20, min(cue.y, PLAY_BOTTOM - 20))
        
        for ball in balls:
            ball.x += ball.speedx * delta_time; ball.y += ball.speedy * delta_time
            ball.speedx *= 0.99; ball.speedy *= 0.99
            if abs(ball.speedx) < 5 and abs(ball.speedy) < 5: ball.speedx, ball.speedy = 0, 0; ball.is_moving = False
            else: ball.is_moving = True
            if not is_near_hole(ball):
                if ball.x < PLAY_LEFT or ball.x > PLAY_RIGHT: ball.speedx *= -1; ball.x = max(PLAY_LEFT + 20, min(ball.x, PLAY_RIGHT - 20))
                if ball.y < PLAY_TOP or ball.y > PLAY_BOTTOM: ball.speedy *= -1; ball.y = max(PLAY_TOP + 20, min(ball.y, PLAY_BOTTOM - 20))
            if ball.is_moving: ball.angle += (abs(ball.speedx) + abs(ball.speedy)) * 0.1

        # Collisions
        for i in range(len(balls)):
            if not balls[i].did_go:
                # Ball-Ball
                for j in range(i + 1, len(balls)):
                    if not balls[j].did_go and check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (balls[j].x, balls[j].y), balls[j].radius):
                        handle_collision(balls[i], balls[j]); col_snd = True
                # Cue-Ball
                if not foul_waiting_for_stop:
                    if check_collision_circles((cue.x, cue.y), cue.radius, (balls[i].x, balls[i].y), balls[i].radius):
                        handle_collision(cue, balls[i]); col_snd = True
                # Potting
                for idx, hole in enumerate(holes):
                    if check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (hole.x, hole.y), hole.radius):
                        if not balls[i].did_go: pot_snd = True
                        balls_potted_this_shot += 1; balls[i].did_go = True
                        balls[i].x, balls[i].y = -5000, -5000; balls[i].speedx, balls[i].speedy = 0, 0
                        game_events.append((player_id, idx+1, BALL_NAMES.get(balls[i].ball_id), "POTTED"))

        # Foul
        for hole in holes:
            if not foul_waiting_for_stop and check_collision_circles((cue.x, cue.y), cue.radius, (hole.x, hole.y), hole.radius):
                if cue.is_moving: pot_snd = True
                cue.x, cue.y = -1000, -1000; cue.speedx, cue.speedy = 0, 0; cue.is_moving = False
                foul_waiting_for_stop = True; timer += 10; show_message = True; message_timer = 0; fouls += 1
                game_events.append((player_id, None, "Cue Ball", "FOUL"))

        if show_message:
            message_timer += 1
            if message_timer > 30: show_message = False

        if col_snd: play_sound(collision_sound)
        if pot_snd: play_sound(potting_sound)

        if not game_over and shots > 0: timer += delta_time
        remaining_time = countdown_time - timer
        if remaining_time <= 0 and not countdown_finished:
            countdown_finished = True; game_over = True; did_win = False; score = 0; remaining_time = 0

        # Achievements Logic (Real-time)
        all_stopped = not cue.is_moving and all(not b.is_moving for b in balls)
        if all_stopped and shots > 0 and balls_potted_this_shot > 0:
            if FIRST_POT_ID not in earned_achievements_cache:
                # NETWORK CALL
                net.send("GRANT_ACHIEVEMENT", {"player_id": player_id, "achievement_id": FIRST_POT_ID})
                earned_achievements_cache.add(FIRST_POT_ID)
                achievement_popup_queue.append({"text": "First Potter!", "timer": 0})
            if balls_potted_this_shot >= 2:
                game_events.append((player_id, None, f"{balls_potted_this_shot} Ball Combo", "COMBO"))
                if COMBO_ACHIEVEMENT_ID not in earned_achievements_cache:
                    net.send("GRANT_ACHIEVEMENT", {"player_id": player_id, "achievement_id": COMBO_ACHIEVEMENT_ID})
                    earned_achievements_cache.add(COMBO_ACHIEVEMENT_ID)
                    achievement_popup_queue.append({"text": "Combo Shot!", "timer": 0})
            total_balls_potted_game += balls_potted_this_shot; balls_potted_this_shot = 0

        # Game Over
        if balls[8].did_go and not game_over:
            win = all(b.did_go for b in balls[:8]) # Check if others potted
            game_over = True; did_win = win
            if win: score = (((countdown_time - timer)/countdown_time)*200 - (shots*1) + 100) * difficulty_factor
            if score < 0: score = 0

        if game_over and not game_over_saved:
            # 1. Save Session (Get ID)
            res_sess = net.send("SAVE_SESSION", {"pid": player_id, "diff": difficulty_id, "score": score, "win": did_win})
            sid = res_sess.get('session_id')
            
            if sid:
                # 2. Save Events
                net.send("SAVE_EVENTS", {"session_id": sid, "events": game_events})
                
                # 3. Check End Game Achievements
                res_ach = net.send("CHECK_ACHIEVEMENTS", {
                    "pid": player_id, "diff": difficulty_id, "timer": timer, 
                    "shots": shots, "fouls": fouls, "win": did_win
                })
                for ach in res_ach.get('data', []):
                    achievement_popup_queue.append({"text": ach["Name"], "timer": 0})
            
            game_over_saved = True

        draw_pool_table(holes)
        if not game_over:
            draw_text(f"Player: {username}", title_font, WHITE, 50, 50)
            draw_text(f"Time: {remaining_time:.1f}", title_font, RED if remaining_time < 30 else SKYBLUE, 50, 100)
            if not foul_waiting_for_stop: cue.draw()
            for ball in balls: ball.draw()
            if is_aiming and not foul_waiting_for_stop:
                mx, my = get_virtual_mouse_pos()
                if aiming_level != 'hard': pygame.draw.line(canvas, WHITE, (cue.x, cue.y), (mx, my), 2)
                pygame.draw.line(canvas, RED, (cue.x, cue.y), (2 * cue.x - mx, 2 * cue.y - my), 2)
            if show_message: draw_text("FOUL (-10s)", foul_font, RED, 700, 400)
        else:
            cx = PLAY_LEFT + (PLAY_WIDTH // 2); cy = V_HEIGHT // 2
            pygame.draw.rect(canvas, (0, 0, 0, 230), (cx - 200, cy - 150, 400, 350), border_radius=20)
            msg = "YOU WON!" if did_win else ("TIME UP!" if countdown_finished else "EARLY PINK!")
            color = GREEN if did_win else RED
            draw_text(msg, foul_font, color, cx - foul_font.size(msg)[0] // 2, cy - 120)
            score_msg = f"SCORE: {score:.0f}"
            draw_text(score_msg, foul_font, WHITE, cx - foul_font.size(score_msg)[0] // 2, cy - 50)
            
            btn_y = cy + 50
            exit_btn = pygame.Rect(cx - 185, btn_y, 110, 50)
            menu_btn = pygame.Rect(cx - 55, btn_y, 110, 50)
            logout_btn = pygame.Rect(cx + 75, btn_y, 110, 50)
            
            pygame.draw.rect(canvas, RED, exit_btn, border_radius=5)
            draw_text("EXIT", main_font, WHITE, exit_btn.x + 30, exit_btn.y + 10)
            pygame.draw.rect(canvas, GREEN, menu_btn, border_radius=5)
            draw_text("MENU", main_font, BLACK, menu_btn.x + 20, menu_btn.y + 10)
            pygame.draw.rect(canvas, BLUE, logout_btn, border_radius=5)
            draw_text("LOGOUT", main_font, WHITE, logout_btn.x + 10, logout_btn.y + 10)
            
            if pygame.mouse.get_pressed()[0]:
                mx, my = get_virtual_mouse_pos()
                if exit_btn.collidepoint((mx, my)): pygame.quit(); sys.exit()
                if menu_btn.collidepoint((mx, my)): return "menu"
                if logout_btn.collidepoint((mx, my)): return "logout"

        if achievement_popup_queue:
            popup = achievement_popup_queue[0]
            r = pygame.Rect(V_WIDTH // 2 - 200, 50, 400, 80)
            pygame.draw.rect(canvas, (20, 20, 20), r, border_radius=10)
            pygame.draw.rect(canvas, GOLD, r, 3, border_radius=10)
            draw_text("Achievement Unlocked!", achievement_font, GOLD, r.x + 90, r.y + 10)
            draw_text(popup['text'], main_font, WHITE, r.x + (400 - main_font.size(popup['text'])[0]) // 2, r.y + 40)
            popup['timer'] += 1
            if popup['timer'] > 180: achievement_popup_queue.pop(0)

        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()
    pygame.quit(); sys.exit()

while True:
    pid_data = login_register_screen() # Returns tuple or None
    if pid_data is None: break
    
    # 1. Unpack Data
    player_id, username, role = pid_data 
    
    # 2. Check Role IMMEDIATELY
    if role == 'ADMIN':
        # --- ADMIN FLOW ---
        # Go straight to Admin Screen, bypassing the Player Menu
        admin_screen(player_id, username)
        
    else:
        # --- PLAYER FLOW ---
        while True:
            # Pass role to menu just in case, but this is the player loop
            choice = post_login_menu(player_id, username, role) 
            
            if choice == "play":
                difficulty_id = difficulty_screen()
                # Check if they backed out of difficulty screen
                if difficulty_id is not None: 
                    result = main_game(player_id, username, difficulty_id)
                    if result == "logout": break
            
            elif choice == "achievements": 
                achievements_screen(player_id, username)
            
            elif choice == "history": 
                history_screen(player_id, username)
                
            elif choice == "logout": 
                break

pygame.quit(); sys.exit()