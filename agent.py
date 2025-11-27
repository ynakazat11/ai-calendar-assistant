"""
Main AI Agent interface for schedule, task, and payment management.
"""
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from calendar_manager import CalendarManager
from task_generator import TaskGenerator
from payment_reminder import PaymentReminder
from intelligent_scheduler import IntelligentScheduler
from calendar_monitor import CalendarMonitor
import config


class ScheduleAgent:
    """Main AI Agent for managing schedule, tasks, and payments."""
    
    def __init__(self):
        print("Initializing Schedule Agent...")
        self.calendar = CalendarManager()
        self.task_generator = TaskGenerator(self.calendar)
        self.payment_reminder = PaymentReminder(self.calendar)
        try:
            self.intelligent_scheduler = IntelligentScheduler(self.calendar)
            print("Intelligent scheduler initialized!")
            # Initialize calendar monitor if scheduler is available
            self.calendar_monitor = CalendarMonitor(self.calendar, self.intelligent_scheduler)
            print("Calendar monitor initialized!")
        except Exception as e:
            print(f"Warning: Intelligent scheduler not available: {e}")
            self.intelligent_scheduler = None
            self.calendar_monitor = None
        print("Agent initialized successfully!")
    
    def resolve_timezone(self, timezone_input: str) -> str:
        """
        Resolve a timezone input (e.g., 'India', 'Tokyo') to an IANA timezone string.
        
        Args:
            timezone_input: User input for timezone
            
        Returns:
            IANA timezone string (e.g., 'Asia/Kolkata') or 'UTC' if unresolved
        """
        if not timezone_input or timezone_input.upper() == 'UTC':
            return 'UTC'
            
        # Try direct ZoneInfo resolution first
        try:
            ZoneInfo(timezone_input)
            return timezone_input
        except Exception:
            pass
            
        # Common aliases
        aliases = {
            'india': 'Asia/Kolkata',
            'ist': 'Asia/Kolkata',
            'japan': 'Asia/Tokyo',
            'jst': 'Asia/Tokyo',
            'uk': 'Europe/London',
            'london': 'Europe/London',
            'ny': 'America/New_York',
            'nyc': 'America/New_York',
            'sf': 'America/Los_Angeles',
            'california': 'America/Los_Angeles',
        }
        
        if timezone_input.lower() in aliases:
            return aliases[timezone_input.lower()]
            
        # Use LLM if available
        if self.intelligent_scheduler:
            try:
                print(f"Resolving timezone for '{timezone_input}'...")
                response = self.intelligent_scheduler.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a timezone resolver. Return ONLY the IANA timezone string for the given location or abbreviation. If unknown, return 'UTC'."},
                        {"role": "user", "content": f"Timezone for: {timezone_input}"}
                    ],
                    temperature=0
                )
                resolved = response.choices[0].message.content.strip()
                # Verify it's valid
                try:
                    ZoneInfo(resolved)
                    print(f"Resolved '{timezone_input}' to '{resolved}'")
                    return resolved
                except Exception:
                    print(f"LLM returned invalid timezone: {resolved}")
            except Exception as e:
                print(f"Error resolving timezone with LLM: {e}")
        
        print(f"Could not resolve timezone '{timezone_input}', defaulting to UTC")
        return 'UTC'

    def schedule_meeting(self, duration_minutes=60, days_ahead=14, timezone_str='UTC', 
                        excluded_dates=None, excluded_days=None, specific_dates=None):
        """
        Suggest time slots for scheduling a meeting.
        
        Args:
            duration_minutes: Duration of the meeting
            days_ahead: Number of days to look ahead
            timezone_str: Target timezone
            excluded_dates: Dates to exclude
            excluded_days: Days of week to exclude
            specific_dates: Specific dates to include
        
        Returns:
            Dictionary with available and conflict-possible slots
        """
        if specific_dates:
            print(f"\nLooking for {duration_minutes}-minute time slots on specific dates: {', '.join(specific_dates)} ({timezone_str})...")
        else:
            print(f"\nLooking for {duration_minutes}-minute time slots in the next {days_ahead} days ({timezone_str})...")
        
        # Detect user's system timezone
        user_timezone = 'UTC'
        try:
            # Try to get system local timezone
            import time
            system_tz = str(datetime.now().astimezone().tzinfo)
            # Resolve it to ensure it's a valid IANA string (e.g. PST -> America/Los_Angeles)
            user_timezone = self.resolve_timezone(system_tz)
        except Exception:
            pass
            
        slots = self.calendar.suggest_time_slots(
            duration_minutes=duration_minutes,
            days_ahead=days_ahead,
            timezone_str=timezone_str,
            excluded_dates=excluded_dates,
            excluded_days=excluded_days,
            user_timezone=user_timezone,
            specific_dates=specific_dates
        )
        
        return slots, user_timezone
    
    def get_tasks(self, months_ahead=None):
        """
        Get to-do tasks based on calendar events.
        
        Args:
            months_ahead: Number of months to look ahead (default: from config)
        
        Returns:
            List of tasks
        """
        if months_ahead is None:
            months_ahead = config.TASK_LOOKAHEAD_MONTHS
        
        print(f"\nGenerating tasks for the next {months_ahead} months...")
        tasks = self.task_generator.generate_tasks(months_ahead=months_ahead)
        return tasks
    
    def get_payment_reminders(self):
        """
        Get payment reminders.
        
        Returns:
            List of payment reminders
        """
        return self.payment_reminder.check_payment_reminders()
    
    def print_schedule_suggestions(self, duration_minutes=60, days_ahead=14, timezone_str='UTC', 
                                 excluded_dates=None, excluded_days=None, specific_dates=None):
        """Print formatted schedule suggestions."""
        slots, user_timezone = self.schedule_meeting(duration_minutes, days_ahead, timezone_str, excluded_dates, excluded_days, specific_dates)
        
        print("\n" + "="*60)
        print(f"SCHEDULE SUGGESTIONS (Your TZ: {user_timezone})")
        print("="*60)
        
        if specific_dates:
            print(f"📅 Showing slots for specific dates: {', '.join(specific_dates)}")
        
        if slots['available']:
            print("\n✅ AVAILABLE SLOTS (No conflicts):")
            
            # Check if any reasonable slots exist
            reasonable_slots = [s for s in slots['available'] if s['is_reasonable']]
            unreasonable_slots = [s for s in slots['available'] if not s['is_reasonable']]
            
            if not reasonable_slots and unreasonable_slots:
                print("⚠️  CAUTION: No slots found within reasonable waking hours (7 AM - 10 PM) in your timezone.")
                print("   Here are the available slots anyway:")
            
            for i, slot_data in enumerate(slots['available'], 1):
                user_start, user_end = slot_data['user_slot']
                target_start, target_end = slot_data['target_slot']
                is_reasonable = slot_data['is_reasonable']
                
                warning = "" if is_reasonable else " ⚠️  (Late/Early)"
                
                print(f"  {i}. {user_start.strftime('%Y-%m-%d %H:%M')} - {user_end.strftime('%H:%M')} {user_timezone}{warning}")
                print(f"     (Target: {target_start.strftime('%H:%M')} - {target_end.strftime('%H:%M')} {timezone_str})")
        
        if slots['conflict_possible']:
            print("\n⚠️  SLOTS WITH POTENTIAL CONFLICTS (Movable events):")
            for i, slot_info in enumerate(slots['conflict_possible'], 1):
                slot_data = slot_info['slot']
                user_start, user_end = slot_data['user_slot']
                target_start, target_end = slot_data['target_slot']
                conflict_start, conflict_end = slot_info['conflict_with']
                
                print(f"  {i}. {user_start.strftime('%Y-%m-%d %H:%M')} - {user_end.strftime('%H:%M')} {user_timezone}")
                print(f"     (Target: {target_start.strftime('%H:%M')} - {target_end.strftime('%H:%M')} {timezone_str})")
                print(f"     ⚠️  Conflicts with: {conflict_start.strftime('%Y-%m-%d %H:%M')} - {conflict_end.strftime('%H:%M')}")
                print(f"     💡 {slot_info['note']}")
        
        if not slots['available'] and not slots['conflict_possible']:
            print("\n❌ No suitable time slots found in the specified period.")
            print("   Try increasing the days_ahead parameter or reducing duration.")
    
    def print_tasks(self, months_ahead=None):
        """Print formatted task list."""
        summary = self.task_generator.get_tasks_summary(months_ahead or config.TASK_LOOKAHEAD_MONTHS)
        print("\n" + "="*60)
        print("TO-DO TASKS")
        print("="*60)
        print(summary)
    
    def print_payment_reminders(self):
        """Print formatted payment reminders."""
        summary = self.payment_reminder.get_reminders_summary()
        print("\n" + "="*60)
        print("PAYMENT REMINDERS")
        print("="*60)
        print(summary)
    
    def schedule_intelligent(self, request: str, days_ahead: int = 14, 
                           auto_create_prep: bool = False):
        """
        Intelligently schedule a meeting with prep planning.
        
        Args:
            request: Natural language scheduling request
            days_ahead: Number of days to look ahead
            auto_create_prep: Whether to automatically create prep events
        """
        if not self.intelligent_scheduler:
            print("❌ Intelligent scheduler not available. Please set OPENAI_API_KEY in .env file.")
            return
        
        result = self.intelligent_scheduler.schedule_intelligent(
            request, days_ahead, auto_create_prep
        )
        
        self._print_intelligent_schedule_result(result)
        
        # Ask user if they want to create prep events
        if not auto_create_prep and result['suggestions']['suggestions']:
            print("\n" + "="*60)
            response = input("Would you like to create prep events for one of these suggestions? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                self._create_prep_events_interactive(result)
    
    def _print_intelligent_schedule_result(self, result: dict):
        """Print formatted intelligent schedule results."""
        parsed = result['parsed_request']
        prep_plan = result['prep_plan']
        suggestions = result['suggestions']['suggestions']
        
        print("\n" + "="*60)
        print("INTELLIGENT SCHEDULE SUGGESTIONS")
        print("="*60)
        
        print(f"\n📋 PREPARATION PLAN")
        print(f"   Total prep time needed: {prep_plan.get('total_prep_hours', 0)} hours")
        print(f"   Number of prep tasks: {len(prep_plan.get('prep_tasks', []))}")
        
        if prep_plan.get('prep_tasks'):
            print("\n   Prep Tasks:")
            for i, task in enumerate(prep_plan.get('prep_tasks', []), 1):
                print(f"   {i}. {task.get('task', 'N/A')} ({task.get('duration_hours', 0)} hours)")
                if task.get('description'):
                    print(f"      {task.get('description', '')[:80]}...")
        
        if prep_plan.get('key_talking_points'):
            print("\n   Key Talking Points:")
            for point in prep_plan.get('key_talking_points', [])[:5]:
                print(f"   • {point}")
        
        print(f"\n📅 SCHEDULE SUGGESTIONS")
        
        if not suggestions:
            print("   ❌ No suitable time slots found.")
            return
        
        for i, suggestion in enumerate(suggestions, 1):
            event_start, event_end = suggestion['event_slot']
            print(f"\n   Option {i}:")
            print(f"   📍 Event: {event_start.strftime('%Y-%m-%d %H:%M')} - {event_end.strftime('%H:%M')}")
            print(f"   ⏱️  Prep time: {suggestion['total_prep_hours']} hours")
            
            prep_slots = suggestion['prep_slots']
            if prep_slots:
                print(f"   📚 Prep schedule:")
                for prep_item in prep_slots:
                    task = prep_item['task']
                    slot = prep_item.get('slot')
                    if slot:
                        prep_start, prep_end = slot
                        print(f"      • {task.get('task', 'Prep')}: {prep_start.strftime('%Y-%m-%d %H:%M')} - {prep_end.strftime('%H:%M')}")
                    else:
                        suggested = prep_item.get('suggested_time', 'TBD')
                        print(f"      • {task.get('task', 'Prep')}: {suggested} (flexible)")
    
    def _create_prep_events_interactive(self, result: dict):
        """Interactive prep event creation."""
        suggestions = result['suggestions']['suggestions']
        
        if not suggestions:
            print("No suggestions available.")
            return
        
        print("\nSelect which option to create prep events for:")
        for i, suggestion in enumerate(suggestions, 1):
            event_start, _ = suggestion['event_slot']
            print(f"  {i}. Event on {event_start.strftime('%Y-%m-%d %H:%M')}")
        
        try:
            choice = int(input("Enter option number: ").strip())
            if 1 <= choice <= len(suggestions):
                selected = suggestions[choice - 1]
                
                # Create prep events
                created = self.intelligent_scheduler.create_prep_events(
                    selected,
                    result['parsed_request'],
                    result['gathered_info'],
                    result['prep_plan']
                )
                
                if created:
                    print(f"\n✅ Created {len(created)} prep event(s) in your calendar!")
                else:
                    print("\n❌ Failed to create prep events.")
            else:
                print("Invalid option.")
        except ValueError:
            print("Invalid input.")
        except Exception as e:
            print(f"Error: {e}")
    
    def check_new_events(self, days_ahead: int = 30, auto_create: bool = True):
        """
        Check for new events in calendar and create prep plans.
        
        Args:
            days_ahead: Number of days ahead to check
            auto_create: Whether to automatically create prep events
        """
        if not self.calendar_monitor:
            print("❌ Calendar monitor not available. Please set OPENAI_API_KEY in .env file.")
            return
        
        processed = self.calendar_monitor.check_new_events(days_ahead, auto_create)
        
        if processed:
            print(f"\n✅ Processed {len(processed)} event(s) with prep planning.")
        else:
            print("\n✅ No new events to process.")
    
    def monitor_continuously(self, check_interval_minutes: int = 60):
        """
        Continuously monitor calendar for new events.
        
        Args:
            check_interval_minutes: Minutes between checks
        """
        if not self.calendar_monitor:
            print("❌ Calendar monitor not available. Please set OPENAI_API_KEY in .env file.")
            return
        
        self.calendar_monitor.monitor_continuously(check_interval_minutes)
    
    def run_interactive(self):
        """Run interactive command-line interface."""
        print("\n" + "="*60)
        print("SCHEDULE AGENT - Interactive Mode")
        print("="*60)
        print("\nCommands:")
        print("  1. schedule [duration] [in days] [timezone/country] - Get schedule suggestions")
        print("     Options: date=YYYY-MM-DD (specific date), ex_date=YYYY-MM-DD (exclude date), ex_day=0-6 (exclude day)")
        print("     Example: schedule 60 14 India ex_day=6")
        print("     Example: schedule 60 date=2025-12-25 date=2025-12-26")
        print("  2. smart \"[request]\" [in days] [timezone/country] - Intelligent scheduling with prep planning")
        print("     Example: smart \"30 minutes interview with exec John at Company X\" 14")
        print("  3. check [in days] [timezone/country] - Check for new events needing prep (default: 30 days)")
        print("  4. monitor [minutes] [timezone/country] - Continuously monitor calendar (default: 60 min)")
        print("  5. tasks [months] [timezone/country] - Get to-do tasks")
        print("  6. payments - Get payment reminders")
        print("  7. all - Show everything")
        print("  8. help - Show this help")
        print("  9. quit - Exit")
        print()
        
        while True:
            try:
                command = input("Agent> ").strip().lower()
                
                if command == 'quit' or command == 'exit':
                    print("Goodbye!")
                    break
                elif command == 'help':
                    print("\nCommands:")
                    print("  schedule [duration] [days] [timezone] [ex_date=YYYY-MM-DD] [ex_day=0-6] - Get schedule suggestions")
                    print("    Example: schedule 60 14 India (60 mins, 14 days, India time)")
                    print("    Example: schedule 60 India (60 mins, default 14 days, India time)")
                    print("  smart \"[request]\" [days] - Intelligent scheduling with prep planning")
                    print("    Example: smart \"30 minutes interview with exec John at Company X\" 14")
                    print("  check [days] - Check for new events needing prep (default: 30 days)")
                    print("  monitor [minutes] - Continuously monitor calendar (default: 60 min)")
                    print("  tasks [months] - Get to-do tasks (default: 3 months)")
                    print("  payments - Get payment reminders")
                    print("  all - Show schedule, tasks, and payments")
                    print("  quit - Exit")
                elif command.startswith('schedule'):
                    parts = command.split()
                    duration = int(parts[1]) if len(parts) > 1 else 60
                    days = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 14
                    
                    # Flexible timezone parsing
                    # If 3rd arg is not a digit, it might be a timezone
                    timezone_input = 'UTC'
                    if len(parts) > 2 and not parts[2].isdigit():
                         # schedule 60 India
                         timezone_input = parts[2]
                    elif len(parts) > 3 and not parts[3].startswith('tz=') and not parts[3].startswith('ex_'):
                         # schedule 60 14 India
                         timezone_input = parts[3]
                    
                    # Parse optional args (tz=..., ex_date=...)
                    excluded_dates = []
                    excluded_days = []
                    specific_dates = []
                    
                    for part in parts[1:]:
                        if part.startswith('tz='):
                            timezone_input = part.split('=')[1]
                        elif part.startswith('ex_date='):
                            excluded_dates.append(part.split('=')[1])
                        elif part.startswith('ex_day='):
                            try:
                                excluded_days.append(int(part.split('=')[1]))
                            except ValueError:
                                pass
                        elif part.startswith('date='):
                            specific_dates.append(part.split('=')[1])
                    
                    timezone_str = self.resolve_timezone(timezone_input)
                    self.print_schedule_suggestions(duration, days, timezone_str, excluded_dates, excluded_days, specific_dates)
                elif command.startswith('smart'):
                    # Parse smart command: smart "request" [days]
                    parts = command.split('"', 2)
                    if len(parts) >= 3:
                        request = parts[1]
                        days_part = parts[2].strip() if len(parts) > 2 else ''
                        days = int(days_part.split()[0]) if days_part and days_part.split()[0].isdigit() else 14
                    else:
                        # Fallback: try to parse without quotes
                        parts = command.split(None, 1)
                        if len(parts) > 1:
                            request = parts[1]
                            # Try to extract days if present
                            request_parts = request.rsplit(None, 1)
                            if len(request_parts) > 1 and request_parts[-1].isdigit():
                                days = int(request_parts[-1])
                                request = ' '.join(request_parts[:-1])
                            else:
                                days = 14
                        else:
                            print("Please provide a scheduling request. Example: smart \"30 minutes interview with John\"")
                            continue
                    self.schedule_intelligent(request, days)
                elif command.startswith('check'):
                    parts = command.split()
                    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 30
                    self.check_new_events(days, auto_create=True)
                elif command.startswith('monitor'):
                    parts = command.split()
                    minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 60
                    self.monitor_continuously(minutes)
                elif command.startswith('tasks'):
                    parts = command.split()
                    months = int(parts[1]) if len(parts) > 1 else None
                    self.print_tasks(months)
                elif command == 'payments':
                    self.print_payment_reminders()
                elif command == 'all':
                    self.print_schedule_suggestions()
                    self.print_tasks()
                    self.print_payment_reminders()
                else:
                    print("Unknown command. Type 'help' for available commands.")
                
                print()
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point."""
    import sys
    
    agent = ScheduleAgent()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'schedule':
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            days = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 14
            
            # Flexible timezone parsing
            timezone_input = 'UTC'
            if len(sys.argv) > 3 and not sys.argv[3].isdigit():
                 timezone_input = sys.argv[3]
            elif len(sys.argv) > 4 and not sys.argv[4].startswith('tz=') and not sys.argv[4].startswith('ex_'):
                 timezone_input = sys.argv[4]
            
            # Parse optional args
            excluded_dates = []
            excluded_days = []
            specific_dates = []
            
            for arg in sys.argv[2:]:
                if arg.startswith('tz='):
                    timezone_input = arg.split('=')[1]
                elif arg.startswith('ex_date='):
                    excluded_dates.append(arg.split('=')[1])
                elif arg.startswith('ex_day='):
                    try:
                        excluded_days.append(int(arg.split('=')[1]))
                    except ValueError:
                        pass
                elif arg.startswith('date='):
                    specific_dates.append(arg.split('=')[1])
            
            timezone_str = agent.resolve_timezone(timezone_input)
            agent.print_schedule_suggestions(duration, days, timezone_str, excluded_dates, excluded_days, specific_dates)
        elif command == 'smart':
            if len(sys.argv) < 3:
                print("Usage: python agent.py smart \"[request]\" [days]")
                print("Example: python agent.py smart \"30 minutes interview with exec John at Company X\" 14")
            else:
                request = sys.argv[2]
                days = int(sys.argv[3]) if len(sys.argv) > 3 else 14
                agent.schedule_intelligent(request, days)
        elif command == 'check':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            agent.check_new_events(days, auto_create=True)
        elif command == 'monitor':
            minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            agent.monitor_continuously(minutes)
        elif command == 'tasks':
            months = int(sys.argv[2]) if len(sys.argv) > 2 else None
            agent.print_tasks(months)
        elif command == 'payments':
            agent.print_payment_reminders()
        elif command == 'all':
            agent.print_schedule_suggestions()
            agent.print_tasks()
            agent.print_payment_reminders()
        else:
            print("Unknown command. Use: schedule, tasks, payments, all, or interactive")
    else:
        # Run in interactive mode
        agent.run_interactive()


if __name__ == '__main__':
    main()

