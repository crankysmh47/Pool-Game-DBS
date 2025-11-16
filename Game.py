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

    def draw(self):
        if not self.did_go:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

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

    while running:
        screen.fill((30, 30, 30))

        draw_text("Welcome, " + username, title_font, WHITE,  450, 120)
        draw_text("Select an option", menu_font, GOLD, 480, 180)

        # Draw Buttons
        pygame.draw.rect(screen, BLUE, play_button)
        pygame.draw.rect(screen, GREEN, achieve_button)

        draw_text("PLAY", menu_font, WHITE,  play_button.x + 85, play_button.y + 18)
        draw_text("ACHIEVEMENTS", menu_font, WHITE,
                  achieve_button.x + 15, achieve_button.y + 18)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                if play_button.collidepoint((mx, my)):
                    return "play"     # go to difficulty next

                if achieve_button.collidepoint((mx, my)):
                    return "achievements"  # open achievement viewer

        pygame.display.update()
def achievements_screen(player_id, username):
    running = True

    # Get all achievement IDs the player already earned
    achievement_ids = auth.get_player_achievements(player_id)

    while running:
        screen.fill((20, 20, 20))

        draw_text(f"{username}'s Achievements", title_font, GOLD, 300, 100)

        if len(achievement_ids) == 0:
            draw_text("No achievements unlocked yet.", main_font, WHITE, 420, 250)
        else:
            y = 200
            for ach_id in achievement_ids:
                name = auth.get_achievement_name(ach_id)
                draw_text(f"• {name}", main_font, WHITE,  300, y)
                y += 40

        draw_text("Click anywhere to return", main_font, RED, 400, 550)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                return  # Back to menu

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

# --- Main Game Function (Updated) ---


def main_game(player_id, username, difficulty_id):
    """
    The main game loop, translated from your C++ main().
    Uses fixed 1500x800 resolution.
    """
    
    # --- Game State Variables ---
    game_over = False
    game_over_saved = False # Flag to ensure we only save the score once
    did_win = False
    show_message = False
    message_timer = 0
    timer = 0.0
    

    earned_achievements_cache = auth.get_player_achievements(player_id)
    COMBO_ACHIEVEMENT_ID = 7   # (Pot 2+ balls in one shot)
    FIRST_POT_ID = 8           # (Pot your first ball)





    # Set time based on difficulty
    if difficulty_id == 1: # Easy
        countdown_time = 500
        aiming_level = 'easy'
        hole_radius_change = 5
        difficulty_factor = 1.0
    elif difficulty_id == 2: # Medium
        countdown_time = 400
        aiming_level = 'medium'
        hole_radius_change = 0
        difficulty_factor = 1.35
    else: # Hard
        countdown_time = 300
        aiming_level = 'hard'
        hole_radius_change = -5
        difficulty_factor = 1.75
    

    countdown_finished = False
    score = 0.0
    shots = 0
    
    fouls = 0
    balls_potted = 0
    total_balls_potted_game = 0
    
    achievement_popup_queue = []


    # --- NEW: Rules string for wrapping ---
    rules_string = (
        "Game Rules\n"
        "\n"
        "* Pot all balls (1-8).\n"
        "* Pot the Pink (9) ball last to win.\n"
        "* Potting the Pink ball early is a loss.\n"
        "* Potting the cue ball is a foul and adds 10s to your time.\n"
        "* Win with the fastest time and fewest shots for max score."
    )

    # --- Setup Balls ---
    # NOTE: Using global SCREEN_WIDTH/HEIGHT now
    startX = SCREEN_WIDTH - (SCREEN_WIDTH - TABLE_START_X) / 4
    startY = SCREEN_HEIGHT / 2
    
    cue = Ball( (SCREEN_WIDTH - TABLE_START_X) / 4 + TABLE_START_X, SCREEN_HEIGHT / 2, WHITE)
    
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
        Ball(startX - 20 * spacing_factor, startY, PINK) # The winning ball
    ]
    
    # --- Setup Holes ---
    # NOTE: Corrected list with 6 holes, using global vars
    holes = [
        Hole(TABLE_START_X + 3, 3),
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, 3),
        Hole(SCREEN_WIDTH - 3, 3),
        Hole(TABLE_START_X + 3, SCREEN_HEIGHT - 3),
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, SCREEN_HEIGHT - 3),
        Hole(SCREEN_WIDTH - 3, SCREEN_HEIGHT - 3)
    ]
    for hole in holes:
        hole.radius += hole_radius_change
    
    is_aiming = False
    running = True
    music_playing = False # <-- ADDED: Flag to track music state
    
    # --- Main Game Loop ---
    while running:
        
        # --- NEW: Music Control Logic ---
        if shots == 0:
            if not music_playing:
                try:
                    pygame.mixer.music.play(-1) # Start looping
                    music_playing = True
                except pygame.error:
                    print("Could not play music.")

        else: # shots > 0
            if music_playing:
                pygame.mixer.music.stop()
                music_playing = False
        # --- End of Music Control Logic ---

        delta_time = clock.tick(60) / 1000.0 # Time in seconds since last frame
        
        # --- NEW: Flag to play sound only once per frame ---
        collision_sound_played_this_frame = False
        potting_sound_played_this_frame = False # <-- ADDED

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if not cue.is_moving and not game_over:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click down
                    is_aiming = True
                    balls_potted = 0
                
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1: # Left click up
                    if is_aiming:
                        is_aiming = False
                        mouse_pos = event.pos
                        dx = cue.x - mouse_pos[0]
                        dy = cue.y - mouse_pos[1]
                        
                        cue.speedx = dx * 2.5
                        cue.speedy = dy * 2.5
                        cue.is_moving = True
                        shots += 1
                        # play_sound(collision_sound) # <-- Replaced with flag
                        collision_sound_played_this_frame = True # Play on first shot

        # --- Game Logic Updates ---
        
        # Update Cue Position
        cue.x += cue.speedx * delta_time
        cue.y += cue.speedy * delta_time
        cue.speedx *= 0.99 # Friction
        cue.speedy *= 0.99

        if abs(cue.speedx) < 5 and abs(cue.speedy) < 5: # Increased threshold
            cue.speedx = 0
            cue.speedy = 0
            cue.is_moving = False
        else:
            cue.is_moving = True # Ensure it's marked as moving

        # Cue Collision with Table Boundaries (Using width/height)
        if cue.x - cue.radius < TABLE_START_X:
            cue.x = TABLE_START_X + cue.radius
            cue.speedx *= -1
        if cue.x + cue.radius > SCREEN_WIDTH:
            cue.x = SCREEN_WIDTH - cue.radius
            cue.speedx *= -1
        if cue.y - cue.radius < 0:
            cue.y = cue.radius
            cue.speedy *= -1
        if cue.y + cue.radius > SCREEN_HEIGHT:
            cue.y = SCREEN_HEIGHT - cue.radius
            cue.speedy *= -1

        # Update Ball Positions
        for ball in balls:
            ball.x += ball.speedx * delta_time
            ball.y += ball.speedy * delta_time
            ball.speedx *= 0.99
            ball.speedy *= 0.99

            if abs(ball.speedx) < 5 and abs(ball.speedy) < 5: # Increased threshold
                ball.speedx = 0
                ball.speedy = 0
                ball.is_moving = False
            else:
                ball.is_moving = True # Ensure it's marked as moving

            # Ball Collision with Table Boundaries (Using width/height)
            if ball.x - ball.radius < TABLE_START_X:
                ball.x = TABLE_START_X + ball.radius
                ball.speedx *= -1
            if ball.x + ball.radius > SCREEN_WIDTH:
                ball.x = SCREEN_WIDTH - ball.radius
                ball.speedx *= -1
            if ball.y - ball.radius < 0:
                ball.y = ball.radius
                ball.speedy *= -1
            if ball.y + ball.radius > SCREEN_HEIGHT:
                ball.y = SCREEN_HEIGHT - ball.radius
                ball.speedy *= -1

        # Collision Detection (Ball-Ball and Ball-Cue)
        for i in range(len(balls)):
            # Check only if ball 'i' is not potted
            if not balls[i].did_go:
                for j in range(i + 1, len(balls)):
                    # Check only if ball 'j' is not potted
                    if not balls[j].did_go and \
                       check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (balls[j].x, balls[j].y), balls[j].radius):
                        handle_collision(balls[i], balls[j])
                        # --- MODIFIED: Only set flag if balls are actually moving ---
                        if balls[i].is_moving or balls[j].is_moving:
                            collision_sound_played_this_frame = True

                if check_collision_circles((cue.x, cue.y), cue.radius, (balls[i].x, balls[i].y), balls[i].radius):
                    handle_collision(cue, balls[i])
                    # --- MODIFIED: Only set flag if balls are actually moving ---
                    if cue.is_moving or balls[i].is_moving:
                        collision_sound_played_this_frame = True

                # Ball-Hole Collision
                for hole in holes:
                    if check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (hole.x, hole.y), hole.radius):
                        # --- MODIFIED: Only play sound if ball hasn't been potted yet ---
                        if not balls[i].did_go:
                            potting_sound_played_this_frame = True
                        balls_potted += 1
                        balls[i].did_go = True
                        balls[i].x = (i + 1) * -5000  # Move off-screen
                        balls[i].y = (i + 1) * -5000
                        balls[i].speedx, balls[i].speedy = 0, 0
                        balls[i].is_moving = False
                        
        # Cue-Hole Collision (Foul)
        for hole in holes:
            if check_collision_circles((cue.x, cue.y), cue.radius, (hole.x, hole.y), hole.radius):
                # --- MODIFIED: Only play sound if cue is actually moving ---
                if cue.is_moving:
                    potting_sound_played_this_frame = True
                cue.x = (SCREEN_WIDTH - TABLE_START_X) / 4 + TABLE_START_X
                cue.y = SCREEN_HEIGHT / 2
                cue.speedx, cue.speedy = 0, 0
                cue.is_moving = False # Stop it from moving
                timer += 10  # 10 second penalty
                show_message = True
                message_timer = 0
                fouls += 1
                
        # --- NEW: Play collision sound once if any collision occurred ---
        if collision_sound_played_this_frame:
            play_sound(collision_sound)
        
        # --- NEW: Play potting sound once if any pot occurred ---
        if potting_sound_played_this_frame:
            play_sound(potting_sound)

        # Timer and Game Over Logic
        if not game_over:
            if shots > 0:
                timer += delta_time
        
        remaining_time = countdown_time - timer
        if remaining_time <= 0 and not countdown_finished:
            countdown_finished = True
            game_over = True
            did_win = False # Explicitly set loss
            score = 0       # Explicitly set score
            remaining_time = 0

        # --- Drawing Code ---
        screen.fill(SKYBLUE) # Background color
        
        # Draw table boundaries (Using width/height)
        pygame.draw.rect(screen, SKYBLUE, (TABLE_START_X, 0, SCREEN_WIDTH - TABLE_START_X, SCREEN_HEIGHT))
        
        # Draw left info panel
        pygame.draw.rect(screen, BLACK, (0, 0, TABLE_START_X, SCREEN_HEIGHT))
        
        if not game_over:
            # Draw baulk line (Using width/height)
            pygame.draw.line(screen, WHITE, (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, 0), (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, SCREEN_HEIGHT), 1)
            pygame.draw.circle(screen, WHITE, (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, SCREEN_HEIGHT / 2), 75, 1) # 'D'

            draw_text(f"Player: {username}", title_font, RED, 50, 50)
            
            if shots == 0:
                # --- NEW: Use text wrapping ---
                # Define the rectangle for the rules text
                rules_rect = pygame.Rect(10, 150, TABLE_START_X - 20, SCREEN_HEIGHT - 200)
                draw_text_wrapped(screen, rules_string, main_font, WHITE, rules_rect)
            
            if show_message:
                message_timer += delta_time
                draw_text("FOUL", foul_font, RED, 700, 400)
                draw_text("-10 seconds", foul_font, RED, 700, 450)
                if message_timer >= 2:
                    show_message = False
                    message_timer = 0
            
            # Display Time
            time_text = f"Time Left: {remaining_time:.2f}"
            time_color = RED if remaining_time < 30 else BLUE
            draw_text(time_text, title_font, time_color, 50, 100)

            # Draw holes, cue, and balls
            for hole in holes:
                hole.draw()
            cue.draw()
            for ball in balls:
                ball.draw()
            
            # Draw cue line
            if is_aiming:
                mouse_pos = pygame.mouse.get_pos()
                if aiming_level != 'hard': # Don't draw brown stick on hard
                    pygame.draw.line(screen, BROWN, (cue.x, cue.y), mouse_pos, 3)
                
                if aiming_level == 'easy': # Only draw ghost line on easy
                    pygame.draw.line(screen, WHITE, (cue.x, cue.y), (2 * cue.x - mouse_pos[0], 2 * cue.y - mouse_pos[1]), 1)
        
        if not cue.is_moving and shots > 0:
            # Check real-time achievements *only if* balls were potted this turn
            if balls_potted > 0:
                
                # 1. Check for "First Potter"
                if FIRST_POT_ID not in earned_achievements_cache and total_balls_potted_game == 0:
                    print("Granting FIRST POTTER")
                    auth.grant_achievement(player_id, FIRST_POT_ID)
                    earned_achievements_cache.add(FIRST_POT_ID)
                    achievement_popup_queue.append({"text": "First Potter!", "timer": 0}) # Add name to popup queue
                
                # 2. Check for "Combo Shot"
                if COMBO_ACHIEVEMENT_ID not in earned_achievements_cache and balls_potted >= 2:
                    print("Granting COMBO SHOT")
                    auth.grant_achievement(player_id, COMBO_ACHIEVEMENT_ID)
                    earned_achievements_cache.add(COMBO_ACHIEVEMENT_ID)
                    achievement_popup_queue.append({"text": "Combo Shot!", "timer": 0}) # Add name to popup queue

                # Update total balls potted
                total_balls_potted_game += balls_potted
            
            # Reset turn counter
            total_balls_potted_game += balls_potted
            balls_potted = 0

        # --- Game Over / Win/Loss Logic ---
        pink_ball = balls[8]
        if pink_ball.did_go and not game_over:
            win = True
            for i in range(8): # Check if all other balls (0-7) are potted
                if not balls[i].did_go:
                    win = False
                    break
            
            game_over = True
            if win:
                did_win = True
                # Score calculation
                score = (((countdown_time - timer) / countdown_time) * 200 - (shots * 1) + 100) * difficulty_factor
                if score < 0: score = 0
            else:
                did_win = False
                score = 0
        
        if countdown_finished:
            draw_text("Time's up!", foul_font, RED, 700, 400)

        if game_over:
            
            # --- SAVE SCORE (Runs only ONCE) ---
            if not game_over_saved:
                print("Game over. Saving score...")
                auth.save_game_session(player_id, difficulty_id, score, did_win)
                auth.check_all_achievements(
                    player_id, 
                    difficulty_id, 
                    timer, 
                    shots, 
                    fouls,  # <-- Passing our new counter
                    did_win
                )
                
                game_over_saved = True # Prevent saving again
            # ---
            if achievement_popup_queue:
                # Get the first item (which is now a dictionary)
                popup_item = achievement_popup_queue[0]
                popup_text = popup_item["text"] # Get the text from the dict
                
                # Create a semi-transparent background
                popup_surf = pygame.Surface((350, 60))
                popup_surf.set_alpha(200) # Semi-transparent
                popup_surf.fill(BLACK)
                
                # Draw the popup
                popup_rect = popup_surf.get_rect(center=(SCREEN_WIDTH // 2, 50))
                screen.blit(popup_surf, popup_rect)
                
                # Draw border and text
                pygame.draw.rect(screen, GOLD, popup_rect, 3) # Gold border
                draw_text("Achievement Unlocked!", achievement_font, GOLD, popup_rect.x + 80, popup_rect.y + 10)
                draw_text(popup_text, main_font, WHITE, popup_rect.x + (350 - main_font.size(popup_text)[0]) // 2, popup_rect.y + 35)
                
                # Simple timer logic: show for 2 seconds (120 frames)
                popup_item["timer"] += 1 # Increment the timer *inside* the dictionary
                
                if popup_item["timer"] > 120:
                    achievement_popup_queue.pop(0)
            
            # Game is over, show scores
            if did_win:
                draw_text("YOU WON! CONGRATS", foul_font, GREEN, 700, 400)
            elif countdown_finished:
                draw_text("YOU LOST ON TIME", foul_font, RED, 700, 400)
            else:
                draw_text("YOU POTTED THE PINK BALL EARLY!", foul_font, RED, 700, 350)
                draw_text("GAME OVER.", foul_font, RED, 700, 400)
            
            score_text = f"YOUR SCORE IS: {score:.2f}"
            draw_text(score_text, foul_font, WHITE, 700, 500)
            
            # Display top scores from DB
            draw_text("Top Scorers:", title_font, WHITE, 50, 150)
            top_scores = auth.get_top_scores()
            if not top_scores:
                draw_text("Be the first to set a score!", main_font, WHITE, 50, 200)
            else:
                for i, record in enumerate(top_scores):
                    text = f"{i+1}. {record['Username']} - {record['Score']:.2f}({record['LevelName']})" # Format score
                    draw_text(text, main_font, WHITE, 50, 200 + i * 35)

            # Wait for user to quit
            draw_text("Click anywhere to quit.", main_font, WHITE, 700, 600)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    running = False

        
                
        # --- NEW: Achievement Popup Drawing Logic ---
        # (This draws on top of everything, including the game over screen)
         # Remove from queue
        # --- End of new block ---

        # --- Update the Display ---
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
        main_game(player_id, username, difficulty_id)

    elif choice == "achievements":
        achievements_screen(player_id, username)
