# -----------------------------------------------------------------------------
# AI engine for RazziPT.
# This module chooses an AI provider, builds prompts,
# and returns responses that the web app can show to the user.
# Features include web search integration for current information.
# Safety filtering is delegated to AI providers themselves.
# -----------------------------------------------------------------------

import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
AI_PROVIDER = os.getenv("AI_PROVIDER", "local").lower()
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Debug: Verify configuration is loaded
print(f"[AI Engine] AI_PROVIDER={AI_PROVIDER}, DEMO_MODE={DEMO_MODE}")
print(f"[AI Engine] TAVILY_API_KEY configured: {bool(TAVILY_API_KEY)}")

from personalities import PERSONALITIES, DEFAULT_PERSONALITY

# -----------------------------------------------------------------------------
# Safety and provider configuration
# This section controls how the AI behaves in the app.
# It defines:
#   - which words are blocked for safety
#   - which AI libraries are available on this machine
#   - how prompts are built for different providers
#
# Understanding this section is useful for learning how the app switches
# between real AI services and the demo fallback mode.
# -----------------------------------------------------------------------------

# REMOVED: Keyword filtering is now handled by AI providers
# This allows educational, historical, and medical questions to be answered appropriately
# while still blocking genuinely harmful content through provider-level safety measures

# Try to import various AI libraries
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from together import Together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


# -----------------------------------------------------------------------
# Web Search Integration
# 
# This section enables RazziPT to provide current information by searching
# the web using Tavily API. Web search is triggered automatically when
# the user asks about current events, latest news, or recent information.
# -----------------------------------------------------------------------

SEARCH_KEYWORDS = {
    "today", "latest", "current", "news", "this year", "recent", "2026", 
    "who won", "stock price", "weather", "election", "score", "schedule", 
    "update", "live", "breaking", "trending", "this month", "recently",
    "latest news", "current events"
}

def should_search_web(user_message: str) -> bool:
    """
    Determine if a query needs current web information.
    
    This function checks if the user's message contains keywords that suggest
    they're asking about current events or recent information. If so, we'll
    perform a web search to get the latest data before asking the AI provider.
    
    Args:
        user_message: The user's input message
        
    Returns:
        True if web search should be performed, False otherwise
    """
    lowered = user_message.lower()
    # Check if message contains any search keywords
    return any(keyword in lowered for keyword in SEARCH_KEYWORDS)


def search_web(query: str, max_results: int = 5) -> dict:
    """
    Search the web using Tavily API for current information.
    
    This function queries the Tavily API to get real-time web search results,
    which are then formatted and injected into the AI prompt to provide
    current, accurate information. Results include source citations.
    
    Args:
        query: The search query
        max_results: Maximum number of search results to return (default 5)
        
    Returns:
        A dictionary containing:
        - success: bool - Whether the search was successful
        - context: str - Formatted search results for AI context
        - sources: list - Source metadata with titles and URLs
        - error: str - Error message if search failed
        
    Example:
        >>> result = search_web("FIFA World Cup 2026 results")
        >>> if result['success']:
        >>>     print(result['context'])  # Use in AI prompt
        >>>     print(result['sources'])  # Show citations to user
    """
    if not TAVILY_AVAILABLE or not TAVILY_API_KEY:
        return {
            "success": False,
            "context": "",
            "sources": [],
            "error": "Tavily API not configured"
        }
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        
        # Perform the web search
        results = client.search(
            query=query,
            max_results=max_results,
            include_answer=True
        )
        
        # Format search results for AI context
        sources = []
        context_lines = []
        
        # Add the summary/answer if provided
        if results.get("answer"):
            context_lines.append(f"Summary: {results['answer']}")
        
        # Process each search result
        for result in results.get("results", []):
            sources.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("content", "")[:200]  # Limit to 200 chars
            })
            # Add to context with content limited to 300 chars
            context_lines.append(f"- {result.get('title', '')}: {result.get('content', '')[:300]}")
        
        # Join all context lines into a single string
        context = "\n".join(context_lines)
        
        return {
            "success": True,
            "context": context,
            "sources": sources,
            "error": None
        }
    except Exception as e:
        print(f"Web search error: {str(e)}")
        return {
            "success": False,
            "context": "",
            "sources": [],
            "error": f"Web search failed: {str(e)}"
        }


def build_context_prompt(user_message: str, history: list | None = None) -> str:
    """
    Attach earlier chat history to the current prompt for context-aware replies.
    
    This function prepends conversation context to the user's message, enabling
    the AI to understand what was discussed previously. This is particularly
    useful for multi-turn conversations where the user refers back to earlier
    points without repeating the entire context.
    
    Args:
        user_message: The current user input
        history: List of previous messages in format {"role": "user|assistant", "content": "..."}
        
    Returns:
        Either the original user_message (if no history), or a formatted string
        combining history and the current question
        
    Example:
        >>> history = [
        >>>     {"role": "user", "content": "What is machine learning?"},
        >>>     {"role": "assistant", "content": "Machine learning is..."}
        >>> ]
        >>> build_context_prompt("Give me an example", history)
        # Returns formatted string with conversation history + current question
    """
    if not history:
        return user_message

    context_lines = []
    for item in history:
        if not isinstance(item, dict):
            continue

        role = str(item.get("role", "user")).lower()
        content = str(item.get("content", "")).strip()
        if not content:
            continue

        label = "User" if role == "user" else "Assistant"
        context_lines.append(f"{label}: {content}")

    if not context_lines:
        return user_message

    return (
        "Use the conversation history below to answer the current question.\n"
        "Conversation history:\n"
        + "\n".join(context_lines)
        + "\n\nCurrent question: "
        + user_message
    )


def build_message_history(history: list | None = None, current_user_message: str = "") -> list:
    """
    Convert stored chat history into the format expected by AI providers.
    
    This function transforms raw history data into the standardized format
    required by OpenAI, Gemini, DeepSeek, and other API-based providers.
    It filters out malformed entries and ensures all messages have proper roles.
    
    Args:
        history: List of messages from database (may have extra fields)
        current_user_message: The new user message to append
        
    Returns:
        A list of properly formatted message dicts: [{"role": "user|assistant|system", "content": "..."}]
        
    Note:
        - Skips invalid entries (non-dict, missing fields)
        - Filters to valid roles only: user, assistant, system
        - Current user message is always appended at the end
        - Empty messages are filtered out
    """
    messages = []

    for item in history or []:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant", "system"} and content:
            messages.append({"role": role, "content": content})

    if current_user_message.strip():
        messages.append({"role": "user", "content": current_user_message.strip()})

    return messages


def ask_together(user_message: str, mode: str, history: list | None = None) -> str:
    """
    Query Together AI (Meta Llama model) for a response.
    
    Together AI is a cost-effective provider offering open-source LLM inference.
    This function uses the Llama 3.1 8B Instruct model.
    
    Args:
        user_message: The user's input message
        mode: Personality mode (determines system prompt)
        history: Previous messages for context
        
    Returns:
        The AI response string, or empty string if failed
        
    Note:
        - Response text is cleaned (excessive whitespace removed)
        - UTF-8 content is preserved (no ASCII filtering)
        - Errors are logged but not raised (graceful fallback)
    """
    if not TOGETHER_AVAILABLE or not TOGETHER_API_KEY:
        return ""

    try:
        client = Together(api_key=TOGETHER_API_KEY)
        personality = PERSONALITIES.get(mode, PERSONALITIES[DEFAULT_PERSONALITY])
        messages = [{"role": "system", "content": personality}]
        messages.extend(build_message_history(history, user_message))

        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            messages=messages,
            max_tokens=2000,
            temperature=0.2,
            top_p=0.8,
        )
        
        if response.choices and response.choices[0].message:
            response_text = response.choices[0].message.content.strip()
            
            # Clean up excessive whitespace only, preserve all valid UTF-8 content
            response_text = ' '.join(response_text.split())
            
            # If response is empty, return failure
            if not response_text:
                return ""
            
            return response_text
        return ""
    except Exception as e:
        import traceback
        print(f"TOGETHER ERROR: {str(e)}")
        print(traceback.format_exc())
        return ""


def ask_gemini(user_message: str, mode: str, history: list | None = None) -> str:
    """
    Query Google Gemini API for a response.
    
    Gemini is our secondary provider (good for long contexts). Uses the
    REST API endpoint with the text-bison-001 model.
    
    Args:
        user_message: The user's input message
        mode: Personality mode (determines system prompt)
        history: Previous messages for context
        
    Returns:
        The AI response string, or empty string if failed
        
    Note:
        - Combines personality + history + user message into a single prompt
        - Removes excessive newlines from response
        - Preserves content quality while cleaning formatting
    """
    if not GEMINI_API_KEY:
        return ""

    effective_message = build_context_prompt(user_message, history)

    try:
        personality = PERSONALITIES.get(mode, PERSONALITIES[DEFAULT_PERSONALITY])
        prompt = f"{personality}\n\nUser: {effective_message}\nAssistant:"

        endpoint = "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generate"
        params = {"key": GEMINI_API_KEY}
        payload = {
            "prompt": {"text": prompt},
            "temperature": 0.7,
            "maxOutputTokens": 2000,
        }

        response = requests.post(endpoint, params=params, json=payload, timeout=30)
        if response.status_code != 200:
            print(f"GEMINI ERROR: HTTP {response.status_code} - {response.text}")
            return ""

        result = response.json()
        text = result.get("candidates", [{}])[0].get("output", "").strip()
        if not text:
            return ""

        # Clean excessive whitespace while preserving content
        text = ' '.join(text.replace('\n', ' ').split())
        return text
    except Exception as e:
        import traceback
        print(f"GEMINI ERROR: {str(e)}")
        print(traceback.format_exc())
        return ""


def ask_openai(user_message: str, mode: str, history: list | None = None) -> str:
    """
    Query OpenAI GPT-3.5 Turbo for a response.
    
    OpenAI is our primary provider (best quality). This function supports both:
    - Official OpenAI Python client (preferred if available)
    - Direct HTTP REST API fallback (if client library not installed)
    
    Args:
        user_message: The user's input message
        mode: Personality mode (determines system prompt)
        history: Previous messages for context
        
    Returns:
        The AI response string, or empty string if failed
        
    Note:
        - Uses gpt-3.5-turbo model for cost-effectiveness and speed
        - Falls back to REST API if openai package not installed
        - Handles JSON parsing errors gracefully
    """
    if not OPENAI_API_KEY:
        return ""

    personality = PERSONALITIES.get(mode, PERSONALITIES[DEFAULT_PERSONALITY])

    try:
        # Prefer the official client if available (better error handling)
        if OPENAI_AVAILABLE:
            client = OpenAI(api_key=OPENAI_API_KEY)
            messages = [{"role": "system", "content": personality}]
            messages.extend(build_message_history(history, user_message))
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=2000,
                temperature=0.7,
            )

            if response.choices and response.choices[0].message:
                return response.choices[0].message.content.strip()
            return ""
        else:
            # HTTP fallback to OpenAI REST API (no external dependencies)
            endpoint = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "system", "content": personality}],
                "max_tokens": 600,
                "temperature": 0.7,
            }
            payload["messages"].extend(build_message_history(history, user_message))

            r = requests.post(endpoint, headers=headers, json=payload, timeout=15)
            if r.status_code != 200:
                print(f"OPENAI ERROR: HTTP {r.status_code} - {r.text}")
                return ""

            j = r.json()
            if isinstance(j.get("choices"), list) and j["choices"]:
                first = j["choices"][0]
                msg = first.get("message") if isinstance(first, dict) else None
                if msg and isinstance(msg, dict):
                    return (msg.get("content") or "").strip()
                return (first.get("text") or "").strip()

            return ""
    except Exception as e:
        import traceback
        print(f"OPENAI ERROR: {str(e)}")
        print(traceback.format_exc())
        return ""


def ask_deepseek(user_message: str, mode: str, history: list | None = None) -> str:
    """
    Query DeepSeek API (OpenAI-compatible endpoint) for a response.
    
    DeepSeek is our third-priority provider. It offers good performance at low cost.
    This function tries multiple DeepSeek models in order of preference.
    
    Args:
        user_message: The user's input message (may include web search context)
        mode: Personality mode (determines system prompt)
        history: Previous messages for context
        
    Returns:
        The AI response string, or empty string if failed
        
    Note:
        - Tries models in order: deepseek-v4-flash → deepseek-v4-pro → deepseek-chat
        - Uses OpenAI-compatible API format
        - Filters out reasoning-heavy responses (starts with "We need to" or similar)
        - Falls through to next model if response seems unhelpful
        - Custom base URL can be set via DEEPSEEK_BASE_URL env var
    """
    if not DEEPSEEK_API_KEY or not DEEPSEEK_BASE_URL:
        return ""

    # Check if message contains web search context
    has_search_context = "Current information from web search:" in user_message
    if has_search_context:
        print(f"[DEBUG] DeepSeek: Message includes web search context")
    
    personality = PERSONALITIES.get(mode, PERSONALITIES[DEFAULT_PERSONALITY])

    # Use HTTP POST directly to the DeepSeek-compatible REST endpoint.
    try:
        endpoint = DEEPSEEK_BASE_URL.rstrip('/') + '/chat/completions'
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        system_content = (
            personality
            + "\n\nAnswer the user directly and clearly. Do not output internal reasoning or planning text."
        )

        # Try multiple DeepSeek models in order of preference
        preferred_models = ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat"]

        def extract_response(json_data):
            """Extract text response from DeepSeek API JSON response."""
            if not isinstance(json_data.get("choices"), list) or not json_data["choices"]:
                return ""
            first = json_data["choices"][0]
            msg = first.get("message") if isinstance(first, dict) else None
            if msg and isinstance(msg, dict):
                return (msg.get("content") or msg.get("reasoning_content") or "").strip()
            return (first.get("text") or "").strip()

        for model in preferred_models:
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system_content}],
                "max_tokens": 2000,
                "temperature": 0.7,
            }
            # Include full user message (with web search context if present)
            payload["messages"].extend(build_message_history(history, user_message))

            print(f"[DEBUG] DeepSeek: Sending request to model={model}")
            r = requests.post(endpoint, headers=headers, json=payload, timeout=15)
            if r.status_code != 200:
                print(f"DEEPSEEK ERROR: HTTP {r.status_code} - {r.text}")
                continue

            j = r.json()
            content = extract_response(j)
            if content:
                # If the model returned a planning-style response, try the next model
                # (Some DeepSeek models are verbose about their reasoning process)
                if content.startswith("We need to") or "I should" in content or "I'll" in content:
                    continue
                print(f"[DEBUG] DeepSeek: Got response from model={model}")
                return content

        return ""
    except Exception as e:
        import traceback
        print(f"DEEPSEEK ERROR: {str(e)}")
        print(traceback.format_exc())
        return ""


def get_demo_response(user_message: str, mode: str = "default") -> str:
    """
    Return lightweight demo replies when live AI credentials are not configured.
    
    This function provides quick responses for testing without real API keys.
    Each mode has different personality responses to show how the system works.
    
    Args:
        user_message: The user's input (not actually used in demo mode)
        mode: Personality mode (default, friendly, rude, playful)
        
    Returns:
        A randomly selected demo response in the chosen personality style
        
    Note:
        - Activated when DEMO_MODE=true in .env
        - Useful for development and testing before API keys are configured
        - Shows users how the interface works without API costs
    """
    demo_responses = {
        "default": [
            "That's an interesting question! I'm in demo mode right now, showing what I'd respond with real APIs enabled.",
            "I appreciate that question! In production, I'd connect to advanced AI models for detailed responses.",
            "Great topic! When real AI is enabled, I can provide much more in-depth analysis."
        ],
        "friendly": [
            "Hey there! Love the question! I'm in demo mode, but with real APIs enabled I'd be super helpful!",
            "Hey! Great to chat! When you set up the real APIs, I can give you amazing responses!",
            "What a cool question! Once the real AI is configured, I'd love to explore this with you!"
        ],
        "rude": [
            "Yeah, sure. I'd have a real response if you actually configured the APIs properly.",
            "Nice question, but I'm stuck in demo mode. Set up the real APIs and I'll actually be useful.",
            "This demo stuff is fine for now, but you need actual API keys for real power."
        ],
        "playful": [
            "Haha, nice one! I'm just playing around in demo mode. Real APIs? That's where the magic happens! 🎉",
            "Ooh fun question! I'm faking it in demo mode, but wait till real mode - that's the good stuff!",
            "Playful mode engaged! But for REAL responses, you gotta add those API keys!"
        ]
    }
    
    responses = demo_responses.get(mode, demo_responses["default"])
    import random
    return random.choice(responses)


def ask_ai(session_id: str, user_message: str, mode: str, history: list, debug: bool = False):
    """
    Main AI dispatch function that orchestrates the entire chat workflow.
    
    This is the core entry point for all chat requests. It handles:
    1. Input validation - rejects empty messages
    2. Demo mode - returns demo responses if API keys aren't configured
    3. Web search detection - determines if current info is needed
    4. Web search execution - fetches live information if needed
    5. Provider failover - tries each AI provider in order until one succeeds
    6. Error reporting - provides detailed feedback if all providers fail
    
    The function is designed to be robust: if web search fails, the AI still works.
    If one provider fails, others are automatically tried. Users always get meaningful
    feedback about what went wrong (rather than generic error messages).
    
    Args:
        session_id: Unique session identifier for tracking context
        user_message: The user's input message
        mode: The personality mode (normal/razzi/razzi_plus)
        history: List of previous messages for context
        debug: If True, return both response and provider name
        
    Returns:
        If debug=False: Just the response string
        If debug=True: Tuple of (response, provider_name)
        
    Example:
        >>> response = ask_ai(
        >>>     session_id="user_123",
        >>>     user_message="Who won the 2026 World Cup?",
        >>>     mode="normal",
        >>>     history=[],
        >>> )
        >>> # Response includes web search results + citations
    """
    if not user_message or not user_message.strip():
        return ("Say something so I can roast it.", "none") if debug else "Say something so I can roast it."
    
    # Demo mode - return lightweight responses without real API calls
    if DEMO_MODE:
        response = get_demo_response(user_message, mode)
        return (response, "demo") if debug else response
    
    # Check if web search is needed for current information
    search_context = ""
    web_sources = []
    if should_search_web(user_message):
        print(f"[DEBUG] Web search triggered for query containing current event keywords")
        search_result = search_web(user_message)
        if search_result["success"]:
            search_context = f"\n\nCurrent information from web search:\n{search_result['context']}"
            web_sources = search_result["sources"]
            print(f"[DEBUG] Web search successful, found {len(web_sources)} sources for: {user_message[:60]}")
        else:
            print(f"[DEBUG] Web search failed: {search_result['error']}")
    else:
        print(f"[DEBUG] No web search needed (no current event keywords in: {user_message[:60]})")
    
    # Modify the user message to include search context if available
    # This ensures the AI provider has current information when answering
    if search_context:
        enhanced_message = user_message + search_context
    else:
        enhanced_message = user_message
    
    # Try providers in order of quality/availability
    providers_to_try = []

    if AI_PROVIDER in {"openai", "auto"}:
        providers_to_try.append(("openai", ask_openai))

    if AI_PROVIDER in {"gemini", "auto"}:
        providers_to_try.append(("gemini", ask_gemini))

    if AI_PROVIDER in {"deepseek", "auto"}:
        providers_to_try.append(("deepseek", ask_deepseek))

    if AI_PROVIDER in {"together", "auto"}:
        providers_to_try.append(("together", ask_together))

    # Track errors for comprehensive failure reporting
    provider_errors = []

    for provider_name, provider_func in providers_to_try:
        try:
            # Call the provider with enhanced message (including web search context if available)
            response = provider_func(enhanced_message if search_context else user_message, mode, history)
            if response and response.strip():
                # If web search was used, append source citations to the response
                if web_sources:
                    response += "\n\n**Sources:**"
                    for source in web_sources[:3]:  # Limit to top 3 sources
                        if source.get("url"):
                            response += f"\n- [{source.get('title', 'Source')}]({source.get('url')})"
                
                if debug:
                    print(f"DEBUG: provider={provider_name} response={response[:80]!r}")
                    return response, provider_name
                return response
            else:
                provider_errors.append(f"{provider_name}: No valid response returned")
        except Exception as e:
            error_msg = f"{provider_name}: {str(e)}"
            provider_errors.append(error_msg)
            print(f"DEBUG: provider={provider_name} failed: {error_msg}")
            continue
    
    # All providers failed - provide detailed error information
    # This helps users understand what went wrong (API key issue, quota, timeout, etc.)
    error_report = "Sorry, all AI providers are currently unavailable. Details:\n\n"
    error_report += "\n".join(f"• {error}" for error in provider_errors) if provider_errors else "No providers are configured."
    error_report += "\n\nPlease try again later or check your API keys in the .env file."
    
    print(f"AIServiceUnavailable: {error_report}")
    return (error_report, "error") if debug else error_report
