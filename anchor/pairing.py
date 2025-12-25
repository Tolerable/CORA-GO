"""
CORA-GO Pairing System
Generates QR codes for mobile device pairing.
"""

import json
import urllib.request
import threading
import time
from typing import Optional, Dict, Callable
from datetime import datetime

from .config import config

# EZTUNES-LIVE Supabase - anon key is safe for client-side
SUPABASE_URL = "https://bugpycickribmdfprryq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ1Z3B5Y2lja3JpYm1kZnBycnlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk2ODQ5MzgsImV4cCI6MjA3NTI2MDkzOH0.1S1ZoV4TvhIyUjKvwYE6wZexS2aM_EMNJzV9Gn8M1CI"


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
        result = self._rpc("generate_pairing_code", {
            "p_anchor_id": self.anchor_id,
            "p_anchor_name": self.anchor_name
        })

        if isinstance(result, str):
            self.current_code = result
            return {
                "code": result,
                "anchor_id": self.anchor_id,
                "qr_url": self.get_qr_url(result)
            }

        return {"error": result.get("error", "Failed to generate code")}

    def get_qr_url(self, code: str) -> str:
        """Get the URL to encode in QR code."""
        # This URL will open the mobile pairing page
        # GitHub Pages: https://tolerable.github.io/CORA-GO/
        base_url = config.get("web.url", "https://tolerable.github.io/CORA-GO")
        return f"{base_url}/web/pair.html?code={code}"

    def generate_qr_image(self, code: str, size: int = 200) -> Optional[bytes]:
        """Generate QR code image as PNG bytes."""
        try:
            import qrcode
            from io import BytesIO

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(self.get_qr_url(code))
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Resize if needed
            if size != 200:
                img = img.resize((size, size))

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()

        except ImportError:
            print("qrcode package not installed. Install with: pip install qrcode[pil]")
            return None
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
        result = self._rpc("check_pairing_status", {"p_code": code})
        return result if isinstance(result, dict) else {"error": str(result)}

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

    # Try to display QR code
    try:
        import qrcode
        from PIL import Image, ImageTk
        from io import BytesIO

        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(qr_img)
        qr_label = tk.Label(qr_frame, image=photo, bg="#1a1a1a")
        qr_label.image = photo  # Keep reference
        qr_label.pack(padx=10, pady=10)

    except ImportError:
        tk.Label(
            qr_frame, text="[QR Code]\n\nInstall qrcode package:\npip install qrcode[pil]",
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

    # Handle pairing success
    def on_paired(result):
        if "error" in result:
            status_label.config(text=result["error"], fg="#ff3333")
        else:
            status_label.config(
                text=f"Paired with {result.get('anchor_name', 'device')}!",
                fg="#00ff88"
            )
            root.after(2000, root.destroy)

    # Start polling
    pairing.start_pairing_poll(code, on_paired)

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
    config.set("relay.anon_key", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ1Z3B5Y2lja3JpYm1kZnBycnlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk2ODQ5MzgsImV4cCI6MjA3NTI2MDkzOH0.1S1ZoV4TvhIyUjKvwYE6wZexS2aM_EMNJzV9Gn8M1CI")

    show_pairing_window()
