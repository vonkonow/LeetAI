#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************
#
#    ██████╗ ██╗████████╗ ██████╗██╗  ██╗
#    ██╔══██╗██║╚══██╔══╝██╔════╝██║  ██║
#    ██████╔╝██║   ██║   ██║     ███████║
#    ██╔═══╝ ██║   ██║   ██║     ██╔══██║
#    ██║     ██║   ██║   ╚██████╗██║  ██║
#    ╚═╝     ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝
#
# Pitch is a synthesizer with a piano roll (suitable for BASS and Lead synths)
# It recieves data wirelessly from the Boss unit that also renders the audio.
#
# Todo:
# * visulalise oktaves on pianoroll.
# * custom library for more efficient display handling.
# * support for editing the song and upload it to the Boss unit.
#
# Done:
#   250430:
#     x major code refactoring and cleanup:
#       directory structure, common modules, manager classes and error handling
#   250104:
#     x optimized visualization (so it can cach up)
#     x real time clock with wireless sync
#     x file transfer including header on pair request
#   240925:
#     x live playback
#   240831:
#     x implemented pianoroll visualization
#     x switched to circuitpython 9.1.3
#   240825
#     x optimized loading (using bytearray instead of textfile)
# 
# ******************************************************************************
import config.config as config
import espnow
import time
import displayio
import adafruit_imageload
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from src.common import hw
from src.common.audio import Sample, Wavetable, Silent, Play
from src.common.ui import Sprite, Field, Image, DisplayManager, colorwheel
from src.common.network import PacketHandler, PacketReadError
from src.common.menu import MenuManager
from src.common.song import LocalSong

#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
class MIDIController:
    """Handles MIDI input/output operations"""
    def __init__(self, channel):
        self.midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=channel-1)
    
    def send_note_on(self, note, intensity):
        """Send a MIDI note on message"""
        self.midi.send(NoteOn(note, intensity))
    
    def send_note_off(self, note):
        """Send a MIDI note off message"""
        self.midi.send(NoteOff(note, 0))

class NetworkManager:
    """Handles network communication"""
    def __init__(self, instrument_id, mac_broadcast):
        self.esp = espnow.ESPNow()
        self.peer_broadcast = espnow.Peer(mac=mac_broadcast)
        self.esp.peers.append(self.peer_broadcast)
        self.network = PacketHandler(self.esp, instrument_id, self.peer_broadcast)
    
    def send_packet(self, packet_type, data):
        """Send a network packet"""
        self.network.send_packet(packet_type, data, self.peer_broadcast)
    
    def read_packet(self):
        """Read an incoming network packet"""
        return self.network.read_packet()
    
    def handle_packet(self, packet):
        """Handle an incoming packet"""
        return self.network.handle_packet(packet)
    
    def send_pair(self):
        """Send a pair request"""
        self.network.send_pair()

class DisplayController:
    """Manages display and visualization"""
    def __init__(self, display, hw):
        self.display_manager = DisplayManager(display, hw)
        self._initialize_display()
    
    def _initialize_display(self):
        """Initialize the display with sprite sheet and text fields"""
        try:
            sprite_sheet, palette = adafruit_imageload.load(
                "assets/images/4x4.bmp",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            self.display_manager.x_max = config.FIELD_X_MAX
            self.display_manager.y_max = config.FIELD_Y_MAX
            self.display_manager.initialize_pattern_field(sprite_sheet, palette, 0, 0)
            self.display_manager.create_text_fields(f"{config.MODE} (CH{config.INSTRUMENT_ID})")
        except Exception as e:
            print(f"Display initialization error: {e}")  # Print to console first
            self.display_manager.show_debug_message("init error")
            hw.display.refresh()
            raise  # Re-raise the original exception
    
    def show_debug_message(self, message):
        """Show a debug message on the display"""
        self.display_manager.show_debug_message(message)
    
    def set_pause_led(self, state):
        """Set the pause LED state"""
        self.display_manager.set_pause_led(state)
    
    def update_mute_leds(self, states):
        """Update the mute LED states"""
        self.display_manager.update_mute_leds(states)
    
    def update_roll(self, pixel_pos, old_pixel_pos, piano_roll):
        """Update the piano roll display"""
        pixel_pos = max(0, pixel_pos)
        pixel_pos = min(pixel_pos, len(piano_roll))
            
        offset = (config.MEDIAN_OCTAVE - 2) * 12  # left edge of visible pianoroll
        delta = pixel_pos - old_pixel_pos
        
        for y in range(config.FIELD_Y_MAX):
            i = pixel_pos + y
            if i < len(piano_roll):
                # Clear old notes
                for p in piano_roll[i - delta]:
                    if p not in piano_roll[i]:
                        x = self._clamp(p - offset, 0, config.FIELD_X_MAX - 1)
                        if 0 <= x < config.FIELD_X_MAX and 0 <= y < config.FIELD_Y_MAX:
                            self.display_manager.field.setBlock(x, y, 0)
                # Draw new notes
                for p in piano_roll[i]:
                    if p not in piano_roll[i - delta]:
                        x = self._clamp(p - offset, 0, config.FIELD_X_MAX - 1)
                        if 0 <= x < config.FIELD_X_MAX and 0 <= y < config.FIELD_Y_MAX:
                            self.display_manager.field.setBlock(x, y, 1)
        hw.display.refresh()
    
    def _clamp(self, val, min_val, max_val):
        """Clamp a value between min and max"""
        return max(min_val, min(val, max_val))

class InputHandler:
    """Handles user input and key presses"""
    def __init__(self, hw, midi_controller, network_manager):
        self.hw = hw
        self.midi = midi_controller
        self.network = network_manager
    
    def process_input(self):
        """Process all user input"""
        try:
            for i in range(16):
                key = self.hw.key_change(i)
                if key[1]:
                    self._handle_key_press(i, key)
        except Exception as e:
            print(f"Input processing error: {e}")
    
    def _handle_key_press(self, i, key):
        """Handle a single key press event"""
        try:
            if config.KEY_PCB_TO_NOTE[i] != -1:
                note = config.MEDIAN_OCTAVE * 16 + config.KEY_PCB_TO_NOTE[i]
                packet = bytearray()
                packet.append(ord('l'))
                packet.append(config.INSTRUMENT_ID)
                packet.append(note)
                
                if key[0]:
                    self.hw.pixels[i] = colorwheel(config.MEDIAN_OCTAVE * 20 & 255)
                    self.midi.send_note_on(note, config.DEFAULT_INTENSITY)
                    packet.append(config.DEFAULT_INTENSITY)
                else:
                    self.hw.pixels[i] = config.UI_COLORS['key_off']
                    self.midi.send_note_off(note)
                    packet.append(0)
                    
                self.network.send_packet('l', packet[1:])
        except Exception as e:
            print(f"Key press error: {e}")

class PitchSynth:
    """Main instrument class that coordinates all components"""
    def __init__(self):
        """Initialize the PitchSynth instrument with all necessary components."""
        self.display = None  # Initialize display attribute to None
        try:
            self.midi = MIDIController(config.MIDI_CHANNEL)
            self.network = NetworkManager(config.INSTRUMENT_ID, config.MAC_BROADCAST)
            self.display = DisplayController(hw.display, hw)
            self.input = InputHandler(hw, self.midi, self.network)
            
            self.song = LocalSong(config.INSTRUMENT_ID)
            self.song_index = 0
            self.mute = 0
            self.pixel_pos = 0
            self.old_pixel_pos = 0
            self.tick_delta = 0
            self.start_time = time.monotonic()
            self.piano_roll = [[] for _ in range(1000)]
            self.mode = config.PLAYBACK_STATES["clear"]
            
            self._initialize_menu()
            self._initialize_network()
            self._initialize_keys()
        except Exception as e:
            print(f"Initialization error: {e}")  # Print to console first
            if self.display:
                try:
                    self.display.show_debug_message("init error")
                except Exception as display_error:
                    print(f"Failed to display error: {display_error}")
            raise  # Re-raise the original exception
        
    def _handle_error(self, context, error, fatal=False):
        """Handle errors consistently across the application.
        
        Args:
            context: String describing where the error occurred
            error: The exception object
            fatal: If True, raises the error after handling"""
        print(f"Error in {context}: {error}")  # Always print to console
        if self.display:
            try:
                self.display.show_debug_message(f"{context} error")
            except Exception as display_error:
                print(f"Failed to display error: {display_error}")
        if fatal:
            raise  # Re-raise the original exception
        
    def _initialize_menu(self) -> None:
        """Initialize the menu system with dispatch table."""
        try:
            menu_dispatch = {
                'send_song': lambda: self.network.send_packet('s', bytearray(), self.network.peer_broadcast),
                'set_channel': lambda: self.network.send_packet('c', bytearray([config.INSTRUMENT_ID]), self.network.peer_broadcast),
                'show_my_ip': lambda: self.display.show_debug_message(f"IP: {hw.ip}"),
                'send_pair': lambda: self.network.send_pair(),
                'show_paired_devices': lambda: self.display.show_debug_message(f"Paired: {len(self.network.esp.peers)}"),
                'set_mode': lambda mode: setattr(config, 'MODE', ['conductor', 'melodic', 'chord', 'arpeggio', 'drum'][mode])
            }
            self.menu_manager = MenuManager(config.MENU_FILE, self.display.display_manager, menu_dispatch)
        except Exception as e:
            self._handle_error("menu initialization", e, fatal=True)
        
    def _initialize_network(self) -> None:
        """Initialize network connection if in pitch mode."""
        try:
            if config.MODE in ("pitch", "pitch2"):
                self.network.send_pair()
        except Exception as e:
            self._handle_error("network initialization", e, fatal=True)
        
    def _initialize_keys(self) -> None:
        """Initialize the key states and LED colors."""
        try:
            for i in range(16):
                if i < 12:
                    hw.pixels[config.KEY_NOTE_TO_PCB[i]] = config.UI_COLORS['key_off']
                else:
                    hw.pixels[config.KEY_NOTE_TO_PCB[i]] = (0, 0, 0)
        except Exception as e:
            self._handle_error("key initialization", e, fatal=True)

    def handle_packet(self, packet_type, *args):
        """Handle incoming network packets based on their type."""
        try:
            packet_handlers = {
                'tick': self._handle_tick_packet,
                'begin': self._handle_begin_packet,
                'stop': self._handle_stop_packet,
                'event': self._handle_event_packet,
                'header': self._handle_header_packet,
                'mute': self._handle_mute_packet,
                'update': self._handle_update_packet,
                'reset': self._handle_reset_packet,
                'clear': self._handle_clear_packet
            }
            
            handler = packet_handlers.get(packet_type)
            if handler:
                handler(*args)
            else:
                print(f"Unknown packet type: {packet_type}")
        except Exception as e:
            self._handle_error(f"packet {packet_type}", e)

    def run(self) -> None:
        """Main execution loop."""
        try:
            while True:
                self._process_playback()
                self._process_network()
                self._process_input()
                self._process_menu()
        except Exception as e:
            self._handle_error("main loop", e)

    def _process_playback(self) -> None:
        """Process song playback if in playing state."""
        try:
            if self.mode == config.PLAYBACK_STATES["playing"] and self.song_index < self.song.get_event_count():
                self._handle_playback()
        except Exception as e:
            self._handle_error("playback", e)
            self.mode = config.PLAYBACK_STATES["paused"]

    def _handle_playback(self) -> None:
        """Handle the playback of a single event."""
        try:
            now = time.monotonic()
            event = self.song.get_event(self.song_index)
            if now >= (self.start_time + (event[0] - self.tick_delta) * self.song.get_metadata('tick_to_time')):
                self._play_event(event)
                self.song_index += 1
                
                # Update display
                self.pixel_pos = int((self.song.get_metadata('time_to_tick') * (now - self.start_time) + self.tick_delta) / 
                                   (self.song.get_metadata('ticks_per_beat') / config.PIXELS_PER_BEAT))
                if self.pixel_pos > self.old_pixel_pos:
                    self.display.update_roll(self.pixel_pos, self.old_pixel_pos, self.piano_roll)
                    self.old_pixel_pos = self.pixel_pos
        except Exception as e:
            self._handle_error("playback handling", e)
            self.mode = config.PLAYBACK_STATES["paused"]

    def _play_event(self, event):
        """Play a single MIDI event."""
        try:
            ch, note, intensity = event[1], event[2], event[3]
            if ch == config.INSTRUMENT_ID:
                i = note % 12
                if intensity == 0:
                    self.midi.send_note_off(note)
                    if not self.mute:
                        hw.pixels[config.KEY_NOTE_TO_PCB[i]] = config.UI_COLORS['key_off']
                else:
                    if not self.mute:
                        self.midi.send_note_on(note, intensity)
                        hw.pixels[config.KEY_NOTE_TO_PCB[i]] = colorwheel(int(note / 12) * 20 & 255)
        except Exception as e:
            self._handle_error("event playback", e)

    def _process_network(self) -> None:
        """Process incoming network packets."""
        if config.MODE in ("pitch", "pitch2"):
            try:
                packet = self.network.read_packet()
                if packet:
                    result = self.network.handle_packet(packet)
                    if result:
                        self.handle_packet(*result)
            except PacketReadError:
                self._handle_error("packet read", PacketReadError())
            except Exception as e:
                self._handle_error("network processing", e)

    def _process_input(self) -> None:
        """Process user input from keys."""
        self.input.process_input()

    def _process_menu(self) -> None:
        """Process menu navigation and selection."""
        try:
            rotation = self._get_rotation()
            if rotation == 1:
                self.menu_manager.handle_rotation(rotation)
            elif rotation == -1:
                self.menu_manager.handle_rotation(rotation)
                
            if hw.key_new(19):
                self.menu_manager.handle_back()
            if hw.key_new(18):
                self.menu_manager.handle_select()
        except Exception as e:
            self._handle_error("menu processing", e)

    def _get_rotation(self):
        """Get the current rotation value from the hardware."""
        try:
            if config.HW_VERSION == 1.1:
                return hw.check_rotation(0, 512)
            elif config.HW_VERSION == 1.0:
                if hw.check_analog_rotation(config.ROTATION_CW):
                    return 1
                if hw.check_analog_rotation(config.ROTATION_CCW):
                    return -1
            return 0
        except Exception as e:
            self._handle_error("rotation", e)
            return 0

    def _handle_tick_packet(self, tick):
        """Handle tick packet for synchronization."""
        try:
            now_tick = int(self.song.get_metadata('time_to_tick') * (time.monotonic() - self.start_time))
            self.tick_delta = tick - now_tick
        except Exception as e:
            self._handle_error("tick packet", e)

    def _handle_begin_packet(self):
        """Handle begin packet to start playback."""
        try:
            if self.song.get_event_count() > 0:
                self.start_time = time.monotonic() - self.song.get_event(self.song_index)[0] * self.song.get_metadata('tick_to_time')
                self.mode = config.PLAYBACK_STATES["playing"]
                self.display.show_debug_message("playing")
                self.display.set_pause_led(False)
        except Exception as e:
            self._handle_error("begin packet", e)

    def _handle_stop_packet(self):
        """Handle stop packet to pause playback."""
        try:
            self.mode = config.PLAYBACK_STATES["paused"]
            self.display.show_debug_message("paused")
            self.display.set_pause_led(True)
        except Exception as e:
            self._handle_error("stop packet", e)

    def _handle_event_packet(self, ch, tick_start, tick_end, note, intensity):
        """Handle event packet containing note information."""
        try:
            if ch == config.INSTRUMENT_ID:
                self.song.add_event(tick_start, tick_end, note, intensity)
                pixel_start = int(tick_start / (self.song.get_metadata('ticks_per_beat') / config.PIXELS_PER_BEAT))
                self.piano_roll[pixel_start].append(note)
        except Exception as e:
            self._handle_error("event packet", e)

    def _handle_header_packet(self, ticks_per_beat, max_ticks, tempo, numerator, denominator, nr_instruments):
        """Handle header packet containing song metadata."""
        try:
            self.song.update_header(ticks_per_beat, max_ticks, tempo, numerator, denominator, nr_instruments)
            if not self.piano_roll:
                max_pixels = int(max_ticks / (ticks_per_beat / config.PIXELS_PER_BEAT))
                self.piano_roll = [[] * max_pixels for _ in range(max_pixels)]
            self.mode = config.PLAYBACK_STATES["paused"]
        except Exception as e:
            self._handle_error("header packet", e)

    def _handle_mute_packet(self, ch, intensity):
        """Handle mute packet to control audio output."""
        try:
            if ch == config.INSTRUMENT_ID:
                self.mute = intensity
                if self.mute:
                    self.display.update_mute_leds([True] * 16)
                    self.display.show_debug_message("muted")
                else:
                    self.display.update_mute_leds([False] * 16)
                    self.display.show_debug_message(" ")
                hw.display.refresh()
        except Exception as e:
            self._handle_error("mute packet", e)

    def _handle_update_packet(self):
        """Handle update packet to refresh display."""
        try:
            self.display.show_debug_message("update")
            self.display.update_roll(self.pixel_pos, self.old_pixel_pos, self.piano_roll)
        except Exception as e:
            self._handle_error("update packet", e)

    def _handle_reset_packet(self):
        """Handle reset packet to restart playback."""
        try:
            self._clear_roll(self.old_pixel_pos, self.piano_roll)
            self.song_index = 0
            if self.song.get_event_count() > 0:
                self.start_time = time.monotonic() - self.song.get_event(self.song_index)[0] * self.song.get_metadata('tick_to_time')
            self.pixel_pos = 1
            self.old_pixel_pos = 0
            self.display.show_debug_message("reset")
            self.display.update_roll(self.pixel_pos, self.old_pixel_pos, self.piano_roll)
            self.old_pixel_pos = self.pixel_pos
        except Exception as e:
            self._handle_error("reset packet", e)

    def _handle_clear_packet(self, ch):
        """Handle clear packet to reset the song."""
        try:
            if ch == config.INSTRUMENT_ID or ch == 255:
                self._clear_roll(self.old_pixel_pos, self.piano_roll)
                self.song.clear()
                self.song_index = 0
                self.piano_roll = []
                self.display.show_debug_message("receiving")
                hw.display.refresh()
                self.mode = config.PLAYBACK_STATES["clear"]
        except Exception as e:
            self._handle_error("clear packet", e)

    def _clear_roll(self, pixel_pos, piano_roll):
        """Clear the piano roll display at the given position."""
        try:
            offset = (config.MEDIAN_OCTAVE - 2) * 12  # left edge of visible pianoroll
            for y in range(config.FIELD_Y_MAX):
                i = pixel_pos + y
                if i < len(piano_roll):
                    for p in piano_roll[i]:
                        x = self._clamp(p - offset, 0, config.FIELD_X_MAX - 1)
                        if 0 <= x < config.FIELD_X_MAX and 0 <= y < config.FIELD_Y_MAX:
                            self.display.display_manager.field.setBlock(x, y, 0)
        except Exception as e:
            self._handle_error("clear roll", e)

    def _clamp(self, val, min_val, max_val):
        """Clamp a value between min and max."""
        return max(min_val, min(val, max_val))

#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

def main():
    """Main entry point for the application."""
    try:
        instrument = PitchSynth()
        instrument.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        if hw.display:
            try:
                # Create a basic display manager for error handling
                display_manager = DisplayManager(hw.display, hw)
                display_manager.create_text_fields("Fatal Error")
                display_manager.show_debug_message(str(e)[:18])
                hw.display.refresh()
            except Exception as display_error:
                print(f"Failed to display error: {display_error}")

if __name__ == "__main__":
    main()
