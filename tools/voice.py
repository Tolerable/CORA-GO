"""
CORA-GO Voice Operations
Kokoro TTS (browser) + Web Speech API (STT)
Local fallback: pyttsx3
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional


# Check for local TTS engines
_tts_engine = None


def _get_local_tts():
    """Get local TTS engine (pyttsx3 fallback)."""
    global _tts_engine
    if _tts_engine is None:
        try:
            import pyttsx3
            _tts_engine = pyttsx3.init()
        except ImportError:
            _tts_engine = False
    return _tts_engine if _tts_engine else None


def speak_local(text: str, rate: int = 150, voice_id: Optional[str] = None) -> str:
    """
    Speak text using local TTS (pyttsx3).

    Args:
        text: Text to speak
        rate: Speech rate (words per minute)
        voice_id: Voice identifier (optional)
    """
    engine = _get_local_tts()
    if not engine:
        return "Error: pyttsx3 not installed. Run: pip install pyttsx3"

    try:
        engine.setProperty('rate', rate)

        if voice_id:
            engine.setProperty('voice', voice_id)

        engine.say(text)
        engine.runAndWait()

        return f"Spoke: {text[:50]}..."
    except Exception as e:
        return f"TTS error: {e}"


def list_voices() -> str:
    """List available local TTS voices."""
    engine = _get_local_tts()
    if not engine:
        return "Error: pyttsx3 not installed"

    try:
        voices = engine.getProperty('voices')
        result = ["Available voices:"]
        for i, voice in enumerate(voices):
            name = voice.name
            lang = getattr(voice, 'languages', ['?'])[0] if hasattr(voice, 'languages') else '?'
            result.append(f"  {i}: {name} ({lang})")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing voices: {e}"


def speak_espeak(text: str, voice: str = "en", speed: int = 150) -> str:
    """
    Speak using espeak (cross-platform fallback).

    Args:
        text: Text to speak
        voice: Voice/language code
        speed: Words per minute
    """
    try:
        result = subprocess.run(
            ['espeak', '-v', voice, '-s', str(speed), text],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return f"Spoke: {text[:50]}..."
        else:
            return f"espeak error: {result.stderr}"
    except FileNotFoundError:
        return "Error: espeak not installed"
    except Exception as e:
        return f"espeak error: {e}"


def speak_say(text: str, voice: Optional[str] = None) -> str:
    """
    Speak using macOS 'say' command.

    Args:
        text: Text to speak
        voice: Voice name (optional)
    """
    try:
        cmd = ['say']
        if voice:
            cmd.extend(['-v', voice])
        cmd.append(text)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return f"Spoke: {text[:50]}..."
        else:
            return f"say error: {result.stderr}"
    except FileNotFoundError:
        return "Error: 'say' command not available (macOS only)"
    except Exception as e:
        return f"say error: {e}"


def text_to_audio(
    text: str,
    output_path: Optional[str] = None,
    voice: str = "en"
) -> str:
    """
    Convert text to audio file using espeak.

    Args:
        text: Text to convert
        output_path: Where to save WAV file
        voice: Voice/language code
    """
    try:
        if output_path:
            path = Path(output_path)
        else:
            path = Path(tempfile.gettempdir()) / f"cora_tts_{hash(text) % 100000}.wav"

        result = subprocess.run(
            ['espeak', '-v', voice, '-w', str(path), text],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and path.exists():
            return f"Audio saved: {path}"
        else:
            return f"Error creating audio: {result.stderr}"
    except FileNotFoundError:
        return "Error: espeak not installed"
    except Exception as e:
        return f"Audio error: {e}"


def transcribe_audio(audio_path: str, model: str = "base") -> str:
    """
    Transcribe audio file using Whisper.

    Args:
        audio_path: Path to audio file
        model: Whisper model (tiny, base, small, medium, large)
    """
    try:
        path = Path(audio_path).expanduser().resolve()
        if not path.exists():
            return f"Error: Audio file not found: {audio_path}"

        # Try whisper CLI
        result = subprocess.run(
            ['whisper', str(path), '--model', model, '--output_format', 'txt'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # Look for output file
            txt_path = path.with_suffix('.txt')
            if txt_path.exists():
                transcript = txt_path.read_text().strip()
                return f"Transcript: {transcript}"
            return "Transcription complete (check output directory)"
        else:
            return f"Whisper error: {result.stderr}"
    except FileNotFoundError:
        return "Error: Whisper not installed. Run: pip install openai-whisper"
    except subprocess.TimeoutExpired:
        return "Error: Transcription timed out"
    except Exception as e:
        return f"Transcription error: {e}"


def record_audio(duration: float = 5.0, output_path: Optional[str] = None) -> str:
    """
    Record audio from microphone.

    Args:
        duration: Recording duration in seconds
        output_path: Where to save WAV file
    """
    try:
        import pyaudio
        import wave

        if output_path:
            path = Path(output_path)
        else:
            import time
            path = Path(tempfile.gettempdir()) / f"cora_rec_{int(time.time())}.wav"

        # Recording parameters
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        p = pyaudio.PyAudio()

        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        frames = []
        num_chunks = int(RATE / CHUNK * duration)

        for _ in range(num_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save to file
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

        return f"Recorded {duration}s to: {path}"
    except ImportError:
        return "Error: pyaudio not installed. Run: pip install pyaudio"
    except Exception as e:
        return f"Recording error: {e}"


def listen_and_transcribe(duration: float = 5.0) -> str:
    """
    Record audio and transcribe it.

    Args:
        duration: How long to listen (seconds)
    """
    # Record
    record_result = record_audio(duration)
    if record_result.startswith("Error"):
        return record_result

    # Extract path
    if "to: " in record_result:
        audio_path = record_result.split("to: ")[1]
    else:
        return "Error: Could not find recorded file path"

    # Transcribe
    return transcribe_audio(audio_path)


# Browser TTS info (for web interface)
KOKORO_INFO = """
Kokoro TTS runs in browser via JavaScript.

Usage in web/js/app.js:
- Uses Web Speech API as primary
- Falls back to Kokoro for better quality voices

Kokoro setup:
1. Include kokoro.js in index.html
2. Initialize: const kokoro = new Kokoro()
3. Speak: kokoro.speak(text, {voice: 'af_bella', rate: 1.0})

Available Kokoro voices:
- af_bella, af_sarah, af_nicole (female)
- am_adam, am_michael (male)
- bf_emma, bf_isabella (British female)
- bm_george, bm_lewis (British male)

Web Speech API (fallback):
- const synth = window.speechSynthesis
- const utterance = new SpeechSynthesisUtterance(text)
- synth.speak(utterance)
"""


def get_tts_info() -> str:
    """Get info about available TTS options."""
    lines = ["CORA-GO TTS Options:", ""]

    # Check pyttsx3
    engine = _get_local_tts()
    if engine:
        lines.append("pyttsx3: Available (local)")
    else:
        lines.append("pyttsx3: Not installed")

    # Check espeak
    try:
        result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            lines.append("espeak: Available")
    except:
        lines.append("espeak: Not installed")

    # Check whisper
    try:
        result = subprocess.run(['whisper', '--help'], capture_output=True, timeout=5)
        lines.append("whisper: Available (for STT)")
    except:
        lines.append("whisper: Not installed")

    lines.append("")
    lines.append("Browser: Kokoro TTS + Web Speech API")

    return "\n".join(lines)
