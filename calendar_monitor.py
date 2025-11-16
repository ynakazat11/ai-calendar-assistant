"""
Calendar monitor that automatically detects new events and triggers prep planning.
Prevents duplicate prep events by tracking processed events.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from calendar_manager import CalendarManager
from intelligent_scheduler import IntelligentScheduler


class CalendarMonitor:
    """Monitors Google Calendar for new events and triggers prep planning."""
    
    def __init__(self, calendar_manager: CalendarManager, intelligent_scheduler: IntelligentScheduler):
        self.calendar = calendar_manager
        self.scheduler = intelligent_scheduler
        self.processed_events_file = 'processed_events.json'
        self.processed_events = self._load_processed_events()
        
        # Keywords that indicate events needing prep
        self.prep_keywords = {
            'interview': ['interview', 'interviews', 'interviewing'],
            'tournament': ['tournament', 'tournaments', 'competition', 'competitions', 'contest', 'contests'],
            'presentation': ['presentation', 'presentations', 'presenting', 'demo', 'demos'],
            'meeting': ['meeting with', 'meeting at', 'call with'],
            'event': ['event', 'events', 'conference', 'conferences']
        }
    
    def _load_processed_events(self) -> Set[str]:
        """Load set of processed event IDs from file."""
        if os.path.exists(self.processed_events_file):
            try:
                with open(self.processed_events_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('event_ids', []))
            except Exception as e:
                print(f"Warning: Could not load processed events: {e}")
                return set()
        return set()
    
    def _save_processed_events(self):
        """Save processed event IDs to file."""
        try:
            data = {
                'event_ids': list(self.processed_events),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.processed_events_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save processed events: {e}")
    
    def _needs_prep(self, event: Dict) -> bool:
        """
        Determine if an event needs prep planning.
        
        Args:
            event: Calendar event dictionary
        
        Returns:
            True if event needs prep, False otherwise
        """
        summary = event.get('summary', '').lower()
        description = event.get('description', '').lower()
        full_text = f"{summary} {description}"
        
        # Check if event already has prep (marked with special tag)
        if '[PREP_PLANNED]' in description or '[PREP_PLANNED]' in summary:
            return False
        
        # Check for prep keywords
        for category, keywords in self.prep_keywords.items():
            if any(keyword in full_text for keyword in keywords):
                # Additional check: skip if it's a recurring event (unless it's a tournament/competition)
                if 'recurrence' in event and category not in ['tournament', 'competition']:
                    continue
                return True
        
        return False
    
    def _extract_event_info(self, event: Dict) -> Dict:
        """
        Extract information from calendar event for prep planning.
        
        Args:
            event: Calendar event dictionary
        
        Returns:
            Dictionary with event information
        """
        summary = event.get('summary', '')
        description = event.get('description', '')
        start = event.get('start', {})
        
        # Get event start time
        start_time_str = start.get('dateTime') or start.get('date')
        if start_time_str:
            try:
                if 'T' in start_time_str:
                    event_start = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                else:
                    event_start = datetime.fromisoformat(start_time_str)
            except:
                event_start = None
        else:
            event_start = None
        
        # Get event end time
        end = event.get('end', {})
        end_time_str = end.get('dateTime') or end.get('date')
        if end_time_str:
            try:
                if 'T' in end_time_str:
                    event_end = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                else:
                    event_end = datetime.fromisoformat(end_time_str)
            except:
                event_end = None
        else:
            event_end = None
        
        # Calculate duration
        duration_minutes = 30  # default
        if event_start and event_end:
            duration = event_end - event_start
            duration_minutes = int(duration.total_seconds() / 60)
        
        # Create a request string for the intelligent scheduler
        request = summary
        if description:
            request += f" - {description[:100]}"  # Limit description length
        
        return {
            'event_id': event.get('id'),
            'summary': summary,
            'description': description,
            'start_time': event_start,
            'end_time': event_end,
            'duration_minutes': duration_minutes,
            'request': request,
            'original_event': event
        }
    
    def _has_existing_prep_events(self, event_info: Dict) -> bool:
        """
        Check if prep events already exist for this event.
        
        Args:
            event_info: Event information dictionary
        
        Returns:
            True if prep events exist, False otherwise
        """
        event_start = event_info['start_time']
        if not event_start:
            return False
        
        # Look for prep events in the 3 days before the event
        search_start = event_start - timedelta(days=3)
        search_end = event_start - timedelta(hours=1)  # Prep should be before the event
        
        events = self.calendar.get_events(search_start, search_end)
        
        # Check if any events have "Prep:" in the title and match the event summary
        event_summary = event_info['summary']
        for event in events:
            event_title = event.get('summary', '')
            if 'Prep:' in event_title and event_summary.lower() in event_title.lower():
                return True
        
        return False
    
    def _mark_event_processed(self, event_id: str):
        """Mark an event as processed."""
        self.processed_events.add(event_id)
        self._save_processed_events()
    
    def check_new_events(self, days_ahead: int = 30, auto_create: bool = True) -> List[Dict]:
        """
        Check for new events that need prep planning.
        
        Args:
            days_ahead: Number of days ahead to check
            auto_create: Whether to automatically create prep events
        
        Returns:
            List of events that were processed
        """
        print(f"\n🔍 Checking for new events in the next {days_ahead} days...")
        
        # Get events from now to days_ahead
        start_time = datetime.now()
        end_time = start_time + timedelta(days=days_ahead)
        
        events = self.calendar.get_events(start_time, end_time)
        
        # Filter for events that need prep and haven't been processed
        new_events_needing_prep = []
        
        for event in events:
            event_id = event.get('id')
            
            # Skip if already processed
            if event_id in self.processed_events:
                continue
            
            # Check if event needs prep
            if self._needs_prep(event):
                event_info = self._extract_event_info(event)
                
                # Check if prep events already exist
                if self._has_existing_prep_events(event_info):
                    print(f"   ⏭️  Skipping {event_info['summary']} - prep events already exist")
                    self._mark_event_processed(event_id)
                    continue
                
                new_events_needing_prep.append(event_info)
        
        if not new_events_needing_prep:
            print("   ✅ No new events needing prep found.")
            return []
        
        print(f"   📋 Found {len(new_events_needing_prep)} new event(s) needing prep:")
        for event_info in new_events_needing_prep:
            print(f"      • {event_info['summary']}")
        
        # Process each event
        processed = []
        for event_info in new_events_needing_prep:
            try:
                result = self._process_event_for_prep(event_info, auto_create)
                if result:
                    processed.append(result)
                    self._mark_event_processed(event_info['event_id'])
            except Exception as e:
                print(f"   ❌ Error processing {event_info['summary']}: {e}")
        
        return processed
    
    def _process_event_for_prep(self, event_info: Dict, auto_create: bool = True) -> Optional[Dict]:
        """
        Process an event and create prep plan.
        
        Args:
            event_info: Event information dictionary
            auto_create: Whether to automatically create prep events
        
        Returns:
            Dictionary with processing results
        """
        print(f"\n   🧠 Processing: {event_info['summary']}")
        
        # Use intelligent scheduler to plan prep
        request = event_info['request']
        event_start = event_info['start_time']
        
        if not event_start:
            print(f"      ⚠️  Cannot process: event has no start time")
            return None
        
        # Calculate days ahead based on event date
        days_until_event = (event_start - datetime.now()).days
        if days_until_event < 0:
            print(f"      ⚠️  Skipping: event is in the past")
            return None
        
        days_ahead = min(days_until_event + 1, 14)  # Look up to 14 days ahead
        
        # Get prep plan using the intelligent scheduler
        result = self.scheduler.schedule_intelligent(request, days_ahead, auto_create=False)
        
        if not result or not result.get('prep_plan'):
            print(f"      ⚠️  No prep plan generated")
            return None
        
        prep_plan = result['prep_plan']
        prep_tasks = prep_plan.get('prep_tasks', [])
        
        if not prep_tasks:
            print(f"      ⚠️  No prep tasks identified")
            return None
        
        # Create a custom suggestion that matches the actual event time
        # We'll schedule prep events before the actual event
        event_slot = (event_start, event_info['end_time'] or event_start + timedelta(minutes=event_info['duration_minutes']))
        
        # Find prep slots before the event
        prep_slots = []
        prep_start_date = event_start - timedelta(days=3)
        prep_end_date = event_start - timedelta(days=1)
        
        current_prep_time = prep_start_date
        for task in prep_tasks:
            task_duration = int(task.get('duration_hours', 1) * 60)  # Convert to minutes
            prep_slot = self.scheduler._find_prep_slot(
                current_prep_time,
                prep_end_date,
                task_duration
            )
            
            if prep_slot:
                prep_slots.append({
                    'task': task,
                    'slot': prep_slot
                })
                current_prep_time = prep_slot[1] + timedelta(hours=1)
            else:
                # If we can't find a slot, suggest a flexible time
                prep_slots.append({
                    'task': task,
                    'slot': None,
                    'suggested_time': f"{prep_start_date.strftime('%Y-%m-%d')} (flexible)"
                })
        
        # Create custom suggestion structure
        custom_suggestion = {
            'event_slot': event_slot,
            'prep_slots': prep_slots,
            'total_prep_hours': prep_plan.get('total_prep_hours', 0)
        }
        
        # Create prep events
        if auto_create:
            created_events = self.scheduler.create_prep_events(
                custom_suggestion,
                result['parsed_request'],
                result['gathered_info'],
                prep_plan
            )
            
            if created_events:
                print(f"      ✅ Created {len(created_events)} prep event(s)")
                
                return {
                    'event_id': event_info['event_id'],
                    'summary': event_info['summary'],
                    'prep_events_created': len(created_events),
                    'prep_plan': prep_plan
                }
            else:
                print(f"      ❌ Failed to create prep events")
        else:
            print(f"      📋 Prep plan ready (auto_create=False)")
            return {
                'event_id': event_info['event_id'],
                'summary': event_info['summary'],
                'prep_plan': prep_plan
            }
        
        return None
    
    def _mark_original_event_with_prep_tag(self, event: Dict):
        """
        Mark the original event with a prep tag to prevent reprocessing.
        Note: This requires write access to update the event.
        """
        # We'll mark it in our tracking system instead of modifying the calendar event
        # to avoid needing write permissions and to keep the calendar clean
        pass  # Already handled by processed_events tracking
    
    def monitor_continuously(self, check_interval_minutes: int = 60):
        """
        Continuously monitor calendar for new events.
        This runs in a loop checking every N minutes.
        
        Args:
            check_interval_minutes: Minutes between checks
        """
        import time
        
        print(f"\n🔄 Starting continuous monitoring (checking every {check_interval_minutes} minutes)")
        print("   Press Ctrl+C to stop")
        
        try:
            while True:
                self.check_new_events(days_ahead=30, auto_create=True)
                print(f"\n   ⏰ Next check in {check_interval_minutes} minutes...")
                time.sleep(check_interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n\n✅ Monitoring stopped.")

