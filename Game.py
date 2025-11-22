import pygame
import math
import sys
import auth  # This is your 'auth.py' file for login/registration

# --- Pygame Setup ---
pygame.init()
pygame.mixer.init()

# Screen dimensions
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 650
TABLE_START_X = SCREEN_WIDTH // 4
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("9-Ball Game (Database Project)")
clock = pygame.time.Clock()
main_font = pygame.font.SysFont("Arial", 25)
title_font = pygame.font.SysFont("Arial", 35)
foul_font = pygame.font.SysFont("Arial", 50)
achievement_font = pygame.font.SysFont("Arial", 20, bold=True)

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
    0: pygame.image.load("assets/cue.png")
}
# Map Ball IDs to Names for the Database
BALL_NAMES = {
    0: "Cue Ball",   # Stays as "Cue Ball"
    1: "Ball#1",     # Yellow
    2: "Ball#2",     # Blue
    3: "Ball#3",     # Red
    4: "Ball#4",     # Purple
    5: "Ball#5",     # Orange
    6: "Ball#6",     # Green
    7: "Ball#7",     # Brown
    8: "Ball#8",     # Black
    9: "Ball#9"      # Pink
}
# --- Colors ---
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

# --- Sound Setup ---
try:
    bg_music = pygame.mixer.music.load("assets/sound/bgm.mp3")
    collision_sound = pygame.mixer.Sound("assets/sound/collision.wav")
    potting_sound = pygame.mixer.Sound("assets/sound/ball_pocket.wav")
except FileNotFoundError:
    print("Sound files not found. Game will run without sound.")
    collision_sound = None
    potting_sound = None


# --- Helper Functions ---
def play_sound(sound):
    if sound:
        sound.play()


def draw_text(text, font, color, x, y):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))


def check_collision_circles(pos1, r1, pos2, r2):
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    distance = math.sqrt(dx * dx + dy * dy)
    return distance < r1 + r2


def handle_collision(ball1, ball):
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
        if ball.is_moving:
            movement_speed = abs(ball.speedx) + abs(ball.speedy)
            ball.angle += movement_speed * 0.5
            ball.angle %= 360

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


# --- Game Object Classes ---
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
        self.angle = 0
        self.ball_id = 0

    def draw(self):
        if not self.did_go:
            img = ball_images[self.ball_id]
            img = pygame.transform.scale(img, (40, 40))
            if self.is_moving:
                rotated_img = pygame.transform.rotate(img, self.angle)
            else:
                rotated_img = img
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

    play_button = pygame.Rect(450, 250, 300, 70)
    achieve_button = pygame.Rect(450, 350, 300, 70)
    change_pass_button = pygame.Rect(450, 450, 300, 70)

    while running:
        screen.fill((30, 30, 30))
        draw_text("Welcome, " + username, title_font, WHITE, 450, 120)
        draw_text("Select an option", menu_font, GOLD, 480, 180)

        pygame.draw.rect(screen, BLUE, play_button)
        pygame.draw.rect(screen, GREEN, achieve_button)
        draw_text("PLAY", menu_font, WHITE, play_button.x + 85, play_button.y + 18)
        draw_text("ACHIEVEMENTS", menu_font, WHITE, achieve_button.x + 15, achieve_button.y + 18)

        pygame.draw.rect(screen, RED, change_pass_button)
        draw_text("CHANGE PASSWORD", menu_font, WHITE, change_pass_button.x + 5, change_pass_button.y + 18)

        for event in pygame.event.get():
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
    earned_raw = auth.get_player_achievements(player_id)
    earned = set()
    for row in earned_raw:
        try:
            val = row[0] if isinstance(row, (tuple, list)) else row
            earned.add(int(val))
        except:
            pass
    all_achievements = auth.get_all_achievements_list()

    unlocked_color = (60, 180, 75)
    locked_color = (70, 70, 70)
    border_color = (230, 230, 230)
    box_width, box_height = 1000, 80
    x, start_y = 150, 150
    scroll_offset = 0
    scroll_speed = 25
    return_button = pygame.Rect(20, 20, 150, 50)

    while running:
        screen.fill((25, 25, 25))
        draw_text(f"{username}'s Achievements", title_font, GOLD, 350, 70)
        pygame.draw.rect(screen, (200, 50, 50), return_button, border_radius=8)
        draw_text("RETURN", main_font, WHITE, return_button.x + 20, return_button.y + 10)

        y = start_y + scroll_offset
        for ach in all_achievements:
            ach_id = int(ach["AchievementID"])
            name, desc = ach["Name"], ach["Description"]
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

        content_height = len(all_achievements) * (box_height + 20)
        visible_height = SCREEN_HEIGHT - start_y - 30
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
                if return_button.collidepoint(event.pos): return
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset += event.y * scroll_speed
                max_scroll = 0
                min_scroll = -(content_height - visible_height) if content_height > visible_height else 0
                scroll_offset = max(min(scroll_offset, max_scroll), min_scroll)
        pygame.display.update()


def difficulty_screen():
    while True:
        center_x = SCREEN_WIDTH // 2
        button_width = 250
        easy_button = pygame.Rect(center_x - button_width // 2, SCREEN_HEIGHT * 0.3, button_width, 70)
        medium_button = pygame.Rect(center_x - button_width // 2, SCREEN_HEIGHT * 0.5, button_width, 70)
        hard_button = pygame.Rect(center_x - button_width // 2, SCREEN_HEIGHT * 0.7, button_width, 70)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if easy_button.collidepoint(event.pos):
                    return 1
                elif medium_button.collidepoint(event.pos):
                    return 2
                elif hard_button.collidepoint(event.pos):
                    return 3

        screen.fill(BLACK)
        draw_text("Select Difficulty", title_font, WHITE, center_x - title_font.size("Select Difficulty")[0] // 2,
                  SCREEN_HEIGHT * 0.1)
        pygame.draw.rect(screen, GREEN, easy_button)
        draw_text("Easy", title_font, BLACK, easy_button.x + 90, easy_button.y + 15)
        pygame.draw.rect(screen, YELLOW, medium_button)
        draw_text("Medium", title_font, BLACK, medium_button.x + 70, medium_button.y + 15)
        pygame.draw.rect(screen, RED, hard_button)
        draw_text("Hard", title_font, BLACK, hard_button.x + 90, hard_button.y + 15)
        pygame.display.flip()
        clock.tick(30)


def login_register_screen():
    username, password = "", ""
    message = "Enter Username & Password"
    active_field = "username"
    color_active, color_inactive = pygame.Color('dodgerblue2'), pygame.Color('lightgray')

    while True:
        center_x = SCREEN_WIDTH // 2
        input_box_user = pygame.Rect(center_x - 200, SCREEN_HEIGHT * 0.3, 400, 50)
        input_box_pass = pygame.Rect(center_x - 200, SCREEN_HEIGHT * 0.45, 400, 50)
        button_login = pygame.Rect(center_x - 200, SCREEN_HEIGHT * 0.6, 180, 50)
        button_register = pygame.Rect(center_x + 20, SCREEN_HEIGHT * 0.6, 180, 50)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_user.collidepoint(event.pos):
                    active_field = "username"
                elif input_box_pass.collidepoint(event.pos):
                    active_field = "password"
                elif button_login.collidepoint(event.pos):
                    result = auth.login_player(username, password)
                    message = result['message']
                    if result['success']: return result['player_id'], username
                elif button_register.collidepoint(event.pos):
                    result = auth.register_player(username, password)
                    message = result['message']

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    result = auth.login_player(username, password)
                    message = result['message']
                    if result['success']: return result['player_id'], username
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

        screen.fill(BLACK)
        draw_text("Pool Game Login", title_font, WHITE, center_x - title_font.size("Pool Game Login")[0] // 2,
                  SCREEN_HEIGHT * 0.1)
        draw_text(message, main_font, RED, center_x - main_font.size(message)[0] // 2, SCREEN_HEIGHT * 0.8)
        pygame.draw.rect(screen, color_active if active_field == "username" else color_inactive, input_box_user, 2)
        draw_text(username, main_font, WHITE, input_box_user.x + 5, input_box_user.y + 5)
        pygame.draw.rect(screen, color_active if active_field == "password" else color_inactive, input_box_pass, 2)
        draw_text('*' * len(password), main_font, WHITE, input_box_pass.x + 5, input_box_pass.y + 5)
        pygame.draw.rect(screen, GREEN, button_login)
        draw_text("Login", main_font, BLACK, button_login.x + 60, button_login.y + 10)
        pygame.draw.rect(screen, BLUE, button_register)
        draw_text("Register", main_font, BLACK, button_register.x + 40, button_register.y + 10)
        pygame.display.flip()
        clock.tick(30)


def change_password_screen(player_id, username):
    current_pass, new_pass, msg = "", "", ""
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
        pygame.draw.rect(screen, GREEN, save_button)
        draw_text("SAVE PASSWORD", main_font, BLACK, save_button.x + 40, save_button.y + 15)
        pygame.draw.rect(screen, BLUE, return_button)
        draw_text("RETURN", main_font, WHITE, return_button.x + 95, return_button.y + 15)
        draw_text(msg, main_font, RED, 450, 500)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_current.collidepoint(event.pos):
                    active = "current"
                elif input_box_new.collidepoint(event.pos):
                    active = "new"
                elif save_button.collidepoint(event.pos):
                    login_check = auth.login_player(username, current_pass)
                    if not login_check["success"]:
                        msg = "Current password incorrect."
                    else:
                        result = auth.update_password(player_id, new_pass)
                        msg = result['message']
                        if result['success']: current_pass, new_pass = "", ""
                elif return_button.collidepoint(event.pos):
                    return
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


def main_game(player_id, username, difficulty_id):
    # --- Game State ---
    game_over = False
    game_over_saved = False
    did_win = False
    show_message = False
    message_timer = 0
    timer = 0.0

    # ### NEW: LOGGING SETUP ###
    game_events = []  # Buffer to store events (PlayerID, PocketID, BallName, Type)
    # ##########################

    # Achievement Setup
    earned_achievements_cache = auth.get_player_achievements(player_id)
    achievement_popup_queue = []
    FIRST_POT_ID = 8
    COMBO_ACHIEVEMENT_ID = 7

    # Difficulty Setup
    if difficulty_id == 1:
        countdown_time = 500;
        aiming_level = 'easy';
        hole_radius_change = 5;
        difficulty_factor = 1.0
    elif difficulty_id == 2:
        countdown_time = 400;
        aiming_level = 'medium';
        hole_radius_change = 0;
        difficulty_factor = 1.35
    else:
        countdown_time = 300;
        aiming_level = 'hard';
        hole_radius_change = -5;
        difficulty_factor = 1.75

    score = 0.0
    shots = 0
    fouls = 0
    balls_potted_this_shot = 0
    total_balls_potted_game = 0

    # --- Setup Balls & Holes ---
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
        Hole(TABLE_START_X + 3, 3),  # ID 1
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, 3),  # ID 2
        Hole(SCREEN_WIDTH - 3, 3),  # ID 3
        Hole(TABLE_START_X + 3, SCREEN_HEIGHT - 3),  # ID 4
        Hole(TABLE_START_X + (SCREEN_WIDTH - TABLE_START_X) / 2, SCREEN_HEIGHT - 3),  # ID 5
        Hole(SCREEN_WIDTH - 3, SCREEN_HEIGHT - 3)  # ID 6
    ]
    for hole in holes: hole.radius += hole_radius_change

    is_aiming = False
    running = True
    music_playing = False
    countdown_finished = False

    while running:
        delta_time = clock.tick(60) / 1000.0

        if shots == 0 and not music_playing:
            try:
                pygame.mixer.music.play(-1); music_playing = True
            except:
                pass
        elif shots > 0 and music_playing:
            pygame.mixer.music.stop();
            music_playing = False

        collision_sound_played_this_frame = False
        potting_sound_played_this_frame = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if not cue.is_moving and not game_over:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    is_aiming = True;
                    balls_potted_this_shot = 0
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

                        # ### NEW: LOG SHOT EVENT ###
                        # (PlayerID, PocketID=None, BallName=None, Type="SHOT")
                        game_events.append((player_id, None, None, "SHOT"))
                        # ###########################

        # Physics
        cue.x += cue.speedx * delta_time;
        cue.y += cue.speedy * delta_time
        cue.speedx *= 0.99;
        cue.speedy *= 0.99
        if abs(cue.speedx) < 5 and abs(cue.speedy) < 5:
            cue.speedx, cue.speedy = 0, 0; cue.is_moving = False
        else:
            cue.is_moving = True

        if cue.x - cue.radius < TABLE_START_X: cue.speedx *= -1; cue.x = TABLE_START_X + cue.radius
        if cue.x + cue.radius > SCREEN_WIDTH: cue.speedx *= -1; cue.x = SCREEN_WIDTH - cue.radius
        if cue.y - cue.radius < 0: cue.speedy *= -1; cue.y = cue.radius
        if cue.y + cue.radius > SCREEN_HEIGHT: cue.speedy *= -1; cue.y = SCREEN_HEIGHT - cue.radius

        for ball in balls:
            ball.x += ball.speedx * delta_time;
            ball.y += ball.speedy * delta_time
            ball.speedx *= 0.99;
            ball.speedy *= 0.99
            if abs(ball.speedx) < 5 and abs(ball.speedy) < 5:
                ball.speedx, ball.speedy = 0, 0; ball.is_moving = False
            else:
                ball.is_moving = True

            if ball.x - ball.radius < TABLE_START_X: ball.speedx *= -1; ball.x = TABLE_START_X + ball.radius
            if ball.x + ball.radius > SCREEN_WIDTH: ball.speedx *= -1; ball.x = SCREEN_WIDTH - ball.radius
            if ball.y - ball.radius < 0: ball.speedy *= -1; ball.y = ball.radius
            if ball.y + ball.radius > SCREEN_HEIGHT: ball.speedy *= -1; ball.y = SCREEN_HEIGHT - ball.radius
            if ball.is_moving: ball.angle += (abs(ball.speedx) + abs(ball.speedy)) * 0.1

        # Interactions
        for i in range(len(balls)):
            if not balls[i].did_go:
                for j in range(i + 1, len(balls)):
                    if not balls[j].did_go and check_collision_circles((balls[i].x, balls[i].y), balls[i].radius,
                                                                       (balls[j].x, balls[j].y), balls[j].radius):
                        handle_collision(balls[i], balls[j])
                        if balls[i].is_moving or balls[j].is_moving: collision_sound_played_this_frame = True

                if check_collision_circles((cue.x, cue.y), cue.radius, (balls[i].x, balls[i].y), balls[i].radius):
                    handle_collision(cue, balls[i])
                    if cue.is_moving or balls[i].is_moving: collision_sound_played_this_frame = True

                # Ball Potting Check
                for idx, hole in enumerate(holes):  # Use enumerate to get Index (0-5)
                    if check_collision_circles((balls[i].x, balls[i].y), balls[i].radius, (hole.x, hole.y),
                                               hole.radius):
                        if not balls[i].did_go: potting_sound_played_this_frame = True
                        balls_potted_this_shot += 1
                        balls[i].did_go = True
                        balls[i].x, balls[i].y = -5000, -5000
                        balls[i].speedx, balls[i].speedy = 0, 0
                        balls[i].is_moving = False

                        # ### NEW: LOG POTTED EVENT ###
                        # idx + 1 gives us PocketID (1-6)
                        pocket_id = idx + 1
                        ball_name = BALL_NAMES.get(balls[i].ball_id, "Unknown")
                        game_events.append((player_id, pocket_id, ball_name, "POTTED"))
                        # #############################

        # Foul
        for hole in holes:
            if check_collision_circles((cue.x, cue.y), cue.radius, (hole.x, hole.y), hole.radius):
                if cue.is_moving: potting_sound_played_this_frame = True
                cue.x = (SCREEN_WIDTH - TABLE_START_X) / 4 + TABLE_START_X;
                cue.y = SCREEN_HEIGHT / 2
                cue.speedx, cue.speedy = 0, 0;
                cue.is_moving = False
                timer += 10;
                show_message = True;
                message_timer = 0;
                fouls += 1

                # ### NEW: LOG FOUL EVENT ###
                game_events.append((player_id, None, "Cue Ball", "FOUL"))
                # ###########################

        if show_message:
            message_timer += 1
            if message_timer > 30: show_message = False

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

        # Achievement Logic (Mid-Game)
        all_stopped = not cue.is_moving and all(not b.is_moving for b in balls)
        if all_stopped and shots > 0 and balls_potted_this_shot > 0:
            if FIRST_POT_ID not in earned_achievements_cache:
                auth.grant_achievement(player_id, FIRST_POT_ID)
                earned_achievements_cache.add(FIRST_POT_ID)
                achievement_popup_queue.append({"text": "First Potter!", "timer": 0})
            if balls_potted_this_shot >= 2:
                # This saves a specific "COMBO" line to your database
                combo_label = f"{balls_potted_this_shot} Ball Combo"
                game_events.append((player_id, None, combo_label, "COMBO"))

                if COMBO_ACHIEVEMENT_ID not in earned_achievements_cache:
                    print(f"Flexible unlock: Combo Shot (Potted {balls_potted_this_shot} balls)")
                    auth.grant_achievement(player_id, COMBO_ACHIEVEMENT_ID)
                    earned_achievements_cache.add(COMBO_ACHIEVEMENT_ID)
                    achievement_popup_queue.append({"text": "Combo Shot!", "timer": 0})
            total_balls_potted_game += balls_potted_this_shot
            balls_potted_this_shot = 0

        # Game Over Logic
        pink_ball = balls[8]
        if pink_ball.did_go and not game_over:
            win = True
            for i in range(8):
                if not balls[i].did_go: win = False; break
            game_over = True;
            did_win = win
            if win: score = (((countdown_time - timer) / countdown_time) * 200 - (shots * 1) + 100) * difficulty_factor
            if score < 0: score = 0

        # Save Game
        if game_over and not game_over_saved:
            # ### NEW: SAVE SESSION & EVENTS ###
            # 1. Save Session and get the ID back
            session_id = auth.save_game_session(player_id, difficulty_id, score, did_win)

            # 2. Save the Event Log if we got a valid session ID
            if session_id:
                auth.save_event_log(session_id, game_events)
            # ##################################

            new_achievements = auth.check_all_achievements(player_id, difficulty_id, timer, shots, fouls, did_win)
            for ach in new_achievements:
                achievement_popup_queue.append({"text": ach["Name"], "timer": 0})
            game_over_saved = True

        # Draw
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
            for hole in holes: hole.draw()
            cue.draw()
            for ball in balls: ball.draw()
            if is_aiming:
                mouse_pos = pygame.mouse.get_pos()
                if aiming_level != 'hard': pygame.draw.line(screen, BROWN, (cue.x, cue.y), mouse_pos, 3)
                if aiming_level == 'easy': pygame.draw.line(screen, WHITE, (cue.x, cue.y),
                                                            (2 * cue.x - mouse_pos[0], 2 * cue.y - mouse_pos[1]), 1)
            if show_message: draw_text("FOUL (-10s)", foul_font, RED, 700, 400)

        else:
            if did_win:
                draw_text("YOU WON!", foul_font, GREEN, 500, 350)
            elif countdown_finished:
                draw_text("TIME UP!", foul_font, RED, 500, 350)
            else:
                draw_text("EARLY PINK!", foul_font, RED, 500, 350)
            draw_text(f"SCORE: {score:.0f}", foul_font, WHITE, 500, 450)

            menu_btn = pygame.Rect(300, 550, 200, 60)
            logout_btn = pygame.Rect(550, 550, 200, 60)
            exit_btn = pygame.Rect(800, 550, 200, 60)

            pygame.draw.rect(screen, GREEN, menu_btn)
            draw_text("MENU", main_font, BLACK, menu_btn.x + 60, menu_btn.y + 15)
            pygame.draw.rect(screen, BLUE, logout_btn)
            draw_text("LOGOUT", main_font, WHITE, logout_btn.x + 50, logout_btn.y + 15)
            pygame.draw.rect(screen, RED, exit_btn)
            draw_text("EXIT", main_font, WHITE, exit_btn.x + 70, exit_btn.y + 15)

            if pygame.mouse.get_pressed()[0]:
                mx, my = pygame.mouse.get_pos()
                if menu_btn.collidepoint(mx, my): return "menu"
                if logout_btn.collidepoint(mx, my): return "logout"
                if exit_btn.collidepoint(mx, my): pygame.quit(); sys.exit()

        if achievement_popup_queue:
            popup = achievement_popup_queue[0]
            box_w, box_h = 400, 80
            center_x = SCREEN_WIDTH // 2
            box_rect = pygame.Rect(center_x - box_w // 2, 50, box_w, box_h)
            pygame.draw.rect(screen, (20, 20, 20), box_rect, border_radius=10)
            pygame.draw.rect(screen, GOLD, box_rect, 3, border_radius=10)
            draw_text("Achievement Unlocked!", achievement_font, GOLD, box_rect.x + 90, box_rect.y + 10)
            txt_surf = main_font.render(popup['text'], True, WHITE)
            txt_x = box_rect.x + (box_w - txt_surf.get_width()) // 2
            screen.blit(txt_surf, (txt_x, box_rect.y + 40))
            popup['timer'] += 1
            if popup['timer'] > 180: achievement_popup_queue.pop(0)

        pygame.display.flip()

    pygame.quit()
    sys.exit()
while True:
    pid_uname = login_register_screen()
    if pid_uname is None: break

    player_id, username = pid_uname

    while True:
        choice = post_login_menu(player_id, username)

        if choice == "play":
            difficulty_id = difficulty_screen()
            result = main_game(player_id, username, difficulty_id)
            if result == "logout": break
        elif choice == "achievements":
            achievements_screen(player_id, username)

pygame.quit()
sys.exit()