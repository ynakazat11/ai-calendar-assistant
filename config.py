"""
Configuration management for the AI Agent.
All sensitive data should be stored in environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Google Calendar API Configuration
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 
                 'https://www.googleapis.com/auth/calendar.events']
# Force console-based OAuth flow (set to 'true' to skip local server and always use console)
GOOGLE_OAUTH_CONSOLE_MODE = os.getenv('GOOGLE_OAUTH_CONSOLE_MODE', 'false').lower() == 'true'

# OpenAI Configuration (for AI agent capabilities)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Payment Reminder Configuration
PAYMENT_REMINDERS = {
    'piano': {
        'day_of_month': 1,  # Remind on 1st of each month
        'description': 'Piano lessons payment'
    },
    'fencing': {
        'day_of_month': 1,  # Remind on 1st of each month
        'description': 'Fencing lessons payment'
    }
}

# Task Generation Configuration
TASK_LOOKAHEAD_MONTHS = 3

