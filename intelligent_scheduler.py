"""
Intelligent scheduler that analyzes meeting requests, gathers information,
plans preparation, and suggests optimal scheduling times.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from duckduckgo_search import DDGS
import config


class IntelligentScheduler:
    """Intelligent scheduler with prep planning capabilities."""
    
    def __init__(self, calendar_manager):
        self.calendar = calendar_manager
        
        # Initialize OpenAI client
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in .env file.")
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Initialize web search
        self.search_client = DDGS()
    
    def parse_request(self, request: str) -> Dict:
        """
        Parse a natural language scheduling request.
        
        Args:
            request: Natural language request (e.g., "30 minutes interview with exec X at company Y")
        
        Returns:
            Dictionary with parsed information
        """
        prompt = f"""Parse the following scheduling request and extract key information.
Return a JSON object with the following fields:
- event_type: Type of event (e.g., "interview", "meeting", "call")
- duration_minutes: Duration in minutes (extract from request or default to 30)
- person_name: Name of the person (if mentioned)
- company_name: Name of the company (if mentioned)
- event_description: Brief description of the event
- additional_context: Any other relevant information

Request: "{request}"

Return only valid JSON, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that parses scheduling requests. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            import json
            parsed = json.loads(response.choices[0].message.content.strip())
            return parsed
        except Exception as e:
            print(f"Error parsing request: {e}")
            # Fallback parsing
            return self._fallback_parse(request)
    
    def _fallback_parse(self, request: str) -> Dict:
        """Fallback parsing if LLM fails."""
        import re
        duration_match = re.search(r'(\d+)\s*(?:min|minute|minutes|hour|hours)', request.lower())
        duration = int(duration_match.group(1)) if duration_match else 30
        if 'hour' in request.lower() and duration_match:
            duration = duration * 60
        
        return {
            'event_type': 'meeting',
            'duration_minutes': duration,
            'person_name': None,
            'company_name': None,
            'event_description': request,
            'additional_context': ''
        }
    
    def gather_information(self, person_name: Optional[str], company_name: Optional[str], 
                          event_type: str) -> Dict:
        """
        Gather information about the person, company, and event type.
        
        Args:
            person_name: Name of the person
            company_name: Name of the company
            event_type: Type of event (e.g., "interview")
        
        Returns:
            Dictionary with gathered information
        """
        info = {
            'person_info': '',
            'company_info': '',
            'event_specific_info': '',
            'prep_resources': []
        }
        
        try:
            # Search for person information
            if person_name:
                search_query = f"{person_name} {company_name or ''} linkedin profile"
                print(f"🔍 Searching for information about {person_name}...")
                results = list(self.search_client.text(search_query, max_results=3))
                if results:
                    info['person_info'] = '\n'.join([r['body'] for r in results[:2]])
            
            # Search for company information
            if company_name:
                search_query = f"{company_name} company information"
                print(f"🔍 Searching for information about {company_name}...")
                results = list(self.search_client.text(search_query, max_results=3))
                if results:
                    info['company_info'] = '\n'.join([r['body'] for r in results[:2]])
            
            # Search for event-specific information (e.g., interview questions)
            if event_type.lower() == 'interview':
                search_queries = []
                if company_name:
                    search_queries.append(f"{company_name} interview questions")
                if person_name and company_name:
                    search_queries.append(f"interview with {person_name} at {company_name} preparation")
                
                for query in search_queries:
                    print(f"🔍 Searching for interview preparation resources...")
                    results = list(self.search_client.text(query, max_results=2))
                    if results:
                        info['event_specific_info'] += '\n'.join([r['body'] for r in results])
                        info['prep_resources'].extend([r['href'] for r in results[:2]])
        except Exception as e:
            print(f"⚠️  Warning: Error during web search: {e}")
            print("   Continuing with limited information...")
        
        return info
    
    def plan_preparation(self, parsed_request: Dict, gathered_info: Dict) -> Dict:
        """
        Use LLM to plan preparation based on gathered information.
        
        Args:
            parsed_request: Parsed request information
            gathered_info: Gathered information about person/company
        
        Returns:
            Dictionary with prep plan including time needed and tasks
        """
        prompt = f"""You are an expert at planning preparation for professional meetings and interviews.

Based on the following information, create a detailed preparation plan:

EVENT DETAILS:
- Type: {parsed_request.get('event_type', 'meeting')}
- Duration: {parsed_request.get('duration_minutes', 30)} minutes
- Person: {parsed_request.get('person_name', 'Not specified')}
- Company: {parsed_request.get('company_name', 'Not specified')}
- Description: {parsed_request.get('event_description', '')}

GATHERED INFORMATION:
Person Info: {gathered_info.get('person_info', 'Not available')[:500]}
Company Info: {gathered_info.get('company_info', 'Not available')[:500]}
Event-Specific Info: {gathered_info.get('event_specific_info', 'Not available')[:500]}

Create a preparation plan that includes:
1. Total estimated prep time in hours
2. Breakdown of prep tasks with time estimates
3. Specific resources or topics to research
4. Key talking points or questions to prepare

Return a JSON object with this structure:
{{
    "total_prep_hours": <number>,
    "prep_tasks": [
        {{
            "task": "<task description>",
            "duration_hours": <number>,
            "description": "<detailed description>",
            "resources": ["<resource URL or description>"]
        }}
    ],
    "key_talking_points": ["<point 1>", "<point 2>", ...],
    "recommended_prep_schedule": "<description of when to do prep>"
}}

Return only valid JSON, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert preparation planner. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            import json
            prep_plan = json.loads(response.choices[0].message.content.strip())
            return prep_plan
        except Exception as e:
            print(f"Error planning preparation: {e}")
            # Fallback plan
            return {
                'total_prep_hours': 2,
                'prep_tasks': [
                    {
                        'task': 'Research person and company',
                        'duration_hours': 1,
                        'description': 'Review background information',
                        'resources': []
                    },
                    {
                        'task': 'Prepare talking points',
                        'duration_hours': 1,
                        'description': 'Outline key discussion points',
                        'resources': []
                    }
                ],
                'key_talking_points': [],
                'recommended_prep_schedule': 'Complete prep 1-2 days before the event'
            }
    
    def suggest_schedule_with_prep(self, parsed_request: Dict, prep_plan: Dict, 
                                  days_ahead: int = 14) -> Dict:
        """
        Suggest schedule times accounting for preparation time needed.
        
        Args:
            parsed_request: Parsed request information
            prep_plan: Preparation plan with time estimates
            days_ahead: Number of days to look ahead
        
        Returns:
            Dictionary with suggested slots and prep schedule
        """
        event_duration = parsed_request.get('duration_minutes', 30)
        total_prep_hours = prep_plan.get('total_prep_hours', 2)
        
        # Calculate minimum lead time based on prep hours
        # Heuristic: 1 day lead time per 2 hours of prep, minimum 2 days if any prep needed
        min_lead_days = 0
        if total_prep_hours > 0:
            min_lead_days = max(2, int(total_prep_hours / 2))
        
        # Adjust start date for suggestion search
        # We want to look for slots starting from now + min_lead_days
        now = datetime.now(timezone.utc)
        search_start_date = now + timedelta(days=min_lead_days)
        
        # Get available slots for the event
        event_slots = self.calendar.suggest_time_slots(
            duration_minutes=event_duration,
            start_date=search_start_date,
            days_ahead=days_ahead
        )
        
        # For each event slot, find prep time slots before it
        suggestions = []
        
        for slot_data in event_slots['available'][:5]:  # Top 5 slots
            # Handle new slot structure (dict) vs old (tuple)
            if isinstance(slot_data, dict):
                event_start, event_end = slot_data['target_slot']
            else:
                event_start, event_end = slot_data
                
            # Find prep time slots before the event (at least 1 day before, up to 3 days before)
            prep_tasks = prep_plan.get('prep_tasks', [])
            prep_slots = []
            
            # Determine prep start time
            # Must be at least now
            now = datetime.now(timezone.utc)
            
            # Ideally start 3 days before, but not in the past
            ideal_prep_start = event_start - timedelta(days=3)
            prep_start_date = max(ideal_prep_start, now)
            
            # Prep must end before event starts (give 1 hour buffer)
            prep_end_date = event_start - timedelta(hours=1)
            
            # If we don't have enough time for prep (e.g. event is today/tomorrow),
            # we might need to squeeze it in.
            if prep_start_date > prep_end_date:
                # Event is very soon. Start prep immediately.
                prep_start_date = now
                # If still invalid (event in past?), just use now
                if prep_start_date > prep_end_date:
                     prep_end_date = event_start # Prep right up to event
            
            # Try to schedule prep tasks before the event
            current_prep_time = prep_start_date
            for task in prep_tasks:
                task_duration = int(task.get('duration_hours', 1) * 60)  # Convert to minutes
                
                # Find available slot for this prep task
                prep_slot = self._find_prep_slot(
                    current_prep_time, 
                    prep_end_date, 
                    task_duration
                )
                
                if prep_slot:
                    prep_slots.append({
                        'task': task,
                        'slot': prep_slot
                    })
                    current_prep_time = prep_slot[1] + timedelta(hours=1)  # Next slot after this one
                else:
                    # If we can't find a slot, suggest a flexible time
                    prep_slots.append({
                        'task': task,
                        'slot': None,
                        'suggested_time': f"{prep_start_date.strftime('%Y-%m-%d')} (flexible)"
                    })
            
            suggestions.append({
                'event_slot': (event_start, event_end),
                'prep_slots': prep_slots,
                'total_prep_hours': total_prep_hours
            })
        
        return {
            'suggestions': suggestions,
            'prep_plan': prep_plan
        }
    
    def _find_prep_slot(self, start_date: datetime, end_date: datetime, 
                       duration_minutes: int) -> Optional[Tuple[datetime, datetime]]:
        """Find an available slot for prep work."""
        # Get busy times in the range
        busy_times = self.calendar.get_busy_times(start_date, end_date)
        busy_times.sort(key=lambda x: x[0])
        
        duration = timedelta(minutes=duration_minutes)
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
            
            # Check for conflicts
            has_conflict = False
            for busy_start, busy_end in busy_times:
                if (current < busy_end and slot_end > busy_start):
                    has_conflict = True
                    break
            
            if not has_conflict:
                return (current, slot_end)
            
            # Move to next potential slot
            current += timedelta(minutes=30)
        
        return None
    
    def create_prep_events(self, suggestion: Dict, parsed_request: Dict, 
                          gathered_info: Dict, prep_plan: Dict) -> List[str]:
        """
        Create calendar events for preparation tasks.
        
        Args:
            suggestion: Selected suggestion with event and prep slots
            parsed_request: Parsed request information
            gathered_info: Gathered information
            prep_plan: Preparation plan
        
        Returns:
            List of created event IDs
        """
        created_events = []
        event_name = parsed_request.get('event_description', 'Meeting')
        
        # Create prep events
        for prep_item in suggestion['prep_slots']:
            task = prep_item['task']
            slot = prep_item.get('slot')
            
            if slot:
                prep_start, prep_end = slot
                event_title = f"Prep: {task.get('task', 'Preparation')} - {event_name}"
                
                # Create detailed description
                description = f"""Preparation for: {event_name}
                
Task: {task.get('task', 'Preparation')}
Duration: {task.get('duration_hours', 1)} hours

Description:
{task.get('description', 'General preparation')}

Resources:
{chr(10).join(['- ' + r for r in task.get('resources', [])])}

Key Talking Points:
{chr(10).join(['- ' + p for p in prep_plan.get('key_talking_points', [])])}

Gathered Information:
Person: {parsed_request.get('person_name', 'N/A')}
Company: {parsed_request.get('company_name', 'N/A')}
"""
                
                event_id = self.calendar.create_event(
                    title=event_title,
                    start_time=prep_start,
                    end_time=prep_end,
                    description=description
                )
                
                if event_id:
                    created_events.append(event_id)
                    print(f"✅ Created prep event: {event_title} at {prep_start.strftime('%Y-%m-%d %H:%M')}")
        
        return created_events
    
    def schedule_intelligent(self, request: str, days_ahead: int = 14, 
                           auto_create_prep: bool = False) -> Dict:
        """
        Main method to intelligently schedule a meeting with prep planning.
        
        Args:
            request: Natural language scheduling request
            days_ahead: Number of days to look ahead
            auto_create_prep: Whether to automatically create prep events
        
        Returns:
            Dictionary with suggestions and information
        """
        print(f"\n🧠 Analyzing request: {request}")
        
        # Step 1: Parse the request
        print("\n📝 Step 1: Parsing request...")
        parsed_request = self.parse_request(request)
        print(f"   Event type: {parsed_request.get('event_type')}")
        print(f"   Duration: {parsed_request.get('duration_minutes')} minutes")
        if parsed_request.get('person_name'):
            print(f"   Person: {parsed_request.get('person_name')}")
        if parsed_request.get('company_name'):
            print(f"   Company: {parsed_request.get('company_name')}")
        
        # Step 2: Gather information
        print("\n🔍 Step 2: Gathering information...")
        gathered_info = self.gather_information(
            parsed_request.get('person_name'),
            parsed_request.get('company_name'),
            parsed_request.get('event_type', 'meeting')
        )
        
        # Step 3: Plan preparation
        print("\n📋 Step 3: Planning preparation...")
        prep_plan = self.plan_preparation(parsed_request, gathered_info)
        print(f"   Estimated prep time: {prep_plan.get('total_prep_hours', 0)} hours")
        print(f"   Prep tasks: {len(prep_plan.get('prep_tasks', []))}")
        
        # Step 4: Suggest schedule with prep
        print("\n📅 Step 4: Finding optimal schedule...")
        suggestions = self.suggest_schedule_with_prep(parsed_request, prep_plan, days_ahead)
        
        return {
            'parsed_request': parsed_request,
            'gathered_info': gathered_info,
            'prep_plan': prep_plan,
            'suggestions': suggestions,
            'auto_create_prep': auto_create_prep
        }

