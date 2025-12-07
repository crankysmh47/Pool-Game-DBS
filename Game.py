import pygame
import math
import sys
import socket
import json
import auth
import random

# --- NETWORK HELPER CLASS (DIRECT LOCAL CALLS) ---
class DirectClient:
    def send(self, command, payload={}):
        try:
            if command == "LOGIN":
                return auth.login_player(payload['username'], payload['password'])
            elif command == "REGISTER":
                return auth.register_player(payload['username'], payload['password'])
            elif command == "GET_HISTORY":
                return {'data': auth.get_full_game_history(payload['player_id'])}
            elif command == "GET_ACHIEVEMENTS":
                return {'data': list(auth.get_player_achievements(payload['player_id']))}
            elif command == "GET_ALL_ACHIEVEMENTS":
                return {'data': auth.get_all_achievements_list()}
            elif command == "GRANT_ACHIEVEMENT":
                auth.grant_achievement(payload['player_id'], payload['achievement_id'])
                return {'status': 'success'}
            elif command == "SAVE_SESSION":
                sid = auth.save_game_session(payload['pid'], payload['diff'], payload['score'], payload['win'])
                return {'session_id': sid}
            elif command == "SAVE_EVENTS":
                auth.save_event_log(payload['session_id'], payload['events'])
                return {'status': 'success'}
            elif command == "CHECK_ACHIEVEMENTS":
                new_ach = auth.check_all_achievements(payload['pid'], payload['diff'], payload['timer'], payload['shots'], payload['fouls'], payload['win'])
                return {'data': new_ach}
            elif command == "CHANGE_PASSWORD":
                return auth.update_password(payload['player_id'], payload['new_password'])
            elif command == "GET_ALL_USERS":
                return {'data': auth.get_all_users_for_admin()}
            elif command == "PROMOTE_USER":
                success = auth.promote_user(payload['target_id'])
                return {'status': 'success' if success else 'error'}
            return {'status': 'error', 'message': 'Unknown Command'}
        except Exception as e:
            print(f"DirectClient Error: {e}")
            return {'status': 'error', 'message': str(e)}

# Initialize Network Global
net = DirectClient()

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

# --- NEON & GLASS UI COLORS ---
NEON_CYAN = (0, 229, 255)
NEON_PURPLE = (218, 0, 255)
NEON_MAGENTA = (255, 0, 140)
BG_DARK = (5, 5, 10)
BG_DARK_SEC = (13, 13, 18)
GLASS_BG = (255, 255, 255, 20)  # Low alpha for glass
GLASS_BORDER = (255, 255, 255, 50)
ACCENT_WHITE = (240, 243, 245)


# --- INTERACTIVE VISUAL CLASSES ---
class Starfield:
    def __init__(self, count=100):
        self.stars = [[random.randint(0, V_WIDTH), random.randint(0, V_HEIGHT), random.random()] for _ in range(count)]
    
    def update_and_draw(self, surface):
        for star in self.stars:
            star[1] += star[2] * 0.5 # Move down slowly
            if star[1] > V_HEIGHT:
                star[1] = 0; star[0] = random.randint(0, V_WIDTH)
            
            # Parallax brightness
            brightness = int(star[2] * 255)
            color = (brightness, brightness, brightness)
            pygame.draw.circle(surface, color, (int(star[0]), int(star[1])), 1 if star[2] < 0.5 else 2)

class Particle:
    def __init__(self, x, y, color, life):
        self.x = x; self.y = y
        self.color = color; self.life = life; self.max_life = life
        angle = random.uniform(0, 6.28)
        speed = random.uniform(1, 4)
        self.vx = math.cos(angle) * speed; self.vy = math.sin(angle) * speed
        self.size = random.randint(2, 4)

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.05)

    def draw(self, surface):
        if self.life > 0:
            alpha = int((self.life / self.max_life) * 255)
            s = pygame.Surface((int(self.size)*2, int(self.size)*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (int(self.size), int(self.size)), int(self.size))
            surface.blit(s, (self.x - self.size, self.y - self.size))

class FloatingText:
    def __init__(self, x, y, text, color):
        self.x = x; self.y = y
        self.text = text; self.color = color
        self.life = 60; self.y_offset = 0

    def update(self):
        self.y_offset -= 1; self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            alpha = int((self.life / 60) * 255)
            txt = achievement_font.render(self.text, True, self.color)
            txt.set_alpha(alpha)
            surface.blit(txt, (self.x, self.y + self.y_offset))

class ScreenShake:
    def __init__(self):
        self.timer = 0; self.intensity = 0
    
    def shake(self, duration, intensity):
        self.timer = duration; self.intensity = intensity
    
    def get_offset(self):
        if self.timer > 0:
            self.timer -= 1
            return random.randint(-self.intensity, self.intensity), random.randint(-self.intensity, self.intensity)
        return 0, 0

# Global Visual Managers
starfield = Starfield()
particles = []
floating_texts = []
shaker = ScreenShake()



def draw_interactive_avatar(surface, x, y, size, state="idle", mouse_pos=(0,0)):
    # Increased visibility: Brighter colors, larger relative features
    
    # Head Glow
    glow_surf = pygame.Surface((size*3, size*3), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (0, 229, 255, 50), (size*1.5, size*1.5), size * 1.2)
    surface.blit(glow_surf, (x - size*1.5, y - size*1.5))

    # Head Base
    pygame.draw.circle(surface, BG_DARK_SEC, (x, y), size)
    pygame.draw.circle(surface, NEON_CYAN, (x, y), size, 3) # Thicker border
    
    # Eyes
    eye_radius = size // 3.5 # Larger eyes
    eye_offset_x = size // 2.8
    eye_offset_y = size // 5
    
    left_eye_pos = (x - eye_offset_x, y - eye_offset_y)
    right_eye_pos = (x + eye_offset_x, y - eye_offset_y)
    
    # Draw Sclera (Whites) - Brighter
    pygame.draw.circle(surface, (255, 255, 255), left_eye_pos, eye_radius)
    pygame.draw.circle(surface, (255, 255, 255), right_eye_pos, eye_radius)
    
    # Pupils
    pupil_radius = eye_radius // 1.8
    
    if state == "shy":
        # Look away (up and to the side)
        pupil_offset_x = eye_radius // 2
        pupil_offset_y = -eye_radius // 2
    else:
        # Track mouse
        mx, my = mouse_pos
        dx = mx - x; dy = my - y
        dist = math.sqrt(dx*dx + dy*dy)
        max_offset = eye_radius - pupil_radius
        if dist > 0:
            pupil_offset_x = int((dx / dist) * max_offset)
            pupil_offset_y = int((dy / dist) * max_offset)
        else:
            pupil_offset_x, pupil_offset_y = 0, 0

    pygame.draw.circle(surface, (10, 10, 20), (left_eye_pos[0] + pupil_offset_x, left_eye_pos[1] + pupil_offset_y), pupil_radius)
    pygame.draw.circle(surface, (10, 10, 20), (right_eye_pos[0] + pupil_offset_x, right_eye_pos[1] + pupil_offset_y), pupil_radius)
    
    # Pupil Glint
    pygame.draw.circle(surface, WHITE, (left_eye_pos[0] + pupil_offset_x - 2, left_eye_pos[1] + pupil_offset_y - 2), 3)
    pygame.draw.circle(surface, WHITE, (right_eye_pos[0] + pupil_offset_x - 2, right_eye_pos[1] + pupil_offset_y - 2), 3)

    # Hands (only if shy)
    if state == "shy":
        hand_radius = size // 2.5
        # Hands covering eyes partially
        pygame.draw.circle(surface, BG_DARK_SEC, (x - eye_offset_x, y + 10), hand_radius)
        pygame.draw.circle(surface, NEON_CYAN, (x - eye_offset_x, y + 10), hand_radius, 2)
        
        pygame.draw.circle(surface, BG_DARK_SEC, (x + eye_offset_x, y + 10), hand_radius)
        pygame.draw.circle(surface, NEON_CYAN, (x + eye_offset_x, y + 10), hand_radius, 2)

def draw_glass_panel(rect, border_color=GLASS_BORDER):
    """Draws a semi-transparent 'glass' panel with a border."""
    # 1. Background (Semi-transparent)
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    s.fill(GLASS_BG)
    canvas.blit(s, (rect.x, rect.y))
    
    # 2. Border
    pygame.draw.rect(canvas, border_color, rect, 2, border_radius=12)

def draw_neon_button(rect, text, color=NEON_CYAN, hover=False):
    """Draws a button with a neon glow effect."""
    # Glow effect (simulated with multiple rects or just color change)
    if hover:
        # Fill with low alpha color
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        r, g, b = color
        s.fill((r, g, b, 50)) # 50 alpha
        canvas.blit(s, (rect.x, rect.y))
        
        # Bright border and text
        pygame.draw.rect(canvas, color, rect, 2, border_radius=4)
        # Outer glow (simple lines for now)
        pygame.draw.rect(canvas, color, rect.inflate(4, 4), 1, border_radius=6)
        
        txt_surf = main_font.render(text, True, color)
    else:
        # Normal state
        pygame.draw.rect(canvas, color, rect, 1, border_radius=4)
        txt_surf = main_font.render(text, True, color)
    
    # Center text
    txt_rect = txt_surf.get_rect(center=rect.center)
    canvas.blit(txt_surf, txt_rect)

def draw_neon_input(rect, text, active=False, is_password=False):
    """Draws a neon-styled input box."""
    color = NEON_PURPLE if active else GLASS_BORDER
    
    # Background
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    s.fill((0, 0, 0, 100))
    canvas.blit(s, (rect.x, rect.y))
    
    # Border
    pygame.draw.rect(canvas, color, rect, 2 if active else 1, border_radius=4)
    
    # Text
    display_text = "*" * len(text) if is_password else text
    txt_surf = main_font.render(display_text, True, ACCENT_WHITE)
    canvas.blit(txt_surf, (rect.x + 10, rect.y + 10))

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
    # --- NEON POOL TABLE ---
    
    # 1. Main Background (Darker, cleaner)
    pygame.draw.rect(canvas, (10, 10, 15), (0, 0, TABLE_START_X, V_HEIGHT))
    
    RAIL_THICKNESS = 50
    PLAY_TOP = RAIL_THICKNESS
    PLAY_BOTTOM = V_HEIGHT - RAIL_THICKNESS
    PLAY_LEFT = TABLE_START_X + RAIL_THICKNESS
    PLAY_RIGHT = V_WIDTH - RAIL_THICKNESS
    PLAY_WIDTH = PLAY_RIGHT - PLAY_LEFT
    PLAY_HEIGHT = PLAY_BOTTOM - PLAY_TOP
    
    # 2. Felt (Dark Blue/Grey with subtle grid or texture if possible, sticking to solid for now)
    # Using a very dark blue for high contrast with neon balls
    FELT_COLOR = (5, 20, 40) 
    pygame.draw.rect(canvas, FELT_COLOR, (PLAY_LEFT - 20, PLAY_TOP - 20, PLAY_WIDTH + 40, PLAY_HEIGHT + 40))
    
    # 3. Rails (Neon Glowing)
    rail_color = (20, 20, 30)
    border_color = NEON_CYAN
    
    # Top Rail
    pygame.draw.rect(canvas, rail_color, (PLAY_LEFT - 50, 0, PLAY_WIDTH + 100, RAIL_THICKNESS))
    pygame.draw.rect(canvas, border_color, (PLAY_LEFT - 50, RAIL_THICKNESS, PLAY_WIDTH + 100, 2)) # Glow line
    
    # Bottom Rail
    pygame.draw.rect(canvas, rail_color, (PLAY_LEFT - 50, V_HEIGHT - RAIL_THICKNESS, PLAY_WIDTH + 100, RAIL_THICKNESS))
    pygame.draw.rect(canvas, border_color, (PLAY_LEFT - 50, V_HEIGHT - RAIL_THICKNESS, PLAY_WIDTH + 100, 2))
    
    # Left Rail
    pygame.draw.rect(canvas, rail_color, (TABLE_START_X, 0, RAIL_THICKNESS, V_HEIGHT))
    pygame.draw.rect(canvas, border_color, (TABLE_START_X + RAIL_THICKNESS, 0, 2, V_HEIGHT))
    
    # Right Rail
    pygame.draw.rect(canvas, rail_color, (V_WIDTH - RAIL_THICKNESS, 0, RAIL_THICKNESS, V_HEIGHT))
    pygame.draw.rect(canvas, border_color, (V_WIDTH - RAIL_THICKNESS, 0, 2, V_HEIGHT))

    # 4. Pockets (Glowing)
    for hole in holes:
        # Glow
        s = pygame.Surface((hole.radius*2.5, hole.radius*2.5), pygame.SRCALPHA)
        pygame.draw.circle(s, (0, 229, 255, 50), (hole.radius*1.25, hole.radius*1.25), hole.radius * 1.2)
        canvas.blit(s, (hole.x - hole.radius*1.25, hole.y - hole.radius*1.25))
        
        # Hole
        pygame.draw.circle(canvas, BLACK, (int(hole.x), int(hole.y)), hole.radius)
        pygame.draw.circle(canvas, NEON_CYAN, (int(hole.x), int(hole.y)), hole.radius, 2)

    # 5. Head Line
    head_line_x = PLAY_LEFT + (PLAY_WIDTH * 0.25)
    pygame.draw.line(canvas, (255, 255, 255, 50), (int(head_line_x), PLAY_TOP), (int(head_line_x), PLAY_BOTTOM), 1)
    
    # 6. Logo/Text
    draw_text("POOL AD", achievement_font, (255, 255, 255, 100), PLAY_LEFT + PLAY_WIDTH / 2 - 50, PLAY_TOP + PLAY_HEIGHT / 2 - 10)

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
    running = True

    # Layout
    btn_width = 300
    btn_height = 60
    center_x = V_WIDTH // 2
    start_y = 220
    gap = 80

    play_btn = pygame.Rect(center_x - btn_width//2, start_y, btn_width, btn_height)
    achieve_btn = pygame.Rect(center_x - btn_width//2, start_y + gap, btn_width, btn_height)
    history_btn = pygame.Rect(center_x - btn_width//2, start_y + gap * 2, btn_width, btn_height)
    pass_btn = pygame.Rect(center_x - btn_width//2, start_y + gap * 3, btn_width, btn_height)
    logout_btn = pygame.Rect(center_x - btn_width//2, start_y + gap * 4, btn_width, btn_height)

    while running:
        canvas.fill(BG_DARK)
        
        # Starfield BG
        starfield.update_and_draw(canvas)

        # Header
        draw_text("WELCOME, AGENT " + username.upper(), title_font, NEON_CYAN, 400, 100)
        draw_text("MAIN MENU", achievement_font, ACCENT_WHITE, 550, 150)

        mx, my = get_virtual_mouse_pos()
        
        # Buttons
        draw_neon_button(play_btn, "PLAY GAME", NEON_CYAN, play_btn.collidepoint((mx, my)))
        draw_neon_button(achieve_btn, "ACHIEVEMENTS", NEON_PURPLE, achieve_btn.collidepoint((mx, my)))
        draw_neon_button(history_btn, "MISSION HISTORY", NEON_CYAN, history_btn.collidepoint((mx, my)))
        draw_neon_button(pass_btn, "CHANGE CREDENTIALS", NEON_PURPLE, pass_btn.collidepoint((mx, my)))
        draw_neon_button(logout_btn, "LOGOUT", NEON_MAGENTA, logout_btn.collidepoint((mx, my)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_btn.collidepoint((mx, my)): return "play"
                if achieve_btn.collidepoint((mx, my)): return "achievements"
                if history_btn.collidepoint((mx, my)): return "history"
                if pass_btn.collidepoint((mx, my)): change_password_screen(player_id, username)
                if logout_btn.collidepoint((mx, my)): return "logout"

        # --- SCALING BLIT ---
            
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
        canvas.fill(BG_DARK)
        # Starfield BG
        starfield.update_and_draw(canvas)
        
        draw_text(f"MISSION HISTORY", title_font, NEON_CYAN, 400, 30)
        
        mx, my = get_virtual_mouse_pos()
        draw_neon_button(return_btn, "RETURN", NEON_MAGENTA, return_btn.collidepoint((mx, my)))

        current_y = content_start_y + scroll_y
        if not games: draw_text("No missions on record.", main_font, ACCENT_WHITE, 450, 300)

        for game in games:
            info = game['info']; events = game['events']
            
            # Glass Panel for each game
            if -200 < current_y < V_HEIGHT:
                panel_rect = pygame.Rect(start_x, current_y, 1000, 40)
                draw_glass_panel(panel_rect, NEON_CYAN if info['IsWinner'] else NEON_MAGENTA)
                
                header_text = f"Date: {info['StartTime']} | Level: {info['LevelName']} | Score: {info['Score']} | {'WIN' if info['IsWinner'] else 'LOSS'}"
                draw_text(header_text, achievement_font, ACCENT_WHITE, start_x + 15, current_y + 8)
            current_y += 50
            
            for event in events:
                if -50 < current_y < V_HEIGHT:
                    evt_type = event['EventType'] 
                    details = ""
                    txt_color = ACCENT_WHITE
                    
                    if evt_type == "SHOT": 
                        details = "Shot taken."
                        txt_color = (150, 150, 150)
                    elif evt_type == "POTTED": 
                        details = f"Potted {event['BallPotted']} (Pocket {event['PocketID']})"
                        txt_color = NEON_CYAN
                    elif evt_type == "FOUL": 
                        details = "FOUL! Penalty applied."
                        txt_color = NEON_MAGENTA
                    elif evt_type == "COMBO": 
                        details = f"COMBO: {event['BallPotted']}"
                        txt_color = NEON_PURPLE

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

    box_width, box_height = 1000, 80;
    x, start_y = 150, 150
    scroll_offset = 0;
    scroll_speed = 25
    return_btn = pygame.Rect(20, 20, 150, 50)

    while running:
        canvas.fill(BG_DARK)
        # Starfield BG
        starfield.update_and_draw(canvas)

        draw_text(f"ACHIEVEMENTS", title_font, NEON_PURPLE, 450, 70)
        
        mx, my = get_virtual_mouse_pos()
        draw_neon_button(return_btn, "RETURN", NEON_MAGENTA, return_btn.collidepoint((mx, my)))

        y = start_y + scroll_offset
        for ach in all_achievements:
            ach_id = int(ach["AchievementID"])
            is_unlocked = ach_id in earned
            
            border_color = NEON_CYAN if is_unlocked else (50, 50, 50)
            text_color = NEON_CYAN if is_unlocked else (100, 100, 100)

            if -100 < y < V_HEIGHT:
                # Glass Panel
                rect = pygame.Rect(x, y, box_width, box_height)
                draw_glass_panel(rect, border_color)
                
                status_text = ach["Name"] if is_unlocked else f"{ach['Name']} (LOCKED)"
                draw_text(status_text, achievement_font, text_color, x + 15, y + 10)
                draw_text(ach["Description"], pygame.font.SysFont("Arial", 18), ACCENT_WHITE if is_unlocked else (100, 100, 100), x + 15, y + 45)
            y += box_height + 20

        content_height = len(all_achievements) * (box_height + 20)
        visible_height = V_HEIGHT - start_y - 30
        if content_height > visible_height:
            scrollbar_height = max(40, (visible_height / content_height) * 300)
            scrollbar_y = 150 + (-scroll_offset / content_height) * 300
            pygame.draw.rect(canvas, (80, 80, 80), (1100, 150, 20, 300), border_radius=10)
            pygame.draw.rect(canvas, NEON_CYAN, (1100, scrollbar_y, 20, scrollbar_height), border_radius=10)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = get_virtual_mouse_pos()
                if return_btn.collidepoint((mx, my)): return
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset += event.y * scroll_speed
                max_scroll = 0
                min_scroll = -(content_height - visible_height) if content_height > visible_height else 0
                scroll_offset = max(min(scroll_offset, max_scroll), min_scroll)
            
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()

def difficulty_screen():
    running = True
    while running:
        canvas.fill(BG_DARK)
        # Starfield BG
        starfield.update_and_draw(canvas)

        center_x = V_WIDTH // 2
        
        # Glass Panel for Title
        title_rect = pygame.Rect(center_x - 200, 50, 400, 80)
        draw_glass_panel(title_rect, NEON_CYAN)
        draw_text("MISSION DIFFICULTY", title_font, NEON_CYAN, center_x - 140, 75)

        # Buttons
        easy_btn = pygame.Rect(center_x - 150, 200, 300, 80)
        med_btn = pygame.Rect(center_x - 150, 320, 300, 80)
        hard_btn = pygame.Rect(center_x - 150, 440, 300, 80)

        mx, my = get_virtual_mouse_pos()

        draw_neon_button(easy_btn, "ROOKIE (EASY)", NEON_CYAN, easy_btn.collidepoint((mx, my)))
        draw_neon_button(med_btn, "AGENT (MEDIUM)", NEON_PURPLE, med_btn.collidepoint((mx, my)))
        draw_neon_button(hard_btn, "VETERAN (HARD)", NEON_MAGENTA, hard_btn.collidepoint((mx, my)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if easy_btn.collidepoint((mx, my)): return 1
                elif med_btn.collidepoint((mx, my)): return 2
                elif hard_btn.collidepoint((mx, my)): return 3
            
        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()

def login_register_screen():
    username, password = "", ""
    message = "IDENTITY VERIFICATION"
    active_field = "username" # username or password
    
    # Animation state
    scan_line_y = 0
    scanning = False
    scan_timer = 0

    while True:
        center_x = V_WIDTH // 2
        
        # Layout - Adjusted to prevent overlap
        # Card is taller or shifted down
        card_y = V_HEIGHT * 0.12
        card_h = 500
        card_rect = pygame.Rect(center_x - 250, card_y, 500, card_h)
        
        # Avatar at top inside card
        avatar_y = int(card_y + 80)
        
        # Title below avatar
        title_y = int(card_y + 160)
        
        # Inputs below title
        input_y_start = int(card_y + 220)
        input_gap = 90
        
        input_box_user = pygame.Rect(center_x - 200, input_y_start, 400, 50)
        input_box_pass = pygame.Rect(center_x - 200, input_y_start + input_gap, 400, 50)
        
        # Buttons at bottom
        btn_y = int(card_y + 400)
        btn_login = pygame.Rect(center_x - 200, btn_y, 190, 50)
        btn_register = pygame.Rect(center_x + 10, btn_y, 190, 50)

        mx, my = get_virtual_mouse_pos()
        
        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_user.collidepoint((mx, my)):
                    active_field = "username"
                elif input_box_pass.collidepoint((mx, my)):
                    active_field = "password"
                elif btn_login.collidepoint((mx, my)):
                    scanning = True
                    scan_timer = 60 # 1 second scan
                    # Logic happens after scan
                elif btn_register.collidepoint((mx, my)):
                    # NETWORK CALL
                    res = net.send("REGISTER", {"username": username, "password": password})
                    message = res.get('message', "Error")
                    if res.get('success'): 
                        message = "REGISTRATION SUCCESSFUL"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    scanning = True
                    scan_timer = 60
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "username": username = username[:-1]
                    elif active_field == "password": password = password[:-1]
                else:
                    if active_field == "username": username += event.unicode
                    elif active_field == "password": password += event.unicode

        # Update Scan Logic
        if scanning:
            scan_timer -= 1
            if scan_timer <= 0:
                scanning = False
                # NETWORK CALL
                res = net.send("LOGIN", {"username": username, "password": password})
                message = res.get('message', "Error")
                if res.get('success'): 
                    return res['player_id'], username, res.get('role', 'PLAYER')

        # --- DRAWING ---
        canvas.fill(BG_DARK)
        starfield.update_and_draw(canvas)

        # Draw Glass Card
        draw_glass_panel(card_rect, NEON_CYAN)
        
        # --- AVATAR ---
        avatar_state = "shy" if active_field == "password" else "idle"
        draw_interactive_avatar(canvas, center_x, avatar_y, 50, avatar_state, (mx, my))

        # Title
        draw_text(message, title_font, NEON_CYAN, center_x - title_font.size(message)[0] // 2, title_y)

        # Inputs
        draw_neon_input(input_box_user, username, active_field == "username")
        draw_neon_input(input_box_pass, password, active_field == "password", is_password=True)
        
        # Labels
        draw_text("AGENT ID", achievement_font, NEON_CYAN, input_box_user.x, input_box_user.y - 25)
        draw_text("PASSWORD", achievement_font, NEON_CYAN, input_box_pass.x, input_box_pass.y - 25)

        # Buttons
        hover_login = btn_login.collidepoint((mx, my))
        hover_register = btn_register.collidepoint((mx, my))
        
        draw_neon_button(btn_login, "LOGIN", NEON_CYAN, hover_login)
        draw_neon_button(btn_register, "REGISTER", NEON_PURPLE, hover_register)

        # Scan Line Animation
        if scanning:
            scan_y = card_rect.y + (60 - scan_timer) * (card_rect.height / 60)
            pygame.draw.line(canvas, NEON_CYAN, (card_rect.left, scan_y), (card_rect.right, scan_y), 2)

        scaled_surf = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(scaled_surf, (0, 0))
        pygame.display.update()

def change_password_screen(player_id, username):
    new_pass, msg = "", ""
    active = False
    
    center_x = V_WIDTH // 2
    center_y = V_HEIGHT // 2
    
    panel_rect = pygame.Rect(center_x - 250, center_y - 200, 500, 400)
    input_box_new = pygame.Rect(center_x - 200, center_y - 20, 400, 50)
    save_button = pygame.Rect(center_x - 200, center_y + 60, 190, 50)
    return_button = pygame.Rect(center_x + 10, center_y + 60, 190, 50)

    while True:
        canvas.fill(BG_DARK)
        starfield.update_and_draw(canvas)
        
        # Interactive Avatar
        mx, my = get_virtual_mouse_pos()
        avatar_state = "shy" if active else "idle"
        draw_interactive_avatar(canvas, center_x, center_y - 120, 60, avatar_state, (mx, my))
        
        # Glass Panel
        draw_glass_panel(panel_rect, NEON_PURPLE)
        
        # Title
        draw_text("SECURITY UPDATE", title_font, NEON_PURPLE, center_x - 130, center_y - 180)
        draw_text(f"AGENT: {username}", achievement_font, ACCENT_WHITE, center_x - 50, center_y - 140)

        # Input
        draw_neon_input(input_box_new, new_pass, active, is_password=True)
        draw_text("NEW PASSWORD", achievement_font, NEON_CYAN, input_box_new.x, input_box_new.y - 25)
        
        # Buttons
        draw_neon_button(save_button, "UPDATE", NEON_CYAN, save_button.collidepoint((mx, my)))
        draw_neon_button(return_button, "RETURN", NEON_MAGENTA, return_button.collidepoint((mx, my)))
        
        # Message
        if msg:
            color = NEON_CYAN if "successfully" in msg else NEON_MAGENTA
            draw_text(msg, main_font, color, center_x - main_font.size(msg)[0]//2, center_y + 130)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_new.collidepoint((mx, my)): active = True
                else: active = False
                
                if save_button.collidepoint((mx, my)):
                    # NETWORK CALL
                    res = net.send("CHANGE_PASSWORD", {"player_id": player_id, "new_password": new_pass})
                    msg = res.get('message', "Error")
                    if res.get('success'): new_pass = ""
                elif return_button.collidepoint((mx, my)): return
            
            if event.type == pygame.KEYDOWN:
                if active:
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
                # Boundary Checks (Strict)
                if cue.x - cue.radius < PLAY_LEFT:
                    cue.x = PLAY_LEFT + cue.radius
                    cue.speedx *= -1
                elif cue.x + cue.radius > PLAY_RIGHT:
                    cue.x = PLAY_RIGHT - cue.radius
                    cue.speedx *= -1
                    
                if cue.y - cue.radius < PLAY_TOP:
                    cue.y = PLAY_TOP + cue.radius
                    cue.speedy *= -1
                elif cue.y + cue.radius > PLAY_BOTTOM:
                    cue.y = PLAY_BOTTOM - cue.radius
                    cue.speedy *= -1
        
        for ball in balls:
            ball.x += ball.speedx * delta_time; ball.y += ball.speedy * delta_time
            ball.speedx *= 0.99; ball.speedy *= 0.99
            if abs(ball.speedx) < 5 and abs(ball.speedy) < 5: ball.speedx, ball.speedy = 0, 0; ball.is_moving = False
            else: ball.is_moving = True
            if not is_near_hole(ball):
                # Boundary Checks (Strict)
                if ball.x - ball.radius < PLAY_LEFT:
                    ball.x = PLAY_LEFT + ball.radius
                    ball.speedx *= -1
                elif ball.x + ball.radius > PLAY_RIGHT:
                    ball.x = PLAY_RIGHT - ball.radius
                    ball.speedx *= -1
                    
                if ball.y - ball.radius < PLAY_TOP:
                    ball.y = PLAY_TOP + ball.radius
                    ball.speedy *= -1
                elif ball.y + ball.radius > PLAY_BOTTOM:
                    ball.y = PLAY_BOTTOM - ball.radius
                    ball.speedy *= -1
            if ball.is_moving: ball.angle += (abs(ball.speedx) + abs(ball.speedy)) * 0.1

        # Collisions
        for i in range(len(balls)):
            if not balls[i].did_go:
                # Ball-Ball
                for j in range(i + 1, len(balls)):
                    if not balls[j].did_go and check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (balls[j].x, balls[j].y), balls[j].radius):
                        handle_collision(balls[i], balls[j]); col_snd = True
                        # Particle Burst
                        cx, cy = (balls[i].x + balls[j].x)/2, (balls[i].y + balls[j].y)/2
                        for _ in range(10): particles.append(Particle(cx, cy, NEON_CYAN, 20))
                        shaker.shake(5, 3)
                # Cue-Ball
                if not foul_waiting_for_stop:
                    if check_collision_circles((cue.x, cue.y), cue.radius, (balls[i].x, balls[i].y), balls[i].radius):
                        handle_collision(cue, balls[i]); col_snd = True
                # Potting
                for idx, hole in enumerate(holes):
                    if check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (hole.x, hole.y), hole.radius):
                        if not balls[i].did_go: pot_snd = True
                        balls_potted_this_shot += 1; balls[i].did_go = True; score += 100 * difficulty_factor
                        balls[i].x, balls[i].y = -5000, -5000; balls[i].speedx, balls[i].speedy = 0, 0
                        game_events.append((player_id, idx+1, BALL_NAMES.get(balls[i].ball_id), "POTTED"))
                        # Potting Effects
                        for _ in range(20): particles.append(Particle(hole.x, hole.y, GOLD, 40))
                        floating_texts.append(FloatingText(hole.x, hole.y - 20, "+100", GOLD))
                        shaker.shake(10, 5)

        # Foul
        for hole in holes:
            if not foul_waiting_for_stop and check_collision_circles((cue.x, cue.y), cue.radius, (hole.x, hole.y), hole.radius):
                if cue.is_moving: pot_snd = True
                cue.x, cue.y = -1000, -1000; cue.speedx, cue.speedy = 0, 0; cue.is_moving = False
                foul_waiting_for_stop = True; timer += 10; show_message = True; message_timer = 0; fouls += 1; score = max(0, score - 50 * difficulty_factor)
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
            balls[8].x=200000
            win = all(b.did_go for b in balls[:8]) # Check if others potted
            game_over = True; did_win = win
            if win: score += (remaining_time * 2 + 500) * difficulty_factor
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
        # Update Effects
        shaker_offset = shaker.get_offset()
        if shaker.timer > 0:
            temp_surf = pygame.Surface((V_WIDTH, V_HEIGHT))
            temp_surf.blit(canvas, shaker_offset)
            canvas.blit(temp_surf, (0,0))

        for p in particles[:]:
            p.update(); p.draw(canvas)
            if p.life <= 0: particles.remove(p)
            
        for ft in floating_texts[:]:
            ft.update(); ft.draw(canvas)
            if ft.life <= 0: floating_texts.remove(ft)

        if not game_over:
            # HUD Glass Panel
            hud_rect = pygame.Rect(20, 20, 275, 100)

            draw_glass_panel(hud_rect, NEON_CYAN)
            draw_text(f"AGENT: {username}", main_font, NEON_CYAN, 35, 30)
            draw_text(f"SCORE: {int(score)}", main_font, ACCENT_WHITE, 35, 60)
            
            # Timer
            timer_color = NEON_CYAN if remaining_time > 30 else NEON_MAGENTA
            draw_text(f"TIME: {remaining_time:.1f}", title_font, timer_color, 35, screen.get_height() -50)
            if not foul_waiting_for_stop: cue.draw()
            for ball in balls: ball.draw()
            if is_aiming and not foul_waiting_for_stop:
                mx, my = get_virtual_mouse_pos()
                
                # Calculate power
                dx = cue.x - mx; dy = cue.y - my
                dist = math.sqrt(dx*dx + dy*dy)
                power_pct = min(dist / 200, 1.0) # Max drag 200
                
                # Aiming Line with Glow
                aim_end_x = cue.x + dx; aim_end_y = cue.y + dy
                
                # Draw Glow
                ls = pygame.Surface((V_WIDTH, V_HEIGHT), pygame.SRCALPHA)
                for w in range(5, 1, -1):
                    alpha = 30 + (5-w)*40
                    pygame.draw.line(ls, (0, 255, 255, alpha), (cue.x, cue.y), (aim_end_x, aim_end_y), w)
                canvas.blit(ls, (0,0))
                
                # Core Line
                pygame.draw.line(canvas, WHITE, (cue.x, cue.y), (aim_end_x, aim_end_y), 1)

                # Power Meter
                bar_w = 100; bar_h = 8 # Increased length
                bar_x = cue.x - bar_w//2; bar_y = cue.y + 35
                
                # Background
                pygame.draw.rect(canvas, (20, 20, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
                # Fill
                fill_w = int(bar_w * power_pct)
                p_color = (int(255 * power_pct), int(255 * (1-power_pct)), 0)
                pygame.draw.rect(canvas, p_color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)
                # Border
                pygame.draw.rect(canvas, (100, 100, 100), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=3)
            if show_message: draw_text("FOUL (-10s)", foul_font, RED, 700, 400)
        else:
            # Game Over Overlay
            overlay = pygame.Surface((V_WIDTH, V_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            canvas.blit(overlay, (0, 0))
            
            cx = V_WIDTH // 2; cy = V_HEIGHT // 2
            panel_rect = pygame.Rect(cx - 250, cy - 200, 500, 400)
            draw_glass_panel(panel_rect, NEON_CYAN if did_win else NEON_MAGENTA)
            
            # POOL AD Branding
            draw_text("POOL AD", achievement_font, GOLD, cx - achievement_font.size("POOL AD")[0] // 2, cy - 190)

            msg = "MISSION ACCOMPLISHED" if did_win else ("TIME CRITICAL FAILURE" if countdown_finished else "MISSION FAILED")
            color = NEON_CYAN if did_win else NEON_MAGENTA
            draw_text(msg, title_font, color, cx - title_font.size(msg)[0] // 2, cy - 150)
            
            score_msg = f"FINAL SCORE: {score:.0f}"
            draw_text(score_msg, foul_font, ACCENT_WHITE, cx - foul_font.size(score_msg)[0] // 2, cy - 80)
            
            btn_y = cy + 50
            exit_btn = pygame.Rect(cx - 180, btn_y, 110, 50)
            menu_btn = pygame.Rect(cx - 55, btn_y, 110, 50)
            logout_btn = pygame.Rect(cx + 70, btn_y, 110, 50)
            
            mx, my = get_virtual_mouse_pos()
            draw_neon_button(exit_btn, "EXIT", NEON_MAGENTA, exit_btn.collidepoint((mx, my)))
            draw_neon_button(menu_btn, "MENU", NEON_CYAN, menu_btn.collidepoint((mx, my)))
            draw_neon_button(logout_btn, "LOGOUT", NEON_PURPLE, logout_btn.collidepoint((mx, my)))
            
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