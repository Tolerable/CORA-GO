"""Test pairing flow end-to-end."""
import sys
import json
import urllib.request
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

SUPABASE_URL = 'https://bugpycickribmdfprryq.supabase.co'
SUPABASE_KEY = 'sb_publishable_c9Q2joJ8g7g7ntdrzbnzbA_RJfa_5jt'

def claim_code(code):
    """Simulate mobile claiming the code."""
    time.sleep(5)  # Wait for window to open
    print(f'\n[MOBILE] Claiming code {code}...')
    url = f'{SUPABASE_URL}/rest/v1/cora_pairing?code=eq.{code}'
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    body = json.dumps({'claimed_at': datetime.now(timezone.utc).isoformat()}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f'[MOBILE] Claimed successfully!')
            return True
    except Exception as e:
        print(f'[MOBILE] Claim error: {e}')
        return False

if __name__ == "__main__":
    from anchor.pairing import pairing, show_pairing_window

    # Generate code first
    result = pairing.generate_pairing_code()
    if 'error' in result:
        print(f'ERROR: {result}')
        sys.exit(1)

    code = result['code']
    print(f'Generated code: {code}')
    print(f'QR URL: {result["qr_url"]}')
    print(f'\nWindow will open. Code will be claimed in 5 seconds.')
    print(f'Watch for: [POLL] Status: ... messages')
    print(f'Should show: CONNECTED to Mobile!')
    print(f'Then close after 2 seconds.\n')

    # Start claim thread
    claim_thread = threading.Thread(target=claim_code, args=(code,), daemon=True)
    claim_thread.start()

    # Show window (blocking)
    show_pairing_window()

    print('\n=== WINDOW CLOSED - TEST COMPLETE ===')
