import pygame
import math
import sys
import auth  # This is your 'auth.py' file for login/registration

# --- Pygame Setup ---
pygame.init()
pygame.mixer.init()  # for sounds

# Screen dimensions (FIXED)
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 650
TABLE_START_X = SCREEN_WIDTH // 4 # The left-side panel width (1500 // 4)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("9-Ball Game (Database Project)")
clock = pygame.time.Clock()
main_font = pygame.font.SysFont("Arial", 25)
title_font = pygame.font.SysFont("Arial", 35)
foul_font = pygame.font.SysFont("Arial", 50)
achievement_font = pygame.font.SysFont("Arial", 20, bold=True) # Font for popups
# ---- Load Ball Images ----
ball_images = {
    1: pygame.image.load("assets/ball1.png"),
    2: pygame.image.load("assets/ball2.png"),
    3: pygame.image.load("assets/ball3.png"),
    4: pygame.image.load("assets/ball4.png"),
    5: pygame.image.load("assets/ball5.png"),
    6: pygame.image.load("assets/ball6.png"),
    7: pygame.image.load("assets/ball7.png"),
    8: pygame.image.load("assets/ball8.png"),
    9: pygame.image.load("assets/ball9.png"),
    0: pygame.image.load("assets/cue.png")  # cue ball
}

# --- Colors ---
SKYBLUE = (135, 206, 235)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 128, 0)  # Table color
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
DARKPURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
DARKGREEN = (0, 100, 0)
PINK = (255, 192, 203)

GOLD = (255, 215, 0) # For achievement popup






# --- Sound Setup (Unchanged) ---
try:
    bg_music = pygame.mixer.music.load("C:/Users/Administrator/source/repos/PONG1/bgm.mp3")
    # pygame.mixer.music.play(-1)  # Loop forever <-- REMOVED, we will control this in the game loop
    collision_sound = pygame.mixer.Sound("C:/Users/Administrator/source/repos/PONG1/collision.wav")
    potting_sound = pygame.mixer.Sound("C:/Users/Administrator/source/repos/PONG1/ball_pocket.wav")
except FileNotFoundError:
    print("Sound files not found. Game will run without sound.")
    collision_sound = None
    potting_sound = None

# --- Helper Functions ---

def play_sound(sound):
    """ Helper to safely play sounds """
    if sound:
        sound.play()


def draw_text(text, font, color, x, y):
    """ Helper to draw text on the screen """
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

# --- NEW: Text Wrapping Function ---
def draw_text_wrapped(surface, text, font, color, rect):
    """
    Draws text, wrapping it to fit inside the given rect.
    """
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        if word == "\n": # Handle manual newlines
            lines.append(current_line)
            lines.append("") # Add a blank line
            current_line = ""
            continue

        test_line = current_line + word + " "
        if font.size(test_line)[0] < rect.width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    
    lines.append(current_line) # Add the last line

    y_offset = 0
    for line in lines:
        text_surface = font.render(line, True, color)
        surface.blit(text_surface, (rect.x, rect.y + y_offset))
        y_offset += font.get_linesize()


def check_collision_circles(pos1, r1, pos2, r2):
    """ Replaces Raylib's CheckCollisionCircles """
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    distance = math.sqrt(dx * dx + dy * dy)
    return distance < r1 + r2

def handle_collision(ball1, ball):
    """ Translated 1:1 from your C++ physics code """
    dx = ball.x - ball1.x
    dy = ball.y - ball1.y
    distance = math.sqrt(dx * dx + dy * dy)

    if distance < 1e-6:
        dx = 0.01
        dy = 0.01
        ball.x += dx
        ball.y += dy
        dx = ball.x - ball1.x
        dy = ball.y - ball1.y
        # --- Rotation Based on Movement ---
        if ball.is_moving:
            movement_speed = abs(ball.speedx) + abs(ball.speedy)
            ball.angle += movement_speed * 0.5  # Control rotation speed
            ball.angle %= 360  # Prevent infinite values

        distance = math.sqrt(dx * dx + dy * dy)
        if distance < 1e-6: return

    nx = dx / distance
    ny = dy / distance
    relative_speed_x = ball.speedx - ball1.speedx
    relative_speed_y = ball.speedy - ball1.speedy
    impact_speed = relative_speed_x * nx + relative_speed_y * ny

    if impact_speed > 0: return

    restitution = 0.8
    impulse = -(1 + restitution) * impact_speed / 2.0

    ball1.speedx -= impulse * nx
    ball1.speedy -= impulse * ny
    ball.speedx += impulse * nx
    ball.speedy += impulse * ny



# --- Game Object Classes (from C++ Structs) ---

class Ball:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.radius = 20
        self.speedx = 0
        self.speedy = 0
        self.color = color
        self.is_moving = False
        self.did_go = False
        self.angle = 0  # Track rotation angle

    def draw(self):
        if not self.did_go:
            img = ball_images[self.ball_id]
            img = pygame.transform.scale(img, (40, 40))  # Resize

            # Apply rotation only when moving
            if self.is_moving:
                rotated_img = pygame.transform.rotate(img, self.angle)
            else:
                rotated_img = img  # No rotation when still

            rect = rotated_img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(rotated_img, rect)


class Hole:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 30

    def draw(self):
        pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.radius)


def post_login_menu(player_id, username):
    menu_font = pygame.font.SysFont("arial", 38)
    running = True

    # Buttons
    play_button = pygame.Rect(450, 250, 300, 70)
    achieve_button = pygame.Rect(450, 350, 300, 70)
    change_pass_button = pygame.Rect(450, 450, 300, 70)

    while running:
        screen.fill((30, 30, 30))

        draw_text("Welcome, " + username, title_font, WHITE, 450, 120)
        draw_text("Select an option", menu_font, GOLD, 480, 180)

        # Draw Buttons
        pygame.draw.rect(screen, BLUE, play_button)
        pygame.draw.rect(screen, GREEN, achieve_button)

        draw_text("PLAY", menu_font, WHITE, play_button.x + 85, play_button.y + 18)
        draw_text("ACHIEVEMENTS", menu_font, WHITE,achieve_button.x + 15, achieve_button.y + 18)
        pygame.draw.rect(screen, RED, change_pass_button)
        draw_text("CHANGE PASSWORD", menu_font, WHITE, change_pass_button.x + 5, change_pass_button.y + 18)

        for event in pygame.event.get():  # <-- THIS IS LINE 189
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                if play_button.collidepoint((mx, my)):
                    return "play"

                if achieve_button.collidepoint((mx, my)):
                    return "achievements"
                if change_pass_button.collidepoint((mx, my)):
                    change_password_screen(player_id, username)

        pygame.display.update()


def achievements_screen(player_id, username):
    running = True

    # --- REPLACED SQL WITH AUTH CALL ---
    # Get earned achievements safely
    earned_raw = auth.get_player_achievements(player_id)

    # Convert to proper integer set
    earned = set()
    for row in earned_raw:
        try:
            # Handle both tuple (id,) and int cases
            val = row[0] if isinstance(row, (tuple, list)) else row
            earned.add(int(val))
        except:
            pass

            # Get ALL achievements using the new auth function
    all_achievements = auth.get_all_achievements_list()
    # -----------------------------------

    # Colors
    unlocked_color = (60, 180, 75)  # GREEN
    locked_color = (70, 70, 70)  # DARK GREY
    border_color = (230, 230, 230)

    # UI layout
    box_width = 1000
    box_height = 80
    x = 150
    start_y = 150

    # SCROLL VARIABLES
    scroll_offset = 0
    scroll_speed = 25

    # Return button
    return_button = pygame.Rect(20, 20, 150, 50)

    while running:
        screen.fill((25, 25, 25))
        draw_text(f"{username}'s Achievements", title_font, GOLD, 350, 70)

        # Draw Return Button
        pygame.draw.rect(screen, (200, 50, 50), return_button, border_radius=8)
        draw_text("RETURN", main_font, WHITE, return_button.x + 20, return_button.y + 10)

        y = start_y + scroll_offset

        for ach in all_achievements:
            ach_id = int(ach["AchievementID"])
            name = ach["Name"]
            desc = ach["Description"]

            is_unlocked = ach_id in earned

            color = unlocked_color if is_unlocked else locked_color
            text_color = WHITE if is_unlocked else (200, 200, 200)

            pygame.draw.rect(screen, color, (x, y, box_width, box_height), border_radius=12)
            pygame.draw.rect(screen, border_color, (x, y, box_width, box_height), 3, border_radius=12)

            status_text = name if is_unlocked else f"{name} (Locked)"
            draw_text(status_text, main_font, text_color, x + 15, y + 10)

            desc_color = WHITE if is_unlocked else (170, 170, 170)
            draw_text(desc, pygame.font.SysFont("Arial", 18), desc_color, x + 15, y + 45)

            y += box_height + 20

        # Scrollbar logic
        content_height = len(all_achievements) * (box_height + 20)
        visible_height = SCREEN_HEIGHT - start_y - 30

        # Only draw scrollbar if content overflows
        if content_height > visible_height:
            scrollbar_height = max(40, (visible_height / content_height) * 300)
            scrollbar_y = 150 + (-scroll_offset / content_height) * 300

            pygame.draw.rect(screen, (80, 80, 80), (1100, 150, 20, 300), border_radius=10)
            pygame.draw.rect(screen, (180, 180, 180), (1100, scrollbar_y, 20, scrollbar_height), border_radius=10)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_button.collidepoint(event.pos):
                    return

            if event.type == pygame.MOUSEWHEEL:
                scroll_offset += event.y * scroll_speed
                max_scroll = 0
                min_scroll = -(content_height - visible_height) if content_height > visible_height else 0
                scroll_offset = max(min(scroll_offset, max_scroll), min_scroll)

        pygame.display.update()
# --- NEW: Difficulty Select Screen (Updated) ---
def difficulty_screen():
    """
    Screen for user to select difficulty level.
    Uses fixed 1500x800 resolution.
    """
    while True:
        # --- Recalculate UI positions based on global SCREEN_WIDTH/HEIGHT ---
        center_x = SCREEN_WIDTH // 2
        button_width = 250
        
        easy_button = pygame.Rect(center_x - button_width // 2, SCREEN_HEIGHT * 0.3, button_width, 70)
        medium_button = pygame.Rect(center_x - button_width // 2, SCREEN_HEIGHT * 0.5, button_width, 70)
        hard_button = pygame.Rect(center_x - button_width // 2, SCREEN_HEIGHT * 0.7, button_width, 70)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if easy_button.collidepoint(event.pos):
                    return 1  # Corresponds to 'Easy' in your DB
                elif medium_button.collidepoint(event.pos):
                    return 2  # Corresponds to 'Medium'
                elif hard_button.collidepoint(event.pos):
                    return 3  # Corresponds to 'Hard'
        
        # --- Drawing the Difficulty Screen (Inside the loop) ---
        screen.fill(BLACK)
        draw_text("Select Difficulty", title_font, WHITE, center_x - title_font.size("Select Difficulty")[0] // 2, SCREEN_HEIGHT * 0.1)
        
        # Draw Easy button
        pygame.draw.rect(screen, GREEN, easy_button)
        draw_text("Easy", title_font, BLACK, easy_button.x + 90, easy_button.y + 15)
        
        # Draw Medium button
        pygame.draw.rect(screen, YELLOW, medium_button)
        draw_text("Medium", title_font, BLACK, medium_button.x + 70, medium_button.y + 15)
        
        # Draw Hard button
        pygame.draw.rect(screen, RED, hard_button)
        draw_text("Hard", title_font, BLACK, hard_button.x + 90, hard_button.y + 15)
        
        pygame.display.flip()
        clock.tick(30)
        


# --- Login/Register Screen (Updated) ---

def login_register_screen():
    """
    New screen to handle user login or registration.
    Uses fixed 1500x800 resolution.
    """
    username = ""
    password = ""
    message = "Enter Username & Password"
    active_field = "username" # "username", "password", "login"
    
    color_active = pygame.Color('dodgerblue2')
    color_inactive = pygame.Color('lightgray')
    
    while True:
        # --- Recalculate UI based on global screen size ---
        center_x = SCREEN_WIDTH // 2
        
        input_box_user = pygame.Rect(center_x - 200, SCREEN_HEIGHT * 0.3, 400, 50)
        input_box_pass = pygame.Rect(center_x - 200, SCREEN_HEIGHT * 0.45, 400, 50)
        button_login = pygame.Rect(center_x - 200, SCREEN_HEIGHT * 0.6, 180, 50)
        button_register = pygame.Rect(center_x + 20, SCREEN_HEIGHT * 0.6, 180, 50)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_user.collidepoint(event.pos):
                    active_field = "username"
                elif input_box_pass.collidepoint(event.pos):
                    active_field = "password"
                elif button_login.collidepoint(event.pos):
                    # --- Try to Login ---
                    print(f"Attempting login for: {username}")
                    result = auth.login_player(username, password)
                    message = result['message'] # <-- This updates the message
                    if result['success']:
                        return result['player_id'], username # Login successful!
                elif button_register.collidepoint(event.pos):
                    # --- Try to Register ---
                    print(f"Attempting registration for: {username}")
                    result = auth.register_player(username, password)
                    message = result['message'] # <-- This updates the message
                    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # --- Try to Login on Enter ---
                    print(f"Attempting login for: {username}")
                    result = auth.login_player(username, password)
                    message = result['message'] # <-- This updates the message
                    if result['success']:
                        return result['player_id'], username # Login successful!
                        
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "username":
                        username = username[:-1]
                    elif active_field == "password":
                        password = password[:-1]
                else:
                    if active_field == "username":
                        username += event.unicode
                    elif active_field == "password":
                        password += event.unicode
                        
        # --- Drawing the Login Screen ---
        screen.fill(BLACK)
        draw_text("Pool Game Login", title_font, WHITE, center_x - title_font.size("Pool Game Login")[0] // 2, SCREEN_HEIGHT * 0.1)
        
        # --- This message is updated on login failure ---
        draw_text(message, main_font, RED, center_x - main_font.size(message)[0] // 2, SCREEN_HEIGHT * 0.8)
        
        # User box
        pygame.draw.rect(screen, color_active if active_field == "username" else color_inactive, input_box_user, 2)
        draw_text(username, main_font, WHITE, input_box_user.x + 5, input_box_user.y + 5)
        
        # Pass box
        pygame.draw.rect(screen, color_active if active_field == "password" else color_inactive, input_box_pass, 2)
        draw_text('*' * len(password), main_font, WHITE, input_box_pass.x + 5, input_box_pass.y + 5)

        # Buttons
        pygame.draw.rect(screen, GREEN, button_login)
        draw_text("Login", main_font, BLACK, button_login.x + 60, button_login.y + 10)
        pygame.draw.rect(screen, BLUE, button_register)
        draw_text("Register", main_font, BLACK, button_register.x + 40, button_register.y + 10)
        
        pygame.display.flip()
        clock.tick(30)


def change_password_screen(player_id, username):
    current_pass = ""
    new_pass = ""
    msg = ""
    active = "current"

    input_box_current = pygame.Rect(450, 250, 300, 50)
    input_box_new = pygame.Rect(450, 330, 300, 50)
    save_button = pygame.Rect(450, 420, 300, 60)
    return_button = pygame.Rect(450, 500, 300, 60)

    while True:
        screen.fill((20, 20, 20))
        draw_text("Change Password", title_font, GOLD, 450, 150)

        draw_text("Current Password:", main_font, WHITE, 300, 260)
        pygame.draw.rect(screen, WHITE, input_box_current, 2)
        draw_text('*' * len(current_pass), main_font, WHITE, input_box_current.x + 5, input_box_current.y + 5)

        draw_text("New Password:", main_font, WHITE, 300, 340)
        pygame.draw.rect(screen, WHITE, input_box_new, 2)
        draw_text('*' * len(new_pass), main_font, WHITE, input_box_new.x + 5, input_box_new.y + 5)

        # Save button
        pygame.draw.rect(screen, GREEN, save_button)
        draw_text("SAVE PASSWORD", main_font, BLACK, save_button.x + 40, save_button.y + 15)
        pygame.draw.rect(screen, BLUE, return_button)
        draw_text("RETURN", main_font, WHITE, return_button.x + 95, return_button.y + 15)

        draw_text(msg, main_font, RED, 450, 500)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_current.collidepoint(event.pos):
                    active = "current"
                elif input_box_new.collidepoint(event.pos):
                    active = "new"
                elif save_button.collidepoint(event.pos):
                    # 1. Verify old password
                    login_check = auth.login_player(username, current_pass)
                    if not login_check["success"]:
                        msg = "Current password incorrect."
                    else:
                        # --- REPLACED SQL WITH AUTH CALL ---
                        result = auth.update_password(player_id, new_pass)
                        msg = result['message']
                        if result['success']:
                            # Clear fields on success
                            current_pass = ""
                            new_pass = ""
                        # -----------------------------------

                elif return_button.collidepoint(event.pos):
                    return  # Go back to previous screen

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    if active == "current":
                        current_pass = current_pass[:-1]
                    else:
                        new_pass = new_pass[:-1]
                else:
                    if active == "current":
                        current_pass += event.unicode
                    else:
                        new_pass += event.unicode

        pygame.display.flip()
# --- Main Game Function (Updated) ---


def main_game(player_id, username, difficulty_id):
    """
    Main game loop with Real-Time Achievement Popups.
    """

    # --- Game State Variables ---
    game_over = False
    game_over_saved = False
    did_win = False
    show_message = False
    message_timer = 0
    timer = 0.0

    # --- ACHIEVEMENT SETUP ---
    # Load what the player already has so we don't give it twice
    earned_achievements_cache = auth.get_player_achievements(player_id)
    achievement_popup_queue = []  # Queue to store popups waiting to show

    # Achievement IDs (Must match your Database)
    FIRST_POT_ID = 8
    COMBO_ACHIEVEMENT_ID = 7

    # Set time based on difficulty
    if difficulty_id == 1:  # Easy
        countdown_time = 500
        aiming_level = 'easy'
        hole_radius_change = 5
        difficulty_factor = 1.0
    elif difficulty_id == 2:  # Medium
        countdown_time = 400
        aiming_level = 'medium'
        hole_radius_change = 0
        difficulty_factor = 1.35
    else:  # Hard
        countdown_time = 300
        aiming_level = 'hard'
        hole_radius_change = -5
        difficulty_factor = 1.75

    score = 0.0
    shots = 0
    fouls = 0

    # Track potting stats
    balls_potted_this_shot = 0  # Resets every shot
    total_balls_potted_game = 0  # Tracks total for the session

    # --- Setup Balls & Holes (Standard Setup) ---
    startX = SCREEN_WIDTH - (SCREEN_WIDTH - TABLE_START_X) / 4
    startY = SCREEN_HEIGHT / 2
    cue = Ball((SCREEN_WIDTH - TABLE_START_X) / 4 + TABLE_START_X, SCREEN_HEIGHT / 2, WHITE)
    cue.ball_id = 0

    spacing_factor = 1.1
    balls = [
        Ball(startX - 60 * spacing_factor, startY, YELLOW),
        Ball(startX - 20 * spacing_factor, startY + 75 * spacing_factor, BLUE),
        Ball(startX + 20 * spacing_factor, startY, RED),
        Ball(startX - 40 * spacing_factor, startY - 37 * spacing_factor, DARKPURPLE),
        Ball(startX, startY - 37 * spacing_factor, ORANGE),
        Ball(startX - 20 * spacing_factor, startY - 75 * spacing_factor, DARKGREEN),
        Ball(startX - 40 * spacing_factor, startY + 37 * spacing_factor, BROWN),
        Ball(startX, startY + 37 * spacing_factor, BLACK),
        Ball(startX - 20 * spacing_factor, startY, PINK)
    ]
    for i, ball in enumerate(balls, start=1): ball.ball_id = i

    holes = [
        Hole(TABLE_START_X + 3, 3),
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, 3),
        Hole(SCREEN_WIDTH - 3, 3),
        Hole(TABLE_START_X + 3, SCREEN_HEIGHT - 3),
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, SCREEN_HEIGHT - 3),
        Hole(SCREEN_WIDTH - 3, SCREEN_HEIGHT - 3)
    ]
    for hole in holes: hole.radius += hole_radius_change

    is_aiming = False
    running = True
    music_playing = False
    countdown_finished = False

    # --- Main Game Loop ---
    while running:
        delta_time = clock.tick(60) / 1000.0

        # Music Logic
        if shots == 0 and not music_playing:
            try:
                pygame.mixer.music.play(-1)
                music_playing = True
            except:
                pass
        elif shots > 0 and music_playing:
            pygame.mixer.music.stop()
            music_playing = False

        collision_sound_played_this_frame = False
        potting_sound_played_this_frame = False

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if not cue.is_moving and not game_over:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    is_aiming = True
                    balls_potted_this_shot = 0  # Reset pot counter for new shot

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if is_aiming:
                        is_aiming = False
                        mouse_pos = event.pos
                        dx = cue.x - mouse_pos[0]
                        dy = cue.y - mouse_pos[1]
                        cue.speedx = dx * 2.5
                        cue.speedy = dy * 2.5
                        cue.is_moving = True
                        shots += 1
                        collision_sound_played_this_frame = True

                        # --- Physics Updates ---
        # (Simplified for brevity - keep your existing physics code here)
        cue.x += cue.speedx * delta_time
        cue.y += cue.speedy * delta_time
        cue.speedx *= 0.99
        cue.speedy *= 0.99
        if abs(cue.speedx) < 5 and abs(cue.speedy) < 5:
            cue.speedx, cue.speedy = 0, 0
            cue.is_moving = False
        else:
            cue.is_moving = True

        # Collisions
        if cue.x - cue.radius < TABLE_START_X: cue.speedx *= -1; cue.x = TABLE_START_X + cue.radius
        if cue.x + cue.radius > SCREEN_WIDTH: cue.speedx *= -1; cue.x = SCREEN_WIDTH - cue.radius
        if cue.y - cue.radius < 0: cue.speedy *= -1; cue.y = cue.radius
        if cue.y + cue.radius > SCREEN_HEIGHT: cue.speedy *= -1; cue.y = SCREEN_HEIGHT - cue.radius

        for ball in balls:
            ball.x += ball.speedx * delta_time
            ball.y += ball.speedy * delta_time
            ball.speedx *= 0.99;
            ball.speedy *= 0.99
            if abs(ball.speedx) < 5 and abs(ball.speedy) < 5:
                ball.speedx, ball.speedy = 0, 0
                ball.is_moving = False
            else:
                ball.is_moving = True

            # Wall Collisions
            if ball.x - ball.radius < TABLE_START_X: ball.speedx *= -1; ball.x = TABLE_START_X + ball.radius
            if ball.x + ball.radius > SCREEN_WIDTH: ball.speedx *= -1; ball.x = SCREEN_WIDTH - ball.radius
            if ball.y - ball.radius < 0: ball.speedy *= -1; ball.y = ball.radius
            if ball.y + ball.radius > SCREEN_HEIGHT: ball.speedy *= -1; ball.y = SCREEN_HEIGHT - ball.radius

            if ball.is_moving: ball.angle += (abs(ball.speedx) + abs(ball.speedy)) * 0.1

        # Ball-Ball & Ball-Hole Interactions
        for i in range(len(balls)):
            if not balls[i].did_go:
                # Ball-Ball
                for j in range(i + 1, len(balls)):
                    if not balls[j].did_go and check_collision_circles((balls[i].x, balls[i].y), balls[i].radius,
                                                                       (balls[j].x, balls[j].y), balls[j].radius):
                        handle_collision(balls[i], balls[j])
                        if balls[i].is_moving or balls[j].is_moving: collision_sound_played_this_frame = True

                # Cue-Ball
                if check_collision_circles((cue.x, cue.y), cue.radius, (balls[i].x, balls[i].y), balls[i].radius):
                    handle_collision(cue, balls[i])
                    if cue.is_moving or balls[i].is_moving: collision_sound_played_this_frame = True

                # Ball-Hole
                for hole in holes:
                    if check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (hole.x, hole.y),
                                               hole.radius):
                        if not balls[i].did_go: potting_sound_played_this_frame = True

                        # --- IMPORTANT: COUNT THE POT ---
                        balls_potted_this_shot += 1
                        balls[i].did_go = True
                        balls[i].x, balls[i].y = -5000, -5000
                        balls[i].speedx, balls[i].speedy = 0, 0
                        balls[i].is_moving = False

        # Foul Logic
        for hole in holes:
            if check_collision_circles((cue.x, cue.y), cue.radius, (hole.x, hole.y), hole.radius):
                if cue.is_moving: potting_sound_played_this_frame = True
                cue.x = (SCREEN_WIDTH - TABLE_START_X) / 4 + TABLE_START_X
                cue.y = SCREEN_HEIGHT / 2
                cue.speedx, cue.speedy = 0, 0;
                cue.is_moving = False
                timer += 10;
                show_message = True;
                message_timer = 0;
                fouls += 1

        if collision_sound_played_this_frame: play_sound(collision_sound)
        if potting_sound_played_this_frame: play_sound(potting_sound)

        if not game_over and shots > 0: timer += delta_time

        remaining_time = countdown_time - timer
        if remaining_time <= 0 and not countdown_finished:
            countdown_finished = True;
            game_over = True;
            did_win = False;
            score = 0;
            remaining_time = 0

        # =================================================================================
        # --- MID-GAME ACHIEVEMENT CHECKER ---
        # This runs when balls stop moving. This is where we catch Combo/First Pot
        # =================================================================================

        # Check if everything has stopped moving
        all_stopped = not cue.is_moving and all(not b.is_moving for b in balls)

        if all_stopped and shots > 0 and balls_potted_this_shot > 0:

            # 1. Check for "First Potter" (ID: 8)
            # Condition: Haven't potted anything before this shot, but potted something now
            if total_balls_potted_game == 0:
                if FIRST_POT_ID not in earned_achievements_cache:
                    print("Unlocking: First Potter")
                    auth.grant_achievement(player_id, FIRST_POT_ID)
                    earned_achievements_cache.add(FIRST_POT_ID)
                    achievement_popup_queue.append({"text": "First Potter!", "timer": 0})

            # 2. Check for "Combo Shot" (ID: 7)
            # Condition: Potted 2 or more balls in this specific turn
            if balls_potted_this_shot >= 2:
                if COMBO_ACHIEVEMENT_ID not in earned_achievements_cache:
                    print("Unlocking: Combo Shot")
                    auth.grant_achievement(player_id, COMBO_ACHIEVEMENT_ID)
                    earned_achievements_cache.add(COMBO_ACHIEVEMENT_ID)
                    achievement_popup_queue.append({"text": "Combo Shot!", "timer": 0})

            # Add to total game stats and reset turn stats
            total_balls_potted_game += balls_potted_this_shot
            balls_potted_this_shot = 0

        # =================================================================================

        # Game Over Logic
        pink_ball = balls[8]
        if pink_ball.did_go and not game_over:
            win = True
            for i in range(8):
                if not balls[i].did_go: win = False; break
            game_over = True
            did_win = win
            if win: score = (((countdown_time - timer) / countdown_time) * 200 - (shots * 1) + 100) * difficulty_factor
            if score < 0: score = 0

        # Save Game Logic (End of Game)
        if game_over and not game_over_saved:
            auth.save_game_session(player_id, difficulty_id, score, did_win)
            new_achievements = auth.check_all_achievements(player_id, difficulty_id, timer, shots, fouls, did_win)
            earned_achievements_cache = auth.get_player_achievements(player_id)

            # Add End-Game achievements to queue
            for ach in new_achievements:
                if ach["AchievementID"] not in earned_achievements_cache:
                   # auth.grant_achievement(player_id,ach['AchievementID'])# Avoid double popup
                    achievement_popup_queue.append({"text": ach["Name"], "timer": 0})

            game_over_saved = True

        # --- DRAWING ---
        screen.fill(SKYBLUE)
        pygame.draw.rect(screen, SKYBLUE, (TABLE_START_X, 0, SCREEN_WIDTH - TABLE_START_X, SCREEN_HEIGHT))
        pygame.draw.rect(screen, BLACK, (0, 0, TABLE_START_X, SCREEN_HEIGHT))

        if not game_over:
            pygame.draw.line(screen, WHITE, (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, 0),
                             (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, SCREEN_HEIGHT), 1)
            pygame.draw.circle(screen, WHITE, (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, SCREEN_HEIGHT / 2),
                               75, 1)

            draw_text(f"Player: {username}", title_font, RED, 50, 50)
            draw_text(f"Time: {remaining_time:.1f}", title_font, RED if remaining_time < 30 else BLUE, 50, 100)

            # Draw Balls & Holes
            for hole in holes: hole.draw()
            cue.draw()
            for ball in balls: ball.draw()

            if is_aiming:
                mouse_pos = pygame.mouse.get_pos()
                if aiming_level != 'hard': pygame.draw.line(screen, BROWN, (cue.x, cue.y), mouse_pos, 3)
                if aiming_level == 'easy': pygame.draw.line(screen, WHITE, (cue.x, cue.y),
                                                            (2 * cue.x - mouse_pos[0], 2 * cue.y - mouse_pos[1]), 1)

            if show_message:
                draw_text("FOUL (-10s)", foul_font, RED, 700, 400)

        else:
            # GAME OVER SCREEN
            if did_win:
                draw_text("YOU WON!", foul_font, GREEN, 700, 400)
            elif countdown_finished:
                draw_text("TIME UP!", foul_font, RED, 700, 400)
            else:
                draw_text("EARLY PINK!", foul_font, RED, 700, 400)

            draw_text(f"SCORE: {score:.0f}", foul_font, WHITE, 700, 500)

            # Replay/Exit Buttons
            replay_btn = pygame.Rect(650, 580, 200, 60)
            exit_btn = pygame.Rect(900, 580, 200, 60)
            pygame.draw.rect(screen, GREEN, replay_btn);
            draw_text("REPLAY", main_font, BLACK, replay_btn.x + 50, replay_btn.y + 15)
            pygame.draw.rect(screen, RED, exit_btn);
            draw_text("EXIT", main_font, WHITE, exit_btn.x + 70, exit_btn.y + 15)

            if pygame.mouse.get_pressed()[0]:
                mx, my = pygame.mouse.get_pos()
                if replay_btn.collidepoint(mx, my): return "replay"
                if exit_btn.collidepoint(mx, my): pygame.quit(); sys.exit()

        # =================================================================================
        # --- POPUP DRAWING SYSTEM (Always draws on top) ---
        # =================================================================================
        if achievement_popup_queue:
            popup = achievement_popup_queue[0]

            # Setup box
            box_w, box_h = 400, 80
            center_x = SCREEN_WIDTH // 2
            box_rect = pygame.Rect(center_x - box_w // 2, 50, box_w, box_h)

            # Draw Box
            pygame.draw.rect(screen, (20, 20, 20), box_rect, border_radius=10)
            pygame.draw.rect(screen, GOLD, box_rect, 3, border_radius=10)

            # Draw Text
            draw_text("Achievement Unlocked!", achievement_font, GOLD, box_rect.x + 90, box_rect.y + 10)

            # Center the name
            txt_surf = main_font.render(popup['text'], True, WHITE)
            txt_x = box_rect.x + (box_w - txt_surf.get_width()) // 2
            screen.blit(txt_surf, (txt_x, box_rect.y + 40))

            # Timer
            popup['timer'] += 1
            if popup['timer'] > 180:  # Show for 3 seconds (60fps * 3)
                achievement_popup_queue.pop(0)
        # =================================================================================

        pygame.display.flip()

    pygame.quit()
    sys.exit()
# --- Main Driver ---
pid_uname = login_register_screen()
if pid_uname is None:
    pygame.quit()
    sys.exit()

player_id, username = pid_uname

while True:
    choice = post_login_menu(player_id, username)

    if choice == "play":
        difficulty_id = difficulty_screen()
        result = main_game(player_id, username, difficulty_id)

        if result == "replay":
            main_game(player_id, username, difficulty_id)

    elif choice == "achievements":
        achievements_screen(player_id, username)
