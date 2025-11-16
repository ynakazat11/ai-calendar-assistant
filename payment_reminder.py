"""
Payment reminder system for recurring payments.
"""
from datetime import datetime, timedelta
from calendar_manager import CalendarManager
import config


class PaymentReminder:
    """Manages payment reminders."""
    
    def __init__(self, calendar_manager=None):
        self.calendar = calendar_manager
        self.payment_config = config.PAYMENT_REMINDERS
    
    def check_payment_reminders(self, current_date=None):
        """
        Check if any payment reminders are due.
        
        Args:
            current_date: datetime object (default: today)
        
        Returns:
            List of payment reminders that are due
        """
        if current_date is None:
            current_date = datetime.now()
        
        reminders = []
        
        for payment_type, config_data in self.payment_config.items():
            reminder_day = config_data['day_of_month']
            current_day = current_date.day
            
            # Check if today is the reminder day
            if current_day == reminder_day:
                reminders.append({
                    'type': payment_type,
                    'description': config_data['description'],
                    'due_date': current_date.date(),
                    'status': 'due'
                })
            # Check if reminder day has passed this month (overdue)
            elif current_day > reminder_day:
                # Check if we've already created a reminder this month
                # (This is a simple check - in production, you'd track sent reminders)
                reminders.append({
                    'type': payment_type,
                    'description': config_data['description'],
                    'due_date': current_date.replace(day=reminder_day).date(),
                    'status': 'overdue'
                })
        
        return reminders
    
    def get_upcoming_reminders(self, days_ahead=7):
        """
        Get payment reminders coming up in the next N days.
        
        Args:
            days_ahead: Number of days to look ahead
        
        Returns:
            List of upcoming payment reminders
        """
        reminders = []
        current_date = datetime.now()
        
        for day_offset in range(days_ahead):
            check_date = current_date + timedelta(days=day_offset)
            
            for payment_type, config_data in self.payment_config.items():
                reminder_day = config_data['day_of_month']
                
                if check_date.day == reminder_day:
                    reminders.append({
                        'type': payment_type,
                        'description': config_data['description'],
                        'due_date': check_date.date(),
                        'status': 'upcoming'
                    })
        
        return reminders
    
    def get_reminders_summary(self):
        """
        Get a formatted summary of payment reminders.
        
        Returns:
            Formatted string with reminder summary
        """
        due_reminders = self.check_payment_reminders()
        upcoming_reminders = self.get_upcoming_reminders()
        
        summary = "Payment Reminders:\n\n"
        
        if due_reminders:
            summary += "🔔 DUE NOW:\n"
            for reminder in due_reminders:
                status_icon = '🔴' if reminder['status'] == 'overdue' else '🟡'
                summary += f"  {status_icon} {reminder['description']} - {reminder['type'].title()}\n"
            summary += "\n"
        
        if upcoming_reminders:
            summary += "📅 UPCOMING:\n"
            for reminder in upcoming_reminders:
                summary += f"  🟢 {reminder['description']} - {reminder['type'].title()} "
                summary += f"(Due: {reminder['due_date'].strftime('%Y-%m-%d')})\n"
        
        if not due_reminders and not upcoming_reminders:
            summary += "No payment reminders at this time.\n"
        
        return summary

