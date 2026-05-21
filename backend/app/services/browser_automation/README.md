# Browser Automation Engine

Production-grade Playwright-based browser automation for GrandpaAssistant.

## Overview

The Browser Automation Engine provides intelligent, persistent web automation with:

- **Multi-browser Support**: Chromium, Firefox, WebKit
- **Persistent Sessions**: Maintain browser state across commands
- **AI-Driven Planning**: Convert natural language commands to action sequences
- **Safety Layer**: Confirms dangerous actions before execution
- **Memory System**: Stores credentials, page state, navigation history
- **Human-like Navigation**: Realistic delays and interaction patterns
- **Retry Logic**: Exponential backoff for transient failures
- **REST APIs**: Full HTTP interface with WebSocket streaming

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  REST API Layer                         │
│              (browser_api.py)                           │
│  POST /api/browser/session/start                        │
│  POST /api/browser/navigate                             │
│  POST /api/browser/click                                │
│  WS   /api/browser/stream/{session_id}                  │
└────────────┬────────────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────────────┐
│                 Service Layer                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │ Session Manager  │      │ Action Planner   │        │
│  │ - Multi-browser  │      │ - AI planning    │        │
│  │ - Persistence    │      │ - Ollama support │        │
│  └──────────────────┘      └──────────────────┘        │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │   Executor       │      │  Safety Layer    │        │
│  │ - Retry logic    │      │ - Risk detection │        │
│  │ - Timeouts       │      │ - Confirmations  │        │
│  └──────────────────┘      └──────────────────┘        │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │  Memory System   │      │  Operations      │        │
│  │ - Credentials    │      │ - Login flow     │        │
│  │ - Page snapshots │      │ - Form filling   │        │
│  └──────────────────┘      └──────────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────────────┐
│              Playwright Core Layer                      │
│  Chromium / Firefox / WebKit                            │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Session Manager (`session_manager.py`)

Manages browser contexts and pages with multi-browser support.

**Features:**
- Create/close persistent browser sessions
- Multi-browser support (Chromium, Firefox, WebKit)
- Session metadata tracking
- Automatic resource cleanup

**Usage:**
```python
from browser_automation.session_manager import BrowserSessionManager, BrowserConfig

manager = BrowserSessionManager(data_dir="browser_sessions")
await manager.start()

# Create session
config = BrowserConfig(browser_type=BrowserType.CHROMIUM, headless=False)
await manager.create_session("session_123", config)

# Get page and navigate
page = await manager.get_page("session_123", "https://example.com")
```

### 2. Executor (`executor.py`)

Executes Playwright actions with robust retry logic.

**Features:**
- Navigate, click, fill, extract operations
- Exponential backoff retry logic
- Human-like interaction delays
- Action result tracking

**Supported Actions:**
- `navigate(page, url)` - Navigate to URL
- `click(page, selector)` - Click element
- `fill(page, selector, text)` - Fill form field
- `extract_text(page, selector)` - Get element text
- `take_screenshot(page, path)` - Capture page

**Example:**
```python
from browser_automation.executor import BrowserExecutor

executor = BrowserExecutor(max_retries=3, base_delay=1.0)

result = await executor.navigate(page, "https://uber.com")
if result.success:
    click_result = await executor.click(page, "[data-test-id='request-ride']")
```

### 3. Action Planner (`action_planner.py`)

Converts natural language commands to action sequences using Ollama.

**Features:**
- AI-driven action planning
- Plan caching
- Fallback patterns for common tasks

**Example:**
```python
from browser_automation.action_planner import BrowserActionPlanner

planner = BrowserActionPlanner(ollama_client=ollama, model="neural-chat")

plan = await planner.plan_action_sequence("Book an Uber")
# Returns: ActionPlan with step-by-step instructions
```

### 4. Memory System (`memory.py`)

Persistent storage for credentials, page state, and history.

**Features:**
- Encrypted credential storage
- Page snapshots for recovery
- Navigation history
- Extracted data storage

**Example:**
```python
from browser_automation.memory import BrowserMemory, PageSnapshot

memory = BrowserMemory(data_dir="browser_memory")

# Store credentials
key = memory.store_credential(
    service="linkedin",
    username="user@example.com",
    password="secret",
    url_pattern="linkedin.com"
)

# Retrieve for auto-fill
cred = memory.get_credential("linkedin")
```

### 5. Safety Layer (`safety_layer.py`)

Validates and confirms dangerous actions.

**Features:**
- Automatic risk classification
- Payment/deletion/modification detection
- Confirmation workflows

**Risk Levels:**
- `LOW` - Navigation, viewing
- `MEDIUM` - File operations
- `HIGH` - Form submissions, account changes
- `CRITICAL` - Payments, account deletion

**Example:**
```python
from browser_automation.safety_layer import BrowserSafetyLayer

safety = BrowserSafetyLayer(require_confirmations=True)

check = safety.classify_action(
    action="submit",
    context="payment checkout"
)
# Returns: ActionSafetyCheck with risk_level=CRITICAL

if check.requires_confirmation:
    action_id = safety.register_pending_action("action_1", check)
    # User confirms...
    safety.confirm_action("action_1")
```

### 6. Operations (`operations.py`)

High-level reusable operations.

**Features:**
- Login flows
- Form filling
- Table extraction
- File upload/download

**Example:**
```python
from browser_automation.operations import BrowserOperations

ops = BrowserOperations(executor)

result = await ops.login(
    page,
    service="linkedin",
    username="user@example.com",
    password="secret",
    login_url="https://linkedin.com/login",
    username_selector="#email",
    password_selector="#password",
    submit_selector="[data-test-id='login-button']"
)
```

## REST API Endpoints

### Session Management

**Start Session**
```http
POST /api/browser/session/start
Content-Type: application/json

{
  "headless": false,
  "browser": "chromium",
  "locale": "en-US"
}

Response:
{
  "session_id": "abc123",
  "status": "active",
  "created_at": "2024-05-20T15:45:30"
}
```

**Get Session State**
```http
GET /api/browser/session/{session_id}/state

Response:
{
  "session_id": "abc123",
  "created_at": "2024-05-20T15:45:30",
  "last_accessed": "2024-05-20T15:45:35",
  "page_count": 2,
  "browser_type": "chromium"
}
```

**End Session**
```http
POST /api/browser/session/{session_id}/end

Response:
{
  "status": "ended"
}
```

### Browser Operations

**Navigate**
```http
POST /api/browser/session/{session_id}/navigate
Content-Type: application/json

{
  "url": "https://uber.com",
  "wait_until": "networkidle"
}

Response:
{
  "action_type": "navigate",
  "success": true,
  "result": {
    "url": "https://uber.com",
    "title": "Uber - Ride Booking"
  },
  "duration_ms": 2450
}
```

**Click**
```http
POST /api/browser/session/{session_id}/click
Content-Type: application/json

{
  "selector": "[data-testid='request-ride']"
}

Response:
{
  "action_type": "click",
  "success": true,
  "duration_ms": 340
}
```

**Fill Form Field**
```http
POST /api/browser/session/{session_id}/fill
Content-Type: application/json

{
  "selector": "#destination",
  "text": "Times Square, NYC"
}

Response:
{
  "action_type": "fill",
  "success": true,
  "result": {
    "selector": "#destination",
    "text_length": 19
  }
}
```

**Login**
```http
POST /api/browser/session/{session_id}/login
Content-Type: application/json

{
  "service": "linkedin",
  "username": "user@example.com",
  "password": "secret",
  "login_url": "https://linkedin.com/login",
  "username_selector": "#email",
  "password_selector": "#password",
  "submit_selector": "[data-testid='login-button']"
}

Response:
{
  "action_type": "login",
  "success": true,
  "result": {
    "service": "linkedin",
    "message": "Successfully logged in to linkedin"
  }
}
```

**Screenshot**
```http
POST /api/browser/session/{session_id}/screenshot

Response:
{
  "success": true,
  "path": "browser_screenshots/abc123_1234567890.png"
}
```

### Real-time Updates

**WebSocket Stream**
```javascript
const ws = new WebSocket("ws://localhost:8765/api/browser/stream/abc123");

ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log("Status:", status);
};

// Sent from server:
{
  "action": "click",
  "status": "in_progress",
  "timestamp": "2024-05-20T15:45:35Z"
}
```

## Configuration

Edit `config.py` to customize:

```python
# Session management
MAX_CONCURRENT_SESSIONS = 5
SESSION_TIMEOUT_MINUTES = 30

# Executor settings
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1.0
PAGE_LOAD_TIMEOUT_MS = 30000
ACTION_TIMEOUT_MS = 10000

# Browser
BROWSER_HEADLESS = False
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

# AI Planning
OLLAMA_MODEL = "neural-chat"

# Safety
REQUIRE_CONFIRMATIONS = True
SAFE_MODE_ENABLED = True
```

## Common Workflows

### 1. Book a Cab

```python
async def book_cab():
    # Start session
    session = await manager.create_session("uber_booking")
    page = await manager.get_page("uber_booking", "https://uber.com")
    
    # Navigate and plan actions
    plan = await planner.plan_action_sequence("Book a ride to Times Square")
    
    # Execute plan
    for step in plan.steps:
        if step.action_type == "navigate":
            await executor.navigate(page, step.value)
        elif step.action_type == "click":
            await executor.click(page, step.selector)
        elif step.action_type == "fill":
            await executor.fill(page, step.selector, step.value)
    
    # Confirm payment
    check = safety.classify_action("submit", "payment checkout")
    if check.requires_confirmation:
        # User confirms in UI
        pass
    
    await manager.end_session("uber_booking")
```

### 2. Login with Persistence

```python
async def login_linkedin():
    session = await manager.create_session("linkedin_session")
    page = await manager.get_page("linkedin_session", "https://linkedin.com/login")
    
    # Check memory for cached credentials
    cred = memory.get_credential("linkedin")
    
    if cred:
        # Auto-fill from memory
        await executor.fill(page, "#email", cred.username)
    else:
        # First time login
        await executor.fill(page, "#email", "user@example.com")
        await executor.fill(page, "#password", "secret")
        
        # Store for future
        memory.store_credential(
            "linkedin", "user@example.com", "secret", "linkedin.com"
        )
    
    await executor.click(page, "[data-testid='login-button']")
```

### 3. Extract Structured Data

```python
async def extract_job_listings():
    session = await manager.create_session("linkedin_jobs")
    page = await manager.get_page("session", "https://linkedin.com/jobs/...")
    
    # Get all job postings
    jobs = await ops.extract_table_data(page, "[role='listbox']")
    
    # Store extracted data
    memory.store_extracted_data("linkedin_jobs", "job_listings", jobs)
    
    return jobs
```

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest backend/tests/unit/browser_automation/ -v

# Test specific component
pytest backend/tests/unit/browser_automation/test_executor.py -v

# With coverage
pytest backend/tests/unit/browser_automation/ --cov=backend.app.services.browser_automation
```

### E2E Tests

```bash
# Run e2e tests (requires browser)
pytest backend/tests/e2e/test_browser_flows.py -v

# Specific flow
pytest backend/tests/e2e/test_browser_flows.py::test_cab_booking_flow -v
```

## Performance Tuning

### Retry Strategy

```python
executor = BrowserExecutor(
    max_retries=3,           # Total attempts
    base_delay=0.5,          # Initial delay in seconds
    page_load_timeout=20000, # 20 seconds max page load
    action_timeout=5000      # 5 seconds for actions
)
```

### Session Limits

```python
# In config.py
MAX_CONCURRENT_SESSIONS = 3  # Reduce to save memory
SESSION_TIMEOUT_MINUTES = 15  # Auto-cleanup inactive sessions
```

### Human-like Delays

```python
# In executor.py
HUMAN_DELAY_MIN_MS = 100   # Minimum 100ms between actions
HUMAN_DELAY_MAX_MS = 500   # Maximum 500ms between actions
```

## Troubleshooting

### Pages not loading

**Problem:** Timeout on page navigation

**Solution:** 
- Increase `PAGE_LOAD_TIMEOUT_MS` in config
- Check network connectivity
- Try different `wait_until` values: `"load"`, `"domcontentloaded"`, `"networkidle"`

### Elements not found

**Problem:** Selector doesn't match elements

**Solution:**
- Use browser inspector to verify selector
- Add screenshot for debugging: `await executor.take_screenshot(page, "debug.png")`
- Check element visibility with Playwright `wait_for_selector`

### Memory leaks

**Problem:** Sessions accumulating

**Solution:**
- Call `await manager.end_session(id)` after use
- Enable `SESSION_TIMEOUT_MINUTES` for auto-cleanup
- Monitor with `manager.list_sessions()`

## Security Notes

⚠️ **Important:**
- Credentials are hashed but not encrypted. Use proper secrets management in production.
- Never log sensitive data (passwords, tokens).
- Validate user input before using in selectors.
- Enable `REQUIRE_CONFIRMATIONS` for all user interactions.
- Use HTTPS for API in production.

## License

Part of GrandpaAssistant. See parent repository for license.
