"""
CORA-GO Voice Tools
TTS via Kokoro (neural) with pyttsx3/PowerShell fallbacks.
Non-blocking, queue-based speech.
"""

import threading
import queue
import subprocess
from typing import Optional
from . import register_tool

# TTS engine state
_tts_queue: queue.Queue = queue.Queue()
_tts_thread: Optional[threading.Thread] = None
_tts_engine = None
_tts_available = False
_engine_type = "none"


def _init_tts():
    """Initialize TTS engine. Try Kokoro → pyttsx3 → PowerShell."""
    global _tts_engine, _tts_available, _engine_type
    
    # Try Kokoro first (best quality)
    try:
        from kokoro_onnx import Kokoro
        _tts_engine = Kokoro("af_bella")  # Neural voice
        _tts_available = True
        _engine_type = "kokoro"
        return
    except Exception:
        pass
    
    # Try pyttsx3 (cross-platform)
    try:
        import pyttsx3
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty('rate', 180)
        _tts_available = True
        _engine_type = "pyttsx3"
        return
    except Exception:
        pass
    
    # Fallback to PowerShell (Windows only)
    try:
        result = subprocess.run(
            ["powershell", "-Command", "echo test"],
            capture_output=True, timeout=2
        )
        if result.returncode == 0:
            _tts_available = True
            _engine_type = "powershell"
            return
    except Exception:
        pass
    
    _tts_available = False
    _engine_type = "none"


def _tts_worker():
    """Background thread that processes TTS queue."""
    while True:
        try:
            text = _tts_queue.get(timeout=1)
            if text is None:  # Shutdown signal
                break
            _speak_sync(text)
            _tts_queue.task_done()
        except queue.Empty:
            continue
        except Exception:
            continue


def _speak_sync(text: str):
    """Synchronous speech (called from worker thread)."""
    global _tts_engine, _engine_type
    
    if _engine_type == "kokoro":
        try:
            import sounddevice as sd
            audio = _tts_engine.create(text)
            sd.play(audio, samplerate=24000)
            sd.wait()
        except Exception:
            pass
    
    elif _engine_type == "pyttsx3":
        try:
            _tts_engine.say(text)
            _tts_engine.runAndWait()
        except Exception:
            pass
    
    elif _engine_type == "powershell":
        try:
            # Escape for PowerShell
            safe_text = text.replace('"', '`"').replace("'", "`'")[:500]
            cmd = f'''Add-Type -AssemblyName System.Speech; 
                      $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; 
                      $s.Speak("{safe_text}")'''
            subprocess.run(["powershell", "-Command", cmd], 
                         capture_output=True, timeout=30)
        except Exception:
            pass


def speak(text: str, block: bool = False) -> dict:
    """
    Speak text via TTS.
    
    Args:
        text: Text to speak
        block: Wait for speech to complete
    
    Returns:
        dict with status
    """
    global _tts_thread, _tts_available
    
    if not _tts_available:
        _init_tts()
    
    if not _tts_available:
        return {"error": "TTS not available", "engine": "none"}
    
    # Start worker thread if needed
    if _tts_thread is None or not _tts_thread.is_alive():
        _tts_thread = threading.Thread(target=_tts_worker, daemon=True)
        _tts_thread.start()
    
    _tts_queue.put(text)
    
    if block:
        _tts_queue.join()
    
    return {"status": "speaking", "text": text[:50], "engine": _engine_type}


def check_tts() -> dict:
    """Check TTS availability and engine type."""
    global _tts_available, _engine_type
    if not _tts_available:
        _init_tts()
    return {
        "available": _tts_available,
        "engine": _engine_type,
    }


def stop_speaking() -> dict:
    """Clear TTS queue (stop pending speech)."""
    while not _tts_queue.empty():
        try:
            _tts_queue.get_nowait()
        except queue.Empty:
            break
    return {"status": "stopped"}


# Register tools for function calling
register_tool(
    name="speak",
    description="Speak text aloud using text-to-speech",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to speak"},
            "block": {"type": "boolean", "description": "Wait for completion", "default": False},
        },
        "required": ["text"],
    },
    func=speak,
)

register_tool(
    name="check_tts",
    description="Check if text-to-speech is available",
    parameters={"type": "object", "properties": {}, "required": []},
    func=check_tts,
)
