#!/usr/bin/env python3
"""
CORA-GO Visual Boot Display
Displays boot sequence progress with audio waveform visualization.

Shows:
- Boot phase progress bars
- System status indicators
- Real-time audio waveform when speaking
- Cyberpunk/goth aesthetic

Ported from Unity AI Lab's CORA project.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import math
import random
import os
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass

# Project directory
_PROJECT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

# Try to import numpy for audio processing
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class BootPhase:
    """Represents a boot phase."""
    name: str
    status: str = "pending"  # pending, running, ok, warn, fail
    message: str = ""


# ============================================================
# AUDIO BUFFER SINGLETON - Shared between TTS and waveform
# ============================================================

class _AudioBufferSingleton:
    """Singleton to share audio data between TTS and waveform."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.data = None
                    cls._instance.current_chunk = None
                    cls._instance.chunk_time = None
                    cls._instance.start_time = None
                    cls._instance.sample_rate = 24000
                    cls._instance.active = False
                    cls._instance.data_lock = threading.Lock()
        return cls._instance


# Single global instance
_audio_buffer_singleton = _AudioBufferSingleton()


def get_audio_buffer():
    """Get the shared audio buffer for waveform visualization."""
    return {
        'data': _audio_buffer_singleton.data,
        'current_chunk': _audio_buffer_singleton.current_chunk,
        'chunk_time': _audio_buffer_singleton.chunk_time,
        'start_time': _audio_buffer_singleton.start_time,
        'sample_rate': _audio_buffer_singleton.sample_rate,
        'active': _audio_buffer_singleton.active,
    }


def set_audio_data(audio_array, sample_rate=24000):
    """Set audio data for waveform visualization (called by TTS)."""
    with _audio_buffer_singleton.data_lock:
        _audio_buffer_singleton.data = audio_array
        _audio_buffer_singleton.start_time = time.time()
        _audio_buffer_singleton.sample_rate = sample_rate
        _audio_buffer_singleton.active = True


def clear_audio_data():
    """Clear audio data when done speaking."""
    with _audio_buffer_singleton.data_lock:
        _audio_buffer_singleton.active = False
        _audio_buffer_singleton.data = None
        _audio_buffer_singleton.current_chunk = None


def set_audio_chunk(chunk):
    """Set the current audio chunk being played RIGHT NOW (called from TTS callback)."""
    with _audio_buffer_singleton.data_lock:
        _audio_buffer_singleton.current_chunk = chunk
        _audio_buffer_singleton.chunk_time = time.time()
        _audio_buffer_singleton.active = True


# ============================================================
# AUDIO WAVEFORM VISUALIZATION
# ============================================================

class AudioWaveform(tk.Canvas):
    """Real-time audio waveform visualization - draws actual wave that follows voice."""

    def __init__(self, parent, width=480, height=100, **kwargs):
        super().__init__(parent, width=width, height=height,
                        bg='#0a0a0a', highlightthickness=1,
                        highlightbackground='#302050', **kwargs)
        self.width = width
        self.height = height
        self.is_playing = False
        self.animation_id = None
        self.num_points = 100  # More points = smoother wave
        self.wave_points = [0.0] * self.num_points
        self.sample_rate = 24000
        self.sample_buffer = [0.0] * self.num_points
        self.phase = 0.0
        self._draw_flat_line()

    def _draw_flat_line(self):
        """Draw a flat center line when idle."""
        self.delete("all")
        center_y = self.height // 2
        self.create_line(0, center_y, self.width, center_y, fill='#301040', width=2)

    def start(self):
        """Start the waveform animation - runs forever."""
        if not self.is_playing:
            self.is_playing = True
            self.wave_points = [0.0] * self.num_points
            self.sample_buffer = [0.0] * self.num_points
            self._animate()

    def stop(self):
        """Stop is a no-op - waveform runs continuously."""
        pass

    def _animate(self):
        """Animate the waveform using real-time audio chunks from TTS."""
        chunk = None
        has_audio = False

        try:
            with _audio_buffer_singleton.data_lock:
                raw_chunk = _audio_buffer_singleton.current_chunk
                chunk_time = _audio_buffer_singleton.chunk_time
                is_active = _audio_buffer_singleton.active

                if chunk_time is not None:
                    time_since_chunk = time.time() - chunk_time
                else:
                    time_since_chunk = 999

                # Accept chunks up to 300ms old
                if raw_chunk is not None and len(raw_chunk) > 0 and time_since_chunk < 0.3 and is_active:
                    has_audio = True
                    if HAS_NUMPY and hasattr(raw_chunk, 'copy'):
                        chunk = raw_chunk.copy()
                    else:
                        chunk = list(raw_chunk)
        except Exception as e:
            pass

        if has_audio and chunk is not None:
            try:
                if HAS_NUMPY:
                    if not isinstance(chunk, np.ndarray):
                        chunk = np.array(chunk, dtype=np.float32)

                    max_val = np.max(np.abs(chunk))
                    if max_val > 1.5:
                        chunk = chunk / 32768.0

                    chunk_len = len(chunk)
                    samples_to_add = min(20, self.num_points // 5)

                    if chunk_len >= samples_to_add:
                        indices = np.linspace(0, chunk_len - 1, samples_to_add, dtype=int)
                        new_samples = chunk[indices]

                        chunk_peak = np.max(np.abs(chunk))
                        if chunk_peak > 0.001:
                            scale_factor = min(0.95 / chunk_peak, 40.0)
                        else:
                            scale_factor = 20.0
                        new_samples = new_samples * scale_factor
                        new_samples = np.clip(new_samples, -1.0, 1.0)
                        self.sample_buffer = self.sample_buffer[samples_to_add:] + list(new_samples)
                else:
                    chunk_len = len(chunk)
                    samples_to_add = min(10, self.num_points // 10)

                    if chunk_len >= samples_to_add:
                        chunk_peak = max(abs(float(x)) for x in chunk)
                        if chunk_peak > 0.001:
                            scale_factor = min(0.95 / chunk_peak, 40.0)
                        else:
                            scale_factor = 20.0

                        step = chunk_len // samples_to_add
                        new_samples = []
                        for i in range(samples_to_add):
                            idx = i * step
                            val = float(chunk[idx]) * scale_factor
                            val = max(-1.0, min(1.0, val))
                            new_samples.append(val)
                        self.sample_buffer = self.sample_buffer[samples_to_add:] + new_samples

                for i in range(self.num_points):
                    target = self.sample_buffer[i]
                    self.wave_points[i] = self.wave_points[i] * 0.3 + target * 0.7

            except Exception:
                for i in range(self.num_points):
                    self.wave_points[i] *= 0.9
        else:
            decay = 0.92
            for i in range(self.num_points):
                self.wave_points[i] *= decay
                self.sample_buffer[i] *= decay

        self._draw_wave()
        self.animation_id = self.after(25, self._animate)

    def _draw_wave(self):
        """Draw the waveform on canvas."""
        self.delete("all")
        actual_width = self.winfo_width()
        if actual_width < 10:
            actual_width = self.width

        center_y = self.height // 2
        max_amp = (self.height // 2) - 5

        self.create_line(0, center_y, actual_width, center_y, fill='#201030', width=1)

        coords = []
        step = actual_width / (self.num_points - 1) if self.num_points > 1 else 1

        for i, amp in enumerate(self.wave_points):
            x = int(i * step)
            y = center_y - int(amp * max_amp)
            coords.extend([x, y])

        if len(coords) >= 4:
            # Outer glow
            self.create_line(*coords, fill='#400060', width=8, smooth=True, splinesteps=16)
            # Mid glow
            self.create_line(*coords, fill='#8000a0', width=5, smooth=True, splinesteps=16)
            # Main wave
            self.create_line(*coords, fill='#ff40ff', width=3, smooth=True, splinesteps=16)
            # Bright core
            self.create_line(*coords, fill='#ffc0ff', width=1, smooth=True, splinesteps=16)


# ============================================================
# BOOT DISPLAY
# ============================================================

class BootDisplay:
    """Visual boot sequence display with waveform, scrolling log, and live stats."""

    def __init__(self):
        self.root = None
        self.phases: List[BootPhase] = []
        self.phase_labels = {}
        self.phase_indicators = {}
        self.status_label = None
        self.waveform = None
        self.progress_var = None
        self.current_text = None
        self.is_speaking = False
        self.log_text = None
        self.log_frame = None

        # Live stats labels
        self.stats_frame = None
        self.cpu_label = None
        self.mem_label = None
        self.disk_label = None
        self.gpu_label = None
        self.gpu_mem_label = None
        self.net_label = None
        self.stats_update_id = None
        self._stats_running = False
        self._stats_data = {}
        self._stats_thread = None

        # Chat input (appears after boot)
        self.chat_frame = None
        self.chat_input = None
        self.send_button = None
        self.boot_complete = False
        self.on_user_input = None

        # Theme colors - dark goth/cyberpunk
        self.bg_color = '#0a0a0a'
        self.fg_color = '#ffffff'
        self.accent_color = '#ff00ff'
        self.accent2_color = '#00ffff'
        self.ok_color = '#00ff88'
        self.warn_color = '#ffaa00'
        self.fail_color = '#ff3333'
        self.pending_color = '#444444'

        # Scalable widgets list
        self._scalable_widgets = []
        self.base_width = 1200
        self.base_height = 800
        self._last_resize_time = 0

    def create_window(self):
        """Create the boot display window."""
        self.root = tk.Tk()
        self.root.title("CORA-GO - Boot Sequence")
        self.root.configure(bg=self.bg_color)

        def on_close():
            self.close()
            import os
            os._exit(0)

        self.root.protocol("WM_DELETE_WINDOW", on_close)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.base_width) // 2
        y = (screen_h - self.base_height) // 2
        self.root.geometry(f"{self.base_width}x{self.base_height}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        self.root.lift()
        self.root.focus_force()

        self.root.bind('<Configure>', self._on_window_resize)

        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)

        # LEFT COLUMN
        left_frame = tk.Frame(main_frame, bg=self.bg_color)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Header
        self.header = tk.Label(
            left_frame, text="CORA-GO",
            font=('Consolas', 42, 'bold'),
            fg=self.accent_color, bg=self.bg_color
        )
        self.header.pack(pady=(5, 0))
        self._scalable_widgets.append((self.header, 42, 'Consolas', 'bold'))

        self.subtitle = tk.Label(
            left_frame, text="Global Outreach - PC Anchor",
            font=('Consolas', 10),
            fg=self.accent2_color, bg=self.bg_color
        )
        self.subtitle.pack(pady=(0, 10))
        self._scalable_widgets.append((self.subtitle, 10, 'Consolas', ''))

        # Waveform
        wave_frame = tk.Frame(left_frame, bg=self.bg_color)
        wave_frame.pack(fill='x', pady=(5, 10))

        self.wave_label = tk.Label(
            wave_frame, text="VOICE SYNTHESIS",
            font=('Consolas', 9),
            fg='#666666', bg=self.bg_color
        )
        self.wave_label.pack(anchor='w')
        self._scalable_widgets.append((self.wave_label, 9, 'Consolas', ''))

        self.waveform = AudioWaveform(wave_frame, width=480, height=100)
        self.waveform.pack(fill='x')
        self.waveform.start()

        # Current speech text
        self.current_text = tk.Label(
            left_frame, text="",
            font=('Consolas', 10, 'italic'),
            fg=self.accent_color, bg=self.bg_color, wraplength=470
        )
        self.current_text.pack(pady=5, fill='x')
        self._scalable_widgets.append((self.current_text, 10, 'Consolas', 'italic'))

        # Progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor='#1a1a1a', background=self.accent_color,
            darkcolor=self.accent_color, lightcolor=self.accent_color,
            bordercolor='#333333'
        )

        self.progress_var = tk.DoubleVar(value=0)
        progress = ttk.Progressbar(
            left_frame, variable=self.progress_var, maximum=100,
            style="Custom.Horizontal.TProgressbar", length=480
        )
        progress.pack(pady=8)

        # Phase indicators - 2 columns
        self.phases_outer = tk.Frame(left_frame, bg=self.bg_color, height=180)
        self.phases_outer.pack(fill='x', pady=5)
        self.phases_outer.pack_propagate(False)

        self.phases_container = tk.Frame(self.phases_outer, bg=self.bg_color)
        self.phases_container.pack(fill='both', expand=True)

        self.phases_col_left = tk.Frame(self.phases_container, bg=self.bg_color)
        self.phases_col_left.pack(side='left', fill='both', expand=True)
        self.phases_col_right = tk.Frame(self.phases_container, bg=self.bg_color)
        self.phases_col_right.pack(side='left', fill='both', expand=True)

        # Status label
        self.status_label = tk.Label(
            left_frame, text="Initializing...",
            font=('Consolas', 12, 'bold'),
            fg=self.accent2_color, bg=self.bg_color
        )
        self.status_label.pack(pady=8)
        self._scalable_widgets.append((self.status_label, 12, 'Consolas', 'bold'))

        # LIVE SYSTEM STATS
        self._create_stats_panel(left_frame)

        # RIGHT COLUMN - Scrolling log
        right_frame = tk.Frame(main_frame, bg='#111111', bd=2, relief='sunken')
        right_frame.pack(side='right', fill='both', expand=True)

        log_header = tk.Label(
            right_frame, text="SYSTEM LOG",
            font=('Consolas', 10, 'bold'),
            fg=self.accent2_color, bg='#111111'
        )
        log_header.pack(pady=(8, 5))

        self.log_frame = tk.Frame(right_frame, bg='#111111')
        self.log_frame.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        scrollbar = tk.Scrollbar(self.log_frame)
        scrollbar.pack(side='right', fill='y')

        self.log_text = tk.Text(
            self.log_frame, bg='#0d0d0d', fg='#cccccc',
            font=('Consolas', 9), wrap='word', bd=0,
            highlightthickness=1, highlightbackground='#333333',
            insertbackground=self.accent_color,
            yscrollcommand=scrollbar.set
        )
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.log_text.yview)
        self._scalable_widgets.append((self.log_text, 9, 'Consolas', ''))

        # Configure tags
        self.log_text.tag_configure('timestamp', foreground='#666666')
        self.log_text.tag_configure('speech', foreground=self.accent_color)
        self.log_text.tag_configure('system', foreground=self.accent2_color)
        self.log_text.tag_configure('ok', foreground=self.ok_color)
        self.log_text.tag_configure('warn', foreground=self.warn_color)
        self.log_text.tag_configure('fail', foreground=self.fail_color)
        self.log_text.tag_configure('phase', foreground='#ffffff', font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure('info', foreground='#888888')
        self.log_text.tag_configure('user', foreground='#ffff00', font=('Consolas', 9, 'bold'))
        self.log_text.tag_configure('action', foreground='#ff9933')
        self.log_text.tag_configure('result', foreground='#66ff66')
        self.log_text.tag_configure('thinking', foreground='#9999ff', font=('Consolas', 9, 'italic'))
        self.log_text.config(state='disabled')

        # Close button
        self.close_btn = tk.Button(
            main_frame, text="x", font=('Arial', 18, 'bold'),
            fg='#666666', bg=self.bg_color,
            activebackground='#333333', activeforeground='#ff0000',
            bd=0, command=self.close
        )
        self.close_btn.place(relx=0.98, y=5, anchor='ne')

        # Initial log
        self._log_entry("CORA-GO Boot Sequence Initiated", 'phase')
        self._log_entry("-" * 50, 'info')

        # Chat input
        self._create_chat_input()

        return self.root

    def _create_stats_panel(self, parent):
        """Create the live system stats panel."""
        self.stats_frame = tk.Frame(parent, bg='#111111', bd=1, relief='groove')
        self.stats_frame.pack(fill='x', pady=5, padx=10)

        stats_header = tk.Label(
            self.stats_frame, text="LIVE SYSTEM STATS",
            font=('Consolas', 9, 'bold'),
            fg=self.accent2_color, bg='#111111'
        )
        stats_header.pack(pady=(3, 2))

        stats_grid = tk.Frame(self.stats_frame, bg='#111111')
        stats_grid.pack(fill='x', padx=5, pady=3)

        # Row 1: CPU, MEM, DISK
        tk.Label(stats_grid, text="CPU:", font=('Consolas', 9), fg='#888888', bg='#111111', width=6, anchor='e').grid(row=0, column=0, sticky='e')
        self.cpu_label = tk.Label(stats_grid, text="---%", font=('Consolas', 9, 'bold'), fg=self.ok_color, bg='#111111', width=8, anchor='w')
        self.cpu_label.grid(row=0, column=1, sticky='w', padx=(2, 10))

        tk.Label(stats_grid, text="MEM:", font=('Consolas', 9), fg='#888888', bg='#111111', width=6, anchor='e').grid(row=0, column=2, sticky='e')
        self.mem_label = tk.Label(stats_grid, text="---%", font=('Consolas', 9, 'bold'), fg=self.ok_color, bg='#111111', width=8, anchor='w')
        self.mem_label.grid(row=0, column=3, sticky='w', padx=(2, 10))

        tk.Label(stats_grid, text="DISK:", font=('Consolas', 9), fg='#888888', bg='#111111', width=6, anchor='e').grid(row=0, column=4, sticky='e')
        self.disk_label = tk.Label(stats_grid, text="---%", font=('Consolas', 9, 'bold'), fg=self.ok_color, bg='#111111', width=8, anchor='w')
        self.disk_label.grid(row=0, column=5, sticky='w')

        # Row 2: GPU, VRAM, NET
        tk.Label(stats_grid, text="GPU:", font=('Consolas', 9), fg='#888888', bg='#111111', width=6, anchor='e').grid(row=1, column=0, sticky='e')
        self.gpu_label = tk.Label(stats_grid, text="---%", font=('Consolas', 9, 'bold'), fg=self.ok_color, bg='#111111', width=8, anchor='w')
        self.gpu_label.grid(row=1, column=1, sticky='w', padx=(2, 10))

        tk.Label(stats_grid, text="VRAM:", font=('Consolas', 9), fg='#888888', bg='#111111', width=6, anchor='e').grid(row=1, column=2, sticky='e')
        self.gpu_mem_label = tk.Label(stats_grid, text="---%", font=('Consolas', 9, 'bold'), fg=self.ok_color, bg='#111111', width=8, anchor='w')
        self.gpu_mem_label.grid(row=1, column=3, sticky='w', padx=(2, 10))

        tk.Label(stats_grid, text="NET:", font=('Consolas', 9), fg='#888888', bg='#111111', width=6, anchor='e').grid(row=1, column=4, sticky='e')
        self.net_label = tk.Label(stats_grid, text="---", font=('Consolas', 9, 'bold'), fg=self.ok_color, bg='#111111', width=8, anchor='w')
        self.net_label.grid(row=1, column=5, sticky='w')

        self._start_stats_update()

    def _create_chat_input(self):
        """Create the chat input area."""
        self.chat_frame = tk.Frame(self.root, bg='#111111', height=60)
        self.chat_frame.pack(side='bottom', fill='x', padx=15, pady=(0, 10))
        self.chat_frame.pack_propagate(False)

        # Tool buttons
        btn_frame = tk.Frame(self.chat_frame, bg='#111111')
        btn_frame.pack(fill='x', pady=(5, 3))

        self.current_mode = None
        self.mode_buttons = {}

        tools = [
            ("Screenshot", "screenshot"),
            ("Vision", "vision"),
            ("System", "system"),
            ("Chat", None),
        ]

        for text, mode in tools:
            btn = tk.Button(
                btn_frame, text=text,
                font=('Consolas', 8),
                fg='#cccccc', bg='#222222',
                activebackground='#333333', activeforeground=self.accent_color,
                bd=0, padx=8, pady=2,
                command=lambda m=mode: self._set_mode(m)
            )
            btn.pack(side='left', padx=2)
            self.mode_buttons[mode] = btn

        # Pair Mobile button
        self.pair_btn = tk.Button(
            btn_frame, text="Pair Mobile",
            font=('Consolas', 8, 'bold'),
            fg='#000000', bg=self.accent2_color,
            activebackground=self.accent_color, activeforeground='#000000',
            bd=0, padx=8, pady=2,
            command=self._show_pairing
        )
        self.pair_btn.pack(side='left', padx=(10, 2))

        self.mode_label = tk.Label(
            btn_frame, text="", font=('Consolas', 8, 'italic'),
            fg='#888888', bg='#111111'
        )
        self.mode_label.pack(side='right', padx=5)

        # Input row
        input_frame = tk.Frame(self.chat_frame, bg='#111111')
        input_frame.pack(fill='x', pady=(0, 3))

        self.chat_input = tk.Entry(
            input_frame, font=('Consolas', 11),
            fg=self.fg_color, bg='#1a1a1a',
            insertbackground=self.accent_color, relief='flat', bd=0,
            highlightthickness=1, highlightbackground='#333333',
            highlightcolor=self.accent_color
        )
        self.chat_input.pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=5)
        self.chat_input.insert(0, "Talk to CORA-GO...")
        self.chat_input.bind('<FocusIn>', self._on_input_focus)
        self.chat_input.bind('<FocusOut>', self._on_input_unfocus)
        self.chat_input.bind('<Return>', self._on_send)
        self._scalable_widgets.append((self.chat_input, 11, 'Consolas', ''))

        self.send_button = tk.Button(
            input_frame, text="Send",
            font=('Consolas', 10, 'bold'),
            fg='#000000', bg=self.accent_color,
            activebackground=self.accent2_color, activeforeground='#000000',
            bd=0, padx=15, pady=5, command=self._on_send
        )
        self.send_button.pack(side='right')
        self._scalable_widgets.append((self.send_button, 10, 'Consolas', 'bold'))

    def _on_input_focus(self, event=None):
        if self.chat_input.get() == "Talk to CORA-GO...":
            self.chat_input.delete(0, 'end')
            self.chat_input.config(fg=self.fg_color)

    def _on_input_unfocus(self, event=None):
        if not self.chat_input.get():
            self.chat_input.insert(0, "Talk to CORA-GO...")
            self.chat_input.config(fg='#666666')

    def _on_send(self, event=None):
        text = self.chat_input.get().strip()
        if text and text != "Talk to CORA-GO...":
            self.chat_input.delete(0, 'end')
            self._process_user_input(text)

    def _set_mode(self, mode: str):
        self.current_mode = mode
        for m, btn in self.mode_buttons.items():
            if m == mode:
                btn.config(bg=self.accent_color, fg='#000000')
            else:
                btn.config(bg='#222222', fg='#cccccc')

        if mode:
            self.mode_label.config(text=f"Mode: {mode.upper()}")
            self.log(f"Mode set to: {mode.upper()}", 'info')
        else:
            self.mode_label.config(text="")

    def _process_user_input(self, text: str):
        """Process user input."""
        self.log_user(text)
        if self.on_user_input:
            self.on_user_input(text)
        else:
            self._default_process_input(text)

    def _default_process_input(self, text: str):
        """Default input processing - integrate with anchor tools."""
        def process():
            try:
                # Try to import anchor tools (handle different run contexts)
                try:
                    from anchor.tools import execute_tool
                except ImportError:
                    import sys
                    from pathlib import Path
                    anchor_path = Path(__file__).parent.parent.parent
                    if str(anchor_path) not in sys.path:
                        sys.path.insert(0, str(anchor_path))
                    from anchor.tools import execute_tool

                # Simple command detection
                text_lower = text.lower()

                # Demo mode - show off all features
                if text_lower in ['/demo', 'demo', '/showcase', '/test']:
                    self._run_demo(execute_tool)
                    return
                elif text_lower in ['/help', 'help', '?']:
                    self.log_system("Commands: /pair, /demo, /tools, system, time, say <text>, screenshot")
                    return
                elif text_lower in ['/pair', 'pair', 'pair mobile', 'qr', 'qr code']:
                    self._show_pairing()
                    return
                elif text_lower in ['/tools', 'tools', 'list tools']:
                    from anchor.tools import list_tools
                    tools = list_tools()
                    self.log_system(f"Available tools ({len(tools)}): {', '.join(tools)}")
                    return
                elif 'screenshot' in text_lower or self.current_mode == 'screenshot':
                    result = execute_tool('desktop_screenshot', {})
                    self.log_result(str(result))
                elif 'system' in text_lower or 'cpu' in text_lower or 'ram' in text_lower:
                    result = execute_tool('system_info', {})
                    self.log_result(str(result))
                elif 'time' in text_lower:
                    result = execute_tool('get_time', {})
                    self.log_result(str(result))
                elif 'speak' in text_lower or 'say' in text_lower:
                    words = text_lower.replace('speak', '').replace('say', '').strip()
                    result = execute_tool('speak', {'text': words or text})
                    self.log_result("Speaking...")
                elif any(w in text_lower for w in ['image', 'picture', 'photo', 'draw', 'generate', 'show me']):
                    # Extract prompt - remove trigger words
                    prompt = text
                    for w in ['generate', 'create', 'make', 'draw', 'show me', 'a picture of', 'an image of', 'a photo of']:
                        prompt = prompt.lower().replace(w, '').strip()
                    result = execute_tool('generate_image', {'prompt': prompt or text})
                    if isinstance(result, dict) and 'url' in result:
                        self.log_ok(f"Image: {result['url']}")
                    else:
                        self.log_result(str(result))
                else:
                    # Try AI query
                    result = execute_tool('ask_ai', {'prompt': text})
                    if isinstance(result, dict) and 'response' in result:
                        response_text = result['response']
                        self.log_result(response_text)
                        # Speak response if not in errors-only mode
                        from ..config import config
                        if not config.get('voice.speak_errors_only', True):
                            execute_tool('speak', {'text': response_text[:500]})
                    elif isinstance(result, dict) and 'error' in result:
                        self.log_warn(result['error'])
                    else:
                        self.log_result(str(result))
            except ImportError:
                self.log('Anchor tools not available', 'warn')
            except Exception as e:
                self.log_fail(f"Error: {e}")

        threading.Thread(target=process, daemon=True).start()

    def _run_demo(self, execute_tool):
        """Run a demo showcasing CORA-GO capabilities."""
        import time as t

        self.log_phase("CORA-GO DEMO")

        # 1. Voice
        self.log_action("Testing voice synthesis...")
        execute_tool('speak', {'text': 'Hello! I am CORA GO, your personal AI assistant.'})
        t.sleep(3)

        # 2. System info
        self.log_action("Checking system status...")
        result = execute_tool('system_info', {})
        if isinstance(result, dict):
            self.log_ok(f"CPU: {result.get('cpu_percent', '?')}% | RAM: {result.get('ram_available_gb', '?')}GB free | GPU: {result.get('gpu', 'N/A')}")
        t.sleep(1)

        # 3. Time
        self.log_action("Getting current time...")
        result = execute_tool('get_time', {})
        if isinstance(result, dict):
            self.log_ok(f"Time: {result.get('time', '?')} | Date: {result.get('date', '?')}")
        t.sleep(1)

        # 4. Tools list
        self.log_action("Listing available tools...")
        from anchor.tools import list_tools
        tools = list_tools()
        self.log_ok(f"{len(tools)} tools: {', '.join(tools[:8])}...")
        t.sleep(1)

        # 5. AI query
        self.log_action("Testing AI backend...")
        result = execute_tool('ask_ai', {'prompt': 'In exactly 10 words, what can you help with?'})
        if isinstance(result, dict) and 'response' in result:
            self.log_ok(f"AI: {result['response'][:100]}")
        t.sleep(1)

        # Done
        execute_tool('speak', {'text': 'Demo complete. All systems are operational.'})
        self.log_phase("DEMO COMPLETE")
        self.log_system("Try: /help, /tools, or just type naturally!")

    def _show_pairing(self):
        """Show QR code pairing window as Toplevel (no threading issues)."""
        self.log_system("Generating pairing code...")

        try:
            # Import pairing module
            try:
                from anchor.pairing import pairing
            except ImportError:
                import sys
                anchor_path = Path(__file__).parent.parent.parent
                if str(anchor_path) not in sys.path:
                    sys.path.insert(0, str(anchor_path))
                from anchor.pairing import pairing

            # Generate pairing code
            result = pairing.generate_pairing_code()
            if "error" in result:
                self.log_fail(f"Pairing error: {result['error']}")
                return

            code = result["code"]
            qr_url = result["qr_url"]
            self.log_ok(f"Pairing code: {code}")

            # Create Toplevel window (uses existing Tk root)
            pair_win = tk.Toplevel(self.root)
            pair_win.title("CORA-GO - Pair Mobile")
            pair_win.configure(bg='#0a0a0a')
            pair_win.geometry("350x450")
            pair_win.resizable(False, False)

            tk.Label(pair_win, text="CORA-GO", font=('Consolas', 20, 'bold'),
                     fg='#ff00ff', bg='#0a0a0a').pack(pady=(15, 5))
            tk.Label(pair_win, text="Scan QR with your phone", font=('Consolas', 10),
                     fg='#00ffff', bg='#0a0a0a').pack(pady=(0, 15))

            # Load QR from free API
            try:
                import urllib.request
                import urllib.parse
                from PIL import Image, ImageTk
                from io import BytesIO

                encoded_url = urllib.parse.quote(qr_url, safe='')
                qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={encoded_url}&format=png&margin=8"

                req = urllib.request.Request(qr_api)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    qr_data = resp.read()

                qr_img = Image.open(BytesIO(qr_data))
                photo = ImageTk.PhotoImage(qr_img)
                qr_label = tk.Label(pair_win, image=photo, bg='#ffffff')
                qr_label.image = photo
                qr_label.pack(pady=10)
                self.log_ok("QR code displayed")

            except Exception as e:
                self.log_warn(f"QR display error: {e}")
                tk.Label(pair_win, text=f"[QR Error: {e}]", font=('Consolas', 9),
                         fg='#ff3333', bg='#0a0a0a', wraplength=300).pack(pady=20)

            # Manual code display
            tk.Label(pair_win, text="Or enter code:", font=('Consolas', 9),
                     fg='#888888', bg='#0a0a0a').pack(pady=(15, 5))
            tk.Label(pair_win, text=code, font=('Consolas', 24, 'bold'),
                     fg='#00ff88', bg='#0a0a0a').pack(pady=5)

            # Status
            status_lbl = tk.Label(pair_win, text="Waiting for mobile...",
                                  font=('Consolas', 9, 'italic'), fg='#666666', bg='#0a0a0a')
            status_lbl.pack(pady=15)

            # URL hint
            tk.Label(pair_win, text=qr_url.split('?')[0], font=('Consolas', 7),
                     fg='#444444', bg='#0a0a0a').pack(pady=5)

            # Poll for pairing completion
            def check_status():
                if not pair_win.winfo_exists():
                    pairing.stop_pairing_poll()
                    return
                status = pairing.check_pairing_status(code)
                print(f"[POLL] Status: {status}", flush=True)
                if status.get("status") == "claimed":
                    status_lbl.config(text="CONNECTED!", fg='#00ff88')
                    self.log_ok(f"Paired with mobile!")

                    # Save pairing to config
                    from anchor.config import config
                    device_name = status.get('device_name') or status.get('anchor_name') or 'Mobile'
                    config.set("paired", True)
                    config.set("paired_device", device_name)
                    config.set("anchor.id", pairing.anchor_id)

                    # Start the relay so mobile sees us online
                    def start_relay_and_close():
                        try:
                            from anchor.relay import relay
                            relay.device_id = pairing.anchor_id
                            if relay.is_configured():
                                relay.heartbeat()
                                relay.start()
                                print("[PAIRING] Relay started - mobile should see us online!")
                                self.log_ok("Relay started!")
                        except Exception as e:
                            print(f"[PAIRING] Failed to start relay: {e}")
                            self.log_warn(f"Relay error: {e}")
                        pair_win.destroy()

                    pair_win.after(1500, start_relay_and_close)
                elif status.get("status") == "expired":
                    status_lbl.config(text="Code expired", fg='#ff3333')
                else:
                    pair_win.after(2000, check_status)

            pair_win.after(2000, check_status)

            def on_close():
                pairing.stop_pairing_poll()
                pair_win.destroy()

            pair_win.protocol("WM_DELETE_WINDOW", on_close)

        except Exception as e:
            self.log_fail(f"Pairing error: {e}")

    def set_input_callback(self, callback):
        """Set callback for user input processing."""
        self.on_user_input = callback

    def enable_chat_mode(self):
        """Enable chat mode after boot completes."""
        self.boot_complete = True
        if self.chat_input:
            self.chat_input.focus_set()
        self._log_entry("-" * 50, 'info')
        self._log_entry("Boot complete! Type below to interact.", 'ok')

    def _log_entry(self, text: str, tag: str = 'info'):
        """Add an entry to the scrolling log."""
        if not self.log_text:
            return
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.config(state='normal')
            self.log_text.insert('end', f"[{timestamp}] ", 'timestamp')
            self.log_text.insert('end', f"{text}\n", tag)
            self.log_text.see('end')
            self.log_text.config(state='disabled')
            if self.root:
                self.root.update_idletasks()
        except:
            pass

    def log(self, text: str, level: str = 'info'):
        """Add a log entry."""
        self._log_entry(text, level)

    def log_speech(self, text: str):
        self._log_entry(f'CORA: "{text}"', 'speech')

    def log_system(self, text: str):
        self._log_entry(f"[SYS] {text}", 'system')

    def log_phase(self, text: str):
        self._log_entry(f"{'=' * 15} {text} {'=' * 15}", 'phase')

    def log_ok(self, text: str):
        self._log_entry(f"[OK] {text}", 'ok')

    def log_warn(self, text: str):
        self._log_entry(f"[WARN] {text}", 'warn')

    def log_fail(self, text: str):
        self._log_entry(f"[FAIL] {text}", 'fail')

    def log_user(self, text: str):
        self._log_entry(f"USER: {text}", 'user')

    def log_action(self, text: str):
        self._log_entry(f"-> ACTION: {text}", 'action')

    def log_result(self, text: str):
        self._log_entry(f"<- RESULT: {text}", 'result')

    def log_thinking(self, text: str):
        self._log_entry(f"... {text}", 'thinking')

    def set_phases(self, phase_names: List[str]):
        """Set up the phase indicators in 2 columns."""
        for widget in self.phases_col_left.winfo_children():
            widget.destroy()
        for widget in self.phases_col_right.winfo_children():
            widget.destroy()

        self.phases = [BootPhase(name=name) for name in phase_names]
        self.phase_labels = {}
        self.phase_indicators = {}

        half = (len(self.phases) + 1) // 2

        for i, phase in enumerate(self.phases):
            parent = self.phases_col_left if i < half else self.phases_col_right
            frame = tk.Frame(parent, bg=self.bg_color)
            frame.pack(fill='x', pady=0)

            indicator = tk.Label(
                frame, text="o", font=('Consolas', 8),
                fg=self.pending_color, bg=self.bg_color, width=2
            )
            indicator.pack(side='left')
            self.phase_indicators[phase.name] = indicator
            self._scalable_widgets.append((indicator, 8, 'Consolas', ''))

            display_name = phase.name[:18] if len(phase.name) > 18 else phase.name
            label = tk.Label(
                frame, text=display_name,
                font=('Consolas', 8),
                fg='#888888', bg=self.bg_color, anchor='w'
            )
            label.pack(side='left', padx=2)
            self.phase_labels[phase.name] = label
            self._scalable_widgets.append((label, 8, 'Consolas', ''))

    def update_phase(self, phase_name: str, status: str, message: str = ""):
        """Update a phase status."""
        if phase_name not in self.phase_indicators:
            return

        indicator = self.phase_indicators[phase_name]
        label = self.phase_labels[phase_name]

        if status == "running":
            indicator.config(text="*", fg=self.accent_color)
            label.config(fg=self.accent_color)
        elif status == "ok":
            indicator.config(text="*", fg=self.ok_color)
            label.config(fg=self.ok_color)
        elif status == "warn":
            indicator.config(text="*", fg=self.warn_color)
            label.config(fg=self.warn_color)
        elif status == "fail":
            indicator.config(text="*", fg=self.fail_color)
            label.config(fg=self.fail_color)
        else:
            indicator.config(text="o", fg=self.pending_color)
            label.config(fg='#888888')

        completed = sum(1 for p in self.phases if p.status in ['ok', 'warn', 'fail'])
        if self.phases:
            self.progress_var.set((completed / len(self.phases)) * 100)

        for p in self.phases:
            if p.name == phase_name:
                p.status = status
                p.message = message
                break

        if self.root:
            self.root.update()

    def set_status(self, text: str):
        """Update the status label."""
        if self.status_label:
            self.status_label.config(text=text)
            if self.root:
                self.root.update()

    def start_speaking(self, text: str):
        """Called when speaking starts."""
        self.is_speaking = True
        try:
            if self.current_text:
                self.current_text.config(text=f'"{text}"')
            self.log_speech(text)
        except:
            pass

    def stop_speaking(self):
        """Called when speaking stops."""
        self.is_speaking = False
        try:
            if self.current_text:
                self.current_text.config(text="")
        except:
            pass

    def set_progress(self, value: float):
        """Set progress bar value (0-100)."""
        if self.progress_var:
            self.progress_var.set(value)
        if self.root:
            self.root.update()

    def _start_stats_update(self):
        """Start the live stats update loop."""
        try:
            import psutil
            psutil.cpu_percent(interval=None)
        except:
            pass
        self._stats_running = True
        self._stats_data = {}
        self._stats_thread = threading.Thread(target=self._stats_collector, daemon=True)
        self._stats_thread.start()
        self._update_stats_ui()

    def _stats_collector(self):
        """Background thread that collects system stats."""
        import subprocess
        try:
            import psutil
        except ImportError:
            return

        while self._stats_running and self.root:
            try:
                stats = {}
                stats['cpu'] = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                stats['mem'] = mem.percent

                try:
                    disk = psutil.disk_usage('C:\\')
                except:
                    disk = psutil.disk_usage('/')
                stats['disk'] = disk.percent

                net_up = False
                try:
                    net = psutil.net_if_stats()
                    for iface, data in net.items():
                        if data.isup and iface != 'lo' and 'Loopback' not in iface:
                            net_up = True
                            break
                except:
                    pass
                stats['net'] = net_up

                try:
                    result = subprocess.run(
                        ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'],
                        capture_output=True, text=True, timeout=1
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        parts = result.stdout.strip().split(', ')
                        if len(parts) >= 3:
                            stats['gpu'] = float(parts[0])
                            gpu_mem_used = float(parts[1])
                            gpu_mem_total = float(parts[2])
                            stats['gpu_mem'] = (gpu_mem_used / gpu_mem_total) * 100 if gpu_mem_total > 0 else 0
                except:
                    stats['gpu'] = None
                    stats['gpu_mem'] = None

                self._stats_data = stats
            except:
                pass
            time.sleep(1)

    def _update_stats_ui(self):
        """Update UI labels from collected stats."""
        if not self.root:
            return

        try:
            stats = self._stats_data

            if 'cpu' in stats:
                cpu = stats['cpu']
                cpu_color = self.ok_color if cpu < 70 else (self.warn_color if cpu < 90 else self.fail_color)
                if self.cpu_label:
                    self.cpu_label.config(text=f"{cpu:.1f}%", fg=cpu_color)

            if 'mem' in stats:
                mem_pct = stats['mem']
                mem_color = self.ok_color if mem_pct < 70 else (self.warn_color if mem_pct < 90 else self.fail_color)
                if self.mem_label:
                    self.mem_label.config(text=f"{mem_pct:.1f}%", fg=mem_color)

            if 'disk' in stats:
                disk_pct = stats['disk']
                disk_color = self.ok_color if disk_pct < 80 else (self.warn_color if disk_pct < 95 else self.fail_color)
                if self.disk_label:
                    self.disk_label.config(text=f"{disk_pct:.1f}%", fg=disk_color)

            if 'net' in stats:
                net_up = stats['net']
                if self.net_label:
                    self.net_label.config(text="UP" if net_up else "DOWN", fg=self.ok_color if net_up else self.fail_color)

            if 'gpu' in stats and stats['gpu'] is not None:
                gpu_util = stats['gpu']
                gpu_color = self.ok_color if gpu_util < 70 else (self.warn_color if gpu_util < 90 else self.fail_color)
                if self.gpu_label:
                    self.gpu_label.config(text=f"{gpu_util:.0f}%", fg=gpu_color)
            elif self.gpu_label:
                self.gpu_label.config(text="N/A", fg='#666666')

            if 'gpu_mem' in stats and stats['gpu_mem'] is not None:
                gpu_mem_pct = stats['gpu_mem']
                vram_color = self.ok_color if gpu_mem_pct < 70 else (self.warn_color if gpu_mem_pct < 90 else self.fail_color)
                if self.gpu_mem_label:
                    self.gpu_mem_label.config(text=f"{gpu_mem_pct:.0f}%", fg=vram_color)
            elif self.gpu_mem_label:
                self.gpu_mem_label.config(text="N/A", fg='#666666')
        except:
            pass

        if self.root:
            self.stats_update_id = self.root.after(1000, self._update_stats_ui)

    def _on_window_resize(self, event):
        """Handle window resize."""
        if event.widget != self.root:
            return

        current_time = time.time()
        if current_time - self._last_resize_time < 0.1:
            return
        self._last_resize_time = current_time

        width_scale = event.width / self.base_width
        height_scale = event.height / self.base_height
        scale = (width_scale + height_scale) / 2
        scale = max(0.6, min(1.8, scale))

        for widget, base_size, font_family, font_weight in self._scalable_widgets:
            try:
                new_size = max(8, int(base_size * scale))
                if font_weight:
                    widget.configure(font=(font_family, new_size, font_weight))
                else:
                    widget.configure(font=(font_family, new_size))
            except:
                pass

    def close(self):
        """Close the display window."""
        self._stats_running = False
        if self.stats_update_id:
            try:
                self.root.after_cancel(self.stats_update_id)
            except:
                pass
        if self.waveform:
            self.waveform.stop()
        if self.root:
            self.root.destroy()
            self.root = None

    def run(self):
        """Run the tkinter mainloop."""
        if self.root:
            self.root.mainloop()


# ============================================================
# GLOBAL DISPLAY INSTANCE
# ============================================================

_boot_display: Optional[BootDisplay] = None


def create_boot_display() -> BootDisplay:
    """Create and return a boot display instance."""
    global _boot_display
    _boot_display = BootDisplay()
    return _boot_display


def get_boot_display() -> Optional[BootDisplay]:
    """Get the current boot display instance."""
    return _boot_display


def close_boot_display():
    """Close the boot display."""
    global _boot_display
    if _boot_display:
        _boot_display.close()
        _boot_display = None


# ============================================================
# TEST
# ============================================================

if __name__ == '__main__':
    print("Testing CORA-GO Boot Display...")

    display = BootDisplay()
    display.create_window()

    phases = [
        "Voice Engine",
        "AI Backend",
        "Hardware Check",
        "Core Tools",
        "Supabase Relay",
        "Mobile Sync",
        "Final Check"
    ]
    display.set_phases(phases)

    def simulate_boot():
        time.sleep(1)

        for i, phase in enumerate(phases):
            display.update_phase(phase, "running")
            display.set_status(f"Running: {phase}...")
            display.log(f"Testing {phase}...", 'system')

            display.start_speaking(f"Now checking {phase}...")
            time.sleep(1.5)
            display.stop_speaking()

            status = "ok" if random.random() > 0.15 else "warn"
            display.update_phase(phase, status)

            if status == "ok":
                display.log_ok(f"{phase} passed")
            else:
                display.log_warn(f"{phase} has warnings")

            time.sleep(0.3)

        display.set_status("Boot Complete - All Systems Online")
        display.enable_chat_mode()

    thread = threading.Thread(target=simulate_boot, daemon=True)
    thread.start()

    display.run()
    print("Test complete!")
