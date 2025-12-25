"""
CORA-GO Hearing Tools
Speech recognition and voice input.
"""

from typing import Optional, Callable, List
from . import register_tool
from ..config import config


def _is_configured() -> bool:
    """Check if hearing is enabled."""
    return config.get("hearing.enabled", False)


def _get_recognizer():
    """Get speech recognizer instance."""
    try:
        import speech_recognition as sr
        return sr.Recognizer()
    except ImportError:
        return None


def check_hearing() -> dict:
    """Check if speech recognition is available."""
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()

        # List available mics
        mics = sr.Microphone.list_microphone_names()
        configured_mic = config.get("hearing.mic_index")

        return {
            "available": True,
            "enabled": _is_configured(),
            "microphones": mics[:10],  # Limit list
            "configured_mic": configured_mic,
            "wake_word": config.get("hearing.wake_word", "cora")
        }

    except ImportError:
        return {
            "available": False,
            "error": "speech_recognition not installed. Run: pip install SpeechRecognition"
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def list_microphones() -> dict:
    """List available microphones."""
    try:
        import speech_recognition as sr
        mics = sr.Microphone.list_microphone_names()
        return {
            "microphones": [
                {"index": i, "name": name}
                for i, name in enumerate(mics)
            ]
        }
    except ImportError:
        return {"error": "speech_recognition not installed"}
    except Exception as e:
        return {"error": str(e)}


def listen(timeout: Optional[int] = None, phrase_limit: Optional[int] = None) -> dict:
    """
    Listen for speech and convert to text.

    Args:
        timeout: Seconds to wait for speech start
        phrase_limit: Max seconds of speech to capture

    Returns:
        Recognized text
    """
    if not _is_configured():
        return {"error": "Hearing not enabled. Set hearing.enabled=true in config."}

    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        mic_index = config.get("hearing.mic_index")
        timeout = timeout or config.get("hearing.timeout", 10)
        phrase_limit = phrase_limit or config.get("hearing.phrase_limit", 15)

        mic_kwargs = {"device_index": mic_index} if mic_index is not None else {}

        with sr.Microphone(**mic_kwargs) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            # Listen
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit
            )

            # Recognize using Google (free, no API key)
            text = recognizer.recognize_google(audio)
            return {"text": text, "source": "google"}

    except ImportError:
        return {"error": "speech_recognition not installed"}
    except Exception as e:
        error_type = type(e).__name__
        if "WaitTimeoutError" in error_type:
            return {"error": "No speech detected (timeout)"}
        elif "UnknownValueError" in error_type:
            return {"error": "Could not understand audio"}
        elif "RequestError" in error_type:
            return {"error": "Speech recognition service unavailable"}
        return {"error": str(e)}


def listen_for_wake(timeout: int = 30) -> dict:
    """
    Listen until wake word is detected.

    Args:
        timeout: Max seconds to listen

    Returns:
        Full phrase containing wake word
    """
    if not _is_configured():
        return {"error": "Hearing not enabled"}

    wake_word = config.get("hearing.wake_word", "cora").lower()

    try:
        import speech_recognition as sr
        import time

        recognizer = sr.Recognizer()
        mic_index = config.get("hearing.mic_index")
        mic_kwargs = {"device_index": mic_index} if mic_index is not None else {}

        start_time = time.time()

        with sr.Microphone(**mic_kwargs) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            while time.time() - start_time < timeout:
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    text = recognizer.recognize_google(audio)

                    if wake_word in text.lower():
                        return {
                            "detected": True,
                            "wake_word": wake_word,
                            "full_text": text
                        }

                except Exception:
                    continue  # Keep listening

        return {"detected": False, "timeout": True}

    except ImportError:
        return {"error": "speech_recognition not installed"}
    except Exception as e:
        return {"error": str(e)}


def ask_and_listen(question: str, timeout: Optional[int] = None) -> dict:
    """
    Speak a question via TTS, then listen for response.

    Args:
        question: Question to ask
        timeout: Seconds to wait for response

    Returns:
        Response text
    """
    if not _is_configured():
        return {"error": "Hearing not enabled"}

    # Speak the question first
    from .voice import speak
    speak_result = speak(question, block=True)

    if "error" in speak_result:
        return {"error": f"TTS failed: {speak_result['error']}"}

    # Add a small delay
    import time
    time.sleep(0.5)

    # Listen for response
    return listen(timeout=timeout)


# Register tools
register_tool(
    name="check_hearing",
    description="Check if speech recognition is available and configured",
    parameters={"type": "object", "properties": {}, "required": []},
    func=check_hearing,
)

register_tool(
    name="list_microphones",
    description="List available microphones for speech input",
    parameters={"type": "object", "properties": {}, "required": []},
    func=list_microphones,
)

register_tool(
    name="listen",
    description="Listen for speech and convert to text",
    parameters={
        "type": "object",
        "properties": {
            "timeout": {"type": "integer", "description": "Seconds to wait for speech"},
            "phrase_limit": {"type": "integer", "description": "Max seconds of speech"},
        },
        "required": [],
    },
    func=listen,
)

register_tool(
    name="listen_for_wake",
    description="Listen until wake word is detected",
    parameters={
        "type": "object",
        "properties": {
            "timeout": {"type": "integer", "description": "Max seconds to listen", "default": 30},
        },
        "required": [],
    },
    func=listen_for_wake,
)

register_tool(
    name="ask_and_listen",
    description="Speak a question via TTS, then listen for spoken response",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question to ask"},
            "timeout": {"type": "integer", "description": "Seconds to wait for response"},
        },
        "required": ["question"],
    },
    func=ask_and_listen,
)
