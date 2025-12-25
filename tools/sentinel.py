"""
CORA-GO Sentinel - Audio Monitoring
Ambient listening, speech detection, transcription, incident logging
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


# Sentinel directories
SENTINEL_DIR = Path.home() / ".cora-go" / "sentinel"
INCIDENTS_DIR = SENTINEL_DIR / "incidents"
WORKING_DIR = SENTINEL_DIR / "working"
CONFIG_FILE = SENTINEL_DIR / "config.json"
LOG_FILE = SENTINEL_DIR / "activity.log"

# Global state
_sentinel_process: Optional[subprocess.Popen] = None
_is_monitoring = False


DEFAULT_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size": 1024,
    "device_index": None,  # Auto-detect
    "buffer_seconds": 30,
    "pre_roll_seconds": 2,
    "post_roll_seconds": 1,
    "silence_threshold": 500,
    "silence_duration_ms": 800,
    "min_speech_ms": 500,
    "wake_words": ["hey cora", "ok cora", "computer", "assistant"],
    "interest_patterns": {
        "safety": ["intruder", "break in", "fire", "emergency", "help", "alarm"],
        "ai_dev": ["claude", "ai", "bot", "automation", "agent", "model", "gpt"],
        "opportunity": ["deal", "discount", "free", "offer", "money"],
        "work": ["project", "deadline", "client", "meeting", "task"],
        "meta": ["listening", "recording", "that machine", "the computer"]
    },
    "use_ollama": True,
    "ollama_model": "llama3.2:1b",
    "transcription_method": "whisper",
    "auto_delete_days": 7,
    "verbose": False
}


def _ensure_dirs():
    """Create required directories."""
    for d in [SENTINEL_DIR, INCIDENTS_DIR, WORKING_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _load_config() -> Dict[str, Any]:
    """Load or create config."""
    _ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text())
            return {**DEFAULT_CONFIG, **saved}
        except:
            pass
    return DEFAULT_CONFIG.copy()


def _save_config(config: Dict[str, Any]):
    """Save config to file."""
    _ensure_dirs()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _log(msg: str, level: str = "INFO"):
    """Log message to file and optionally stdout."""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")


def start_sentinel(quiet: bool = False, device: Optional[int] = None) -> str:
    """
    Start the Audio Sentinel monitoring.

    Args:
        quiet: Reduce console output
        device: Audio input device index (optional)
    """
    global _sentinel_process, _is_monitoring

    if _is_monitoring and _sentinel_process and _sentinel_process.poll() is None:
        return f"Sentinel already running (PID: {_sentinel_process.pid})"

    _ensure_dirs()
    config = _load_config()

    if device is not None:
        config['device_index'] = device
        _save_config(config)

    # Check for pyaudio
    try:
        import pyaudio
    except ImportError:
        return "Error: pyaudio not installed. Run: pip install pyaudio"

    # Start monitoring in background thread
    def monitor_loop():
        global _is_monitoring
        _is_monitoring = True

        try:
            import wave
            import struct

            p = pyaudio.PyAudio()
            device_idx = config.get('device_index')

            stream = p.open(
                format=pyaudio.paInt16,
                channels=config['channels'],
                rate=config['sample_rate'],
                input=True,
                input_device_index=device_idx,
                frames_per_buffer=config['chunk_size']
            )

            _log("Sentinel started")

            audio_buffer = []
            is_recording = False
            silence_start = None
            current_event = []

            while _is_monitoring:
                try:
                    data = stream.read(config['chunk_size'], exception_on_overflow=False)
                    audio_buffer.append(data)

                    # Keep buffer limited
                    max_chunks = int(config['buffer_seconds'] * config['sample_rate'] / config['chunk_size'])
                    if len(audio_buffer) > max_chunks:
                        audio_buffer.pop(0)

                    # Calculate RMS amplitude
                    count = len(data) // 2
                    shorts = struct.unpack(f"{count}h", data)
                    rms = (sum(s * s for s in shorts) / count) ** 0.5 if count > 0 else 0

                    is_speech = rms > config['silence_threshold']

                    if is_speech:
                        if not is_recording:
                            # Start recording with pre-roll
                            is_recording = True
                            pre_chunks = int(config['pre_roll_seconds'] * config['sample_rate'] / config['chunk_size'])
                            current_event = audio_buffer[-pre_chunks:]
                            _log("Speech detected - recording")

                        current_event.append(data)
                        silence_start = None

                    elif is_recording:
                        current_event.append(data)

                        if silence_start is None:
                            silence_start = time.time()
                        elif (time.time() - silence_start) * 1000 > config['silence_duration_ms']:
                            # End recording
                            is_recording = False
                            _log(f"Silence - processing {len(current_event)} chunks")

                            # Process in background
                            event_copy = current_event.copy()
                            threading.Thread(
                                target=_process_audio_event,
                                args=(event_copy, config)
                            ).start()

                            current_event = []
                            silence_start = None

                except Exception as e:
                    _log(f"Audio read error: {e}", "ERROR")
                    time.sleep(0.1)

            stream.stop_stream()
            stream.close()
            p.terminate()
            _log("Sentinel stopped")

        except Exception as e:
            _log(f"Sentinel error: {e}", "ERROR")
            _is_monitoring = False

    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()

    # Give it a moment to start
    time.sleep(0.5)

    if _is_monitoring:
        return "Sentinel started - monitoring audio"
    else:
        return "Sentinel failed to start - check logs"


def stop_sentinel() -> str:
    """Stop the Audio Sentinel monitoring."""
    global _is_monitoring, _sentinel_process

    if _sentinel_process and _sentinel_process.poll() is None:
        _sentinel_process.terminate()
        _sentinel_process = None

    if _is_monitoring:
        _is_monitoring = False
        _log("Sentinel stopping")
        return "Sentinel stopped"

    return "Sentinel not running"


def sentinel_status() -> str:
    """Check Sentinel status and recent activity."""
    global _is_monitoring

    status = f"Sentinel: {'RUNNING' if _is_monitoring else 'STOPPED'}"

    # Check incidents
    _ensure_dirs()
    incidents = list(INCIDENTS_DIR.glob("*.json"))
    status += f"\nIncidents: {len(incidents)} total"

    if incidents:
        # Show recent 5
        recent = sorted(incidents, reverse=True)[:5]
        status += "\nRecent:"
        for inc_file in recent:
            try:
                data = json.loads(inc_file.read_text())
                cat = data.get('category', '?')[:10]
                txt = data.get('transcript', '')[:40]
                ts = data.get('timestamp', '')[:10]
                status += f"\n  [{cat}] {ts} - {txt}..."
            except:
                pass

    return status


def get_incidents(
    category: Optional[str] = None,
    since: str = "24h"
) -> str:
    """
    Get saved audio incidents.

    Args:
        category: Filter by category (safety, ai_dev, opportunity, work, meta)
        since: Timeframe (1h, 24h, 7d)
    """
    _ensure_dirs()
    incidents = list(INCIDENTS_DIR.glob("*.json"))

    if not incidents:
        return "No incidents recorded"

    # Parse timeframe
    now = datetime.now()
    if since.endswith('h'):
        cutoff = now - timedelta(hours=int(since[:-1]))
    elif since.endswith('d'):
        cutoff = now - timedelta(days=int(since[:-1]))
    else:
        cutoff = now - timedelta(hours=24)

    results = []
    for inc_file in sorted(incidents, reverse=True):
        try:
            data = json.loads(inc_file.read_text())

            # Time filter
            ts = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
            if ts < cutoff:
                continue

            # Category filter
            if category and data.get('category', '').lower() != category.lower():
                continue

            cat = data.get('category', '?')
            txt = data.get('transcript', '')[:60]
            results.append(f"[{cat}] {ts.strftime('%m-%d %H:%M')} - {txt}...")

        except:
            pass

    if not results:
        msg = f"No incidents in last {since}"
        if category:
            msg += f" with category '{category}'"
        return msg

    return f"Incidents ({len(results)}):\n" + "\n".join(results[:20])


def _process_audio_event(audio_chunks: List[bytes], config: Dict[str, Any]):
    """Process a detected audio event (runs in background thread)."""
    try:
        import wave
        import tempfile

        # Check minimum duration
        duration_sec = len(audio_chunks) * config['chunk_size'] / config['sample_rate']
        if duration_sec < 0.5:
            return

        # Save to temp file
        temp_file = WORKING_DIR / f"temp_{int(time.time())}.wav"
        with wave.open(str(temp_file), 'wb') as wf:
            wf.setnchannels(config['channels'])
            wf.setsampwidth(2)
            wf.setframerate(config['sample_rate'])
            wf.writeframes(b''.join(audio_chunks))

        # Transcribe with Whisper
        transcript = None
        try:
            result = subprocess.run(
                ['whisper', str(temp_file), '--model', 'base', '--output_format', 'txt',
                 '--output_dir', str(WORKING_DIR)],
                capture_output=True, text=True, timeout=60
            )
            txt_file = WORKING_DIR / (temp_file.stem + '.txt')
            if txt_file.exists():
                transcript = txt_file.read_text().strip()
                txt_file.unlink()
        except:
            pass

        # Clean up temp audio
        temp_file.unlink()

        if not transcript or len(transcript) < 3:
            return

        # Check for wake words
        for wake in config.get('wake_words', []):
            if wake.lower() in transcript.lower():
                _log(f"Wake word detected: {wake}")
                return  # Don't save wake word events

        # Check interest patterns
        category = "general"
        for cat, patterns in config.get('interest_patterns', {}).items():
            for pattern in patterns:
                if pattern.lower() in transcript.lower():
                    category = cat
                    break

        # Save incident
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_cat = category.replace('|', '_').replace('/', '_')[:25]

        meta = {
            "id": timestamp,
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "transcript": transcript,
            "duration_seconds": duration_sec
        }

        meta_file = INCIDENTS_DIR / f"{timestamp}_{safe_cat}.json"
        meta_file.write_text(json.dumps(meta, indent=2))

        _log(f"Saved incident: {category} - {transcript[:50]}...")

    except Exception as e:
        _log(f"Process event error: {e}", "ERROR")
