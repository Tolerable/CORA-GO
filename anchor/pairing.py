"""
CORA-GO Pairing System
Generates QR codes for mobile device pairing.
"""

import json
import urllib.request
import urllib.parse
import threading
import time
from typing import Optional, Dict, Callable
from datetime import datetime

from .config import config

# EZTUNES-LIVE Supabase - publishable key for client operations
SUPABASE_URL = "https://bugpycickribmdfprryq.supabase.co"
SUPABASE_KEY = "sb_publishable_c9Q2joJ8g7g7ntdrzbnzbA_RJfa_5jt"


class PairingManager:
    """Handles QR code generation and device pairing."""

    def __init__(self):
        # Use config if set, else use hardcoded EZTUNES
        self.url = config.get("relay.url", "") or SUPABASE_URL
        self.key = config.get("relay.anon_key", "") or SUPABASE_KEY
        self.anchor_id = config.get("anchor.id", "anchor-" + self._generate_id())
        self.anchor_name = config.get("anchor.name", "PC Anchor")
        self.current_code: Optional[str] = None
        self.on_device_paired: Optional[Callable] = None
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None

    def _generate_id(self) -> str:
        """Generate a unique anchor ID."""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    def is_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.url and self.key)

    def _rpc(self, func: str, params: Dict) -> Dict:
        """Call Supabase RPC function."""
        if not self.is_configured():
            return {"error": "Supabase not configured"}

        url = f"{self.url}/rest/v1/rpc/{func}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

        try:
            body = json.dumps(params).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.load(resp)
        except Exception as e:
            return {"error": str(e)}

    def generate_pairing_code(self) -> Dict:
        """Generate a new pairing code for QR display."""
        import random
        from datetime import datetime, timedelta, timezone

        # Generate CORA-XXXX code locally (bypass broken RPC)
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        code = 'CORA-' + ''.join(random.choices(chars, k=4))

        # Calculate expiry (5 minutes)
        expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

        # Insert directly into cora_pairing table
        url = f"{self.url}/rest/v1/cora_pairing"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        data = {
            "code": code,
            "anchor_id": self.anchor_id,
            "anchor_name": self.anchor_name,
            "expires_at": expires
        }

        try:
            body = json.dumps(data).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in [200, 201]:
                    self.current_code = code
                    return {
                        "code": code,
                        "anchor_id": self.anchor_id,
                        "qr_url": self.get_qr_url(code)
                    }
        except Exception as e:
            return {"error": f"Failed to create pairing code: {e}"}

        return {"error": "Failed to generate code"}

    def get_qr_url(self, code: str) -> str:
        """Get the URL to encode in QR code."""
        # This URL will open the mobile pairing page
        # GitHub Pages: https://tolerable.github.io/CORA-GO/
        base_url = config.get("web.url", "https://tolerable.github.io/CORA-GO")
        return f"{base_url}/web/pair.html?code={code}"

    def generate_qr_image(self, code: str, size: int = 200) -> Optional[bytes]:
        """Generate QR code image as PNG bytes using free API."""
        try:
            url = self.get_qr_url(code)
            encoded_url = urllib.parse.quote(url, safe='')
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}&format=png&margin=10"

            req = urllib.request.Request(qr_api)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read()

        except Exception as e:
            print(f"QR generation error: {e}")
            return None

    def save_qr_image(self, code: str, path: str, size: int = 200) -> bool:
        """Save QR code image to file."""
        img_bytes = self.generate_qr_image(code, size)
        if img_bytes:
            with open(path, "wb") as f:
                f.write(img_bytes)
            return True
        return False

    def get_paired_devices(self) -> list:
        """Get list of devices paired with this anchor."""
        result = self._rpc("get_anchor_devices", {"p_anchor_id": self.anchor_id})
        if isinstance(result, list):
            return result
        return []

    def check_pairing_status(self, code: str) -> Dict:
        """Check if a pairing code has been claimed."""
        # Query cora_pairing table directly instead of RPC
        try:
            url = f"{self.url}/rest/v1/cora_pairing?code=eq.{code}&select=claimed_at,claimed_by,anchor_id,anchor_name"
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
            }
            print(f"[DEBUG] Checking: {url}")
            print(f"[DEBUG] Using key: {self.key[:20]}...")
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
                print(f"[DEBUG] Raw data: {data}")
                if data and len(data) > 0:
                    row = data[0]
                    # If claimed_at is set, pairing is complete
                    if row.get("claimed_at"):
                        return {
                            "status": "claimed",
                            "device_name": row.get("claimed_by", "Mobile"),
                            "anchor_id": row.get("anchor_id"),
                            "anchor_name": row.get("anchor_name")
                        }
                    return {"status": "pending"}
                return {"status": "expired"}
        except Exception as e:
            print(f"[DEBUG] Error: {e}")
            return {"error": str(e)}

    def start_pairing_poll(self, code: str, callback: Callable[[Dict], None], interval: float = 2.0):
        """Start polling for pairing completion."""
        self._polling = True

        def poll():
            while self._polling:
                status = self.check_pairing_status(code)
                if status.get("status") == "claimed":
                    self._polling = False
                    callback(status)
                    break
                elif status.get("status") == "expired":
                    self._polling = False
                    callback({"error": "Pairing code expired"})
                    break
                time.sleep(interval)

        self._poll_thread = threading.Thread(target=poll, daemon=True)
        self._poll_thread.start()

    def stop_pairing_poll(self):
        """Stop polling for pairing."""
        self._polling = False


# Global instance
pairing = PairingManager()


def show_pairing_window():
    """Show a tkinter window with QR code for pairing."""
    import tkinter as tk
    from tkinter import ttk

    if not pairing.is_configured():
        print("Supabase not configured - cannot show pairing window")
        return

    # Generate pairing code
    result = pairing.generate_pairing_code()
    if "error" in result:
        print(f"Failed to generate pairing code: {result['error']}")
        return

    code = result["code"]
    qr_url = result["qr_url"]

    # Create window
    root = tk.Tk()
    root.title("CORA-GO - Pair Mobile Device")
    root.configure(bg='#0a0a0a')
    root.geometry("400x500")
    root.resizable(False, False)

    # Header
    tk.Label(
        root, text="CORA-GO",
        font=("Consolas", 24, "bold"),
        fg="#ff00ff", bg="#0a0a0a"
    ).pack(pady=(20, 5))

    tk.Label(
        root, text="Scan to pair your mobile device",
        font=("Consolas", 11),
        fg="#00ffff", bg="#0a0a0a"
    ).pack(pady=(0, 20))

    # QR Code frame
    qr_frame = tk.Frame(root, bg="#1a1a1a", bd=2, relief="groove")
    qr_frame.pack(pady=10)

    # Load QR code from free API (no packages needed!)
    try:
        from PIL import Image, ImageTk
        from io import BytesIO

        # Use free QR server API
        encoded_url = urllib.parse.quote(qr_url, safe='')
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded_url}&format=png&margin=10"

        req = urllib.request.Request(qr_api_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            qr_data = resp.read()

        qr_img = Image.open(BytesIO(qr_data))
        photo = ImageTk.PhotoImage(qr_img)
        qr_label = tk.Label(qr_frame, image=photo, bg="#ffffff")
        qr_label.image = photo  # Keep reference
        qr_label.pack(padx=10, pady=10)

    except Exception as e:
        print(f"QR load error: {e}")
        tk.Label(
            qr_frame, text=f"[QR Code Error]\n\n{e}",
            font=("Consolas", 10),
            fg="#888888", bg="#1a1a1a",
            width=30, height=10
        ).pack(padx=10, pady=10)

    # Pairing code
    tk.Label(
        root, text="Or enter code manually:",
        font=("Consolas", 10),
        fg="#888888", bg="#0a0a0a"
    ).pack(pady=(20, 5))

    code_label = tk.Label(
        root, text=code,
        font=("Consolas", 28, "bold"),
        fg="#00ff88", bg="#0a0a0a"
    )
    code_label.pack(pady=5)

    # Status
    status_label = tk.Label(
        root, text="Waiting for mobile device...",
        font=("Consolas", 10, "italic"),
        fg="#666666", bg="#0a0a0a"
    )
    status_label.pack(pady=20)

    # URL hint
    tk.Label(
        root, text=f"Open: {qr_url.split('?')[0]}",
        font=("Consolas", 8),
        fg="#444444", bg="#0a0a0a"
    ).pack(pady=5)

    # Handle pairing success (called from main thread via root.after)
    def on_paired(result):
        print(f"[PAIRING] on_paired called with: {result}")
        if "error" in result:
            status_label.config(text=result["error"], fg="#ff3333")
        else:
            device_name = result.get('device_name') or result.get('anchor_name') or 'Mobile'
            status_label.config(
                text=f"CONNECTED to {device_name}!",
                fg="#00ff88"
            )
            print(f"[PAIRING] Connected to {device_name}")

            # Save pairing to config
            config.set("paired", True)
            config.set("paired_device", device_name)
            config.set("anchor.id", pairing.anchor_id)

            # Start the relay immediately!
            def start_relay_and_close():
                try:
                    from .relay import relay
                    relay.device_id = pairing.anchor_id
                    if relay.is_configured():
                        # Send first heartbeat so mobile sees us online
                        relay.heartbeat()
                        relay.start()
                        print(f"[PAIRING] Relay started - mobile should see us online now!")
                except Exception as e:
                    print(f"[PAIRING] Failed to start relay: {e}")
                print("[PAIRING] Closing window")
                root.destroy()

            root.after(1500, start_relay_and_close)

    # Poll in main thread using root.after (thread-safe)
    def poll_status():
        import sys
        try:
            status = pairing.check_pairing_status(code)
            print(f"[POLL] Status: {status}", flush=True)
            sys.stdout.flush()

            if status.get("status") == "claimed":
                print("[POLL] Calling on_paired!", flush=True)
                on_paired(status)
            elif status.get("status") == "expired":
                print("[POLL] Code expired!", flush=True)
                on_paired({"error": "Pairing code expired"})
            else:
                # Keep polling every 2 seconds
                root.after(2000, poll_status)
        except Exception as e:
            print(f"[POLL] EXCEPTION: {e}", flush=True)
            import traceback
            traceback.print_exc()
            root.after(2000, poll_status)

    # Start polling after 1 second
    root.after(1000, poll_status)

    def on_close():
        pairing.stop_pairing_poll()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    # Test pairing window
    from .config import config

    # Configure with EZTUNES-LIVE
    config.set("relay.url", "https://bugpycickribmdfprryq.supabase.co")
    config.set("relay.anon_key", "sb_secret_6J4iNVJCBckqYECbbxz1OQ_248Vktk9")

    show_pairing_window()
