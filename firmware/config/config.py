"""
config.py - Central configuration for hardware, display, and application settings.

This file contains all hardware pin assignments, display settings, and application-level
constants for the project. By centralizing these settings, you can easily adapt the codebase
to new hardware or change system-wide parameters in one place.

Sections:
- Device mode selection
- Common configuration (network, MIDI, etc.)
- Display settings
- Menu settings
- Hardware pin assignments (import board required)
- Mode-specific configuration (e.g., boss, chords)
- UI settings
- Audio settings
- Network settings

Usage:
Import this module as `import config.config as config` and use the variables directly.
Example: `config.AN1_PIN`, `config.DISPLAY_WIDTH`, `config.KEY_RESET`, etc.
"""
import board
# Device mode selection
# Choose the mode for this device (boss, pitch, time, chords, scale)
# MODE = "boss"
MODE = "pitch" # piano roll
# MODE = "pattern"  # drums / pad
# MODE = "chords" # chord progression
# MODE = "arp" # arpeggio


#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# Mode-specific configuration
# These settings may override or extend the above depending on the selected MODE.
if MODE == 'boss':
    # Hardware settings
    HW_VERSION = 1.0
    KEY_RESET = 10
    KEY_PLAY_PAUSE = 11
    INSTRUMENT_ID = 1
    # Song settings
    SONG_NAME = "arpai"
    SONG_PATH = "assets/"

if MODE == 'pitch':    
    # LEAD:
    INSTRUMENT_ID = 2
    MEDIAN_OCTAVE = 7
    # BASS
    # INSTRUMENT_ID = 1
    # MEDIAN_OCTAVE = 5
    HW_VERSION = 1.1
    PLAYBACK_STATES = {
        "paused": 0,
        "playing": 1,
        "reset": 2,
        "clear": 3
    }
    FIELD_X_MAX = 40
    FIELD_Y_MAX = 16
    FIELD_TILE_WIDTH = 4
    FIELD_TILE_HEIGHT = 4    
    PIXELS_PER_BEAT = 4
    KEY_PCB_TO_NOTE = [1, 3, -1, 6, 8, 10, -1, 13, 0, 2, 4, 5, 7, 9, 11, 12]
    KEY_NOTE_TO_PCB = [8, 0, 9, 1, 10, 11, 3, 12, 4, 13, 5, 14, 2, 6, 7, 15]

if MODE == 'pattern':
    INSTRUMENT_ID = 3
    MEDIAN_OCTAVE = 1
    HW_VERSION = 1.1
    FIELD_X_MAX = 16
    FIELD_Y_MAX = 4
    FIELD_TILE_WIDTH = 10
    FIELD_TILE_HEIGHT = 10
    XSTART = 0
    YSTART = 0

    # Mode configuration
    MODES = {
        'paused': 0,
        'playing': 1,
        'reset': 2,
        'clear': 3
    }

    # Drum configuration
    DRUM_NOTES = [36, 38, 42, 57]  # bass, snare, hi-hat, crash
    DRUM_NAMES = [
        "bass (36)",
        "snare (38)",
        "closed hi-hat (42)",
        "crash (57)"
    ]

    # Menu configuration
    MENU_ACTIONS = {
        'send_song': lambda: None,  # Will be set in pattern.py
        'set_channel': lambda: None,
        'show_my_ip': lambda: None,
        'send_pair': lambda: None,
        'show_paired_devices': lambda: None,
        'set_mode': lambda mode_id: None
    }

if MODE == 'chords':
    INSTRUMENT_ID = 1
    MEDIAN_OCTAVE = 3           # (0:5 1:3 2:7)
    HW_VERSION = 1.0

if MODE == 'arp':
    INSTRUMENT_ID = 0
    MEDIAN_OCTAVE = 5
    HW_VERSION = 1.0
    FIELD_X_MAX = 8
    FIELD_Y_MAX = 8
    FIELD_TILE_WIDTH = 10
    FIELD_TILE_HEIGHT = 10
    PIXELS_PER_BEAT = 4
    PLAYBACK_STATES = {
        "paused": 0,
        "playing": 1,
        "reset": 2,
        "clear": 3
    }
    # Arpeggiator constants
    TICKS_PER_BEAT = 480
    MAX_TICKS = 47522
    TEMPO = 160
    DENOMINATOR = 4
    MAX_NOTE = 66
    MIN_NOTE = 55
    DEFAULT_ARP_PATTERN = [0, 1, 2, 1]
    XSTART = 40
    YSTART = 0
    BACKGROUND_Y_OFFSET = 81
    DEFAULT_TILE_VALUE = 3
    PATTERN_ACTIVE_TILE = 1
    PATTERN_CURRENT_TILE = 2
    LED_OFF_COLOR = 0x000000
    LED_ACTIVE_COLOR = 0x200010
    SCALE_C = 60
    SCALE_G = 55
    SCALE_A = 57
    SCALE_F = 65



#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# Common configuration
# Network and MIDI settings
# MAC_BROADCAST: Broadcast MAC address for ESP-NOW
# EXTRA_PAYLOAD: Used to pad packets for robustness
# MIDI_CHANNEL: Default MIDI channel
# DEFAULT_INTENSITY: Default velocity for MIDI events
MAC_BROADCAST = b'\xFF\xFF\xFF\xFF\xFF\xFF'
EXTRA_PAYLOAD = "PAYLOAD TO MAKE A PACKET MORE ROBUST..."    
MIDI_CHANNEL = 1            # pick your MIDI channel here
DEFAULT_INTENSITY = 100     # midi intensity for live input

# Display settings
# DISPLAY_WIDTH/HEIGHT: Physical display dimensions in pixels
DISPLAY_WIDTH = 160
DISPLAY_HEIGHT = 128

# Menu settings
# MENU_FILE: Path to the menu configuration file
MENU_FILE = "config/menu.txt"

#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

if HW_VERSION == 1.0:
    NEOPIXEL_NUM = 12
    KEY_NUM = 16
    KEY_COL = 8
    NR_KEYS = 12
    KEY_BACK = 13
    KEY_SELECT = 12
    ROTATION_CW = 3
    ROTATION_CCW = 2
    ROTATION_TOP_CW = 1
    ROTATION_TOP_CCW = 0

    # Key matrix column pins (8 columns)
    COL_PINS = [
        board.IO8, board.IO7, board.IO6, board.IO5,
        board.IO4, board.IO3, board.IO2, board.IO1
    ]

if HW_VERSION == 1.1:
    NEOPIXEL_NUM = 16
    KEY_NUM = 20
    KEY_COL = 10
    NR_KEYS = 16
    KEY_BACK = 19
    KEY_SELECT = 18

    # Key matrix column pins (10 columns)
    COL_PINS = [
        board.IO8, board.IO7, board.IO6, board.IO5,  board.IO4,
        board.IO3, board.IO2, board.IO1, board.IO13, board.IO14
    ]
    SCL0_PIN = board.IO9
    SDA0_PIN = board.IO16
    SCL1_PIN = board.IO17
    SDA1_PIN = board.IO18


# Analog input pins for rotary encoders or analog controls
AN1_PIN = board.IO14
AN2_PIN = board.IO13

# Key matrix row pins
ROW0_PIN = board.IO33
ROW1_PIN = board.IO34

# Neopixel (RGB LED) settings
NEOPIXEL_PIN = board.IO21

# Built-in LED pin
BUILTIN_LED_PIN = board.IO15

# Display interface pins
PICO_PIN = board.IO35  # data
CLK_PIN = board.IO36   # clock
RST_PIN = board.IO37   # reset
CS_PIN = board.IO40    # chip select
DC_PIN = board.IO39    # data/command
BL_PIN = board.IO38    # backlight

#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# UI Settings
UI_COLORS = {
    'off': (0, 0, 0),
    'mute': (0, 10, 0),
    'pause': (30, 0, 10),
    'selected': (18, 70, 23),
    'current': (200, 200, 200),
    'current_bg': (14, 0, 20),
    'key_off': (20, 0, 10)
}

# Display settings
DISPLAY_REFRESH_RATE = 250


# Text field positions
TEXT_FIELD_POSITIONS = {
    'title': (10, 80),
    'channel': (20, 90),
    'note': (50, 90),
    'intensity': (80, 90),
    'menu': (10, 110),
    'debug': (10, 120)
}

#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# Audio Settings
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_MIXER_VOICES = 8
DEFAULT_MIXER_VOLUME = 0.2

# Audio I2S pins
I2S_BCLK_PIN = board.IO12
I2S_WS_PIN = board.IO10
I2S_DATA_PIN = board.IO11

# Audio mixer configuration
MIXER_CHANNEL_COUNT = 1
MIXER_BITS_PER_SAMPLE = 16
MIXER_SAMPLES_SIGNED = True

# Wavetable channel configuration
WAVETABLE_VOICE_NUMBERS = [4, 5, 6]  # Voice numbers for melodic instruments
WAVETABLE_WAVEFORM_INDICES = [0, 4, 3]  # Indices into waveforms array for each channel

# Sample configuration
SAMPLE_FILES = [
    "assets/audio/909_36.wav",
    "assets/audio/909_38.wav",
    "assets/audio/909_42.wav",
    "assets/audio/909_57.wav"
]
SAMPLE_VOLUMES = {36: 0.4, 38: 0.1, 42: 0.1, 57: 0.1}
SAMPLE_MAP = {36: 0, 38: 1, 42: 2, 57: 3}

#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# Network Settings
NETWORK_PACKET_TYPES = {
    'event': ord('e'),
    'live': ord('l'),
    'pair': ord('p'),
    'tick': ord('t'),
    'begin': ord('b'),
    'stop': ord('s'),
    'header': ord('h'),
    'mute': ord('m'),
    'update': ord('u'),
    'reset': ord('r'),
    'clear': ord('c'),
    'scale': ord('n')  # Added scale packet type
}

NETWORK_PACKET_RETRANSMISSION = 1
NETWORK_PACKET_DELAY = 0.004

#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# Song Settings
DEFAULT_SONG_METADATA = {
    'ticks_per_beat': 480,
    'max_ticks': 0,
    'tempo': 160,
    'numerator': 4,
    'denominator': 4,
    'nr_instruments': 1
}

# Provide MODES mapping if not defined (fallback to PLAYBACK_STATES)
if 'MODES' not in globals():
    MODES = PLAYBACK_STATES
