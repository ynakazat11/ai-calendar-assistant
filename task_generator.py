"""
Generate to-do tasks based on calendar events.
Identifies one-off and ad-hoc events that require preparation.
"""
from datetime import datetime, timedelta
from calendar_manager import CalendarManager
import re


class TaskGenerator:
    """Generates tasks based on calendar events."""
    
    def __init__(self, calendar_manager):
        self.calendar = calendar_manager
        
        # Keywords that suggest preparation tasks
        self.preparation_keywords = {
            'competition': ['register', 'registration', 'sign up', 'prepare', 'training'],
            'flight': ['book', 'booking', 'reservation', 'check-in', 'pack'],
            'meeting': ['prepare', 'agenda', 'materials', 'review'],
            'event': ['prepare', 'organize', 'arrange'],
            'deadline': ['submit', 'complete', 'review', 'finalize']
        }
    
    def analyze_event(self, event):
        """
        Analyze an event to determine if it needs preparation tasks.
        
        Args:
            event: Calendar event dictionary
        
        Returns:
            List of suggested tasks
        """
        tasks = []
        summary = event.get('summary', '').lower()
        description = event.get('description', '').lower()
        full_text = f"{summary} {description}"
        
        # Check for competition-related events
        if any(keyword in full_text for keyword in ['competition', 'contest', 'tournament']):
            event_date = self._get_event_date(event)
            if event_date:
                days_before = (event_date - datetime.now()).days
                if 0 < days_before <= 90:  # Within 3 months
                    tasks.append({
                        'task': f"Register for {event.get('summary', 'competition')}",
                        'due_date': event_date - timedelta(days=14),  # 2 weeks before
                        'priority': 'high',
                        'category': 'competition',
                        'related_event': event.get('summary')
                    })
                    tasks.append({
                        'task': f"Prepare for {event.get('summary', 'competition')}",
                        'due_date': event_date - timedelta(days=7),  # 1 week before
                        'priority': 'medium',
                        'category': 'competition',
                        'related_event': event.get('summary')
                    })
        
        # Check for travel/flight events
        if any(keyword in full_text for keyword in ['flight', 'travel', 'trip', 'airport']):
            event_date = self._get_event_date(event)
            if event_date:
                days_before = (event_date - datetime.now()).days
                if 0 < days_before <= 90:
                    tasks.append({
                        'task': f"Book flight for {event.get('summary', 'trip')}",
                        'due_date': event_date - timedelta(days=30),  # 1 month before
                        'priority': 'high',
                        'category': 'travel',
                        'related_event': event.get('summary')
                    })
                    tasks.append({
                        'task': f"Pack for {event.get('summary', 'trip')}",
                        'due_date': event_date - timedelta(days=2),
                        'priority': 'medium',
                        'category': 'travel',
                        'related_event': event.get('summary')
                    })
        
        # Check for one-off events (not recurring)
        if not self._is_recurring(event):
            event_date = self._get_event_date(event)
            if event_date:
                days_before = (event_date - datetime.now()).days
                if 0 < days_before <= 90:
                    # Generic preparation task for one-off events
                    if not any(keyword in full_text for keyword in ['meeting', 'call', 'lunch', 'dinner']):
                        tasks.append({
                            'task': f"Prepare for {event.get('summary', 'event')}",
                            'due_date': event_date - timedelta(days=3),
                            'priority': 'medium',
                            'category': 'preparation',
                            'related_event': event.get('summary')
                        })
        
        return tasks
    
    def _get_event_date(self, event):
        """Extract datetime from event."""
        start = event.get('start', {})
        date_str = start.get('dateTime') or start.get('date')
        
        if not date_str:
            return None
        
        try:
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(date_str)
        except ValueError:
            return None
    
    def _is_recurring(self, event):
        """Check if event is recurring."""
        return 'recurrence' in event
    
    def generate_tasks(self, months_ahead=3):
        """
        Generate all tasks based on calendar events for the next N months.
        
        Args:
            months_ahead: Number of months to look ahead
        
        Returns:
            List of task dictionaries
        """
        end_date = datetime.now() + timedelta(days=months_ahead * 30)
        events = self.calendar.get_events(
            start_time=datetime.now(),
            end_time=end_date
        )
        
        all_tasks = []
        for event in events:
            tasks = self.analyze_event(event)
            all_tasks.extend(tasks)
        
        # Sort by due date
        all_tasks.sort(key=lambda x: x['due_date'])
        
        return all_tasks
    
    def get_tasks_summary(self, months_ahead=3):
        """
        Get a formatted summary of tasks.
        
        Args:
            months_ahead: Number of months to look ahead
        
        Returns:
            Formatted string with task summary
        """
        tasks = self.generate_tasks(months_ahead)
        
        if not tasks:
            return "No tasks generated from your calendar events."
        
        summary = f"Generated {len(tasks)} tasks from your calendar:\n\n"
        
        current_date = None
        for task in tasks:
            task_date = task['due_date'].date()
            if current_date != task_date:
                current_date = task_date
                summary += f"\n{current_date.strftime('%Y-%m-%d (%A)')}:\n"
            
            priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '⚪')
            summary += f"  {priority_icon} {task['task']} (Category: {task['category']})\n"
            if task.get('related_event'):
                summary += f"     Related to: {task['related_event']}\n"
        
        return summary

