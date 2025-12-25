"""
CORA-GO Screenshot Tools
Desktop, window, and web page screenshots.
"""

import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional
from . import register_tool
from ..config import config


def _get_screenshot_dir() -> Path:
    """Get screenshot storage directory."""
    save_dir = config.get("screenshots.save_dir", "screenshots")
    # Relative to anchor directory
    ss_dir = Path(__file__).parent.parent / save_dir
    ss_dir.mkdir(exist_ok=True)
    return ss_dir


def _get_format() -> str:
    """Get screenshot format from config."""
    return config.get("screenshots.format", "png")


def screenshot_desktop(filename: Optional[str] = None) -> dict:
    """
    Take a screenshot of the entire desktop.

    Args:
        filename: Optional custom filename

    Returns:
        Path to saved screenshot
    """
    if not config.get("screenshots.enabled", True):
        return {"error": "Screenshots disabled in config"}

    ss_dir = _get_screenshot_dir()
    fmt = _get_format()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"desktop_{timestamp}.{fmt}"

    filepath = ss_dir / filename

    try:
        if platform.system() == "Windows":
            # Use PowerShell for Windows screenshot
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
            $bitmap.Save("{filepath}")
            $graphics.Dispose()
            $bitmap.Dispose()
            '''
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return {"error": result.stderr or "Screenshot failed"}
        else:
            # Linux/Mac - use scrot or screencapture
            if platform.system() == "Darwin":
                subprocess.run(["screencapture", str(filepath)], timeout=10)
            else:
                subprocess.run(["scrot", str(filepath)], timeout=10)

        if filepath.exists():
            return {"path": str(filepath), "size": filepath.stat().st_size}
        return {"error": "Screenshot file not created"}

    except subprocess.TimeoutExpired:
        return {"error": "Screenshot timed out"}
    except Exception as e:
        return {"error": str(e)}


def screenshot_window(title: Optional[str] = None) -> dict:
    """
    Take a screenshot of a specific window by title.

    Args:
        title: Window title to capture (partial match)

    Returns:
        Path to saved screenshot
    """
    if not config.get("screenshots.enabled", True):
        return {"error": "Screenshots disabled in config"}

    ss_dir = _get_screenshot_dir()
    fmt = _get_format()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        if platform.system() == "Windows":
            # Find window and capture it
            if title:
                safe_title = title.replace('"', '`"')
                filename = f"window_{title[:20].replace(' ', '_')}_{timestamp}.{fmt}"
            else:
                safe_title = ""
                filename = f"window_active_{timestamp}.{fmt}"

            filepath = ss_dir / filename

            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {{
                [DllImport("user32.dll")]
                public static extern IntPtr GetForegroundWindow();
                [DllImport("user32.dll")]
                public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
            }}
            public struct RECT {{
                public int Left, Top, Right, Bottom;
            }}
"@

            $hwnd = [Win32]::GetForegroundWindow()
            $rect = New-Object RECT
            [Win32]::GetWindowRect($hwnd, [ref]$rect)

            $width = $rect.Right - $rect.Left
            $height = $rect.Bottom - $rect.Top

            $bitmap = New-Object System.Drawing.Bitmap($width, $height)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, [System.Drawing.Size]::new($width, $height))
            $bitmap.Save("{filepath}")
            $graphics.Dispose()
            $bitmap.Dispose()
            '''
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return {"error": result.stderr or "Window capture failed"}

            if filepath.exists():
                return {"path": str(filepath), "size": filepath.stat().st_size}
            return {"error": "Screenshot file not created"}
        else:
            return {"error": "Window capture only supported on Windows currently"}

    except Exception as e:
        return {"error": str(e)}


def screenshot_url(url: str, full_page: bool = True, filename: Optional[str] = None) -> dict:
    """
    Take a screenshot of a web page.

    Args:
        url: URL to screenshot
        full_page: Capture entire scrollable page
        filename: Optional custom filename

    Returns:
        Path to saved screenshot
    """
    if not config.get("screenshots.enabled", True):
        return {"error": "Screenshots disabled in config"}

    ss_dir = _get_screenshot_dir()
    fmt = _get_format()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not filename:
        # Create filename from URL
        safe_url = url.replace("https://", "").replace("http://", "")
        safe_url = "".join(c if c.isalnum() else "_" for c in safe_url)[:30]
        filename = f"web_{safe_url}_{timestamp}.{fmt}"

    filepath = ss_dir / filename

    try:
        # Try playwright first (best quality)
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.screenshot(path=str(filepath), full_page=full_page)
                browser.close()

            if filepath.exists():
                return {"path": str(filepath), "url": url, "size": filepath.stat().st_size}

        except ImportError:
            pass

        # Fallback to selenium if playwright not available
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            driver = webdriver.Chrome(options=options)
            driver.get(url)

            if full_page:
                # Get full page height
                height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1920, height)

            driver.save_screenshot(str(filepath))
            driver.quit()

            if filepath.exists():
                return {"path": str(filepath), "url": url, "size": filepath.stat().st_size}

        except ImportError:
            return {"error": "No web screenshot library available. Install playwright or selenium."}

        return {"error": "Screenshot file not created"}

    except Exception as e:
        return {"error": str(e)}


def list_screenshots(limit: int = 20) -> dict:
    """
    List recent screenshots.

    Args:
        limit: Maximum number to return

    Returns:
        List of screenshot files
    """
    ss_dir = _get_screenshot_dir()

    files = []
    for f in sorted(ss_dir.glob("*.*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            files.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
            if len(files) >= limit:
                break

    return {"screenshots": files, "count": len(files)}


# Register tools
register_tool(
    name="screenshot_desktop",
    description="Take a screenshot of the entire desktop",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Custom filename"},
        },
        "required": [],
    },
    func=screenshot_desktop,
)

register_tool(
    name="screenshot_window",
    description="Take a screenshot of the active or specified window",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Window title to capture"},
        },
        "required": [],
    },
    func=screenshot_window,
)

register_tool(
    name="screenshot_url",
    description="Take a screenshot of a web page",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to screenshot"},
            "full_page": {"type": "boolean", "description": "Capture full page", "default": True},
            "filename": {"type": "string", "description": "Custom filename"},
        },
        "required": ["url"],
    },
    func=screenshot_url,
)

register_tool(
    name="list_screenshots",
    description="List recent screenshots",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max to return", "default": 20},
        },
        "required": [],
    },
    func=list_screenshots,
)
