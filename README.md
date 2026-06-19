# RazziPT — Multi-Personality AI Chat Application

![RazziPT](static/logo.png)

**RazziPT** is a full-featured, production-ready FastAPI-based AI chat application with user authentication, saved chat history, multiple AI personalities, and a modern responsive UI. The project combines a robust Python backend, SQLite persistence, and a professional browser interface.

## 🎯 What is New in This Version

This version includes **major professional improvements and UI/UX enhancements**:

### 🎨 UI/UX Improvements
- **Professional logout message** - Transparent effect in both light and dark modes for consistent elegance
- **Fixed mobile chat input** - Chat input bar now properly visible on phone-sized screens when viewing saved conversations
- **Personality mode protection** - When attempting to switch personalities mid-chat, users see a professional system message with a direct "Start New Chat" button instead of a popup alert
- **Enhanced system messages** - Gradient-styled system notifications with action buttons for better user guidance
- **Improved mobile responsiveness** - Fixed viewport height calculations for proper layout on all device sizes

### 🤖 AI & Backend Features
- **Web search integration** via Tavily API for live information on current events
- **Removed keyword bans** - Allows educational questions about history, politics, medicine, and sensitive topics
- **Removed ASCII filter** - Full multilingual support (Chinese, Arabic, emoji, etc.)
- **Better error messages** - Detailed provider failover information instead of generic "I'm speechless"
- **Source citations** - Automatically appends sources from web search results
- **Personality-aware indicators** - Shows "Raza is thinking..." instead of "RazziPT is thinking..."

### 🔐 Core Features
- **User registration, login, logout, and password reset flows** with secure authentication
- **Authenticated pages** for chat, about, contact, and profile
- **Saved chat threads** with titles and full message history
- **Chat attachments** and file upload support
- **Multiple AI providers** (OpenAI, Gemini, DeepSeek, Together) with automatic fallback behavior
- **Demo mode** for local testing without API credentials
- **Three personality presets** for different conversation styles (Raza, Razo, Razi)
- **Dark/Light theme support** with persistent user preferences
- **Modern responsive UI** with professional gradient styling

## Current personality presets

The AI tone currently uses the following presets from the backend:

- **Raza** — balanced and helpful (mode: `normal`)
- **Razo** — witty and playful (mode: `razzi`)
- **Razi** — bold, opinionated, and dramatic (mode: `razzi_plus`)

---

## 📚 Code Documentation & Architecture

### Backend Architecture (Python)

#### **main.py** — FastAPI Application Server
The central controller of the entire application. Handles HTTP routing, request/response processing, and database integration.

**Key Endpoints**:
- `GET /` — Landing page
- `GET /chat` — Main chat interface (requires auth)
- `GET /signin`, `/signup` — Authentication pages
- `POST /register` — User registration
- `POST /login` — User login
- `POST /chat` — Send message to AI (core endpoint)
- `GET /get-chats` — List saved chats
- `POST /upload` — File upload handler
- `POST /delete-chat` — Delete chat thread

**Important Functions**:
- `startup_event()` - Initializes databases on server start
- `chat_endpoint()` - Main handler: receives message → calls AI engine → stores result → returns response
- `create_new_chat()` - Creates new saved chat thread for logged-in users
- Authentication middleware protects pages by checking `auth_token` cookies

---

#### **ai_engine.py** — AI Provider Management
Manages communication with multiple AI providers and integrates web search capability.

**Supported Providers** (with automatic fallback):
1. OpenAI (GPT-4, GPT-3.5)
2. Google Gemini
3. DeepSeek
4. Together AI

**Key Features**:
- **Provider Fallback**: If OpenAI is unavailable/over quota, automatically tries next provider
- **Web Search Integration**: Uses Tavily API to search the internet for current information
- **Personality Injection**: Embeds selected personality (Raza/Razo/Razi) into system prompt
- **Source Citations**: Returns web search sources with responses
- **Error Reporting**: Shows which provider failed and why (transparent to user)

**Main Function**:
```python
ask_ai(message, mode='normal', search_enabled=True)
# Returns: {"response": "...", "sources": [...]}
```

**Web Search Keywords** (triggers automatic search):
- today, latest, current, news, recent, this year, 2026
- who won, stock price, weather, election, score, schedule
- live, breaking, trending, breaking news

---

#### **memory.py** — SQLite Data Persistence
Manages all database operations for chat storage and history.

**Two SQLite Databases**:
- `database.db` - Chat threads and message history
- `razzipt.db` - User authentication data (separate)

**Tables**:
- `conversations` - Temporary session messages (not saved long-term)
- `chats` - User-owned saved chat threads
- `messages` - Full message content for saved chats

**Key Functions**:
- `init_db()` - Creates tables on startup
- `create_chat(user_id, title)` - Creates new saved chat
- `add_message(session_id, role, content)` - Stores temporary message
- `get_chats(user_id)` - Lists user's saved chats
- `delete_chat(chat_id)` - Deletes a chat thread

---

#### **auth.py** — Authentication & User Accounts
Handles user registration, login, and password management.

**Security**:
- Passwords stored as SHA256 hash (salted)
- Session tokens generated on login (random UUID)
- Sessions tracked with expiration times

**Key Functions**:
- `register_user()` - Creates new account
- `login_user()` - Validates credentials, returns session token
- `reset_password()` - Resets password with personal info verification
- `get_user_by_id()` - Retrieves user profile

---

#### **personalities.py** — AI Personality Configuration
Simple mapping of personality modes to system prompts.

```python
PERSONALITIES = {
    'normal': "You are Raza, a balanced and helpful AI assistant...",
    'razzi': "You are Razo, witty and playful...",
    'razzi_plus': "You are Razi, bold and opinionated..."
}
```

These prompts are injected into the AI request to shape response tone.

---

### Frontend Architecture (HTML/CSS/JavaScript)

#### **static/chat.html** — Main Chat Interface
The core user-facing application for AI conversations.

**JavaScript Key Features**:

1. **Session Management**
   - `getSessionId()` - Unique ID for anonymous users
   - `currentChatId` - Tracks which chat user is viewing
   - `currentChatMode` - Locks personality mode for consistency

2. **Personality Mode Locking** (NEW!)
   ```javascript
   // User selects personality → locked for that chat
   // Trying to switch mid-chat shows system message
   // "You are chatting with Raza. Start New Chat to try a different personality."
   ```

3. **Message Flow**
   - `sendMessage()` - Main function: user input → backend → response → display
   - `addMessageToChat(name, content, type)` - Renders message in UI
   - `addMessageToChat()` also supports system messages with action buttons

4. **Chat Management**
   - `createNewChat()` - New conversation thread
   - `loadConversation(chatId)` - Load saved chat
   - `deleteChat(chatId)` - Remove chat

5. **Theme Support**
   - Dark/light mode toggle
   - Preference saved to localStorage
   - CSS variables adjust colors dynamically

**CSS Improvements** (This Version):
- **System messages**: Gradient background with action buttons
- **Logout message**: Transparent effect (light mode now matches dark mode)
- **Mobile layout**: Fixed viewport calculations for proper input bar visibility

---

#### Other HTML Pages
- `landing.html` - Welcome page
- `signin.html`, `signup.html` - Authentication
- `profile.html` - User account management
- `about-us.html`, `contact-us.html` - Info pages

---

#### **static/theme.js** — Theme Manager
Handles dark/light mode toggling and persistence.

---

#### **static/styles.css** — Global Styles
Shared CSS for typography, spacing, and base components.

---

### Configuration Files

#### **.env** Example
```env
# Provider selection
AI_PROVIDER=auto                    # auto, openai, gemini, deepseek, or together
DEMO_MODE=false                     # Use mock responses for testing

# API keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=
DEEPSEEK_API_KEY=sk-...
TOGETHER_API_KEY=

# Web search
TAVILY_API_KEY=tvly-dev-...
```

---

## How the System Works: Message Flow

1. **User types message** in chat interface
   ```javascript
   // chat.html - sendMessage() function
   "Hello, what's the latest news?"
   ```

2. **Frontend sends POST request**
   ```json
   POST /chat
   {
     "session_id": "user_abc123",
     "message": "Hello, what's the latest news?",
     "mode": "normal",
     "chat_id": 42
   }
   ```

3. **Backend processes request**
   ```python
   # main.py - chat_endpoint()
   - Validates user authentication
   - Checks chat ownership
   - Verifies personality mode
   - Calls AI engine
   ```

4. **AI Engine handles response**
   ```python
   # ai_engine.py - ask_ai()
   - Detects keywords (e.g., "latest news" → triggers web search)
   - Builds prompt with Raza personality
   - Tries OpenAI first, falls back to Gemini if needed
   - Tavily searches web for "latest news"
   - Returns response with sources
   ```

5. **Backend stores message**
   ```python
   # memory.py
   - Saves user message to chat_42
   - Saves AI response
   - Updates chat title if new
   ```

6. **Response sent to frontend**
   ```json
   {
     "response": "The latest news includes...",
     "sources": [
       { "title": "...", "url": "..." }
     ]
   }
   ```

7. **Frontend displays response**
   ```javascript
   // chat.html - addMessageToChat()
   - Shows message with "Raza" label
   - Renders sources at bottom
   - Scrolls to new message
   ```

---

## Personality Locking Mechanism

**Purpose**: Ensure consistent AI personality throughout a conversation

**How it works**:

| Step | State | Action |
|------|-------|--------|
| 1 | No chat open | User selects "Raza" → `selectedMode = 'normal'` |
| 2 | New chat created | First message sent → `currentChatMode = 'normal'` |
| 3 | Mid-chat | User tries clicking "Razo" → `selectMode('razzi')` called |
| 4 | Mode conflict | `currentChatMode ('normal') !== selectedMode ('razzi')` |
| 5 | Protection triggered | System message shows: "You are chatting with Raza..." |
| 6 | User options | Can click "✨ Start New Chat" button to switch |
| 7 | New chat | Fresh chat with Razo, new locked mode |

---

## Project File Structure

```
razzipt/
├── main.py                          # FastAPI server & routing
├── ai_engine.py                     # AI provider management & web search
├── auth.py                          # User authentication & account management
├── memory.py                        # SQLite data persistence layer
├── personalities.py                 # AI personality presets (Raza, Razo, Razi)
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (create this file)
├── START_SERVER.bat                 # Windows server launcher
├── razzipt.db                       # User authentication database (auto-created)
├── database.db                      # Chat history database (auto-created)
└── static/                          # Frontend assets
    ├── landing.html                 # Welcome page
    ├── signin.html                  # Login page
    ├── signup.html                  # Registration page
    ├── forgot-password.html         # Password reset page
    ├── chat.html                    # Main chat interface
    ├── profile.html                 # User profile page
    ├── about-us.html                # About page
    ├── contact-us.html              # Contact page
    ├── index.html                   # Home page
    ├── app.js                       # Legacy chat interface (alternative)
    ├── theme.js                     # Dark/light mode toggle
    ├── styles.css                   # Global styles
    ├── logo.png                     # Application logo
    └── uploads/                     # User-uploaded files (auto-created)
```

## Requirements

Make sure you have Python 3.8+ installed.

Install the project dependencies:

```bash
pip install -r requirements.txt
```

## Environment Setup

Create a `.env` file in the project root with your API keys:

```env
# AI Provider Selection
AI_PROVIDER=auto                    # Options: auto, openai, gemini, deepseek, together, local
DEMO_MODE=false                     # Set to true to use mock responses without API keys

# API Keys (leave blank to skip that provider in fallback chain)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
TOGETHER_API_KEY=...

# Web Search Integration
TAVILY_API_KEY=tvly-dev-...         # Get free key from https://tavily.com
```


### Configuration Notes

- **TAVILY_API_KEY** - Get a free key from https://tavily.com for live web search
- Leave AI provider keys blank if you want fallback to other available providers
- Set **AI_PROVIDER=auto** to try providers in order: OpenAI → Gemini → DeepSeek → Together
- Or choose a specific provider: openai, gemini, deepseek, together, or local
- Set **DEMO_MODE=true** to use lightweight demo responses without real API credentials
- **Never commit your .env file to version control**

### How Web Search Works

The AI automatically triggers web search when it detects keywords like:
- today, latest, current, news, this year, recent, 2026
- who won, stock price, weather, election, score, schedule
- live, breaking, trending, recent events

Example: Asking "Who won the 2026 World Cup?" will automatically search for current results and cite sources.

## Running the app

### Option 1: run directly

```bash
python main.py
```

Then open:

```text
http://127.0.0.1:8000
```

### Option 2: use the Windows launcher

Double-click START_SERVER.bat or run it from PowerShell:

```bat
START_SERVER.bat
```

## Summary

RazziPT v2 brings professional-grade AI assistant features while maintaining a fun, personality-driven approach. The key improvements focus on:

1. **Transparency** - Clear error messages instead of cryptic failures
2. **Accuracy** - Live web search for current information
3. **Inclusivity** - Removed keyword bans to enable educational questions
4. **Reliability** - Proper provider failover and UTF-8 multilingual support
5. **UX** - Personality-aware thinking indicators

### Major Improvements in This Release

| Problem | Solution | Result |
|---------|----------|--------|
| **Keyword bans blocked valid questions** | Removed BANNED_KEYWORDS; delegate to provider safety | Ask about history, medicine, politics without blocks |
| **ASCII filter corrupted responses** | Replaced with UTF-8 whitespace cleanup | Full multilingual support (Chinese, Arabic, emoji) |
| **Generic "I'm speechless" error** | Structured error reporting with provider details | Know exactly which provider failed and why |
| **Outdated AI knowledge cutoff** | Integrated Tavily web search | Real-time answers with source citations |
| **Generic "RazziPT" labels** | Personality-aware naming | "Raza is thinking..." vs "RazziPT is thinking..." |

### Files Modified

- **ai_engine.py** - Web search integration, error handling, removed filters
- **static/chat.html** - Personality-aware thinking indicator, message labels
- **static/app.js** - (legacy) Personality mapping for alternative UI
- **requirements.txt** - Added `tavily-python`
- **README.md** - This updated documentation

### Testing the New Features

```bash
# 1. Start the server
python main.py
# or
.\START_SERVER.bat

# 2. Test each feature
```

**Test 1: Educational Questions (Keyword Bans Removed)**
```
User: "Explain how Nazi Germany rose to power"
Expected: Educational historical explanation (not blocked)
```

**Test 2: Multilingual Support (ASCII Filter Removed)**
```
User: "你好，请用中文回答这个问题" (Chinese)
Expected: Proper Chinese response (not corrupted)
```

**Test 3: Web Search + Citations**
```
User: "Who won the 2026 World Cup?"
Expected: Live results with sources cited at bottom
```

**Test 4: Better Error Messages**
```
(Disable all API keys in .env)
User: "Hi, how are you?"
Expected: Detailed error showing which provider failed
```

**Test 5: Personality Names**
```
Select "Raza" mode
User: "Hi"
Expected: Shows "Raza is thinking..." (not "RazziPT is thinking...")
```

## Project structure

- **main.py** - FastAPI server, routes, authentication, chat API endpoint
- **ai_engine.py** - AI provider dispatch, web search, failover logic, response formatting
- **memory.py** - SQLite database for chat history and conversation storage
- **auth.py** - User authentication, registration, password reset, account management
- **personalities.py** - Personality presets (Raza, Razo, Razi) used by AI engine
- **static/** - Frontend: HTML, CSS, JavaScript, images, and uploaded files
  - **chat.html** - Main chat interface with personality-aware thinking indicator
  - **app.js** - Alternative chat implementation (legacy)
  - **theme.js** - Dark/light theme management
  - **styles.css** - UI styling for all pages
- **requirements.txt** - Python package dependencies
- **START_SERVER.bat** - Windows batch script to launch the server
- **.env** - Configuration file (create this, don't commit to git)

---

## 💡 Code Documentation Highlights

All major functions now include detailed comments and docstrings explaining:
- **What** the function does (its purpose)
- **Why** it matters (how it fits into the application)
- **How** it works internally (the algorithm or process)
- **Parameters** and return values
- **Example** usage where helpful

### Key Areas with Comprehensive Comments

**Backend (Python)**:
- `ai_engine.py`:
  - `should_search_web()` - Keyword detection logic for web search
  - `ask_ai()` - Main orchestration function with provider fallback
  - `call_openai()`, `call_gemini()`, etc. - Individual provider implementations
- `main.py`:
  - `chat_endpoint()` - Core message handling and routing
  - `create_new_chat()` - Chat creation workflow
  - Request/response models - Pydantic validation
- `memory.py`:
  - Database initialization and schema
  - Chat/message storage functions
- `auth.py`:
  - Registration, login, password reset flows

**Frontend (JavaScript)**:
- `chat.html`:
  - Session management and localStorage usage
  - `sendMessage()` - Complete message flow from input to display
  - `selectMode()` - Personality mode locking mechanism
  - `loadConversation()` - Loading saved chats
  - `addMessageToChat()` - Rendering messages with proper formatting

---

## 🚀 Running the Application

### Prerequisites
- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Setup Steps

```bash
# 1. Navigate to project directory
cd razzipt

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file with your API keys
# (See "Environment Setup" section above)

# 4. Run the server
python main.py
# or on Windows:
START_SERVER.bat

# 5. Open browser to http://localhost:8000
```

### Configuration Options

| Setting | Values | Purpose |
|---------|--------|---------|
| `AI_PROVIDER` | auto, openai, gemini, deepseek, together, local | Which AI to use |
| `DEMO_MODE` | true, false | Test without API keys |
| `TAVILY_API_KEY` | tvly-dev-... | Enable web search |

---

## 📊 User Experience Improvements (This Version)

| Feature | Before | After | Benefit |
|---------|--------|-------|---------|
| **Logout Message** | 100% red, opaque | Transparent gradient | Professional, consistent look |
| **Mobile Chat Input** | Hidden on phones | Always visible | Can chat on saved conversations |
| **Mode Switch Alert** | Browser popup | In-chat system message | Better UX flow, action button provided |
| **Error Messages** | "I'm speechless" | Detailed provider info | Users understand what went wrong |
| **Web Search** | Not available | Automatic keywords | Current information available |
| **Personality Names** | "RazziPT is thinking" | "Raza is thinking" | More personal and engaging |

---

## 🧪 Testing Checklist

- [ ] **Authentication**: Register, login, logout, password reset
- [ ] **Chat**: Send message, receive response, personality switching
- [ ] **Personality Locking**: Try to switch mid-chat (should show system message)
- [ ] **Web Search**: Ask about current events (should auto-search)
- [ ] **Dark Mode**: Toggle theme, verify persistence
- [ ] **Mobile**: Test on phone (640px width), input bar visible
- [ ] **Error Handling**: Disable API keys, observe error messages
- [ ] **Performance**: Send multiple messages, verify responsiveness

---

## 📝 Summary

**RazziPT** is a modern AI chat application combining:
- Multiple AI providers with fallback capability
- Live web search for current information
- Three distinct personalities for different interaction styles
- Secure user authentication and chat persistence
- Professional, responsive UI with dark/light themes
- Comprehensive code documentation for maintenance

Perfect for learning full-stack web development, AI integration, and database design!

---

## 📧 Support & Contribution

For issues or improvements, refer to the inline code comments and this documentation.

The application demonstrates best practices in:
- FastAPI backend development
- SQLite database design
- Frontend-backend communication
- API integration and error handling
- Authentication and sessions
- Responsive web design

Happy chatting! 🎉
