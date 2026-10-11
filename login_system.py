import pygame
import sys
import subprocess
import sqlite3
import hashlib
import re
import time
import os

# Initialize pygame
pygame.init()

# Get screen dimensions
width, height = 1280, 720
screen = pygame.display.set_mode((width,height))
pygame.display.set_caption("Login Screen")

# Colors
white = (255, 255, 255)
black = (0, 0, 0)
grey = (128, 128, 128)
blue = (0, 0, 255)
green = (0, 200, 0)
red = (255, 0, 0)
light_grey = (200, 200, 200)
dark_grey = (100, 100, 100)
dropdown_grey = (50, 50, 50)



# Per-user saves (so coins or unlocked tracks are different for one account)

SAVE_DIR = "saves"

def default_save() -> dict:
    return {
        "coins": 0,
        "owned": ["Starter"],
        "upgrades": {},
        "track_progress": 1,
        "best_times": {},
    }

def _ensure_save_dir(): # checks whether the username exists
    os.makedirs(SAVE_DIR, exist_ok=True)

def save_path_for_user(username: str) -> str:
    safe = "".join(c for c in username if c.isalnum() or c in ("_", "-"))
    if not safe:
        safe = "player"
    _ensure_save_dir()
    return os.path.join(SAVE_DIR, f"save_{safe}.json")

def create_user_save_if_missing(username: str):
    path = save_path_for_user(username)
    if os.path.exists(path):
        return
    try:
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_save(), f, indent=2)
    except Exception:
        pass
# Security Questions
SECURITY_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "What was your childhood nickname?",
    "What is your favorite book?"
]

# Login attempt tracking
login_attempts = {}
lockout_time = 300  # 5 minutes in seconds

# Fonts
font_type = pygame.font.Font(None, 32)
title_font = pygame.font.Font(None, 48)
small_font = pygame.font.Font(None, 24)

# Input boxes dimensions
box_width = 300
box_height = 40
dropdown_width = 400
dropdown_item_height = 35

# Calculate center positions
center_x = width // 2
center_y = height // 2

# Load and scale background
# Try to load background, use black if the background file isn't found
try:
    background = pygame.image.load("images/background.jpg")
    background = pygame.transform.scale(background, (width, height))
except:
    background = pygame.Surface((width, height))
    background.fill(black)

# Database functions
def create_database(): # creating the database
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # First, check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = cursor.fetchone() is not None
    
    if table_exists:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns if needed
        if 'security_question' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN security_question TEXT NOT NULL DEFAULT ''")
        
        if 'security_answer_hash' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN security_answer_hash TEXT NOT NULL DEFAULT ''")
        
        #tables with the security questions columns 
        # we need to handle existing users
        print(f"Existing columns: {columns}")
    
    else:
        # Create new table with all columns
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                security_question TEXT NOT NULL,
                security_answer_hash TEXT NOT NULL
            )
        ''')
        print("Created new table with all columns")
    
    conn.commit()
    conn.close()

def hash_password(password): # hashes the password for higher security
    return hashlib.sha256(password.encode()).hexdigest()

def hash_security_answer(answer): # hashes the security answer for higher security
    return hashlib.sha256(answer.lower().strip().encode()).hexdigest()

def is_user_locked(username): # if 5 attempts were incorrect, then the user is locked for 5 minutes 
    """Check if user is locked out due to too many failed attempts"""
    if username in login_attempts:
        attempts, lock_time = login_attempts[username]
        if attempts >= 5:
            if time.time() - lock_time < lockout_time:
                remaining_time = lockout_time - (time.time() - lock_time)
                return True, remaining_time
            else:
                # Reset after lockout period
                del login_attempts[username]
                return False, 0
    return False, 0

def checking_details(username, password):
    # Check if the user is locked from logging into their account
    locked, remaining = is_user_locked(username)
    if locked:
        minutes = int(remaining // 60) # converted to an integer and it finds the remainder
        seconds = int(remaining % 60) # converted to an integer and it finds the remainder
        return False, f"Account locked. Try again in {minutes}:{seconds:02d}" # writes the message if the username or password is incorrect
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    password_hash = hash_password(password)
    
    try:
        cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", 
                      (username, password_hash))
        result = cursor.fetchone()
        conn.close()
        
        if result is not None: # checks whether the username and the password were found in the database
            # if there's a failed login previously, the attempt count is reset after a successful login
            if username in login_attempts:
                del login_attempts[username]
            return True, "Login successful"
        else:
            # Tracks failed attempts
            if username not in login_attempts:
                login_attempts[username] = [1, time.time()] # if the username is not found, the login attempt has failed
            else:
                login_attempts[username][0] += 1 # increments the number of failed attempts if the user already exists in the database
            
            attempts = login_attempts[username][0]
            remaining_attempts = 5 - attempts
            
            if remaining_attempts > 0:
                return False, f"Invalid username or password. {remaining_attempts} attempts remaining"
            else:
                return False, "Account locked for 5 minutes due to too many failed attempts"
    except sqlite3.Error as e: # it catches any database related errors 
        conn.close()
        print(f"Database error in checking_details: {e}") # Shows the actual error message in the database
        return False, "Database error. Please try again."

def save_data(username, password, security_question, security_answer): # saves the data onto the database
    if len(username) < 4 or len(password) < 6:
        return False, "Username (min 4) or password (min 6) too short"
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    password_hash = hash_password(password)
    security_answer_hash = hash_security_answer(security_answer)
    
    try:
        cursor.execute("INSERT INTO users (username, password_hash, security_question, security_answer_hash) VALUES (?, ?, ?, ?)", 
                      (username, password_hash, security_question, security_answer_hash)) # this allows python to communicate with the sqlite database
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except sqlite3.Error as e:
        print(f"Database error in save_data: {e}")
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

def update_password(username, new_password, security_answer): # update password if the user forgot their password
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    try:
        # First verify security answer
        cursor.execute("SELECT security_answer_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, "Username not found"
        
        stored_hash = result[0]
        input_hash = hash_security_answer(security_answer)
        
        if stored_hash != input_hash:
            conn.close()
            return False, "Incorrect security answer"
        
        # Update password
        password_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
        conn.commit()
        updated = cursor.rowcount > 0
        
        if updated:
            # Reset login attempts for this user
            if username in login_attempts:
                del login_attempts[username]
            return True, "Password reset successful!"
        else:
            return False, "Failed to update password"
            
    except sqlite3.Error as e:
        print(f"Database error in update_password: {e}")
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

# Initialize database
create_database()

def draw_button(surface, rect, color, text, text_color=white):
    pygame.draw.rect(surface, color, rect)
    text_surf = font_type.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)

def draw_dropdown(surface, rect, color, text, is_open=False): # this creates a box for the security questions, a type of list for the questions
    pygame.draw.rect(surface, color, rect, 2)
    pygame.draw.rect(surface, black, rect, 1)
    
    # Truncate text if too long
    display_text = text
    if len(text) > 35:
        display_text = text[:32] + "..."
    
    text_surf = small_font.render(display_text, True, white)
    text_rect = text_surf.get_rect(midleft=(rect.x + 10, rect.centery))
    surface.blit(text_surf, text_rect)
    
    # Draw dropdown arrow
    arrow_size = 5
    if is_open:
        # Up arrow
        points = [
            (rect.right - 15, rect.centery + arrow_size),
            (rect.right - 10, rect.centery - arrow_size),
            (rect.right - 5, rect.centery + arrow_size)
        ]
    else:
        # Down arrow
        points = [
            (rect.right - 15, rect.centery - arrow_size),
            (rect.right - 10, rect.centery + arrow_size),
            (rect.right - 5, rect.centery - arrow_size)
        ]
    pygame.draw.polygon(surface, white, points)

def check_password_strength(password):
    if len(password) < 6: # password less than 6 
        return "Too short", (255,0,0) # outputs too short with the colour red
    #make use of a point system to grade the strength of the password
    strengthChecker = 0
    if len(password) >= 8:
        strengthChecker += 1
    if re.search(r"[A-Z]", password): # checks at least one of the letters within the password is captial 
        strengthChecker += 1
    if re.search(r"[0-9]", password): # checks at least there is one number from 0 to 9
        strengthChecker += 1
    if re.search(r"[@$!%*?&#]", password): # checks if there are any special characters in the password
        strengthChecker += 1

    if strengthChecker <= 1:
        return "Weak", (255,100,100) # red colour
    elif strengthChecker == 2:
        return "Medium", (255,165,0) # orange colour
    elif strengthChecker > 2:
        return "Strong", (0,200,0) # green colour

def password_requirements(password):
    requirements = {
        "At least 8 characters": len(password) >= 8,
        "At least one uppercase letter": bool(re.search(r"[A-Z]", password)),
        "At least one number": bool(re.search(r"[0-9]", password)),
        "At least one special character (@$!%*?&#)": bool(re.search(r"[@$!%*?&#]", password))
    }
    return requirements

def register_screen():
    username = ""
    password = ""
    confirm_password = ""
    security_answer = ""
    active = None
    message = ""
    message_color = red
    selected_question = -1
    dropdown_open = False
    dropdown_hover = -1

    # drawing the input boxes
    reg_username_box = pygame.Rect(center_x - box_width//2, center_y - 180, box_width, box_height)
    security_question_box = pygame.Rect(center_x - box_width//2, center_y - 100, box_width, box_height)
    security_answer_box = pygame.Rect(center_x - box_width//2, center_y - 20, box_width, box_height)
    reg_password_box = pygame.Rect(center_x - box_width//2, center_y + 60, box_width, box_height)
    reg_confirm_box = pygame.Rect(center_x - box_width//2, center_y + 140, box_width, box_height)
    register_btn = pygame.Rect(center_x - box_width//2, center_y + 220, box_width, box_height)
    back_btn = pygame.Rect(center_x - box_width//2, center_y + 280, box_width, box_height)
    
    # Create dropdown rectangle, positioned to the right of the security question box
    dropdown_rect = pygame.Rect(
        security_question_box.right + 10, 
        security_question_box.y,
        dropdown_width,
        200  # Fixed height for dropdown
    )
    
    running = True
    scroll_offset = 0
    max_visible = 5  # Show 5 items at once
    
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                
                if active == "username":
                    if event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    else:
                        username += event.unicode
                elif active == "security_answer":
                    if event.key == pygame.K_BACKSPACE:
                        security_answer = security_answer[:-1]
                    else:
                        security_answer += event.unicode
                elif active == "password":
                    if event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    else:
                        password += event.unicode
                elif active == "confirm":
                    if event.key == pygame.K_BACKSPACE:
                        confirm_password = confirm_password[:-1]
                    else:
                        confirm_password += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN:
                active = None
                
                if reg_username_box.collidepoint(event.pos):
                    active = "username"
                    dropdown_open = False
                elif security_question_box.collidepoint(event.pos):
                    dropdown_open = not dropdown_open
                    if not dropdown_open:
                        active = None
                elif security_answer_box.collidepoint(event.pos):
                    active = "security_answer"
                    dropdown_open = False
                elif reg_password_box.collidepoint(event.pos):
                    active = "password"
                    dropdown_open = False
                elif reg_confirm_box.collidepoint(event.pos):
                    active = "confirm"
                    dropdown_open = False
                else:
                    # Check if click is outside dropdown
                    if dropdown_open and not dropdown_rect.collidepoint(event.pos):
                        dropdown_open = False
                
                # Check dropdown items
                if dropdown_open:
                    for i in range(max_visible):
                        item_index = i + scroll_offset
                        if item_index >= len(SECURITY_QUESTIONS):
                            break
                            
                        item_rect = pygame.Rect(
                            dropdown_rect.x,
                            dropdown_rect.y + i * dropdown_item_height,
                            dropdown_rect.width,
                            dropdown_item_height
                        )
                        
                        if item_rect.collidepoint(event.pos):
                            selected_question = item_index
                            dropdown_open = False
                            break
                
                if register_btn.collidepoint(event.pos):
                    if register_enabled:
                        if selected_question == -1:
                            message = "Please select a security question"
                            message_color = red
                        elif not security_answer:
                            message = "Please provide an answer to the security question"
                            message_color = red
                        else:
                            success, msg = save_data(username, password, SECURITY_QUESTIONS[selected_question], security_answer)
                            message = msg
                            message_color = green if success else red
                            if success:
                                create_user_save_if_missing(username)
                                pygame.time.delay(1000)
                                return
                    else:
                        # Provide specific feedback for the user
                        if not username:
                            message = "Please enter username (min 4 chars)"
                        elif len(username) < 4:
                            message = "Username must be at least 4 characters"
                        elif not password:
                            message = "Please enter password"
                        elif not confirm_password:
                            message = "Please confirm password"
                        elif not security_answer:
                            message = "Please provide security answer"
                        elif selected_question == -1:
                            message = "Please select security question"
                        elif not passwords_match:
                            message = "Passwords do not match"
                        elif not password_ok:
                            message = "Password too weak - use Medium or Strong password"
                        else:
                            message = "Please fill all required fields"
                        message_color = red

                if back_btn.collidepoint(event.pos):
                    return
            
            # Handle mouse wheel for dropdown scrolling
            if event.type == pygame.MOUSEWHEEL and dropdown_open:
                scroll_offset -= event.y
                scroll_offset = max(0, min(scroll_offset, len(SECURITY_QUESTIONS) - max_visible))
        
        # Update dropdown hover
        dropdown_hover = -1
        if dropdown_open:
            for i in range(max_visible):
                item_index = i + scroll_offset
                if item_index >= len(SECURITY_QUESTIONS):
                    break
                    
                item_rect = pygame.Rect(
                    dropdown_rect.x,
                    dropdown_rect.y + i * dropdown_item_height,
                    dropdown_rect.width,
                    dropdown_item_height
                )
                
                if item_rect.collidepoint(mouse_pos):
                    dropdown_hover = i
                    break

        # Check password strength and match
        strength_text, strength_color = check_password_strength(password) if password else ("", white)
        password_ok = strength_text in ["Medium", "Strong"]
        passwords_match = (password == confirm_password and password != "")
        username_ok = len(username) >= 4
        security_answer_ok = len(security_answer.strip()) > 0
        security_question_selected = selected_question != -1

        register_enabled = password_ok and passwords_match and username_ok and security_answer_ok and security_question_selected

        # Drawing background
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        # Titles foreach individual screen
        title = title_font.render("Create New Account", True, white)
        screen.blit(title, (center_x - title.get_width()//2, center_y - 250))

        # Input boxes
        pygame.draw.rect(screen, blue if active == "username" else grey, reg_username_box, 2)
        draw_dropdown(screen, security_question_box, blue if dropdown_open else grey, 
                     SECURITY_QUESTIONS[selected_question] if selected_question != -1 else "Select security question...", 
                     dropdown_open)
        pygame.draw.rect(screen, blue if active == "security_answer" else grey, security_answer_box, 2)
        pygame.draw.rect(screen, blue if active == "password" else grey, reg_password_box, 2)
        pygame.draw.rect(screen, blue if active == "confirm" else grey, reg_confirm_box, 2)

        # Draw dropdown items if open
        if dropdown_open:
            # Draw dropdown background
            pygame.draw.rect(screen, dropdown_grey, dropdown_rect)
            pygame.draw.rect(screen, black, dropdown_rect, 2)
            
            # Drawing the scrollable items
            for i in range(max_visible):
                item_index = i + scroll_offset
                if item_index >= len(SECURITY_QUESTIONS):
                    break
                    
                item_rect = pygame.Rect(
                    dropdown_rect.x,
                    dropdown_rect.y + i * dropdown_item_height,
                    dropdown_rect.width,
                    dropdown_item_height
                )
                
                color = light_grey if dropdown_hover == i else dark_grey
                pygame.draw.rect(screen, color, item_rect)
                pygame.draw.rect(screen, black, item_rect, 1)
                
                # Truncate question text
                question_text = f"{item_index + 1}. {SECURITY_QUESTIONS[item_index]}"
                if len(question_text) > 45:
                    question_text = question_text[:42] + "..."
                
                text_surf = small_font.render(question_text, True, white)
                text_rect = text_surf.get_rect(midleft=(item_rect.x + 10, item_rect.centery))
                screen.blit(text_surf, text_rect)
            
            # Draw scroll indicator if needed
            if len(SECURITY_QUESTIONS) > max_visible:
                scroll_track_height = dropdown_rect.height
                scroll_thumb_height = scroll_track_height * max_visible / len(SECURITY_QUESTIONS)
                scroll_thumb_y = dropdown_rect.y + (scroll_offset * scroll_track_height / len(SECURITY_QUESTIONS))
                scroll_bar_rect = pygame.Rect(dropdown_rect.right - 5, scroll_thumb_y, 5, scroll_thumb_height)
                pygame.draw.rect(screen, light_grey, scroll_bar_rect)

        # Buttons
        draw_button(screen, register_btn, green if register_enabled else grey, "Register")
        draw_button(screen, back_btn, red, "Back to Login")

        # Text inside boxes
        screen.blit(font_type.render(username, True, white), (reg_username_box.x + 10, reg_username_box.y + 5))
        screen.blit(font_type.render(security_answer, True, white), (security_answer_box.x + 10, security_answer_box.y + 5))
        screen.blit(font_type.render("*" * len(password), True, white), (reg_password_box.x + 10, reg_password_box.y + 5))
        screen.blit(font_type.render("*" * len(confirm_password), True, white), (reg_confirm_box.x + 10, reg_confirm_box.y + 5))

        # Labels
        screen.blit(font_type.render("Username (min 4 chars):", True, white), (reg_username_box.x, reg_username_box.y - 30))
        screen.blit(font_type.render("Security Question:", True, white), (security_question_box.x, security_question_box.y - 30))
        screen.blit(font_type.render("Security Answer:", True, white), (security_answer_box.x, security_answer_box.y - 30))
        screen.blit(font_type.render("Password:", True, white), (reg_password_box.x, reg_password_box.y - 30))
        screen.blit(font_type.render("Confirm Password:", True, white), (reg_confirm_box.x, reg_confirm_box.y - 30))

        # Confirm password match
        if confirm_password:
            match_symbol = "" if passwords_match else ""
            match_color = green if passwords_match else red
            match_surface = font_type.render(match_symbol, True, match_color)
            screen.blit(match_surface, (reg_confirm_box.right + 10, reg_confirm_box.y + 5))
            
        # Password requirements checklist
        if password:
            reqs = password_requirements(password)
            x_offset = reg_password_box.right + 20   
            y_offset = reg_password_box.y
            for req_text, passed in reqs.items():
                color = green if passed else red
                req_surface = font_type.render(f"{req_text}", True, color)
                screen.blit(req_surface, (x_offset, y_offset))
                y_offset += 30  

        # Password strength indicator
        if password:
            strength_surface = font_type.render(f"Password Strength: {strength_text}", True, strength_color)
            screen.blit(strength_surface, (reg_confirm_box.x, reg_confirm_box.y + 50))

        # Show error or success messages
        if message:
            msg_surface = font_type.render(message, True, message_color)
            screen.blit(msg_surface, (center_x - msg_surface.get_width()//2, center_y + 350))

        pygame.display.flip()

def forgot_password_screen():
    username = ""
    password = ""
    confirm_password = ""
    security_answer = ""
    active = None
    message = ""
    message_color = red
    user_question = ""

    # Creating the input boxes when later to be drawn
    user_box = pygame.Rect(center_x - box_width//2, center_y - 180, box_width, box_height)
    question_box = pygame.Rect(center_x - box_width//2, center_y - 100, box_width, box_height)
    answer_box = pygame.Rect(center_x - box_width//2, center_y - 20, box_width, box_height)
    pass_box = pygame.Rect(center_x - box_width//2, center_y + 60, box_width, box_height)
    confirm_box = pygame.Rect(center_x - box_width//2, center_y + 140, box_width, box_height)
    reset_btn = pygame.Rect(center_x - box_width//2, center_y + 220, box_width, box_height)
    back_btn = pygame.Rect(center_x - box_width//2, center_y + 280, box_width, box_height)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if active == "username":
                    if event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                        user_question = ""
                    else:
                        username += event.unicode
                elif active == "security_answer":
                    if event.key == pygame.K_BACKSPACE:
                        security_answer = security_answer[:-1]
                    else:
                        security_answer += event.unicode
                elif active == "password":
                    if event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    else:
                        password += event.unicode
                elif active == "confirm":
                    if event.key == pygame.K_BACKSPACE:
                        confirm_password = confirm_password[:-1]
                    else:
                        confirm_password += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN:
                active = None
                
                if user_box.collidepoint(event.pos):
                    active = "username"
                elif question_box.collidepoint(event.pos):
                    # When clicking question box, fetch question from database
                    if username:
                        conn = sqlite3.connect("users.db")
                        cursor = conn.cursor()
                        try:
                            cursor.execute("SELECT security_question FROM users WHERE username = ?", (username,))
                            result = cursor.fetchone()
                            
                            if result:
                                user_question = result[0]
                                message = ""  # Clear previous messages
                                message_color = green
                            else:
                                user_question = ""
                                message = "Username not found"
                                message_color = red
                        except sqlite3.Error as e:
                            print(f"Database error: {e}")
                            user_question = ""
                            message = f"Database error: {str(e)}"
                            message_color = red
                        finally:
                            conn.close()
                    else:
                        message = "Please enter username first"
                        message_color = red
                elif answer_box.collidepoint(event.pos):
                    active = "security_answer"
                elif pass_box.collidepoint(event.pos):
                    active = "password"
                elif confirm_box.collidepoint(event.pos):
                    active = "confirm"

                if reset_btn.collidepoint(event.pos):
                    if not username:
                        message = "Please enter username"
                        message_color = red
                    elif not user_question:
                        message = "Click on security question box to load your question"
                        message_color = red
                    elif not security_answer:
                        message = "Please answer security question"
                        message_color = red
                    elif password != confirm_password:
                        message = "Passwords do not match!"
                        message_color = red
                    else:
                        reqs = password_requirements(password)
                        if not all(reqs.values()):
                            message = "Password does not meet requirements!"
                            message_color = red
                        else:
                            success, msg = update_password(username, password, security_answer)
                            message = msg
                            message_color = green if success else red
                            if success:
                                pygame.time.delay(1000)
                                return

                if back_btn.collidepoint(event.pos):
                    return

        strength_text, strength_color = check_password_strength(password) if password else ("", white)
        reset_password_ok = strength_text in ["Medium", "Strong"]
        reset_password_match = (password == confirm_password and password != "")
        reset_username_ok = len(username) >= 4
        security_answer_ok = len(security_answer.strip()) > 0

        reset_enabled = reset_password_ok and reset_password_match and reset_username_ok and security_answer_ok and user_question
        
        # Draw background
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        # Title of each individual screen
        title = title_font.render("Reset Your Password", True, white)
        screen.blit(title, (center_x - title.get_width()//2, center_y - 250))

        # drawing the input boxes
        pygame.draw.rect(screen, blue if active == "username" else grey, user_box, 2)
        pygame.draw.rect(screen, blue, question_box, 2)
        pygame.draw.rect(screen, blue if active == "security_answer" else grey, answer_box, 2)
        pygame.draw.rect(screen, blue if active == "password" else grey, pass_box, 2)
        pygame.draw.rect(screen, blue if active == "confirm" else grey, confirm_box, 2)

        # drawing the buttons and the user will be able to reset the password if their password matches and username
        draw_button(screen, reset_btn, green if reset_enabled else grey, "Reset Password")
        draw_button(screen, back_btn, red, "Back to Login")

        # Text inside boxes
        screen.blit(font_type.render(username, True, white), (user_box.x + 10, user_box.y + 5))
        
        # Display security question
        display_question = user_question
        if len(user_question) > 35:
            display_question = user_question[:32] + "..."
        screen.blit(small_font.render(display_question, True, white), (question_box.x + 10, question_box.y + 5))
        
        screen.blit(font_type.render(security_answer, True, white), (answer_box.x + 10, answer_box.y + 5))
        screen.blit(font_type.render("*" * len(password), True, white), (pass_box.x + 10, pass_box.y + 5))
        screen.blit(font_type.render("*" * len(confirm_password), True, white), (confirm_box.x + 10, confirm_box.y + 5))

        # Labels
        screen.blit(font_type.render("Username:", True, white), (user_box.x, user_box.y - 30))
        screen.blit(font_type.render("Security Question (click to load):", True, white), (question_box.x, question_box.y - 30))
        screen.blit(font_type.render("Security Answer:", True, white), (answer_box.x, answer_box.y - 30))
        screen.blit(font_type.render("New Password:", True, white), (pass_box.x, pass_box.y - 30))
        screen.blit(font_type.render("Confirm Password:", True, white), (confirm_box.x, confirm_box.y - 30))

        # Password requirements checklist 
        if password:
            reqs = password_requirements(password)
            x_offset = pass_box.right + 20
            y_offset = pass_box.y
            for req_text, passed in reqs.items():
                color = green if passed else red
                req_surface = font_type.render(f"{req_text}", True, color)
                screen.blit(req_surface, (x_offset, y_offset))
                y_offset += 30

        # Password strength indicator
        if password:
            strength_text, strength_color = check_password_strength(password)
            strength_surface = font_type.render(f"Password Strength: {strength_text}", True, strength_color)
            screen.blit(strength_surface, (confirm_box.x, confirm_box.y + 50))

        # Message
        if message:
            msg_surface = font_type.render(message, True, message_color)
            screen.blit(msg_surface, (center_x - msg_surface.get_width()//2, center_y + 350))

        pygame.display.flip()

def login_screen():
    username = ""
    password = ""
    active = None
    message = ""
    
    # Create rectangles for the login screen
    login_username_box = pygame.Rect(center_x - box_width//2, center_y - 100, box_width, box_height)
    login_password_box = pygame.Rect(center_x - box_width//2, center_y - 20, box_width, box_height)
    login_btn = pygame.Rect(center_x - box_width//2, center_y + 60, box_width, box_height)
    register_btn = pygame.Rect(center_x - box_width//2, center_y + 120, box_width, box_height)
    forgot_password_btn = pygame.Rect(center_x - box_width//2, center_y + 180, box_width, box_height)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                if active == "username":
                    if event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    else:
                        username += event.unicode
                elif active == "password":
                    if event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    else:
                        password += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN:
                active = None
                if login_username_box.collidepoint(event.pos):
                    active = "username"
                elif login_password_box.collidepoint(event.pos):
                    active = "password"
                
                # Handle login button click
                if login_btn.collidepoint(event.pos):
                    if not username or not password:
                        message = "Please enter username and password"
                    else:
                        success, msg = checking_details(username, password)
                        if success:
                            create_user_save_if_missing(username)
                            return username  # takes the user to the main game

                        else:
                            message = msg
                
                # Handle forgot password button click
                if forgot_password_btn.collidepoint(event.pos):
                    forgot_password_screen()
                    message = ""  # clear old messages when returning
                
                # Handle register button click
                if register_btn.collidepoint(event.pos):
                    register_screen()
                    message = ""  # Clear message when returning from register screen

        # Drawing the background 
        screen.blit(background, (0, 0))
        
        # Add overlay
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        
        # Draw title
        title = title_font.render("Retro Drifters login", True, white)
        screen.blit(title, (center_x - title.get_width()//2, center_y - 200))
        
        # Draw input boxes
        pygame.draw.rect(screen, blue if active == "username" else grey, login_username_box, 2)
        pygame.draw.rect(screen, blue if active == "password" else grey, login_password_box, 2)
        
        # Draw buttons
        draw_button(screen, login_btn, green, "Login")
        draw_button(screen, register_btn, (100, 100, 255), "Register")
        draw_button(screen, forgot_password_btn, red, "Forgot password?")
        
        # Draw text in boxes
        screen.blit(font_type.render(username, True, white), (login_username_box.x + 10, login_username_box.y + 5))
        screen.blit(font_type.render("*" * len(password), True, white), (login_password_box.x + 10, login_password_box.y + 5))
        
        # Draw labels
        screen.blit(font_type.render("Username:", True, white), (login_username_box.x, login_username_box.y - 30))
        screen.blit(font_type.render("Password:", True, white), (login_password_box.x, login_password_box.y - 30))
        
        # Draw message below the forgot password button
        if message:
            msg_surface = font_type.render(message, True, red)
            screen.blit(
                msg_surface, 
                (center_x - msg_surface.get_width()//2, forgot_password_btn.y + forgot_password_btn.height + 20)
            )

        pygame.display.flip()


def run_login():
    # returns username string on success, or None if user quits
    return login_screen()


# Start with the login screen
# login_screen()
# pygame.quit()
# sys.exit()
if __name__ == "__main__":
    user = run_login()
    pygame.quit()
    sys.exit()
