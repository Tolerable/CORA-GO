"""
CORA-GO Vision Tools
Camera capture and image analysis.
"""

import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from . import register_tool
from ..config import config


def _is_configured() -> bool:
    """Check if vision is enabled."""
    return config.get("vision.enabled", False)


def _get_snapshot_dir() -> Path:
    """Get snapshot storage directory."""
    snapshot_dir = config.get("vision.snapshot_dir", "snapshots")
    # Relative to anchor directory
    ss_dir = Path(__file__).parent.parent / snapshot_dir
    ss_dir.mkdir(exist_ok=True)
    return ss_dir


def check_vision() -> dict:
    """Check camera availability."""
    cameras = config.get("vision.cameras", [])

    if not cameras:
        # Try to detect cameras
        detected = detect_cameras()
        if "cameras" in detected:
            cameras = detected["cameras"]

    return {
        "enabled": _is_configured(),
        "cameras": cameras,
        "default_camera": config.get("vision.default_camera", 0),
        "snapshot_dir": str(_get_snapshot_dir())
    }


def detect_cameras() -> dict:
    """
    Detect available cameras.

    Returns:
        List of detected cameras
    """
    cameras = []

    try:
        import cv2

        # Try indices 0-5
        for i in range(6):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Get camera info if possible
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cameras.append({
                    "index": i,
                    "name": f"Camera {i}",
                    "resolution": f"{width}x{height}"
                })
                cap.release()

        return {"cameras": cameras, "count": len(cameras)}

    except ImportError:
        return {"error": "opencv-python not installed. Run: pip install opencv-python"}
    except Exception as e:
        return {"error": str(e)}


def capture(camera: Optional[int] = None, filename: Optional[str] = None) -> dict:
    """
    Capture a frame from camera.

    Args:
        camera: Camera index (uses default if not specified)
        filename: Optional custom filename

    Returns:
        Path to saved image
    """
    if not _is_configured():
        return {"error": "Vision not enabled. Set vision.enabled=true in config."}

    if camera is None:
        camera = config.get("vision.default_camera", 0)

    # Verify camera is in configured list
    cameras = config.get("vision.cameras", [])
    if cameras and not any(c.get("index") == camera for c in cameras):
        return {"error": f"Camera {camera} not in configured cameras"}

    snapshot_dir = _get_snapshot_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not filename:
        filename = f"snap_cam{camera}_{timestamp}.jpg"

    filepath = snapshot_dir / filename

    try:
        import cv2

        cap = cv2.VideoCapture(camera)
        if not cap.isOpened():
            return {"error": f"Could not open camera {camera}"}

        # Capture frame
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return {"error": "Failed to capture frame"}

        # Save image
        cv2.imwrite(str(filepath), frame)

        if filepath.exists():
            return {
                "path": str(filepath),
                "camera": camera,
                "size": filepath.stat().st_size,
                "resolution": f"{frame.shape[1]}x{frame.shape[0]}"
            }
        return {"error": "Failed to save image"}

    except ImportError:
        return {"error": "opencv-python not installed"}
    except Exception as e:
        return {"error": str(e)}


def look(camera: Optional[int] = None) -> dict:
    """
    Capture image and describe what's seen using AI vision.

    Args:
        camera: Camera index

    Returns:
        Description of what's seen
    """
    if not _is_configured():
        return {"error": "Vision not enabled"}

    # Capture image first
    capture_result = capture(camera=camera)
    if "error" in capture_result:
        return capture_result

    image_path = capture_result["path"]

    # Use Ollama vision model to describe
    ollama_url = config.get("ai.ollama_url", "http://localhost:11434")
    vision_model = config.get("ai.ollama_vision", "llava:7b")

    try:
        import base64
        import json
        import urllib.request

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # Query Ollama
        payload = {
            "model": vision_model,
            "prompt": "Describe what you see in this image in 2-3 sentences.",
            "images": [image_data],
            "stream": False
        }

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.load(resp)
            description = result.get("response", "")

        return {
            "description": description,
            "image_path": image_path,
            "camera": camera or config.get("vision.default_camera", 0),
            "model": vision_model
        }

    except Exception as e:
        return {
            "error": f"Vision analysis failed: {e}",
            "image_path": image_path,
            "note": "Image captured but analysis failed"
        }


def look_and_tell(camera: Optional[int] = None) -> dict:
    """
    Look through camera and speak what's seen.

    Args:
        camera: Camera index

    Returns:
        Description that was spoken
    """
    # Get description
    result = look(camera=camera)

    if "error" in result and "description" not in result:
        return result

    description = result.get("description", "")
    if description:
        # Speak it
        from .voice import speak
        speak(f"I see: {description[:200]}", block=False)
        result["spoken"] = True

    return result


def list_snapshots(limit: int = 20) -> dict:
    """
    List recent snapshots.

    Args:
        limit: Maximum to return

    Returns:
        List of snapshot files
    """
    snapshot_dir = _get_snapshot_dir()

    files = []
    for f in sorted(snapshot_dir.glob("*.jpg"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            "name": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
        if len(files) >= limit:
            break

    return {"snapshots": files, "count": len(files)}


# Register tools
register_tool(
    name="check_vision",
    description="Check camera availability and vision configuration",
    parameters={"type": "object", "properties": {}, "required": []},
    func=check_vision,
)

register_tool(
    name="detect_cameras",
    description="Detect available cameras connected to the system",
    parameters={"type": "object", "properties": {}, "required": []},
    func=detect_cameras,
)

register_tool(
    name="capture",
    description="Capture a photo from camera",
    parameters={
        "type": "object",
        "properties": {
            "camera": {"type": "integer", "description": "Camera index"},
            "filename": {"type": "string", "description": "Custom filename"},
        },
        "required": [],
    },
    func=capture,
)

register_tool(
    name="look",
    description="Capture image and describe what's seen using AI vision",
    parameters={
        "type": "object",
        "properties": {
            "camera": {"type": "integer", "description": "Camera index"},
        },
        "required": [],
    },
    func=look,
)

register_tool(
    name="look_and_tell",
    description="Look through camera and speak what's seen",
    parameters={
        "type": "object",
        "properties": {
            "camera": {"type": "integer", "description": "Camera index"},
        },
        "required": [],
    },
    func=look_and_tell,
)

register_tool(
    name="list_snapshots",
    description="List recent camera snapshots",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max to return", "default": 20},
        },
        "required": [],
    },
    func=list_snapshots,
)
