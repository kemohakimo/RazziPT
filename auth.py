# -----------------------------------------------------------------------------
# Authentication and account-management module.
# This file handles user registration, password hashing, login validation,
# password reset, and basic profile lookup for the application.
# -----------------------------------------------------------------------------

import sqlite3
import hashlib
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "razzipt.db"

# The authentication layer uses a local SQLite database for user accounts.
# Passwords are never stored in plain text. Instead, the app converts the
# password into a SHA256 hash before saving it to the database.
#
# This is a simple educational approach for learning:
#   - how user information is stored
#   - how login checks are performed
#   - how a basic account system works in a real web app

def init_auth_db():
    """Create the authentication database and its required tables on startup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        country_code TEXT,
        phone TEXT NOT NULL,
        birthday TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Sessions table (for login sessions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Convert a plain-text password into a SHA256 hash for storage.

    Why this matters:
    - the database should not keep raw passwords
    - the hash can be compared later during login
    - even if the database is opened by someone else, the real password is
      still not visible in plain text
    """
    return hashlib.sha256(password.encode()).hexdigest()

def is_adult(birthday_str: str) -> bool:
    """Determine whether a supplied birthday indicates the user is 18 or older."""
    try:
        birth_date = datetime.strptime(birthday_str, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age >= 18
    except:
        return False

def register_user(name: str, email: str, country_code: str, phone: str, birthday: str, password: str) -> tuple:
    """Create a new account after validating the input.

    The registration flow is important because it checks the safety rules before
    saving any data:
      - the user must be at least 18 years old
      - all required information must be present
      - the password must be long enough
      - the email must be unique

    If all checks pass, the password is converted to a hash and saved.
    """
    
    # Validate age
    if not is_adult(birthday):
        return False, "You must be 18 years or older to register.", None
    
    # Validate inputs
    if not all([name, email, country_code, phone, birthday, password]):
        return False, "All fields are required.", None
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters.", None
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute("""
        INSERT INTO users (name, email, country_code, phone, birthday, password_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, country_code, phone, birthday, password_hash))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return True, "Registration successful!", user_id
    
    except sqlite3.IntegrityError:
        return False, "Email already registered.", None
    except Exception as e:
        return False, f"Error: {str(e)}", None

def login_user(email: str, password: str) -> tuple:
    """Validate email/password credentials and return the session details if valid.

    This is the authentication check used by the login page. The password is
    hashed again and compared with the stored value in the database.
    """
    
    if not email or not password:
        return False, "Email and password required.", None, None, None
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute("""
        SELECT id, name, phone FROM users WHERE email = ? AND password_hash = ?
        """, (email, password_hash))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_id, user_name, phone = result
            return True, "Login successful!", user_id, user_name, phone
        else:
            return False, "Invalid email or password.", None, None, None
    
    except Exception as e:
        return False, f"Error: {str(e)}", None, None, None

def verify_user_for_reset(email: str, country_code: str, phone: str, birthday: str) -> tuple:
    """Confirm a user identity before allowing a password reset request."""
    
    if not all([email, country_code, phone, birthday]):
        return False, "All fields are required."
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id FROM users WHERE email = ? AND country_code = ? AND phone = ? AND birthday = ?
        """, (email, country_code, phone, birthday))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return True, "User verified successfully."
        else:
            return False, "Email, country code, phone number, or birthday not found. Please check your information."
    
    except Exception as e:
        return False, f"Error: {str(e)}"

def reset_password(email: str, country_code: str, phone: str, birthday: str, new_password: str) -> tuple:
    """Update the stored password after verifying the identity details."""
    
    if not all([email, country_code, phone, birthday, new_password]):
        return False, "All fields are required."
    
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify email, country code, phone, AND birthday match
        cursor.execute("""
        SELECT id FROM users WHERE email = ? AND country_code = ? AND phone = ? AND birthday = ?
        """, (email, country_code, phone, birthday))
        
        result = cursor.fetchone()
        
        if not result:
            return False, "Email, country code, phone number, or birthday not found. Please check your information."
        
        user_id = result[0]
        password_hash = hash_password(new_password)
        
        cursor.execute("""
        UPDATE users SET password_hash = ? WHERE id = ?
        """, (password_hash, user_id))
        
        conn.commit()
        conn.close()
        
        return True, "Password reset successful!"
    
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_user_by_id(user_id: int) -> dict:
    """Get user information by ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, name, email, phone FROM users WHERE id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"id": result[0], "name": result[1], "email": result[2], "phone": result[3]}
        return None
    except:
        return None

def update_user_name(user_id: int, new_name: str) -> tuple:
    """Update the user's display name."""
    if not new_name or not new_name.strip():
        return False, "Name cannot be empty."
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users SET name = ? WHERE id = ?
        """, (new_name.strip(), user_id))
        conn.commit()
        conn.close()
        return True, "Name updated successfully."
    except Exception as e:
        return False, f"Error updating name: {str(e)}"

# Initialize database on import
init_auth_db()
