"""
Google Calendar integration for schedule management.
Uses OAuth2 for authentication - no passwords stored.
"""
import os
import pickle
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
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
    
    def suggest_time_slots(self, duration_minutes=60, start_date=None, days_ahead=14, 
                          timezone_str='UTC', excluded_dates=None, excluded_days=None,
                          user_timezone='UTC', specific_dates=None):
        """
        Suggest available time slots for scheduling.
        Also suggests slots with potential conflicts (movable events).
        
        Args:
            duration_minutes: Duration of the meeting in minutes
            start_date: datetime to start looking from (default: now)
            days_ahead: Number of days ahead to look
            timezone_str: Target timezone string (e.g., 'Asia/Kolkata')
            excluded_dates: List of dates to exclude (YYYY-MM-DD)
            excluded_days: List of days of week to exclude (0=Monday, 6=Sunday)
            user_timezone: User's local timezone string (e.g., 'America/Los_Angeles')
            specific_dates: List of specific dates to schedule on (YYYY-MM-DD). If provided, days_ahead is ignored.
        
        Returns:
            Dictionary with 'available' and 'conflict_possible' time slots.
            Each slot is now a dictionary containing:
            - target_slot: (start, end) in target timezone
            - user_slot: (start, end) in user timezone
            - is_reasonable: boolean (7 AM - 10 PM in user timezone)
        """
        if excluded_dates is None:
            excluded_dates = []
        if excluded_days is None:
            excluded_days = []
        if specific_dates is None:
            specific_dates = []
            
        try:
            target_tz = ZoneInfo(timezone_str)
        except Exception:
            print(f"Warning: Invalid target timezone '{timezone_str}', falling back to UTC")
            target_tz = timezone.utc
            
        try:
            user_tz = ZoneInfo(user_timezone)
        except Exception:
            print(f"Warning: Invalid user timezone '{user_timezone}', falling back to UTC")
            user_tz = timezone.utc

        if start_date is None:
            # Start from now in target timezone
            start_date = datetime.now(target_tz).replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            start_date = self._normalize_datetime(start_date).astimezone(target_tz)
        
        # If specific dates are provided, we don't use days_ahead logic in the same way
        # Instead, we'll check each specific date
        if specific_dates:
            # We still need a range for get_busy_times, so let's find min and max of specific dates
            # But specific_dates are strings, need to convert to dates relative to target_tz
            pass # Logic handled inside loop or by pre-calculating range
            
            # Actually, let's just determine the overall range to fetch busy times once
            # It's more efficient than fetching for each day
            sorted_dates = sorted(specific_dates)
            try:
                min_date_str = sorted_dates[0]
                max_date_str = sorted_dates[-1]
                
                # Parse as date objects
                min_date = datetime.strptime(min_date_str, '%Y-%m-%d').date()
                max_date = datetime.strptime(max_date_str, '%Y-%m-%d').date()
                
                # Create datetime range in target_tz
                # Start of min_date
                range_start = datetime.combine(min_date, datetime.min.time()).replace(tzinfo=target_tz)
                # End of max_date
                range_end = datetime.combine(max_date, datetime.max.time()).replace(tzinfo=target_tz)
                
                # Ensure range_start is not before start_date (which defaults to now)
                # Unless user specifically asked for a past date? (Usually we shouldn't allow past)
                # But let's respect start_date if it's "now"
                if range_start < start_date:
                    # If specific date is today, we might start from now
                    if range_start.date() == start_date.date():
                        range_start = start_date
                    else:
                        # If it's strictly in the past, we might want to skip or show error?
                        # For now, let's just use the requested date start (00:00) 
                        # but get_busy_times will handle it.
                        # However, the loop below checks `current < end_date`.
                        pass
                
                end_date = range_end
                
                # We will iterate differently if specific_dates is set
            except ValueError:
                print("Error parsing specific dates. Ignoring.")
                specific_dates = []
                end_date = start_date + timedelta(days=days_ahead)
        else:
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
        if specific_dates:
            # Iterate through each specific date
            for date_str in specific_dates:
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    # Start at 9 AM on that date in target_tz
                    # We need to handle DST correctly, so use proper timezone conversion if needed
                    # But simpler: create naive datetime and localize
                    # Actually, we already have target_tz.
                    
                    # Create a datetime at 9 AM on that date
                    # We need to be careful about creating it directly with tzinfo if it's not fixed offset
                    # Best way: datetime.combine(date, time) -> replace(tzinfo=None) -> astimezone(target_tz) ??
                    # No, target_tz is a ZoneInfo.
                    
                    # Correct way with ZoneInfo:
                    dt_naive = datetime.combine(target_date, datetime.min.time())
                    # We want 9 AM in that timezone.
                    # Let's start at 00:00 and loop, skipping non-working hours?
                    # Or just jump to 9 AM?
                    
                    # Let's construct 9 AM in target timezone
                    # This might be tricky if 9 AM doesn't exist (DST gap), but rare for 9 AM.
                    
                    # Let's use a helper to get start of day in target tz
                    # We can assume the date string is meant for the target timezone.
                    
                    # Construct 9 AM
                    current = datetime.combine(target_date, datetime.min.time().replace(hour=9)).replace(tzinfo=target_tz)
                    
                    # If this specific date is today, and now is past 9 AM, start from now
                    if current < start_date:
                        current = start_date
                        # Round up to next 30 min
                        if current.minute >= 30:
                            current = current.replace(minute=0) + timedelta(hours=1)
                        elif current.minute > 0:
                            current = current.replace(minute=30)
                    
                    # End of this working day (6 PM)
                    day_end = datetime.combine(target_date, datetime.min.time().replace(hour=18)).replace(tzinfo=target_tz)
                    
                    while current < day_end:
                        # Logic inside loop is same as below, refactor?
                        # Or just copy-paste for safety/speed now.
                        
                        slot_end = current + duration
                        
                        if slot_end > day_end:
                            break
                            
                        # Check conflicts (same logic)
                        has_conflict = False
                        conflict_event = None
                        
                        for busy_start, busy_end in busy_times:
                            if (current < busy_end and slot_end > busy_start):
                                has_conflict = True
                                conflict_event = (busy_start, busy_end)
                                break
                        
                        if not has_conflict:
                            # Calculate user time and reasonableness
                            user_start = current.astimezone(user_tz)
                            user_end = slot_end.astimezone(user_tz)
                            is_reasonable = 7 <= user_start.hour < 22
                            
                            available_slots.append({
                                'target_slot': (current, slot_end),
                                'user_slot': (user_start, user_end),
                                'is_reasonable': is_reasonable
                            })
                        else:
                            conflict_duration = conflict_event[1] - conflict_event[0]
                            if conflict_duration < timedelta(hours=2):
                                user_start = current.astimezone(user_tz)
                                user_end = slot_end.astimezone(user_tz)
                                is_reasonable = 7 <= user_start.hour < 22
                                
                                conflict_slots.append({
                                    'slot': {
                                        'target_slot': (current, slot_end),
                                        'user_slot': (user_start, user_end),
                                        'is_reasonable': is_reasonable
                                    },
                                    'conflict_with': conflict_event,
                                    'note': 'Short event - might be movable'
                                })
                        
                        current += timedelta(minutes=30)
                        
                except ValueError:
                    continue
                    
        else:
            # Original loop for days_ahead
            current = start_date
            
            while current < end_date:
                # Check exclusions
                if current.weekday() in excluded_days:
                    current += timedelta(days=1)
                    current = current.replace(hour=9, minute=0)
                    continue
                    
                current_date_str = current.strftime('%Y-%m-%d')
                if current_date_str in excluded_dates:
                    current += timedelta(days=1)
                    current = current.replace(hour=9, minute=0)
                    continue

                # Skip weekends (unless explicitly allowed - but keeping default behavior for now + user exclusions)
                if current.weekday() >= 5:
                    current += timedelta(days=1)
                    current = current.replace(hour=9, minute=0)
                    continue
                
                # Skip outside working hours (9 AM - 6 PM in the requested timezone)
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
                    # Calculate user time and reasonableness
                    user_start = current.astimezone(user_tz)
                    user_end = slot_end.astimezone(user_tz)
                    
                    # Reasonable hours: 7 AM to 10 PM
                    is_reasonable = 7 <= user_start.hour < 22
                    
                    available_slots.append({
                        'target_slot': (current, slot_end),
                        'user_slot': (user_start, user_end),
                        'is_reasonable': is_reasonable
                    })
                else:
                    # Check if the conflicting event might be movable
                    # (e.g., not an all-day event, not too long)
                    conflict_duration = conflict_event[1] - conflict_event[0]
                    if conflict_duration < timedelta(hours=2):  # Short events might be movable
                        user_start = current.astimezone(user_tz)
                        user_end = slot_end.astimezone(user_tz)
                        is_reasonable = 7 <= user_start.hour < 22
                        
                        conflict_slots.append({
                            'slot': {
                                'target_slot': (current, slot_end),
                                'user_slot': (user_start, user_end),
                                'is_reasonable': is_reasonable
                            },
                            'conflict_with': conflict_event,
                            'note': 'Short event - might be movable'
                        })
                
                # Move to next potential slot (30-minute increments)
                current += timedelta(minutes=30)
        
        # Add conflict resolution suggestions
        # (Keep existing logic, but ensure it handles the new slot structure if needed)
        # The existing logic uses conflict_slots which we populated correctly above.
        
        conflict_resolutions = []
        if conflict_slots:
            # Suggest alternative times near conflicts
            for conflict_info in conflict_slots[:3]:
                conflict_start, conflict_end = conflict_info['conflict_with']
                slot_data = conflict_info['slot']
                slot_start, slot_end = slot_data['target_slot']
                
                # Suggest time before conflict
                before_suggestion = conflict_start - duration
                # Check if before_suggestion is within working hours/days?
                # For simplicity, just check hours
                if before_suggestion >= start_date and before_suggestion.hour >= 9 and before_suggestion.hour < 18:
                    user_before = before_suggestion.astimezone(user_tz)
                    conflict_resolutions.append({
                        'type': 'before_conflict',
                        'suggested_time': {
                            'target_slot': (before_suggestion, before_suggestion + duration),
                            'user_slot': (user_before, user_before + duration),
                            'is_reasonable': 7 <= user_before.hour < 22
                        },
                        'conflict_with': conflict_info['conflict_with'],
                        'note': f"Schedule before {conflict_start.strftime('%H:%M')} to avoid conflict"
                    })
                
                # Suggest time after conflict
                after_suggestion = conflict_end
                if after_suggestion + duration <= end_date and after_suggestion.hour >= 9 and after_suggestion.hour < 18:
                    user_after = after_suggestion.astimezone(user_tz)
                    conflict_resolutions.append({
                        'type': 'after_conflict',
                        'suggested_time': {
                            'target_slot': (after_suggestion, after_suggestion + duration),
                            'user_slot': (user_after, user_after + duration),
                            'is_reasonable': 7 <= user_after.hour < 22
                        },
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

