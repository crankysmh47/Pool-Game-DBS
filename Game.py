import pygame
import math
import sys
import auth  # This is your 'auth.py' file for login/registration
import mysql.connector
from mysql.connector import Error

# --- Database Connection Details ---
# (These must match your auth.py)
DB_HOST = "localhost"
DB_NAME = "pool_game_db"
DB_USER = "root"
DB_PASS = "roo123"  # <-- !!! CHANGE THIS to your MySQL password !!!

# --- Pygame Setup ---
pygame.init()
pygame.mixer.init() # for sounds

# Screen dimensions
SCREEN_WIDTH = 920
SCREEN_HEIGHT = 450
TABLE_START_X = 225 # The left-side panel width
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("9-Ball Game (Database Project)")
clock = pygame.time.Clock()
main_font = pygame.font.SysFont("Arial", 25)
title_font = pygame.font.SysFont("Arial", 35)
foul_font = pygame.font.SysFont("Arial", 50)

# --- Colors ---
SKYBLUE = (135, 206, 235)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 128, 0) # Table color
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
DARKPURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
DARKGREEN = (0, 100, 0)
PINK = (255, 192, 203)

# --- Sound Setup (Commented out, add your own paths) ---
try:
    bg_music = pygame.mixer.music.load("C:/Users/Administrator/source/repos/PONG1/bgm.mp3")
    pygame.mixer.music.play(-1) # Loop forever
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

# --- Database Functions (Replaces File I/O) ---

def get_db_connection():
    """ Helper function to create a database connection. """
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

def save_game_session(player_id, difficulty_id, score, did_win):
    """
    Saves the completed game to the database.
    This replaces updateScoresFile().
    """
    conn = get_db_connection()
    if conn is None:
        print("Could not save score. DB connection failed.")
        return

    cursor = conn.cursor()
    try:
        # 1. Create the GameSession
        sql_session = "INSERT INTO GameSession (DifficultyID) VALUES (%s)"
        cursor.execute(sql_session, (difficulty_id,))
        game_session_id = cursor.lastrowid # Get the ID of the new session
        
        # 2. Link the Player to the session
        sql_participant = """
            INSERT INTO GameParticipant (GameSessionID, PlayerID, Score, IsWinner) 
            VALUES (%s, %s, %s, %s)
        """
        values = (game_session_id, player_id, int(score), did_win)
        cursor.execute(sql_participant, values)
        
        conn.commit()
        print(f"Game session {game_session_id} saved for player {player_id} with score {score}.")

    except Error as e:
        print(f"Database error saving game: {e}")
    finally:
        cursor.close()
        conn.close()

def get_top_scores():
    """
    Gets the top 5 scores from the database.
    This replaces getTopScore().
    """
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    top_scores = []
    try:
        # Join Player and GameParticipant, order by score, get top 5
        sql = """
            SELECT p.Username, gp.Score
            FROM GameParticipant gp
            JOIN Player p ON p.PlayerID = gp.PlayerID
            ORDER BY gp.Score DESC
            LIMIT 5
        """
        cursor.execute(sql)
        top_scores = cursor.fetchall()

    except Error as e:
        print(f"Database error getting top scores: {e}")
    finally:
        cursor.close()
        conn.close()
        return top_scores

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

# --- Login/Register Screen ---

def login_register_screen():
    """
    New screen to handle user login or registration.
    Replaces getUsernameInput().
    """
    username = ""
    password = ""
    message = "Enter Username & Password"
    active_field = "username" # "username", "password", "login"
    
    input_box_user = pygame.Rect(200, 200, 400, 50)
    input_box_pass = pygame.Rect(200, 300, 400, 50)
    button_login = pygame.Rect(200, 400, 180, 50)
    button_register = pygame.Rect(420, 400, 180, 50)
    
    color_active = pygame.Color('dodgerblue2')
    color_inactive = pygame.Color('lightgray')
    
    while True:
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
                    message = result['message']
                    if result['success']:
                        return result['player_id'], username # Login successful!
                elif button_register.collidepoint(event.pos):
                    # --- Try to Register ---
                    print(f"Attempting registration for: {username}")
                    result = auth.register_player(username, password)
                    message = result['message']
                    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # --- Try to Login on Enter ---
                    print(f"Attempting login for: {username}")
                    result = auth.login_player(username, password)
                    message = result['message']
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
        draw_text("Pool Game Login", title_font, WHITE, 200, 100)
        draw_text(message, main_font, RED, 200, 500)
        
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

# --- Main Game Function ---

def main_game(player_id, username):
    """
    The main game loop, translated from your C++ main().
    """
    
    # --- Game State Variables ---
    game_over = False
    did_win = False
    show_message = False
    message_timer = 0
    timer = 0.0
    countdown_time = 300.0
    countdown_finished = False
    score = 0.0
    shots = 0

    # --- Setup Balls ---
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
    holes = [
        Hole(TABLE_START_X + 3, 3),
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, 3),
        Hole(SCREEN_WIDTH - 3, 3),
        Hole(TABLE_START_X + 3, SCREEN_HEIGHT - 3),
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, SCREEN_HEIGHT - 3),
        Hole(SCREEN_WIDTH - 3, SCREEN_HEIGHT - 3)
    ]
    
    is_aiming = False
    running = True
    
    # --- Main Game Loop ---
    while running:
        
        delta_time = clock.tick(60) / 1000.0 # Time in seconds since last frame
        
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if not cue.is_moving and not game_over:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click down
                    is_aiming = True
                
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
                        play_sound(collision_sound)

        # --- Game Logic Updates ---
        
        # Update Cue Position
        cue.x += cue.speedx * delta_time
        cue.y += cue.speedy * delta_time
        cue.speedx *= 0.99 # Friction
        cue.speedy *= 0.99

        if abs(cue.speedx) < 10 and abs(cue.speedy) < 10:
            cue.speedx = 0
            cue.speedy = 0
            cue.is_moving = False

        # Cue Collision with Table Boundaries
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

            if abs(ball.speedx) < 10 and abs(ball.speedy) < 10:
                ball.speedx = 0
                ball.speedy = 0
                ball.is_moving = False

            # Ball Collision with Table Boundaries
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
            for j in range(i + 1, len(balls)):
                if check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (balls[j].x, balls[j].y), balls[j].radius):
                    handle_collision(balls[i], balls[j])
                    play_sound(collision_sound)

            if check_collision_circles((cue.x, cue.y), cue.radius, (balls[i].x, balls[i].y), balls[i].radius):
                handle_collision(cue, balls[i])
                play_sound(collision_sound)

            # Ball-Hole Collision
            for hole in holes:
                if check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (hole.x, hole.y), hole.radius):
                    balls[i].did_go = True
                    balls[i].x = (i + 1) * -5000 # Move off-screen
                    balls[i].y = (i + 1) * -5000
                    balls[i].speedx, balls[i].speedy = 0, 0
                    balls[i].is_moving = False
                    play_sound(potting_sound)
                    
        # Cue-Hole Collision (Foul)
        for hole in holes:
            if check_collision_circles((cue.x, cue.y), cue.radius, (hole.x, hole.y), hole.radius):
                cue.x = (SCREEN_WIDTH - TABLE_START_X) / 4 + TABLE_START_X
                cue.y = SCREEN_HEIGHT / 2
                cue.speedx, cue.speedy = 0, 0
                timer += 10 # 10 second penalty
                show_message = True
                message_timer = 0
                play_sound(potting_sound)

        # Timer and Game Over Logic
        if not game_over:
            if shots > 0:
                timer += delta_time
        
        remaining_time = countdown_time - timer
        if remaining_time <= 0 and not countdown_finished:
            countdown_finished = True
            game_over = True
            remaining_time = 0

        # --- Drawing Code ---
        screen.fill(SKYBLUE) # Table felt color
        
        # Draw table boundaries
        pygame.draw.rect(screen, GREEN, (TABLE_START_X, 0, SCREEN_WIDTH - TABLE_START_X, SCREEN_HEIGHT))
        
        # Draw left info panel
        pygame.draw.rect(screen, BLACK, (0, 0, TABLE_START_X, SCREEN_HEIGHT))
        
        if not game_over:
            # Draw baulk line
            pygame.draw.line(screen, WHITE, (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, 0), (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, SCREEN_HEIGHT), 1)
            pygame.draw.circle(screen, WHITE, (TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 4, SCREEN_HEIGHT / 2), 75, 1) # 'D'

            draw_text(f"Player: {username}", title_font, RED, 50, 50)
            
            if shots == 0:
                rules = [
                    "Game Rules",
                    "",
                    "* Pot all balls (1-8).",
                    "* Pot the Pink (9) ball last to win.",
                    "* Potting the Pink ball early is a loss.",
                    "* Potting the cue ball is a foul",
                    "  and adds 10s to your time.",
                    "* Win with the fastest time",
                    "  and fewest shots for max score.",
                ]
                for i, line in enumerate(rules):
                    draw_text(line, main_font, WHITE, 10, 150 + i * 30)
            
            if show_message:
                message_timer += delta_time
                draw_text("FOUL", foul_font, RED, 700, 400)
                draw_text("-10 seconds", foul_font, RED, 700, 450)
                if message_timer >= 2:
                    show_message = False
                    message_timer = 0
            
            # Display Time
            time_text = f"Time Left: {remaining_time:.2f}"
            draw_text(time_text, title_font, BLUE, 50, 100)

            # Draw holes, cue, and balls
            for hole in holes:
                hole.draw()
            cue.draw()
            for ball in balls:
                ball.draw()
            
            # Draw cue line
            if is_aiming:
                mouse_pos = pygame.mouse.get_pos()
                pygame.draw.line(screen, BROWN, (cue.x, cue.y), mouse_pos, 3)
                pygame.draw.line(screen, WHITE, (cue.x, cue.y), (2 * cue.x - mouse_pos[0], 2 * cue.y - mouse_pos[1]), 1)
        
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
                score = ((countdown_time - timer) / countdown_time) * 200 - (shots * 1) + 100
                if score < 0: score = 0
            else:
                did_win = False
                score = 0
        
        if countdown_finished:
            draw_text("Time's up!", foul_font, RED, 700, 400)

        if game_over:
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
            top_scores = get_top_scores()
            if not top_scores:
                draw_text("Be the first to set a score!", main_font, WHITE, 50, 200)
            else:
                for i, record in enumerate(top_scores):
                    text = f"{i+1}. {record['Username']} - {record['Score']}"
                    draw_text(text, main_font, WHITE, 50, 200 + i * 35)

            # Wait for user to quit
            draw_text("Click anywhere to quit.", main_font, WHITE, 700, 600)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    running = False

        # --- Update the Display ---
        pygame.display.flip()
        
    # --- End of Game Loop ---
    # Save the score
    if score > 0 or did_win:
        # We'll use 1 for 'Easy' difficulty. You can change this.
        save_game_session(player_id, 1, score, did_win)
    
    pygame.quit()
    sys.exit()

# --- Main Driver ---
if __name__ == "__main__":
    # 1. Show login screen.
    # This loop won't exit until login is successful.
    player_id, username = login_register_screen()
    
    # 2. Start the main game
    print(f"Starting game for PlayerID: {player_id}, User: {username}")
    main_game(player_id, username)