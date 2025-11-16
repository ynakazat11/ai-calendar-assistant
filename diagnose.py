#!/usr/bin/env python3
"""Diagnostic script to check why intelligent scheduler might not be available"""
import os
import sys

print("=" * 60)
print("DIAGNOSTIC CHECK")
print("=" * 60)

# Check 1: Current directory
print("\n1. Current directory:")
print(f"   {os.getcwd()}")

# Check 2: .env file
print("\n2. .env file:")
env_path = os.path.join(os.getcwd(), '.env')
print(f"   Path: {env_path}")
print(f"   Exists: {os.path.exists(env_path)}")
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        content = f.read()
        has_key = 'OPENAI_API_KEY' in content
        print(f"   Has OPENAI_API_KEY: {has_key}")
        if has_key:
            lines = [l for l in content.split('\n') if 'OPENAI_API_KEY' in l and not l.strip().startswith('#')]
            if lines:
                key_line = lines[0]
                key_value = key_line.split('=', 1)[1].strip() if '=' in key_line else ''
                print(f"   Key length: {len(key_value)}")
                print(f"   Key starts with: {key_value[:10]}..." if len(key_value) > 10 else "   Key is empty!")

# Check 3: Config loading
print("\n3. Config loading:")
try:
    sys.path.insert(0, os.getcwd())
    import config
    print(f"   Config loaded: ✅")
    print(f"   OPENAI_API_KEY in config: {bool(config.OPENAI_API_KEY)}")
    if config.OPENAI_API_KEY:
        print(f"   Key value (first 15 chars): {config.OPENAI_API_KEY[:15]}...")
    else:
        print("   ⚠️  OPENAI_API_KEY is None or empty in config!")
except Exception as e:
    print(f"   ❌ Error loading config: {e}")

# Check 4: Intelligent scheduler initialization
print("\n4. Intelligent scheduler initialization:")
try:
    from calendar_manager import CalendarManager
    from intelligent_scheduler import IntelligentScheduler
    
    print("   Initializing calendar manager...")
    cm = CalendarManager()
    print("   ✅ Calendar manager OK")
    
    print("   Initializing intelligent scheduler...")
    scheduler = IntelligentScheduler(cm)
    print("   ✅ Intelligent scheduler OK")
    
except ValueError as e:
    if "OPENAI_API_KEY" in str(e):
        print(f"   ❌ {e}")
        print("   This is the issue! The API key is not being loaded.")
    else:
        print(f"   ❌ {e}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Check 5: Agent initialization
print("\n5. Agent initialization:")
try:
    from agent import ScheduleAgent
    agent = ScheduleAgent()
    print(f"   intelligent_scheduler is None: {agent.intelligent_scheduler is None}")
    print(f"   calendar_monitor is None: {agent.calendar_monitor is None}")
    if agent.intelligent_scheduler is None:
        print("   ⚠️  Intelligent scheduler is None - this will cause the error!")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

