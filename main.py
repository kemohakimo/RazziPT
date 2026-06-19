import os
import re
import uuid
from pathlib import Path
from fastapi import FastAPI, Request, Response, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from ai_engine import ask_ai
from memory import (
    init_db,
    add_message,
    get_conversation,
    clear_conversation,
    create_chat,
    add_chat_message,
    get_chat_messages,
    get_chats,
    search_chats,
    rename_chat,
    delete_chat,
    clear_chat_messages,
)
from auth import (
    register_user, login_user, reset_password, get_user_by_id,
    init_auth_db
)

# Load environment variables from .env before the app starts.
# This lets the app read API keys and runtime settings such as AI provider mode.
load_dotenv()

# -----------------------------------------------------------------------------
# Main application entry point for RazziPT.
# This file is the central controller of the project:
#   - it starts the FastAPI server
#   - it serves the HTML pages
#   - it handles user authentication
#   - it stores and retrieves chat data
#   - it connects the front end to the AI engine
# -----------------------------------------------------------------------------

app = FastAPI(title="RazziPT")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve all front-end assets from the static folder, including HTML, CSS,
# JavaScript, and uploaded media files. This keeps the API and UI separated
# while still allowing them to work together in one application.
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------------------------------------------------------------
# Request/response models
# These Pydantic models validate the JSON payloads received from the browser.
# They define the structure of each API request and help prevent invalid input.
# -----------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str
    message: str
    mode: str
    clear: bool = False
    chat_id: Optional[int] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None

class RegisterRequest(BaseModel):
    name: str
    email: str
    country: str
    phone: str
    birthday: str
    password: str
    confirm_password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class VerifyResetRequest(BaseModel):
    email: str
    country: str
    phone: str
    birthday: str

class ResetPasswordRequest(BaseModel):
    email: str
    country: str
    phone: str
    birthday: str
    new_password: str
    confirm_password: str

# -----------------------------------------------------------------------------
# Runtime state
# The sessions dictionary acts like a small in-memory login tracker.
# When a user signs in, the server creates a random token and stores the
# user information in this dictionary. On later requests, the browser sends
# that token back in a cookie, so the server can identify the logged-in user.
#
# UPLOAD_DIR is the folder where uploaded images and files are saved for the
# web pages to display later.
# -----------------------------------------------------------------------------

sessions = {}
UPLOAD_DIR = Path("static/uploads")

@app.on_event("startup")
def startup_event():
    """Initialize databases and upload directory when the server starts."""
    init_db()
    init_auth_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Page routes
# These endpoints serve the static HTML pages used by the front end.
# They also protect authenticated pages by checking the auth cookie.
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def read_landing():
    """Landing page."""
    with open("static/landing.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/landing", response_class=HTMLResponse)
def read_landing_page():
    """Landing page - alternate route."""
    with open("static/landing.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/signup", response_class=HTMLResponse)
def read_signup():
    """Sign up page."""
    with open("static/signup.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/signin", response_class=HTMLResponse)
def read_signin():
    """Sign in page."""
    with open("static/signin.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/forgot-password", response_class=HTMLResponse)
def read_forgot():
    """Forgot password page."""
    with open("static/forgot-password.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/chat", response_class=HTMLResponse)
def read_chat(request: Request):
    """Chat page - requires authentication."""
    auth_token = request.cookies.get("auth_token")
    if not auth_token or auth_token not in sessions:
        return RedirectResponse(url="/signin", status_code=302)
    
    with open("static/chat.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/about-us", response_class=HTMLResponse)
def read_about_us(request: Request):
    """About Us page - requires authentication."""
    auth_token = request.cookies.get("auth_token")
    if not auth_token or auth_token not in sessions:
        return RedirectResponse(url="/signin", status_code=302)
    
    with open("static/about-us.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/contact-us", response_class=HTMLResponse)
def read_contact_us(request: Request):
    """Contact Us page - requires authentication."""
    auth_token = request.cookies.get("auth_token")
    if not auth_token or auth_token not in sessions:
        return RedirectResponse(url="/signin", status_code=302)
    
    with open("static/contact-us.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/profile", response_class=HTMLResponse)
def read_profile(request: Request):
    """Profile page - requires authentication."""
    auth_token = request.cookies.get("auth_token")
    if not auth_token or auth_token not in sessions:
        return RedirectResponse(url="/signin", status_code=302)

    session = sessions[auth_token]
    with open("static/profile.html", "r", encoding="utf-8") as file:
        html = file.read()

    user_name = session.get("user_name", "Your Account")
    email = session.get("email", "")
    initials = "".join(part[0].upper() for part in user_name.split()[:2]) or "U"

    html = html.replace("[[USER_NAME]]", user_name)
    html = html.replace("[[USER_EMAIL]]", email)
    html = html.replace("[[USER_INITIALS]]", initials)
    html = html.replace("[[USER_STATUS]]", "Active session")
    html = html.replace("[[USER_ACCOUNT]]", "Logged in as " + user_name)

    return HTMLResponse(content=html)

# -----------------------------------------------------------------------------
# Authentication and account-management APIs
# These endpoints handle registration, login, password reset, and session state.
# -----------------------------------------------------------------------------

@app.post("/api/register")
def register(req: RegisterRequest):
    """Register a new user."""
    
    if req.password != req.confirm_password:
        return {"success": False, "message": "Passwords do not match."}
    
    success, message, user_id = register_user(
        name=req.name,
        email=req.email,
        country_code=req.country,
        phone=req.phone,
        birthday=req.birthday,
        password=req.password
    )
    
    return {"success": success, "message": message}

@app.post("/api/login")
def login(req: LoginRequest, response: Response):
    """Login user."""
    
    success, message, user_id, user_name, phone = login_user(req.email, req.password)
    
    if success:
        # Create session token
        token = str(uuid.uuid4())
        sessions[token] = {"user_id": user_id, "user_name": user_name, "email": req.email, "phone": phone}
        
        # Set cookie
        response.set_cookie("auth_token", token, max_age=86400*7)  # 7 days
        
        return {
            "success": True,
            "message": message,
            "redirect": "/chat"
        }
    
    return {"success": False, "message": message}

@app.post("/api/verify-reset")
def verify_reset(req: VerifyResetRequest):
    """Verify user information for password reset."""
    
    if not all([req.email, req.country, req.phone, req.birthday]):
        return {"success": False, "message": "All fields are required."}
    
    # Debug: Log what was received
    print(f"DEBUG: Received verify-reset request - email={req.email}, country={req.country}, phone={req.phone}, birthday={req.birthday}")
    
    # Check if user exists with these credentials
    from auth import verify_user_for_reset
    success, message = verify_user_for_reset(req.email, req.country, req.phone, req.birthday)
    
    print(f"DEBUG: Verification result - success={success}, message={message}")
    
    return {"success": success, "message": message}

@app.post("/api/reset-password")
def reset_pwd(req: ResetPasswordRequest):
    """Reset password."""
    
    if req.new_password != req.confirm_password:
        return {"success": False, "message": "Passwords do not match."}
    
    success, message = reset_password(
        email=req.email,
        country_code=req.country,
        phone=req.phone,
        birthday=req.birthday,
        new_password=req.new_password
    )
    
    return {"success": success, "message": message}

def get_profile_picture_url(user_id: int):
    """Locate the user's uploaded profile image, if one exists."""
    for ext in ["png", "jpg", "jpeg", "gif", "webp"]:
        file_path = UPLOAD_DIR / f"user_{user_id}.{ext}"
        if file_path.exists():
            return f"/static/uploads/{file_path.name}"
    return None

@app.get("/api/user")
def get_user(request: Request):
    """Get current user info."""
    auth_token = request.cookies.get("auth_token")
    
    if not auth_token or auth_token not in sessions:
        return {"authenticated": False}
    
    session = sessions[auth_token]
    return {
        "authenticated": True,
        "user_id": session["user_id"],
        "user_name": session["user_name"],
        "email": session["email"],
        "phone": session.get("phone", ""),
        "profile_picture": get_profile_picture_url(session["user_id"])
    }

@app.post("/api/logout")
def logout(request: Request, response: Response):
    """Logout user."""
    auth_token = request.cookies.get("auth_token")
    
    if auth_token and auth_token in sessions:
        del sessions[auth_token]
    
    response.delete_cookie("auth_token")
    return {"success": True, "message": "Logged out successfully."}

# -----------------------------------------------------------------------------
# File upload handling
# This endpoint accepts uploaded profile pictures or chat attachments and saves
# them into the static upload folder for later access in the UI.
# -----------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload an image or document to chat."""
    auth_token = request.cookies.get("auth_token")
    if not auth_token or auth_token not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")



    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"}
    original_name = file.filename or "upload.bin"
    filename = Path(original_name)
    file_ext = filename.suffix.lower()

    if file_ext not in allowed_extensions:
        return JSONResponse(status_code=400, content={"success": False, "message": "Unsupported file type."})

    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    destination = UPLOAD_DIR / unique_name
    contents = await file.read()
    destination.write_bytes(contents)
    file_url = f"/static/uploads/{unique_name}"

    return {
        "success": True,
        "file_name": filename.name,
        "file_url": file_url,
        "file_type": file.content_type or "application/octet-stream"
    }

def get_current_user_id(request: Request) -> Optional[int]:
    auth_token = request.cookies.get("auth_token")
    if not auth_token or auth_token not in sessions:
        return None
    return sessions[auth_token].get("user_id")


def generate_chat_title(text: str) -> str:
    """Generate a concise, professional title for a chat thread.

    This helper keeps saved conversations organized. It first tries an
    OpenAI-based title suggestion when an API key is available, and if that
    fails it falls back to a lightweight keyword-based title generator that
    works in offline or demo mode.
    """

    # Internal helper: clean noisy text, remove punctuation, and keep only the
    # most meaningful words for a concise chat title.
    def clean_title(value: str) -> str:
        raw = re.sub(r"[^A-Za-z0-9\s]", " ", value or "")
        raw = re.sub(r"\s+", " ", raw).strip()
        tokens = [token.lower() for token in raw.split() if len(token) > 2]

        stop_words = {
            "about", "after", "again", "against", "all", "also", "am", "an", "and", "any", "are",
            "as", "at", "be", "because", "been", "before", "being", "between", "both", "but", "by",
            "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
            "from", "further", "had", "has", "have", "having", "here", "how", "if", "in", "into",
            "is", "it", "its", "itself", "just", "like", "likely", "may", "me", "might", "more",
            "most", "my", "need", "needs", "no", "nor", "not", "of", "off", "on", "once", "only",
            "or", "other", "our", "ours", "out", "over", "own", "same", "she", "should", "so",
            "some", "such", "than", "that", "the", "their", "theirs", "them", "then", "there",
            "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very",
            "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
            "with", "would", "you", "your", "yours", "please", "tell", "show", "help", "learn",
            "understand", "explain", "explains", "use", "using", "work", "works", "working", "simple",
            "basics", "basic", "beginner", "beginners", "quick", "short", "topic", "concept", "terms",
            "need", "needs", "just", "really", "very", "good", "great", "nice", "best", "better", "well"
        }

        important_words = [word for word in tokens if word not in stop_words]
        important_words = list(dict.fromkeys(important_words))

        if not important_words:
            return "New Chat"

        base_words = important_words[:4]
        title = " ".join(word.capitalize() for word in base_words)

        is_question_style = any(word in {"how", "what", "why", "explain", "learn", "understand"} for word in tokens)
        if is_question_style and len(base_words) >= 2 and "explained" not in title.lower():
            title = f"{title} Explained"

        return title[:50].strip() or "New Chat"

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": "You generate short, professional chat titles. Use at most 5 words, no quotation marks, no punctuation, and summarize the main topic.",
                    },
                    {
                        "role": "user",
                        "content": f"Generate a short professional title for this chat message. Message: {text}",
                    },
                ],
                temperature=0.2,
                max_output_tokens=24,
            )
            ai_title = getattr(response, "output_text", None) or ""
            if ai_title:
                generated = clean_title(ai_title)
                if generated and generated != "New Chat":
                    return generated
        except Exception:
            pass

    return clean_title(text)


# -----------------------------------------------------------------------------
# Chat-thread management APIs
# These routes manage the user’s saved conversations.
# They help the app:
#   - create a new chat thread
#   - show the existing list of chats
#   - rename a chat title
#   - search old conversations
#   - delete a chat and its messages
# -----------------------------------------------------------------------------

@app.post("/api/chat/new")
def create_new_chat(request: Request):
    """Create a new chat thread for the current user."""
    user_id = get_current_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    chat_id = create_chat(user_id=user_id, title="New Chat")
    return {"chat_id": chat_id, "title": "New Chat"}


@app.get("/api/chats")
def list_chats(request: Request):
    """List all chats for the current authenticated user."""
    user_id = get_current_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    return get_chats(user_id)


@app.get("/api/search")
def search_chats_api(request: Request):
    """Search chat titles and message content for the current user."""
    user_id = get_current_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    query = request.query_params.get("q", "")
    return search_chats(user_id, query)


@app.get("/api/chat/{chat_id}")
def get_chat_messages_api(request: Request, chat_id: int):
    """Return stored messages for a specific chat."""
    user_id = get_current_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    if not any(item["id"] == chat_id for item in get_chats(user_id)):
        return JSONResponse(status_code=404, content={"error": "Chat not found"})

    return get_chat_messages(chat_id)


@app.put("/api/chat/rename")
def rename_chat_api(request: Request, chat_id: int, title: str):
    """Rename a chat thread."""
    user_id = get_current_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    if not any(item["id"] == chat_id for item in get_chats(user_id)):
        return JSONResponse(status_code=404, content={"error": "Chat not found"})

    rename_chat(chat_id, title)
    return {"success": True, "chat_id": chat_id, "title": title}


@app.delete("/api/chat/{chat_id}")
def delete_chat_api(request: Request, chat_id: int):
    """Delete a chat thread and its messages."""
    user_id = get_current_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    if not any(item["id"] == chat_id for item in get_chats(user_id)):
        return JSONResponse(status_code=404, content={"error": "Chat not found"})

    delete_chat(chat_id)
    return {"success": True, "chat_id": chat_id}


# -----------------------------------------------------------------------------
# Main chat processing endpoint
# This is the most important request handler in the project.
# It follows this flow:
#   1. Make sure the user is signed in
#   2. Read the message from the browser
#   3. Save the message into the correct memory table
#   4. Ask the AI engine for a reply
#   5. Save the AI reply and return both to the front end
# -----------------------------------------------------------------------------

@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    """Handle user chats and return AI responses for the active session.

    The request may belong to either a temporary browser session or a saved
    user chat thread. This function decides which storage path to use and
    then sends the message to the AI engine for a response.
    """
    auth_token = request.cookies.get("auth_token")
    if not auth_token or auth_token not in sessions:
        return {"error": "Not authenticated"}

    user_id = sessions[auth_token].get("user_id")
    user_message = (req.message or "").strip()

    if req.attachment_name and req.attachment_url:
        attachment_text = f"\n\nAttachment: {req.attachment_name} ({req.attachment_type or 'file'})\n{req.attachment_url}"
        user_message = f"{user_message}{attachment_text}" if user_message else attachment_text

    if req.chat_id is not None:
        # This branch handles long-lived, saved chat threads for authenticated
        # users. The message is stored in the persistent chat database and the
        # response is appended to the same thread for future reopening.
        chat_id = req.chat_id
        if user_id is None:
            return {"error": "Not authenticated"}

        if not any(item["id"] == chat_id for item in get_chats(user_id)):
            return JSONResponse(status_code=404, content={"error": "Chat not found"})

        if req.clear:
            clear_chat_messages(chat_id)
            return {"response": "Chat cleared. Ready for a fresh conversation.", "history": [], "chat_id": chat_id}

        history = get_chat_messages(chat_id)
        if not user_message:
            return {"response": "Send a message or attach a file so RazziPT can respond.", "history": history, "chat_id": chat_id}

        current_title = None
        if user_id is not None:
            current_chats = get_chats(user_id)
            current_title = next((item["title"] for item in current_chats if item["id"] == chat_id), None)

        add_chat_message(chat_id, "user", user_message, req.mode)
        if current_title in (None, "", "New Chat"):
            rename_chat(chat_id, generate_chat_title(user_message))

        reply = ask_ai(req.session_id, user_message, req.mode, history)
        reply_text = reply[0] if isinstance(reply, tuple) else reply
        add_chat_message(chat_id, "assistant", reply_text, req.mode)
        return {
            "response": reply_text,
            "history": get_chat_messages(chat_id),
            "chat_id": chat_id,
        }

    if req.clear:
        # This branch clears temporary in-memory session history. It is mainly
        # used for quick browser-session chats and does not affect saved user
        # chat threads created through the persistent chat system.
        clear_conversation(req.session_id)
        return {"response": "Memory cleared. Ready for a fresh roast.", "history": []}

    history = get_conversation(req.session_id)

    if not user_message:
        return {"response": "Send a message or attach a file so RazziPT can respond.", "history": history}

    add_message(req.session_id, "user", user_message)
    reply = ask_ai(req.session_id, user_message, req.mode, history)
    reply_text = reply[0] if isinstance(reply, tuple) else reply
    add_message(req.session_id, "assistant", reply_text)
    return {
        "response": reply_text,
        "history": get_conversation(req.session_id)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print("RazziPT Server Starting...")
    print(f"Listening on 0.0.0.0:{port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
