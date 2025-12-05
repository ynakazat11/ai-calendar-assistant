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
        prompt = f"""Parse the following scheduling request into a structured plan with a primary task and optional dependent tasks.
Return a JSON object with the following fields:
- primary_task: Object containing:
    - description: Task description
    - duration_minutes: Duration in minutes
    - constraints: Object with 'timezone', 'time_preference', and 'min_days_ahead' (int, optional)
- dependent_tasks: List of objects, each containing:
    - description: Task description
    - duration_minutes: Duration
    - relation: Relationship to primary (e.g. 'before', 'after')
    - constraints: Object with 'timezone' and 'time_preference'
- context: Object containing extracted entities if present (person_name, company_name, event_type)

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
            'primary_task': {
                'description': request,
                'duration_minutes': duration,
                'constraints': {}
            },
            'dependent_tasks': [],
            'context': {
                'event_type': 'meeting',
                'person_name': None,
                'company_name': None
            }
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
            # Catch all exceptions including Ratelimit to prevent crashing
            print(f"⚠️  Warning: Web search failed (possibly rate limited). Continuing without external info.")
            # print(f"   Debug error: {e}") # Uncomment for debugging
        
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
    
    def suggest_complex_schedule(self, parsed_request: Dict, prep_plan: Dict = None, 
                                  days_ahead: int = 14) -> Dict:
        """
        Suggest schedule for a primary task and its dependencies.
        
        Args:
            parsed_request: Parsed request with primary_task and dependent_tasks
            prep_plan: Optional prep plan (legacy/compatibility)
            days_ahead: Number of days to look ahead
        
        Returns:
            Dictionary with suggested slots
        """
        primary = parsed_request.get('primary_task', {})
        dependents = parsed_request.get('dependent_tasks', [])
        
        # If prep_plan is provided (legacy flow), convert it to a dependent task if not already present
        if prep_plan and not dependents:
            total_prep = prep_plan.get('total_prep_hours', 0)
            if total_prep > 0:
                dependents.append({
                    'description': 'Preparation',
                    'duration_minutes': int(total_prep * 60),
                    'relation': 'before',
                    'constraints': {} # Default constraints
                })
        
        # 1. Find slots for Primary Task
        p_duration = primary.get('duration_minutes', 30)
        p_constraints = primary.get('constraints', {})
        p_timezone = p_constraints.get('timezone', 'UTC')
        p_time_pref = p_constraints.get('time_preference', '').lower()
        p_min_days = p_constraints.get('min_days_ahead', 0)
        
        # Calculate start date based on dependencies (e.g. if prep needed, start later)
        # Simple heuristic: if any 'before' dependency, push start date
        start_delay_days = p_min_days
        for dep in dependents:
            if dep.get('relation') == 'before':
                # Add 1 day delay per 2 hours of dependent task?
                dur = dep.get('duration_minutes', 0)
                if dur > 0:
                    start_delay_days += max(1, int(dur / 120))
        
        now = datetime.now(timezone.utc)
        search_start = now + timedelta(days=start_delay_days)
        
        print(f"Searching primary slots in {p_timezone} starting {search_start.strftime('%Y-%m-%d')}...")
        
        primary_slots = self.calendar.suggest_time_slots(
            duration_minutes=p_duration,
            start_date=search_start,
            days_ahead=days_ahead,
            timezone_str=p_timezone
        )
        
        suggestions = []
        
        # 2. For each primary slot, try to schedule dependents
        for p_slot_data in primary_slots['available'][:5]: # Top 5
            if isinstance(p_slot_data, dict):
                p_start, p_end = p_slot_data['target_slot']
                p_user_start, p_user_end = p_slot_data['user_slot']
            else:
                p_start, p_end = p_slot_data
                p_user_start = p_start # Fallback
            
            # Filter primary slot by time preference if needed
            if p_time_pref and not self._check_time_preference(p_start, p_time_pref):
                continue

            valid_chain = True
            chain_details = []
            
            for dep in dependents:
                d_desc = dep.get('description', 'Task')
                d_duration = dep.get('duration_minutes', 60)
                d_relation = dep.get('relation', 'before')
                d_constraints = dep.get('constraints', {})
                d_timezone = d_constraints.get('timezone', p_timezone) # Default to primary TZ
                d_time_pref = d_constraints.get('time_preference', '').lower()
                
                # Search window depends on relation
                d_search_start = now
                d_search_end = None
                
                if d_relation == 'before':
                    d_search_end = p_start
                    # Ideally start looking from now
                elif d_relation == 'after':
                    d_search_start = p_end
                    d_search_end = p_end + timedelta(days=7) # Look ahead 1 week
                
                # We need a way to search for a SINGLE slot for this dependent task
                # reusing suggest_time_slots but we need to constrain the end date
                # suggest_time_slots takes days_ahead, not end_date.
                # We can approximate days_ahead.
                
                days_for_dep = 7
                if d_search_end:
                    delta = d_search_end - d_search_start
                    days_for_dep = max(1, delta.days + 1)
                
                dep_slots = self.calendar.suggest_time_slots(
                    duration_minutes=d_duration,
                    start_date=d_search_start,
                    days_ahead=days_for_dep,
                    timezone_str=d_timezone
                )
                
                # Find a valid slot for dependent
                found_dep_slot = None
                for d_slot_data in dep_slots['available']:
                    if isinstance(d_slot_data, dict):
                        ds_start, ds_end = d_slot_data['target_slot']
                    else:
                        ds_start, ds_end = d_slot_data
                    
                    # Check relation constraint strictly
                    if d_relation == 'before' and ds_end > p_start:
                        continue
                    if d_relation == 'after' and ds_start < p_end:
                        continue
                        
                    # Check time preference
                    if d_time_pref and not self._check_time_preference(ds_start, d_time_pref):
                        continue
                    
                    found_dep_slot = (ds_start, ds_end)
                    break
                
                if found_dep_slot:
                    chain_details.append({
                        'description': d_desc,
                        'slot': found_dep_slot,
                        'timezone': d_timezone
                    })
                else:
                    valid_chain = False
                    break
            
            if valid_chain:
                suggestions.append({
                    'primary_slot': (p_start, p_end),
                    'primary_timezone': p_timezone,
                    'dependent_slots': chain_details
                })
        
        return {'suggestions': suggestions}
                

    def _check_time_preference(self, slot_start: datetime, preference: str) -> bool:
        """Check if a slot matches the time preference."""
        h = slot_start.hour
        pref = preference.lower()
        
        if 'morning' in pref and h >= 12:
            return False
        if 'afternoon' in pref and (h < 12 or h >= 17):
            return False
        if 'evening' in pref and h < 17:
            return False
        if 'night' in pref and h < 19:
            return False
            
        # Handle "after X pm"
        if 'after' in pref and 'pm' in pref:
            try:
                import re
                m = re.search(r'after (\d+)', pref)
                if m:
                    limit = int(m.group(1))
                    if limit < 12: limit += 12 # Assume PM
                    if h < limit:
                        return False
            except:
                pass
                
        return True

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
        primary = parsed_request.get('primary_task', {})
        context = parsed_request.get('context', {})
        
        print(f"   Primary Task: {primary.get('description')}")
        print(f"   Duration: {primary.get('duration_minutes')} minutes")
        if context.get('person_name'):
            print(f"   Person: {context.get('person_name')}")
        
        # Step 2: Gather information (Optional, mostly for context)
        print("\n🔍 Step 2: Gathering information...")
        gathered_info = self.gather_information(
            context.get('person_name'),
            context.get('company_name'),
            context.get('event_type', 'meeting')
        )
        
        # Step 3: Suggest schedule
        print("\n📅 Step 3: Finding optimal schedule...")
        suggestions = self.suggest_complex_schedule(parsed_request, days_ahead=days_ahead)
        
        return {
            'parsed_request': parsed_request,
            'gathered_info': gathered_info,
            'suggestions': suggestions,
            'auto_create_prep': auto_create_prep
        }

