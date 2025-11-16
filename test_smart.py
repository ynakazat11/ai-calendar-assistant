#!/usr/bin/env python3
"""Test script for intelligent scheduler"""
import sys
from calendar_manager import CalendarManager
from intelligent_scheduler import IntelligentScheduler

print('Initializing calendar manager...')
try:
    cm = CalendarManager()
    print('✅ Calendar manager OK')
except Exception as e:
    print(f'❌ Calendar manager failed: {e}')
    sys.exit(1)

print('Initializing intelligent scheduler...')
try:
    scheduler = IntelligentScheduler(cm)
    print('✅ Intelligent scheduler OK')
except Exception as e:
    print(f'❌ Intelligent scheduler failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('\nTesting parse_request...')
try:
    result = scheduler.parse_request('30 minutes interview with John at Company X')
    print('✅ Parse result:', result)
except Exception as e:
    print(f'❌ Parse request failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('\n✅ All tests passed!')

