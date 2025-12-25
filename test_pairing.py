"""Test pairing flow end-to-end."""
import sys
import json
import urllib.request
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# Setup path FIRST
sys.path.insert(0, str(Path(__file__).parent))

# Force reload of pairing module to get latest code
import importlib
from anchor import pairing as pairing_module
importlib.reload(pairing_module)
from anchor.pairing import pairing, show_pairing_window, SUPABASE_URL, SUPABASE_KEY

print(f'Using key: {SUPABASE_KEY[:25]}...')

# Global to store the code from window
window_code = None

def claim_after_window_opens():
    """Wait for window to generate code, then claim it."""
    global window_code
    time.sleep(3)  # Wait for window

    # Get the current code from pairing instance
    code = pairing.current_code
    if not code:
        print('[MOBILE] No code found yet, waiting...')
        time.sleep(3)
        code = pairing.current_code

    if not code:
        print('[MOBILE] ERROR: No code generated')
        return

    print(f'\n[MOBILE] Found code: {code}')
    print(f'[MOBILE] Claiming...')

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
            result = resp.read().decode()
            print(f'[MOBILE] Claimed! Response: {result[:80]}...')
    except Exception as e:
        print(f'[MOBILE] Claim error: {e}')

if __name__ == "__main__":
    print(f'Pairing URL: {pairing.url}')
    print(f'Pairing key: {pairing.key[:25]}...')
    print(f'\nStarting window...')
    print(f'Will claim whatever code the window generates.\n')

    # Start claim thread
    claim_thread = threading.Thread(target=claim_after_window_opens, daemon=True)
    claim_thread.start()

    # Show window (blocking) - this generates its own code
    show_pairing_window()

    print('\n=== WINDOW CLOSED - TEST COMPLETE ===')
