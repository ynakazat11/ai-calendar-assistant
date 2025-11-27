# AI Schedule Agent

An intelligent agent for managing your schedule, to-do lists, and payment reminders. Integrates with Google Calendar using OAuth2 (no passwords stored).

## Features

- **Intelligent Scheduling**: 🧠 **NEW!** Natural language scheduling with automatic prep planning
  - Parse scheduling requests (e.g., "30 minutes interview with exec X at company Y")
  - Automatically gather information about people, companies, and interview processes
  - Calculate preparation time needed based on event type
  - Suggest optimal schedule times accounting for prep time
  - Create prep blocks in Google Calendar with detailed notes and resources
- **Schedule Management**: Suggests available time slots for meetings, including options with potential conflicts (movable events)
- **Task Generation**: Automatically generates to-do tasks based on calendar events, especially for one-off events like competitions and travel
- **Payment Reminders**: Tracks and reminds you about recurring payments (piano and fencing lessons)

## Setup

### 1. Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Calendar API enabled
- Google OAuth2 credentials

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Google Calendar API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Choose "Desktop app" as the application type
   - Download the credentials JSON file
5. Save the credentials file as `credentials.json` in the project root
   - **Important**: Add `credentials.json` to `.gitignore` (already included)
   - Do NOT commit this file to GitHub

### 4. Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
OPENAI_API_KEY=your_openai_api_key_here
# Optional: Force console-based OAuth (set to 'true' to avoid localhost issues)
GOOGLE_OAUTH_CONSOLE_MODE=false
```

**Important**: 
- `OPENAI_API_KEY` is **required** for intelligent scheduling features
- Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- The `.env` file is already in `.gitignore` and won't be committed

### 5. First Run Authentication

On first run, the agent will:
1. Open a browser window for Google OAuth authentication
2. Ask you to sign in and grant calendar permissions
3. Save the authentication token to `token.json` (also in `.gitignore`)

**Security Note**: 
- `credentials.json` and `token.json` are in `.gitignore`
- Never commit these files to GitHub
- The token will auto-refresh when needed

## Usage

### Interactive Mode
Run the agent in interactive mode:
```bash
python agent.py
```
Commands:
- `schedule [duration] [days] [timezone]` - Get suggestions (e.g., `schedule 60 14 India`)
  - Options: `date=YYYY-MM-DD`, `ex_date=YYYY-MM-DD`, `ex_day=0-6`
- `smart "[request]" [days] [timezone]` - Intelligent scheduling (e.g., `smart "meeting with John" 14`)
- `check [days]` - Check for upcoming events needing prep
- `monitor` - Run in background monitoring mode

### Command Line
Quick schedule check:
```bash
# Basic usage
python agent.py schedule 60 14

# With timezone (e.g., India)
python agent.py schedule 60 14 India

# Specific dates
python agent.py schedule 60 date=2025-12-25 date=2025-12-26

# Exclude weekends (Sat=5, Sun=6) and specific date
python agent.py schedule 60 14 ex_day=5 ex_day=6 ex_date=2025-12-25
```

### Features

#### 🌍 Smart Timezone Support
- **Flexible Input**: Use country names ("India"), cities ("Tokyo"), or codes ("PST").
- **Cross-Timezone Scheduling**: Searches in the target timezone but displays results in **your local timezone**.
- **Reasonable Hours Check**: Warns if a slot is outside 7 AM - 10 PM in your local time.

#### 📅 Advanced Scheduling
- **Specific Dates**: Request slots for specific days using `date=YYYY-MM-DD`.
- **Exclusions**: Exclude specific dates (`ex_date`) or days of the week (`ex_day`).
- **Smart Prep**: Automatically schedules preparation time for important meetings, ensuring enough lead time.
- `smart "[request]" [days] [timezone]` - **NEW!** Intelligent scheduling with prep planning
  - Example: `smart "30 minutes interview with exec John at Company X" 14 India`
  - Automatically gathers info, plans prep, and suggests optimal times
- `check [days] [timezone]` - **NEW!** Check for new events in calendar needing prep (default: 30 days)
  - Automatically detects interviews, tournaments, presentations, etc.
  - Creates prep events for newly added calendar events
- `monitor [minutes] [timezone]` - **NEW!** Continuously monitor calendar (default: 60 min)
  - Runs in background checking for new events periodically
- `tasks [months] [timezone]` - Get to-do tasks (default: 3 months)
- `payments [timezone]` - Get payment reminders
- `all` - Show everything
- `help` - Show help
- `quit` - Exit

### Command Line Mode

```bash
# Get schedule suggestions
python agent.py schedule 60 14

# Intelligent scheduling with prep planning
python agent.py smart "30 minutes interview with exec John at Company X" 14

# Check for new events needing prep
python agent.py check 30

# Continuously monitor calendar (runs in background)
python agent.py monitor 60

# Get tasks for next 3 months
python agent.py tasks 3

# Get payment reminders
python agent.py payments

# Show everything
python agent.py all
```

## Configuration

Edit `config.py` to customize:

- **Payment Reminders**: Modify `PAYMENT_REMINDERS` dictionary
- **Task Lookahead**: Change `TASK_LOOKAHEAD_MONTHS` (default: 3)
- **Google Scopes**: Adjust `GOOGLE_SCOPES` if needed

### Example: Adding a New Payment Reminder

Edit `config.py`:

```python
PAYMENT_REMINDERS = {
    'piano': {
        'day_of_month': 1,
        'description': 'Piano lessons payment'
    },
    'fencing': {
        'day_of_month': 1,
        'description': 'Fencing lessons payment'
    },
    'swimming': {  # New payment
        'day_of_month': 5,
        'description': 'Swimming lessons payment'
    }
}
```

## How It Works

### Intelligent Scheduling 🧠

The intelligent scheduler uses AI to help you prepare for important meetings:

1. **Request Parsing**: Understands natural language requests like "30 minutes interview with exec X at company Y"
2. **Information Gathering**: 
   - Searches the web for information about the person, company, and event type
   - Gathers interview questions, company background, and relevant resources
3. **Prep Planning**: 
   - Uses AI to analyze the gathered information
   - Calculates how much prep time you need
   - Breaks down prep into specific tasks with time estimates
   - Identifies key talking points and resources
4. **Smart Scheduling**: 
   - Finds optimal time slots for the event
   - Schedules prep blocks before the event (1-3 days in advance)
   - Accounts for your existing calendar commitments
5. **Calendar Integration**: 
   - Creates prep events in Google Calendar with detailed notes
   - Includes gathered information, talking points, and resources
   - Prep events are synced and visible in your calendar

**Example Workflow:**
```
You: smart "30 minutes interview with exec Sarah at TechCorp" 14

Agent:
1. Parses: Interview, 30 min, Sarah, TechCorp
2. Searches: Sarah's LinkedIn, TechCorp info, interview questions
3. Plans: 2 hours prep (1h research, 1h talking points)
4. Suggests: Event on 2024-01-15 14:00, Prep on 2024-01-13 10:00
5. Creates: Prep event with all gathered info and resources
```

### Automatic Calendar Monitoring 🔄

The calendar monitor automatically detects new events added directly to Google Calendar and creates prep plans:

1. **Event Detection**: 
   - Monitors calendar for new events (interviews, tournaments, presentations, etc.)
   - Identifies events needing prep based on keywords and event types
   - Skips events that already have prep events

2. **Duplicate Prevention**: 
   - Tracks processed events to avoid creating duplicate prep events
   - Checks for existing prep events before creating new ones
   - Uses event IDs and timestamps to ensure uniqueness

3. **Automatic Prep Creation**: 
   - When you add an event like "Kids Tournament" or "Interview with John" directly to Google Calendar
   - The monitor detects it and automatically:
     - Gathers relevant information
     - Plans preparation tasks
     - Creates prep blocks in your calendar
     - Adds detailed notes and resources

**Usage:**
```bash
# Check once for new events
python agent.py check 30

# Or run continuous monitoring (checks every 60 minutes)
python agent.py monitor 60
```

**Example:**
```
1. You add "Kids Fencing Tournament" to Google Calendar for next Saturday
2. Run: python agent.py check 30
3. Agent detects the tournament, searches for tournament info
4. Creates prep events: "Prep: Tournament Registration" and "Prep: Equipment Check"
5. All prep events synced to your calendar with detailed notes
```

### Schedule Management

- Scans your Google Calendar for the next N days
- Identifies available time slots (9 AM - 6 PM, weekdays)
- Also suggests slots with conflicts where the conflicting event might be movable (short events < 2 hours)

### Task Generation

- Analyzes calendar events for the next 3 months
- Identifies one-off and ad-hoc events
- Generates preparation tasks for:
  - **Competitions**: Registration and preparation tasks
  - **Travel**: Flight booking and packing tasks
  - **Other one-off events**: Generic preparation tasks

### Payment Reminders

- Checks on the 1st of each month for piano and fencing payments
- Shows overdue reminders if the day has passed
- Displays upcoming reminders for the next 7 days

## Project Structure

```
.
├── agent.py              # Main agent interface
├── calendar_manager.py   # Google Calendar integration
├── intelligent_scheduler.py  # Intelligent scheduling with prep planning
├── calendar_monitor.py   # Automatic calendar monitoring and prep creation
├── task_generator.py     # Task generation logic
├── payment_reminder.py   # Payment reminder system
├── config.py             # Configuration
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Security Best Practices

✅ **Implemented:**
- OAuth2 authentication (no passwords)
- Credentials and tokens in `.gitignore`
- Environment variables for sensitive data
- Token auto-refresh
- Event tracking to prevent duplicate prep events

❌ **Never commit:**
- `credentials.json`
- `token.json`
- `.env` file
- `processed_events.json` (tracks processed events)

## Troubleshooting

### "FileNotFoundError: credentials.json"

Download your OAuth2 credentials from Google Cloud Console and save as `credentials.json` in the project root.

### "Token expired"

The token should auto-refresh. If issues persist, delete `token.json` and re-authenticate.

### "No events found"

Check that:
- Your Google Calendar has events
- The date range includes your events
- You've granted calendar read permissions

### "Intelligent scheduler not available"

Make sure you have:
- Set `OPENAI_API_KEY` in your `.env` file
- Installed all dependencies: `pip install -r requirements.txt`
- Valid OpenAI API key with sufficient credits

### "Access blocked: This app has not completed the Google verification process"

This error occurs when your OAuth app is in "Testing" mode and your Google account isn't added as a test user. Here's how to fix it:

**Solution: Add Yourself as a Test User**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to "APIs & Services" → "OAuth consent screen"
4. Scroll down to the "Test users" section
5. Click "+ ADD USERS"
6. Add your Google account email address (the one you're using to sign in)
7. Click "ADD"
8. Try authenticating again

**Alternative: Publish Your App (for personal use only)**

If you're the only user, you can publish the app without verification:
1. Go to "OAuth consent screen"
2. Change "Publishing status" from "Testing" to "In production"
3. Note: This only works if you're the only user. For multiple users, you'll need Google verification.

**Important Notes:**
- In Testing mode, only test users can sign in
- For production use with multiple users, Google requires verification
- For personal use, adding yourself as a test user is the easiest solution

### OAuth "redirect_uri_mismatch" or localhost allowlist error

If you encounter errors about localhost redirect URIs or allowlist issues:

**Solution 1: Use Manual Authentication Mode (Automatic Fallback)**
The agent now automatically falls back to manual authentication if local server fails. You'll be prompted to:
1. Copy the authorization URL from the console
2. Open it in your browser
3. Sign in and authorize the application
4. The browser will redirect to localhost (you may see an error page - that's OK)
5. Copy the ENTIRE URL from your browser's address bar
6. Paste it back into the console when prompted

**Solution 2: Configure OAuth in Google Cloud Console**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to "APIs & Services" → "Credentials"
4. Click on your OAuth 2.0 Client ID
5. Under "Authorized redirect URIs", add:
   - `http://localhost:8080/` (or the port shown in the error)
   - `http://127.0.0.1:8080/`
   - For desktop apps, you may also need to add `urn:ietf:wg:oauth:2.0:oob`
6. Save the changes
7. Try authenticating again

**Solution 3: Force Manual Mode**
Add this to your `.env` file to always use manual authentication:
```env
GOOGLE_OAUTH_CONSOLE_MODE=true
```
This uses `run_local_server()` with `open_browser=False`, which prints a URL you can open manually. This still requires localhost redirect URIs to be configured, but gives you more control over the process.

## License

MIT License - feel free to use and modify as needed.

