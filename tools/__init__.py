"""
CORA-GO Tools Module
Unified toolkit from CORA + MINIBOT
"""

from .files import read_file, write_file, list_files, search_files, move_file
from .system import run_shell, system_info, take_screenshot, get_clipboard, set_clipboard
from .web import web_search, fetch_url, fetch_and_summarize, get_weather
from .notes import add_note, get_note, list_notes, delete_note, search_notes
from .ai import query_ollama, query_pollinations, analyze_image, generate_image, list_ollama_models
from .sentinel import start_sentinel, stop_sentinel, sentinel_status, get_incidents
from .bots import list_bots, launch_bot, stop_bot, running_bots, stop_all_bots
from .voice import speak_local, list_voices, transcribe_audio, record_audio, listen_and_transcribe, get_tts_info
from .sync import configure_sync, sync_status, sync_notes_up, sync_notes_down, register_device, heartbeat, push_system_status
from .feeds import fetch_rss, fetch_json_feed, get_news, parse_feed_items, monitor_feed
from .gateway import (gateway_ping, gateway_directory, gateway_register, gateway_status,
                      gateway_blog_post, gateway_nostr_post, gateway_generate_image,
                      gateway_feed, gateway_rdb_command)
from .colab import (configure_colab, colab_status, query_colab, colab_check_mentions,
                    colab_heartbeat, is_configured as colab_is_configured)

__all__ = [
    # Files
    'read_file', 'write_file', 'list_files', 'search_files', 'move_file',
    # System
    'run_shell', 'system_info', 'take_screenshot', 'get_clipboard', 'set_clipboard',
    # Web
    'web_search', 'fetch_url', 'fetch_and_summarize', 'get_weather',
    # Notes
    'add_note', 'get_note', 'list_notes', 'delete_note', 'search_notes',
    # AI
    'query_ollama', 'query_pollinations', 'analyze_image', 'generate_image', 'list_ollama_models',
    # Sentinel
    'start_sentinel', 'stop_sentinel', 'sentinel_status', 'get_incidents',
    # Bots
    'list_bots', 'launch_bot', 'stop_bot', 'running_bots', 'stop_all_bots',
    # Voice
    'speak_local', 'list_voices', 'transcribe_audio', 'record_audio', 'listen_and_transcribe', 'get_tts_info',
    # Sync
    'configure_sync', 'sync_status', 'sync_notes_up', 'sync_notes_down', 'register_device', 'heartbeat', 'push_system_status',
    # Feeds
    'fetch_rss', 'fetch_json_feed', 'get_news', 'parse_feed_items', 'monitor_feed',
    # Gateway (optional AI-Ministries network)
    'gateway_ping', 'gateway_directory', 'gateway_register', 'gateway_status',
    'gateway_blog_post', 'gateway_nostr_post', 'gateway_generate_image',
    'gateway_feed', 'gateway_rdb_command',
    # Colab (optional backend - like choosing GPT/Anthropic)
    'configure_colab', 'colab_status', 'query_colab', 'colab_check_mentions',
    'colab_heartbeat', 'colab_is_configured'
]
