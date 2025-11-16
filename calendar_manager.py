"""
Google Calendar integration for schedule management.
Uses OAuth2 for authentication - no passwords stored.
"""
import os
import pickle
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config


class CalendarManager:
    """Manages Google Calendar operations."""
    
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API using OAuth2."""
        creds = None
        
        # Check if token.json exists (from previous authentication)
        if os.path.exists(config.GOOGLE_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(
                config.GOOGLE_TOKEN_FILE, config.GOOGLE_SCOPES
            )
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    print("Re-authenticating...")
                    creds = None
            
            if not creds or not creds.valid:
                if not os.path.exists(config.GOOGLE_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Please download credentials.json from Google Cloud Console "
                        f"and place it in the project root. See README.md for instructions."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GOOGLE_CREDENTIALS_FILE, config.GOOGLE_SCOPES
                )
                
                # Check if console mode is forced via config
                if config.GOOGLE_OAUTH_CONSOLE_MODE:
                    print("Using manual authentication mode (forced by config)...")
                    print("=" * 60)
                    print("MANUAL AUTHENTICATION REQUIRED")
                    print("=" * 60)
                    print("\n1. A URL will be displayed below.")
                    print("2. Copy the URL and open it in your browser.")
                    print("3. Sign in and authorize the application.")
                    print("4. The browser will redirect - you may see an error page, that's OK.")
                    print("5. Copy the ENTIRE URL from your browser's address bar.")
                    print("6. Paste it here when prompted.")
                    print("=" * 60)
                    print()
                    # Use local server but don't open browser automatically
                    creds = flow.run_local_server(port=0, open_browser=False)
                else:
                    # Try local server first, fall back to manual mode if it fails
                    try:
                        print("Attempting OAuth flow with local server...")
                        creds = flow.run_local_server(port=0, open_browser=True)
                    except Exception as e:
                        print(f"Local server flow failed: {e}")
                        print("\nSwitching to manual authentication mode...")
                        print("=" * 60)
                        print("MANUAL AUTHENTICATION REQUIRED")
                        print("=" * 60)
                        print("\n1. A URL will be displayed below.")
                        print("2. Copy the URL and open it in your browser.")
                        print("3. Sign in and authorize the application.")
                        print("4. The browser will redirect - you may see an error page, that's OK.")
                        print("5. Copy the ENTIRE URL from your browser's address bar.")
                        print("6. Paste it here when prompted.")
                        print("=" * 60)
                        print()
                        
                        # Use local server but don't open browser automatically
                        creds = flow.run_local_server(port=0, open_browser=False)
            
            # Save the credentials for the next run
            with open(config.GOOGLE_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            print("✅ Authentication successful! Credentials saved.")
        
        self.service = build('calendar', 'v3', credentials=creds)
    
    def _normalize_datetime(self, dt):
        """Normalize datetime to timezone-aware UTC if naive."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Assume naive datetime is in UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def get_events(self, start_time=None, end_time=None, max_results=250):
        """
        Retrieve events from Google Calendar.
        
        Args:
            start_time: datetime object for start time (default: now)
            end_time: datetime object for end time (default: 3 months from now)
            max_results: maximum number of events to retrieve
        
        Returns:
            List of event dictionaries
        """
        if not self.service:
            raise RuntimeError("Calendar service not initialized. Please authenticate first.")
        
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        else:
            start_time = self._normalize_datetime(start_time)
        
        if end_time is None:
            end_time = start_time + timedelta(days=90)  # 3 months
        else:
            end_time = self._normalize_datetime(end_time)
        
        try:
            # Format datetime for Google Calendar API (RFC3339 format)
            # If timezone-aware, use as-is; if naive, assume UTC
            if start_time.tzinfo is None:
                start_time_str = start_time.isoformat() + 'Z'
            else:
                # Convert to UTC and format
                start_time_utc = start_time.astimezone(timezone.utc)
                start_time_str = start_time_utc.isoformat().replace('+00:00', 'Z')
            
            if end_time.tzinfo is None:
                end_time_str = end_time.isoformat() + 'Z'
            else:
                # Convert to UTC and format
                end_time_utc = end_time.astimezone(timezone.utc)
                end_time_str = end_time_utc.isoformat().replace('+00:00', 'Z')
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_time_str,
                timeMax=end_time_str,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return events
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_busy_times(self, start_time, end_time):
        """
        Get busy time slots from calendar.
        
        Args:
            start_time: datetime object for start time
            end_time: datetime object for end time
        
        Returns:
            List of tuples (start, end) for busy periods
        """
        events = self.get_events(start_time, end_time)
        busy_times = []
        
        for event in events:
            start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
            end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))
            
            if start and end:
                try:
                    if 'T' in start:
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    else:
                        start_dt = datetime.fromisoformat(start)
                        end_dt = datetime.fromisoformat(end)
                    
                    busy_times.append((start_dt, end_dt))
                except ValueError:
                    continue
        
        return busy_times
    
    def suggest_time_slots(self, duration_minutes=60, start_date=None, days_ahead=14):
        """
        Suggest available time slots for scheduling.
        Also suggests slots with potential conflicts (movable events).
        
        Args:
            duration_minutes: Duration of the meeting in minutes
            start_date: datetime to start looking from (default: now)
            days_ahead: Number of days ahead to look
        
        Returns:
            Dictionary with 'available' and 'conflict_possible' time slots
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            start_date = self._normalize_datetime(start_date)
        
        end_date = start_date + timedelta(days=days_ahead)
        busy_times = self.get_busy_times(start_date, end_date)
        
        # Normalize all busy times to timezone-aware
        busy_times = [(self._normalize_datetime(start), self._normalize_datetime(end)) 
                     for start, end in busy_times]
        
        # Sort busy times
        busy_times.sort(key=lambda x: x[0])
        
        duration = timedelta(minutes=duration_minutes)
        available_slots = []
        conflict_slots = []
        
        # Working hours: 9 AM to 6 PM
        current = start_date
        
        while current < end_date:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                current = current.replace(hour=9, minute=0)
                continue
            
            # Skip outside working hours
            if current.hour < 9:
                current = current.replace(hour=9, minute=0)
            elif current.hour >= 18:
                current += timedelta(days=1)
                current = current.replace(hour=9, minute=0)
                continue
            
            slot_end = current + duration
            
            # Check if slot conflicts with existing events
            has_conflict = False
            conflict_event = None
            
            for busy_start, busy_end in busy_times:
                # Check for overlap
                if (current < busy_end and slot_end > busy_start):
                    has_conflict = True
                    conflict_event = (busy_start, busy_end)
                    break
            
            if not has_conflict:
                available_slots.append((current, slot_end))
            else:
                # Check if the conflicting event might be movable
                # (e.g., not an all-day event, not too long)
                conflict_duration = conflict_event[1] - conflict_event[0]
                if conflict_duration < timedelta(hours=2):  # Short events might be movable
                    conflict_slots.append({
                        'slot': (current, slot_end),
                        'conflict_with': conflict_event,
                        'note': 'Short event - might be movable'
                    })
            
            # Move to next potential slot (30-minute increments)
            current += timedelta(minutes=30)
        
        # Add conflict resolution suggestions
        conflict_resolutions = []
        if conflict_slots:
            # Suggest alternative times near conflicts
            for conflict_info in conflict_slots[:3]:
                conflict_start, conflict_end = conflict_info['conflict_with']
                slot_start, slot_end = conflict_info['slot']
                
                # Suggest time before conflict
                before_suggestion = conflict_start - duration
                if before_suggestion >= start_date and before_suggestion.hour >= 9 and before_suggestion.hour < 18:
                    conflict_resolutions.append({
                        'type': 'before_conflict',
                        'suggested_time': (before_suggestion, before_suggestion + duration),
                        'conflict_with': conflict_info['conflict_with'],
                        'note': f"Schedule before {conflict_start.strftime('%H:%M')} to avoid conflict"
                    })
                
                # Suggest time after conflict
                after_suggestion = conflict_end
                if after_suggestion + duration <= end_date and after_suggestion.hour >= 9 and after_suggestion.hour < 18:
                    conflict_resolutions.append({
                        'type': 'after_conflict',
                        'suggested_time': (after_suggestion, after_suggestion + duration),
                        'conflict_with': conflict_info['conflict_with'],
                        'note': f"Schedule after {conflict_end.strftime('%H:%M')} to avoid conflict"
                    })
        
        return {
            'available': available_slots[:10],  # Top 10 available
            'conflict_possible': conflict_slots[:5],  # Top 5 with potential conflicts
            'conflict_resolutions': conflict_resolutions[:3]  # Top 3 conflict resolution suggestions
        }
    
    def create_event(self, title: str, start_time: datetime, end_time: datetime, 
                    description: str = '', location: str = '', 
                    check_duplicates: bool = True, check_past: bool = True) -> str:
        """
        Create a new calendar event.
        
        Args:
            title: Event title
            start_time: Event start time (datetime object)
            end_time: Event end time (datetime object)
            description: Event description
            location: Event location (optional)
            check_duplicates: Whether to check for duplicate events (default: True)
            check_past: Whether to prevent past events (default: True)
        
        Returns:
            Event ID if successful, None otherwise
        
        Raises:
            ValueError: If event is in the past or is a duplicate
        """
        if not self.service:
            raise RuntimeError("Calendar service not initialized. Please authenticate first.")
        
        # Normalize datetimes to timezone-aware
        start_time = self._normalize_datetime(start_time)
        end_time = self._normalize_datetime(end_time)
        
        # Validate past events
        if check_past:
            now = datetime.now(timezone.utc)
            if start_time < now:
                raise ValueError(
                    f"Cannot create events in the past. "
                    f"Event start time ({start_time.strftime('%Y-%m-%d %H:%M')}) is before now ({now.strftime('%Y-%m-%d %H:%M')})"
                )
        
        # Check for duplicates
        if check_duplicates:
            # Check for events with same title and overlapping time
            existing_events = self.get_events(
                start_time - timedelta(minutes=1),
                end_time + timedelta(minutes=1)
            )
            
            for event in existing_events:
                event_title = event.get('summary', '')
                event_start_str = event.get('start', {}).get('dateTime', '')
                event_end_str = event.get('end', {}).get('dateTime', '')
                
                if event_start_str and event_end_str:
                    try:
                        if 'T' in event_start_str:
                            event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                            event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00'))
                        else:
                            event_start = datetime.fromisoformat(event_start_str)
                            event_end = datetime.fromisoformat(event_end_str)
                        
                        event_start = self._normalize_datetime(event_start)
                        event_end = self._normalize_datetime(event_end)
                        
                        # Check if same title and overlapping time
                        if (event_title.lower() == title.lower() and 
                            start_time < event_end and end_time > event_start):
                            raise ValueError(
                                f"Duplicate event detected: '{title}' at {start_time.strftime('%Y-%m-%d %H:%M')}. "
                                f"An event with the same title already exists at {event_start.strftime('%Y-%m-%d %H:%M')}"
                            )
                    except (ValueError, KeyError):
                        continue
        
        # Convert datetime to RFC3339 format with timezone
        start_rfc3339 = start_time.isoformat()
        end_rfc3339 = end_time.isoformat()
        
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_rfc3339,
            },
            'end': {
                'dateTime': end_rfc3339,
            },
        }
        
        # Add timezone if datetime is timezone-aware
        if start_time.tzinfo is not None:
            # Use UTC timezone name for Google Calendar
            event['start']['timeZone'] = 'UTC'
            event['end']['timeZone'] = 'UTC'
        
        if location:
            event['location'] = location
        
        try:
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return created_event.get('id')
        except HttpError as error:
            print(f'An error occurred creating event: {error}')
            return None
        except ValueError as e:
            # Re-raise ValueError (for duplicates/past events)
            raise

