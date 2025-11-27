
import sys
import os
import subprocess
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

def test_interactive_dates():
    print("\n=== Testing Interactive Specific Date Scheduling ===")
    
    # Calculate a future date
    target_date = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
    
    # Input command
    input_str = f"schedule 60 India date={target_date}\nquit\n"
    
    print(f"Sending input: {input_str.strip()}")
    
    process = subprocess.Popen(
        ['python3', 'agent.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=input_str)
    
    print("\n--- Output ---")
    # Print only relevant parts to avoid clutter
    for line in stdout.splitlines():
        if "Looking for" in line or "Showing slots" in line or "Warning" in line:
            print(line)
            
    if f"specific dates: {target_date}" in stdout:
        print("✅ Verified: Agent detected specific date.")
    else:
        print("❌ Failed: Agent did not detect specific date.")
        print("Full output snippet:")
        print(stdout[:1000])

    if "Warning: Invalid user timezone" not in stdout:
        print("✅ Verified: No invalid timezone warning.")
    else:
        print("❌ Failed: Still seeing invalid timezone warning.")

if __name__ == "__main__":
    try:
        test_interactive_dates()
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
