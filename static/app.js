// -----------------------------------------------------------------------------
// Front-end chat page logic for RazziPT.
// This script manages theme behavior, session creation, message rendering,
// and the interaction between the browser and the FastAPI chat endpoint.
// -----------------------------------------------------------------------------

const chatPanel = document.getElementById("chatPanel");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const modeSelect = document.getElementById("modeSelect");
const messageInput = document.getElementById("messageInput");

const SESSION_KEY = "razzipt_session_id";

// Map modes to personality names
const PERSONALITY_NAMES = {
    "normal": "Raza",
    "razzi": "Razo",
    "razzi_plus": "Razi"
};

function getPersonalityName(mode) {
    return PERSONALITY_NAMES[mode] || "RazziPT";
}

// -----------------------------------------------------------------------------
// Session management
// A unique session ID is stored in localStorage to keep chat context stable
// during the browser session and to support the backend conversation memory.
// -----------------------------------------------------------------------------

function getSessionId() {
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
        sessionId = crypto.randomUUID();
        localStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
}

// -----------------------------------------------------------------------------
// Message rendering helpers
// These functions normalize and display AI responses in a readable format.
// -----------------------------------------------------------------------------

function normalizeResponseText(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\r\n?/g, '\n')
        .trim();
}

function createMessageContentNode(text) {
    const container = document.createElement('div');
    container.classList.add('message-content');

    const normalized = normalizeResponseText(text);
    const lines = normalized.split('\n');
    let currentList = null;

    lines.forEach((rawLine) => {
        const line = rawLine.trim();
        if (!line) {
            currentList = null;
            return;
        }

        const headingMatch = line.match(/^#{1,3}\s*(.*)$/);
        if (headingMatch) {
            currentList = null;
            const heading = document.createElement('strong');
            heading.classList.add('message-heading');
            heading.textContent = headingMatch[1];
            container.appendChild(heading);
            return;
        }

        const bulletMatch = line.match(/^([-*+]\s+|•\s+)(.*)$/);
        if (bulletMatch) {
            if (!currentList) {
                currentList = document.createElement('ul');
                currentList.classList.add('message-bullet-list');
                container.appendChild(currentList);
            }
            const li = document.createElement('li');
            li.textContent = bulletMatch[2];
            currentList.appendChild(li);
            return;
        }

        currentList = null;
        const paragraph = document.createElement('p');
        paragraph.textContent = line;
        container.appendChild(paragraph);
    });

    return container;
}

function addMessage(role, content, mode = null) {
    """Render a chat bubble for either the user or the assistant."""
    const message = document.createElement("div");
    message.classList.add("message", role === "user" ? "user" : "assistant");
    
    let label;
    if (role === "user") {
        label = "YOU";
    } else {
        label = mode ? getPersonalityName(mode).toUpperCase() : "RAZZIPT";
    }

    const strong = document.createElement("strong");
    strong.textContent = label;

    const contentNode = createMessageContentNode(content);

    message.appendChild(strong);
    message.appendChild(contentNode);
    chatPanel.appendChild(message);
    chatPanel.scrollTop = chatPanel.scrollHeight;
}

// -----------------------------------------------------------------------------
// Chat submission flow
// This asynchronous function sends the user input to the backend, receives the
// AI response, and displays the result in the chat panel.
// -----------------------------------------------------------------------------

async function sendMessage(clear = false) {
    const text = messageInput.value.trim();
    if (!text && !clear) {
        return;
    }

    if (!clear) {
        addMessage("user", text);
    }

    sendBtn.disabled = true;
    sendBtn.textContent = clear ? "Clearing..." : "Sending...";

    const mode = modeSelect ? modeSelect.value : "normal";
    const payload = {
        session_id: getSessionId(),
        message: text,
        mode: mode,
        clear,
    };

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });
        const data = await response.json();

        if (clear) {
            chatPanel.innerHTML = "";
            addMessage("assistant", data.response, mode);
        } else {
            addMessage("assistant", data.response, mode);
        }
    } catch (error) {
        addMessage("assistant", "Network error. Check the server and try again.", mode);
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send";
        messageInput.value = "";
    }
}

sendBtn.addEventListener("click", () => sendMessage());
clearBtn.addEventListener("click", () => sendMessage(true));
messageInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

addMessage("assistant", "Welcome to RazziPT. Choose a mode and say something savage.");
