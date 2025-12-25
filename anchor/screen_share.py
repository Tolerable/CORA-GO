"""
CORA-GO Screen Sharing
Captures screenshots and uploads to Supabase for TeamViewer mode.
"""

import json
import time
import base64
import threading
from io import BytesIO
from typing import Optional

from .config import config

SUPABASE_URL = "https://bugpycickribmdfprryq.supabase.co"
SUPABASE_KEY = "sb_publishable_c9Q2joJ8g7g7ntdrzbnzbA_RJfa_5jt"


class ScreenShare:
    """Handles screen capture and upload for remote viewing."""

    def __init__(self):
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.anchor_id = config.get("anchor.id", "anchor")
        self.fps = config.get("screen_share.fps", 1)  # Frames per second
        self.quality = config.get("screen_share.quality", 50)  # JPEG quality
        self.scale = config.get("screen_share.scale", 0.5)  # Scale factor

    def capture_screen(self) -> Optional[tuple]:
        """Capture screenshot and return (base64_data, width, height)."""
        try:
            from PIL import ImageGrab

            # Capture screen
            img = ImageGrab.grab()
            orig_width, orig_height = img.size

            # Scale down for bandwidth
            if self.scale < 1.0:
                new_size = (int(orig_width * self.scale), int(orig_height * self.scale))
                img = img.resize(new_size)

            # Convert to JPEG bytes
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=self.quality)
            img_bytes = buffer.getvalue()

            # Base64 encode
            b64_data = base64.b64encode(img_bytes).decode('utf-8')

            return (b64_data, orig_width, orig_height)

        except Exception as e:
            print(f"[SCREEN] Capture error: {e}")
            return None

    def upload_screen(self, b64_data: str, width: int, height: int) -> bool:
        """Upload screenshot to Supabase."""
        import urllib.request

        try:
            url = f"{SUPABASE_URL}/rest/v1/rpc/update_cora_screen"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            data = json.dumps({
                "p_anchor_id": self.anchor_id,
                "p_image_data": b64_data,
                "p_width": width,
                "p_height": height
            }).encode()

            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200

        except Exception as e:
            print(f"[SCREEN] Upload error: {e}")
            return False

    def share_loop(self):
        """Continuous screen sharing loop."""
        interval = 1.0 / self.fps

        while self.running:
            try:
                result = self.capture_screen()
                if result:
                    b64_data, width, height = result
                    self.upload_screen(b64_data, width, height)

            except Exception as e:
                print(f"[SCREEN] Loop error: {e}")

            time.sleep(interval)

    def start(self):
        """Start screen sharing."""
        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(target=self.share_loop, daemon=True)
        self._thread.start()
        print(f"[SCREEN] Started sharing at {self.fps} FPS")

    def stop(self):
        """Stop screen sharing."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[SCREEN] Stopped sharing")

    def is_running(self) -> bool:
        return self.running


# Global instance
screen_share = ScreenShare()
