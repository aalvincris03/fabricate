import pygame
import random
import sys
import threading
import time

# Try to import GPIO and MFRC522 libraries (for Raspberry Pi)
try:
    import RPi.GPIO as GPIO
    from mfrc522 import SimpleMFRC522
    RFID_AVAILABLE = True
except ImportError:
    RFID_AVAILABLE = False
    print("RFID libraries not available. RFID functionality disabled.")

# Initialize Pygame
pygame.init()

# Load and scale background image
background_image = pygame.image.load('uploads/bg_game.png')
background_image = pygame.transform.scale(background_image, (800, 512))

# Screen dimensions for 7" x 4.5" LCD (aspect ratio ~16:9, assuming 800x512)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 512

# Colors (kid-friendly and bright)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
PINK = (255, 192, 203)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)

# Background gradient colors
BG_TOP = (135, 206, 235)  # Sky blue
BG_BOTTOM = (255, 255, 224)  # Light yellow

# Game states
MENU = 0
GAME = 1
END = 2

# Operation types
ADDITION = 0
SUBTRACTION = 1
MULTIPLICATION = 2
DIVISION = 3

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Arithmetic Game")

# Fonts
font_large = pygame.font.SysFont(None, 72)
font_medium = pygame.font.SysFont(None, 48)
font_small = pygame.font.SysFont(None, 36)

# Game variables
current_state = MENU
selected_operation = None  # Start with no operation selected
score = 0
question_index = 0
total_questions = 20
current_question = None
selected_answer = None
show_feedback = False
feedback_timer = 0
question_timer = 30  # 30 seconds per question
last_timer_update = 0
show_menu_confirm = False

# RFID variables (only if available)
if RFID_AVAILABLE:
    reader = SimpleMFRC522()
    rfid_thread = None
    rfid_tag = None
    rfid_lock = threading.Lock()

    # RFID tag mappings for answers (A, B, C, D)
    rfid_tags = {
        'A': 'TAG_A_ID',  # Replace with actual RFID tag ID for answer A
        'B': 'TAG_B_ID',  # Replace with actual RFID tag ID for answer B
        'C': 'TAG_C_ID',  # Replace with actual RFID tag ID for answer C
        'D': 'TAG_D_ID'   # Replace with actual RFID tag ID for answer D
    }
else:
    reader = None
    rfid_thread = None
    rfid_tag = None
    rfid_lock = None
    rfid_tags = {}

# Button class for UI elements
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color=None, selected_color=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color or color
        self.selected_color = selected_color or color
        self.is_hovered = False
        self.is_selected = False

    def draw(self, screen):
        if self.is_selected:
            color = self.selected_color
        else:
            color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=10)

        text_surf = font_medium.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos, mouse_click):
        return self.rect.collidepoint(mouse_pos) and mouse_click

# Function to generate a random question
def generate_question(selected_operation):
    # Ensure answer is 2-digit (10-99)
    answer = random.randint(10, 90)

    if selected_operation == ADDITION:
        op = '+'
        num2 = random.randint(1, answer - 1)
        num1 = answer - num2
    elif selected_operation == SUBTRACTION:
        op = '-'
        num2 = random.randint(1, answer - 1)
        num1 = answer + num2
    elif selected_operation == MULTIPLICATION:
        op = '*'
        # Find factors of answer
        factors = []
        for i in range(1, answer + 1):
            if answer % i == 0:
                factors.append(i)
        num2 = random.choice(factors)
        num1 = answer // num2
    else:  # DIVISION
        op = '/'
        num2 = random.randint(1, answer)
        num1 = answer * num2

    if op == '*':
        op_display = 'x'
    elif op == '/':
        op_display = '÷'
    else:
        op_display = op
    question = f"{num1} {op_display} {num2} = ?"

    # Generate wrong answers
    wrong_answers = []
    while len(wrong_answers) < 3:
        wrong = answer + random.randint(-10, 10)
        if wrong != answer and wrong >= 0 and wrong not in wrong_answers:
            wrong_answers.append(wrong)

    # Shuffle answers
    answers = [answer] + wrong_answers
    random.shuffle(answers)

    return question, answers, answers.index(answer)

# Function to draw gradient background
def draw_gradient_background():
    for y in range(SCREEN_HEIGHT):
        r = BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * y // SCREEN_HEIGHT
        g = BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * y // SCREEN_HEIGHT
        b = BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * y // SCREEN_HEIGHT
        pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

# RFID reading function
def rfid_reader_thread():
    global rfid_tag
    try:
        while running:
            id, text = reader.read()
            with rfid_lock:
                rfid_tag = str(id)
    except Exception as e:
        print(f"RFID reader error: {e}")

# Function to initialize RFID
def init_rfid():
    global rfid_thread
    if RFID_AVAILABLE:
        try:
            rfid_thread = threading.Thread(target=rfid_reader_thread, daemon=True)
            rfid_thread.start()
        except Exception as e:
            print(f"Failed to initialize RFID: {e}")

# Function to get RFID answer
def get_rfid_answer():
    if not RFID_AVAILABLE:
        return None
    global rfid_tag
    with rfid_lock:
        tag = rfid_tag
        rfid_tag = None  # Reset after reading
    if tag:
        for answer, tag_id in rfid_tags.items():
            if tag == tag_id:
                return ord(answer) - ord('A')  # Convert A->0, B->1, C->2, D->3
    return None

# Initialize RFID
init_rfid()

# Main game loop
running = True
clock = pygame.time.Clock()

while running:
    mouse_pos = pygame.mouse.get_pos()
    mouse_click = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_click = True

    screen.blit(background_image, (0, 0))

    if current_state == MENU:
        # Draw title
        title_text = font_large.render("Arithmetic Game", True, BLACK)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 150))
        screen.blit(title_text, title_rect)

        # Operation buttons
        add_btn = Button(225, 200, 150, 50, "+", WHITE, selected_color=GREEN)
        sub_btn = Button(425, 200, 150, 50, "-", WHITE, selected_color=GREEN)
        mul_btn = Button(225, 280, 150, 50, "x", WHITE, selected_color=GREEN)
        div_btn = Button(425, 280, 150, 50, "÷", WHITE, selected_color=GREEN)
        start_btn = Button(320, 360, 150, 50, "Start", CYAN if selected_operation is not None else GRAY)

        add_btn.is_selected = (selected_operation == ADDITION)
        sub_btn.is_selected = (selected_operation == SUBTRACTION)
        mul_btn.is_selected = (selected_operation == MULTIPLICATION)
        div_btn.is_selected = (selected_operation == DIVISION)

        add_btn.check_hover(mouse_pos)
        sub_btn.check_hover(mouse_pos)
        mul_btn.check_hover(mouse_pos)
        div_btn.check_hover(mouse_pos)
        start_btn.check_hover(mouse_pos)

        add_btn.draw(screen)
        sub_btn.draw(screen)
        mul_btn.draw(screen)
        div_btn.draw(screen)
        start_btn.draw(screen)

        if mouse_click:
            if add_btn.is_clicked(mouse_pos, mouse_click):
                selected_operation = ADDITION
            elif sub_btn.is_clicked(mouse_pos, mouse_click):
                selected_operation = SUBTRACTION
            elif mul_btn.is_clicked(mouse_pos, mouse_click):
                selected_operation = MULTIPLICATION
            elif div_btn.is_clicked(mouse_pos, mouse_click):
                selected_operation = DIVISION
            elif start_btn.is_clicked(mouse_pos, mouse_click) and selected_operation is not None:
                current_state = GAME
                score = 0
                question_index = 0
                current_question = generate_question(selected_operation)
                question_timer = 30
                last_timer_update = pygame.time.get_ticks()

    elif current_state == GAME:
        # Update timer
        current_time = pygame.time.get_ticks()
        if current_time - last_timer_update >= 1000:  # 1 second
            question_timer -= 1
            last_timer_update = current_time
            if question_timer <= 0:
                # Time's up, skip question without scoring
                show_feedback = False
                question_index += 1
                if question_index >= total_questions:
                    current_state = END
                else:
                    current_question = generate_question(selected_operation)
                    question_timer = 30
                    last_timer_update = current_time

        # Draw header bar with top margin
        header_margin = 10
        header_left_margin = 20
        header_height = 80
        pygame.draw.rect(screen, WHITE, (header_left_margin, header_margin, SCREEN_WIDTH - 2*header_left_margin, header_height), border_radius=15)
        pygame.draw.rect(screen, BLACK, (header_left_margin, header_margin, SCREEN_WIDTH - 2*header_left_margin, header_height), 2, border_radius=15)

        # Draw operation label
        operation_names = ["Addition", "Subtraction", "Multiplication", "Division"]
        operation_text = font_small.render(f"{operation_names[selected_operation]}", True, BLACK)
        operation_rect = operation_text.get_rect(center=(SCREEN_WIDTH//2, header_margin + header_height//2 - 10))
        screen.blit(operation_text, operation_rect)

        # Draw score on new line
        score_text = font_small.render(f"Score: {score}/{question_index}", True, BLACK)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH//4, header_margin + header_height//2 + 20))
        screen.blit(score_text, score_rect)

        # Draw progress on new line
        progress_text = font_small.render(f"Question {question_index + 1}/{total_questions}", True, BLACK)
        progress_rect = progress_text.get_rect(center=(3*SCREEN_WIDTH//4, header_margin + header_height//2 + 20))
        screen.blit(progress_text, progress_rect)

        # Draw timer on new line
        timer_text = font_small.render(f"Time: {question_timer}", True, BLACK)
        timer_rect = timer_text.get_rect(center=(SCREEN_WIDTH//2, header_margin + header_height//2 + 20))
        screen.blit(timer_text, timer_rect)

        # Draw question card with margin
        card_margin = 20
        pygame.draw.rect(screen, WHITE, (card_margin, header_height + card_margin, SCREEN_WIDTH - 2*card_margin, 100), border_radius=20)
        pygame.draw.rect(screen, BLACK, (card_margin, header_height + card_margin, SCREEN_WIDTH - 2*card_margin, 100), 3, border_radius=20)

        question_text = font_large.render(current_question[0], True, BLACK)
        question_rect = question_text.get_rect(center=(SCREEN_WIDTH//2, header_height + card_margin + 50))
        screen.blit(question_text, question_rect)

        # Answer buttons with card layout
        answers = current_question[1]
        correct_index = current_question[2]

        btn_colors = [CYAN, CYAN, CYAN, CYAN]
        if show_feedback:
            if selected_answer == correct_index:
                btn_colors[selected_answer] = GREEN
            else:
                btn_colors[selected_answer] = RED
                btn_colors[correct_index] = GREEN

        # Draw answer cards
        card_width = 300
        card_height = 80
        card_margin = 20
        answer_start_y = header_height + card_margin + 100 + card_margin  # 80 + 20 + 100 + 20 = 220

        # A button card
        pygame.draw.rect(screen, WHITE, (75, answer_start_y, card_width, card_height), border_radius=15)
        pygame.draw.rect(screen, BLACK, (75, answer_start_y, card_width, card_height), 2, border_radius=15)
        a_btn = Button(85, answer_start_y + 10, card_width - 20, card_height - 20, f"A: {answers[0]}", btn_colors[0])

        # B button card
        pygame.draw.rect(screen, WHITE, (425, answer_start_y, card_width, card_height), border_radius=15)
        pygame.draw.rect(screen, BLACK, (425, answer_start_y, card_width, card_height), 2, border_radius=15)
        b_btn = Button(435, answer_start_y + 10, card_width - 20, card_height - 20, f"B: {answers[1]}", btn_colors[1])

        # C button card
        pygame.draw.rect(screen, WHITE, (75, answer_start_y + card_height + card_margin, card_width, card_height), border_radius=15)
        pygame.draw.rect(screen, BLACK, (75, answer_start_y + card_height + card_margin, card_width, card_height), 2, border_radius=15)
        c_btn = Button(85, answer_start_y + card_height + card_margin + 10, card_width - 20, card_height - 20, f"C: {answers[2]}", btn_colors[2])

        # D button card
        pygame.draw.rect(screen, WHITE, (425, answer_start_y + card_height + card_margin, card_width, card_height), border_radius=15)
        pygame.draw.rect(screen, BLACK, (425, answer_start_y + card_height + card_margin, card_width, card_height), 2, border_radius=15)
        d_btn = Button(435, answer_start_y + card_height + card_margin + 10, card_width - 20, card_height - 20, f"D: {answers[3]}", btn_colors[3])

        a_btn.check_hover(mouse_pos)
        b_btn.check_hover(mouse_pos)
        c_btn.check_hover(mouse_pos)
        d_btn.check_hover(mouse_pos)

        a_btn.draw(screen)
        b_btn.draw(screen)
        c_btn.draw(screen)
        d_btn.draw(screen)

        # Menu button
        menu_btn = Button(550, 420, 200, 50, "Main Menu", RED)
        menu_btn.check_hover(mouse_pos)
        menu_btn.draw(screen)

        # Menu confirmation dialog
        if show_menu_confirm:
            # Draw semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(128)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            # Draw dialog box
            dialog_width = 420
            dialog_height = 180
            dialog_x = (SCREEN_WIDTH - dialog_width) // 2
            dialog_y = ((SCREEN_HEIGHT - dialog_height) // 5)
            pygame.draw.rect(screen, WHITE, (dialog_x, dialog_y, dialog_width, dialog_height), border_radius=20)
            pygame.draw.rect(screen, BLACK, (dialog_x, dialog_y, dialog_width, dialog_height), 3, border_radius=20)

            # Dialog text
            confirm_text = font_medium.render("Go back to Main menu?", True, BLACK)
            confirm_rect = confirm_text.get_rect(center=(SCREEN_WIDTH//2, dialog_y + 50))
            screen.blit(confirm_text, confirm_rect)

            # Yes button
            yes_btn = Button(dialog_x + 50, dialog_y + 100, 150, 50, "Yes", CYAN)
            yes_btn.check_hover(mouse_pos)
            yes_btn.draw(screen)

            # No button
            no_btn = Button(dialog_x + dialog_width - 200, dialog_y + 100, 150, 50, "No", RED)
            no_btn.check_hover(mouse_pos)
            no_btn.draw(screen)

            # Handle dialog clicks
            if mouse_click:
                if yes_btn.is_clicked(mouse_pos, mouse_click):
                    current_state = MENU
                    selected_operation = None
                    score = 0
                    question_index = 0
                    current_question = None
                    selected_answer = None
                    show_feedback = False
                    question_timer = 30
                    show_menu_confirm = False
                elif no_btn.is_clicked(mouse_pos, mouse_click):
                    show_menu_confirm = False

        # Check for RFID input
        rfid_answer = get_rfid_answer()
        if not show_feedback and not show_menu_confirm and rfid_answer is not None:
            selected_answer = rfid_answer
            show_feedback = True
            feedback_timer = pygame.time.get_ticks()
            if selected_answer == correct_index:
                score += 1

        if not show_feedback and not show_menu_confirm and mouse_click:
            if a_btn.is_clicked(mouse_pos, mouse_click):
                selected_answer = 0
                show_feedback = True
                feedback_timer = pygame.time.get_ticks()
                if selected_answer == correct_index:
                    score += 1
            elif b_btn.is_clicked(mouse_pos, mouse_click):
                selected_answer = 1
                show_feedback = True
                feedback_timer = pygame.time.get_ticks()
                if selected_answer == correct_index:
                    score += 1
            elif c_btn.is_clicked(mouse_pos, mouse_click):
                selected_answer = 2
                show_feedback = True
                feedback_timer = pygame.time.get_ticks()
                if selected_answer == correct_index:
                    score += 1
            elif d_btn.is_clicked(mouse_pos, mouse_click):
                selected_answer = 3
                show_feedback = True
                feedback_timer = pygame.time.get_ticks()
                if selected_answer == correct_index:
                    score += 1
            elif menu_btn.is_clicked(mouse_pos, mouse_click):
                show_menu_confirm = True

        # Handle feedback timing
        if show_feedback and pygame.time.get_ticks() - feedback_timer > 2000:
            show_feedback = False
            question_index += 1
            if question_index >= total_questions:
                current_state = END
            else:
                current_question = generate_question(selected_operation)
                question_timer = 30
                last_timer_update = pygame.time.get_ticks()

    elif current_state == END:
        # Draw end screen
        end_text = font_large.render("Game Over!", True, BLACK)
        end_rect = end_text.get_rect(center=(SCREEN_WIDTH//2, 150))
        screen.blit(end_text, end_rect)

        final_score_text = font_medium.render(f"Final Score: {score}/{total_questions}", True, BLACK)
        final_score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH//2, 250))
        screen.blit(final_score_text, final_score_rect)

        restart_btn = Button(300, 350, 200, 60, "Play Again", GREEN)
        restart_btn.check_hover(mouse_pos)
        restart_btn.draw(screen)

        if mouse_click and restart_btn.is_clicked(mouse_pos, mouse_click):
            current_state = MENU
            selected_operation = None

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

