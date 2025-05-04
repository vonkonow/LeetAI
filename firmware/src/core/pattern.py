#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************
#     ______   ______     ______   ______   ______     ______     __   __    
#    /\  == \ /\  __ \   /\__  _\ /\__  _\ /\  ___\   /\  == \   /\ "-.\ \   
#    \ \  _-/ \ \  __ \  \/_/\ \/ \/_/\ \/ \ \  __\   \ \  __<   \ \ \-.  \  
#     \ \_\    \ \_\ \_\    \ \_\    \ \_\  \ \_____\  \ \_\ \_\  \ \_\\"\_\ 
#      \/_/     \/_/\/_/     \/_/     \/_/   \/_____/   \/_/ /_/   \/_/ \/_/ 
#
# Pattern is a synthesizer with a sequenser setup (suitable for Drums)
# It recieves data wirelessly from the Boss unit that also renders the audio.
#
# Todo:
# * implement mute handling
# * implement beat edit (key input and channel select)
# * implement menu driven sample mapping (hardcoded today)
#
# Done:
#   250426:
#     x major code refactoring and cleanup:
#       directory structure, common modules, manager classes and error handling
# 250104:
#   x Implemented first version (based on pitch)
#   x 
#
# ******************************************************************************
"""
Pattern mode implementation for the music application.
"""

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
from src.common.ui import DisplayManager, Field
from src.common.network import PacketHandler, PacketReadError
from src.common.menu import MenuManager
from src.common.song import LocalSong

# load config
MODE = config.MODE
INSTRUMENT_ID = config.INSTRUMENT_ID
MIDI_CHANNEL = config.MIDI_CHANNEL
DEFAULT_INTENSITY = config.DEFAULT_INTENSITY
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=MIDI_CHANNEL-1)

if MODE == "pattern":
    esp = espnow.ESPNow()
    peer_broadcast = espnow.Peer(mac=config.MAC_BROADCAST)
    esp.peers.append(peer_broadcast)
    packet_handler = PacketHandler(esp, INSTRUMENT_ID, peer_broadcast)

class PatternState:
    """
    A class for managing pattern mode state.
    
    Attributes:
        instrument_id: ID of the instrument
        mode: Current mode (paused, playing, reset, clear)
        song_index: Current position in song
        selected_channel: Selected channel
        is_muted: Mute state
        current_pixel: Current pixel position
        previous_pixel: Previous pixel position
        needs_display_update: Flag for display update
        tick_delta: Time delta for ticks
        playback_start_time: Start time for playback
    """
    
    def __init__(self, instrument_id: int):
        """Initialize pattern state."""
        self.instrument_id = instrument_id
        self.mode = "clear"
        self.song_index = 0
        self.selected_channel = 0
        self.is_muted = 0
        self.current_pixel = 0
        self.previous_pixel = 0
        self.needs_display_update = 0
        self.tick_delta = 0
        self.playback_start_time = time.monotonic()

    def set_mode(self, mode: str) -> None:
        """
        Set the pattern mode.
        
        Args:
            mode: Mode to set
            
        Raises:
            PatternStateError: If mode is invalid
        """
        if mode not in config.MODES:
            raise PatternStateError(f"Invalid mode: {mode}")
        self.mode = mode

class PatternHardware:
    """
    A class for managing hardware interactions in pattern mode.
    
    Attributes:
        hw: Hardware interface
        drum_notes: List of drum note numbers
        drum_names: List of drum names
    """
    
    def __init__(self, hw):
        """Initialize pattern hardware interface."""
        self.hw = hw
        self.drum_notes = config.DRUM_NOTES
        self.drum_names = config.DRUM_NAMES
    
    def handle_key_input(self, pixel_pos: int, selected_channel: int, song: LocalSong, state: PatternState, field: Field, display_manager: DisplayManager) -> bool:
        """
        Handle key input for pattern editing.
        
        Args:
            pixel_pos: Current pixel position
            selected_channel: Selected channel
            song: LocalSong instance
            state: PatternState instance
            field: Field instance
            display_manager: DisplayManager instance
            
        Returns:
            bool: True if key was pressed, False otherwise
        """
        for i in range(20):
            if self.hw.key_new(i):
                roll_position = i + pixel_pos - pixel_pos % 16
                print("key:", str(i), song.pattern_roll[roll_position])
                if not self.drum_notes[selected_channel] in song.pattern_roll[roll_position]:
                    song.pattern_roll[roll_position].append(self.drum_notes[selected_channel])
                    forced_update = True
                    state.previous_pixel = update_roll(pixel_pos, state.previous_pixel, selected_channel, forced_update, song.pattern_roll, field)
                    self.hw.display.refresh()
                else:
                    song.pattern_roll[roll_position].remove(self.drum_notes[selected_channel])
                    forced_update = True
                    state.previous_pixel = update_roll(pixel_pos, state.previous_pixel, selected_channel, forced_update, song.pattern_roll, field)
                    self.hw.display.refresh()
                return True
        return False
    
    def handle_menu_navigation(self, menu_manager: MenuManager) -> None:
        """
        Handle menu navigation.
        
        Args:
            menu_manager: MenuManager instance
        """
        rotation = self.hw.check_rotation(0, config.DISPLAY_REFRESH_RATE)
        if rotation != 0:
            menu_manager.handle_rotation(rotation)
        if self.hw.key_new(13):  # menu back
            menu_manager.handle_back()
        if self.hw.key_new(12):  # menu select
            menu_manager.handle_select()
    
    def handle_drum_selection(self, state: PatternState, song: LocalSong, field: Field, display_manager: DisplayManager) -> None:
        """
        Handle drum selection.
        
        Args:
            state: PatternState instance
            song: LocalSong instance
            field: Field instance
            display_manager: DisplayManager instance
        """
        rotation = self.hw.check_rotation(1, config.DISPLAY_REFRESH_RATE)
        # next drum (cw)
        if rotation == 1:
            state.selected_channel -= 1
            if state.selected_channel < 0:
                state.selected_channel = 0
            display_manager.text_fields['title'].showText(self.drum_names[state.selected_channel])
            forced_update = True
            state.previous_pixel = update_roll(state.current_pixel, state.previous_pixel, state.selected_channel, forced_update, song.pattern_roll, field)
            self.hw.display.refresh()
        # previous drum (ccw)
        elif rotation == -1:
            state.selected_channel += 1
            if state.selected_channel > 3:
                state.selected_channel = 3
            display_manager.text_fields['title'].showText(self.drum_names[state.selected_channel])
            forced_update = True
            state.previous_pixel = update_roll(state.current_pixel, state.previous_pixel, state.selected_channel, forced_update, song.pattern_roll, field)
            self.hw.display.refresh()

# Forward declaration of PatternDisplay to allow type annotations
class PatternDisplay:
    """Forward declaration placeholder."""
    pass

class PatternPacketHandler:
    """
    A class for handling packets in pattern mode.
    
    Attributes:
        packet_handler: PacketHandler instance
        instrument_id: ID of the instrument
        display_manager: DisplayManager instance
        field: Field instance
        song: LocalSong instance
        state: PatternState instance
        pattern_display: PatternDisplay instance
    """
    
    def __init__(self, packet_handler: PacketHandler, instrument_id: int, 
                 display_manager: DisplayManager, field: Field, 
                 song: LocalSong, state: PatternState, pattern_display: PatternDisplay):
        """Initialize pattern packet handler."""
        self.packet_handler = packet_handler
        self.instrument_id = instrument_id
        self.display_manager = display_manager
        self.field = field
        self.song = song
        self.state = state
        self.pattern_display = pattern_display
        self.modes = config.MODES
    
    def handle_packet(self, packet) -> None:
        """
        Handle a received packet.
        
        Args:
            packet: Received packet
            
        Raises:
            PatternPacketError: If packet handling fails
        """
        try:
            if packet is None:
                return
                
            result = self.packet_handler.handle_packet(packet)
            if result:
                if result[0] == 'tick':
                    self._handle_tick_packet(result)
                elif result[0] == 'begin':
                    self._handle_begin_packet(result)
                elif result[0] == 'stop':
                    self._handle_stop_packet(result)
                elif result[0] == 'header':
                    self._handle_header_packet(result)
                elif result[0] == 'mute':
                    self._handle_mute_packet(result)
                elif result[0] == 'update':
                    self._handle_update_packet()
                elif result[0] == 'reset':
                    self._handle_reset_packet()
                elif result[0] == 'clear':
                    self._handle_clear_packet(result)
                elif result[0] == 'event':
                    self._handle_event_packet(result)  # Pass the full result tuple
        except Exception as e:
            raise PatternPacketError(f"Failed to handle packet: {str(e)}") from e
    
    def _handle_tick_packet(self, packet) -> None:
        """Handle tick packet."""
        # packet is a tuple: ('tick', tick)
        _, tick = packet
        now_tick = int(time_to_tick * (time.monotonic() - self.state.playback_start_time))
        self.state.tick_delta = tick - now_tick
        print("now", now_tick, "in_tick", tick, "delta", self.state.tick_delta)
    
    def _handle_begin_packet(self, packet) -> None:
        """Handle begin packet."""
        # packet is a tuple: ('begin',)
        self.state.playback_start_time = time.monotonic() - self.song.get_event(self.state.song_index)[0] * tick_to_time   
        self.state.mode = self.modes["playing"]
        self.display_manager.show_debug_message("playing")
        self.display_manager.hw.display.refresh()
    
    def _handle_stop_packet(self, packet) -> None:
        """Handle stop packet."""
        # packet is a tuple: ('stop',)
        self.state.mode = self.modes["paused"]
        self.display_manager.show_debug_message("paused")
        self.display_manager.hw.display.refresh()
    
    def _handle_header_packet(self, packet) -> None:
        """Handle header packet."""
        # packet is a tuple: ('header', ticks_per_beat, max_tick, tempo, numerator, denominator, nr_instruments)
        _, ticks_per_beat, max_tick, tempo, numerator, denominator, nr_instruments = packet
        self.song.update_header(ticks_per_beat, max_tick, tempo, numerator, denominator, nr_instruments)
        # Update local timing variables from song metadata
        global tick_to_time, time_to_tick, song_length, sprite_tick, sprite_time, max_pixels
        tick_to_time = self.song.get_metadata('tick_to_time')
        time_to_tick = self.song.get_metadata('time_to_tick')
        song_length = self.song.get_metadata('song_length')
        sprite_tick = self.song.get_metadata('sprite_tick')
        sprite_time = self.song.get_metadata('sprite_time')
        max_pixels = self.song.get_metadata('max_pixels')
        self.state.mode = self.modes["paused"]
    
    def _handle_mute_packet(self, packet) -> None:
        """Handle mute packet."""
        # packet is a tuple: ('mute', ch, intensity)
        _, ch, intensity = packet
        if ch == self.instrument_id:
            self.state.is_muted = intensity
            if self.state.is_muted:
                self.display_manager.update_mute_leds([True] * 12)
                self.display_manager.show_debug_message("muted")
                self.display_manager.hw.display.refresh()
            else:
                self.display_manager.update_mute_leds([False] * 12)
                self.display_manager.show_debug_message(" ")
                self.display_manager.hw.display.refresh()
    
    def _handle_update_packet(self) -> None:
        """Handle update packet."""
        # packet is a tuple: ('update',)
        self.display_manager.show_debug_message("update")
        self.display_manager.show_debug_message(" ")
        redraw()
        self.pattern_display.update_display()
    
    def _handle_reset_packet(self) -> None:
        """Handle reset packet."""
        # packet is a tuple: ('reset',)
        self.field.reset(0)
        self.state.song_index = 0
        if self.song.get_event_count() > 0:
            event = self.song.get_event(0)
            if event:
                self.state.playback_start_time = time.monotonic() - event[0] * tick_to_time   
        self.state.current_pixel = 0
        self.state.previous_pixel = 15
        self.display_manager.show_debug_message("reset")
        self.pattern_display.update_display()
    
    def _handle_clear_packet(self, packet) -> None:
        """Handle clear packet."""
        # packet is a tuple: ('clear', id)
        _, id = packet
        if id == self.instrument_id or id == 255:
            self.field.reset(0)
            self.song.clear()
            self.state.song_index = 0
            self.display_manager.show_debug_message("receiving")
            self.display_manager.hw.display.refresh()
            self.state.mode = self.modes["clear"]
    
    def _handle_event_packet(self, packet) -> None:
        """Handle event packet."""
        if packet is None:
            return
            
        # packet is a tuple: ('event', ch, tick_start, tick_end, note, intensity)
        _, ch, tick_start, tick_end, note, intensity = packet
        
        if ch == self.instrument_id:
            self.song.add_event(tick_start, tick_end, note, intensity)
            # add event to pattern_roll
            pixel_start = int(tick_start / self.song.get_metadata('ticks_per_pixel'))
            if pixel_start < len(self.song.pattern_roll):
                self.song.pattern_roll[pixel_start].append(note)

class PatternPlayback:
    """
    A class for managing playback in pattern mode.
    
    Attributes:
        song: LocalSong instance
        state: PatternState instance
        display_manager: DisplayManager instance
        field: Field instance
        midi: MIDI interface
    """
    
    def __init__(self, song: LocalSong, state: PatternState, 
                 display_manager: DisplayManager, field: Field, midi):
        """Initialize pattern playback."""
        self.song = song
        self.state = state
        self.display_manager = display_manager
        self.field = field
        self.midi = midi
        self.modes = {"paused":0, "playing":1, "reset":2, "clear":3}
    
    def update(self) -> None:
        """
        Update playback state.
        
        Raises:
            PatternPlaybackError: If playback update fails
        """
        try:
            ch = 0
            note = 0
            intensity = 0

            if self.state.mode == self.modes["playing"] and self.state.song_index < self.song.get_event_count():
                # new event to play?
                now = time.monotonic()
                event = self.song.get_event(self.state.song_index)
                if event and now >= (self.state.playback_start_time + (event[0] - self.state.tick_delta) * self.song.get_metadata('tick_to_time')):
                    ch = event[1]
                    note = event[2]
                    intensity = event[3]
                    self.state.song_index += 1

                    if ch == self.state.instrument_id:
                        # send USB midi command
                        i = note % 12
                        if(intensity==0):
                            self.midi.send(NoteOff(note, intensity))
                        else:
                            if not self.state.is_muted:
                                self.midi.send(NoteOn(note, intensity))
                
                # update textfields on display
                self.display_manager.update_channel_info(ch, note, intensity)
        
                # update display
                self.state.current_pixel = int((self.song.get_metadata('time_to_tick') * (now - self.state.playback_start_time) + self.state.tick_delta) / self.song.get_metadata('ticks_per_pixel')) 
                if self.state.current_pixel > self.state.previous_pixel:
                    forced_update = False
                    self.state.previous_pixel = update_roll(
                        self.state.current_pixel, 
                        self.state.previous_pixel, 
                        self.state.selected_channel, 
                        forced_update, 
                        self.song.pattern_roll,
                        self.field
                    )
                    self.display_manager.hw.display.refresh()
            
            if self.state.song_index >= self.song.get_event_count():
                # end of song (no action since conductor stops and resets song)
                pass
        except Exception as e:
            raise PatternPlaybackError(f"Failed to update playback: {str(e)}") from e

class PatternDisplay:
    """
    A class for managing display updates in pattern mode.
    
    Attributes:
        display_manager: DisplayManager instance
        field: Field instance
        state: PatternState instance
        song: LocalSong instance
    """
    
    def __init__(self, display_manager: DisplayManager, field: Field, 
                 state: PatternState, song: LocalSong):
        """Initialize pattern display."""
        self.display_manager = display_manager
        self.field = field
        self.state = state
        self.song = song
    
    def update_display(self, forced_update: bool = False) -> None:
        """
        Update the display.
        
        Args:
            forced_update: Whether to force a full display update
        """
        self.display_manager.update_mute_leds([False] * 12)
        self.state.previous_pixel = update_roll(
            self.state.current_pixel, 
            self.state.previous_pixel, 
            self.state.selected_channel, 
            forced_update, 
            self.song.pattern_roll,
            self.field
        )
        self.display_manager.update_channel_info(0, 0, 0)
        redraw()
    
    def update_channel_info(self, ch: int, note: int, intensity: int) -> None:
        """
        Update channel information display.
        
        Args:
            ch: Channel number
            note: Note number
            intensity: Note intensity
        """
        self.display_manager.update_channel_info(ch, note, intensity)
    
    def show_debug_message(self, message: str) -> None:
        """
        Show a debug message.
        
        Args:
            message: Debug message to display
        """
        self.display_manager.show_debug_message(message)
        self.display_manager.hw.display.refresh()
    
    def update_mute_leds(self, is_muted: bool) -> None:
        """
        Update mute LED states.
        
        Args:
            is_muted: Whether the channel is muted
        """
        self.display_manager.update_mute_leds([is_muted] * 12)

def update_roll(pixel_pos, old_pixel_pos, selected_ch, forced_update, pattern_roll, field):
    """
    Update the pattern roll display.
    
    Args:
        pixel_pos: Current pixel position
        old_pixel_pos: Previous pixel position
        selected_ch: Selected channel
        forced_update: Whether to force a full update
        pattern_roll: Pattern roll data
        field: Field instance for display updates
        
    Returns:
        int: Updated pixel position
    """
    drum_notes = [36, 38, 42, 57]  # MIDI note numbers for drums
        
    if pixel_pos < 0:
        pixel_pos = 0
    if pixel_pos >= len(pattern_roll):
        pixel_pos = len(pattern_roll) - 1
        
    current_column = pixel_pos % 16
    previous_column = old_pixel_pos % 16        
    
    # new page?
    if forced_update:
        for x, i in enumerate(range(pixel_pos, pixel_pos + config.FIELD_X_MAX)):
            hw.pixels[x] = (0,0,0)
            if 0 <= i < len(pattern_roll):
                for y in range(4):
                    if not drum_notes[y] in pattern_roll[i]:
                        field.setBlock(x, y, 0) # black
                    else:
                        field.setBlock(x, y, 1) # red
                        if y == selected_ch:
                            hw.pixels[x] = (18,70,23)

    elif current_column < previous_column:
        column_offset = 16
        for x, i in enumerate(range(pixel_pos, pixel_pos + config.FIELD_X_MAX)):
            hw.pixels[x] = (0,0,0)
            if 0 <= i < len(pattern_roll):
                for note in pattern_roll[i-column_offset]:
                    if not note in pattern_roll[i]:
                        field.setBlock(x, drum_notes.index(note), 0) # black
                for note in pattern_roll[i]:
                    if not note in pattern_roll[i-column_offset]:
                        field.setBlock(x, drum_notes.index(note), 1) # red
                        if drum_notes.index(note) == selected_ch:
                            hw.pixels[x] = (18,70,23)
    
    for y in range(config.FIELD_Y_MAX):
        # restore previous column
        if 0 <= old_pixel_pos < len(pattern_roll) and drum_notes[y] in pattern_roll[old_pixel_pos]:
            field.setBlock(previous_column, y, 1) # red
            if y == selected_ch:
                hw.pixels[previous_column] = (18,70,23)
        else:
            field.setBlock(previous_column, y, 0) # black
            if y == selected_ch:
                hw.pixels[previous_column] = (0,0,0)
        # update current column    
        if 0 <= pixel_pos < len(pattern_roll) and drum_notes[y] in pattern_roll[pixel_pos]:
            if y == selected_ch:
                hw.pixels[current_column] = (200,200,200)
                field.setBlock(current_column, y, 5) # white
            else:
                field.setBlock(current_column, y, 3) # light red
        else:
            if y == selected_ch:
                hw.pixels[current_column] = (14,0,20)
                field.setBlock(current_column, y, 4) # light blue
            else:
                field.setBlock(current_column, y, 2) # blue
    return pixel_pos

def redraw():
    """Create and remove a black sprite to refresh the screen."""
    black_sprite = displayio.TileGrid(displayio.Bitmap(160, 128, 1), pixel_shader=displayio.Palette(1), x=0, y=0)
    hw.displayGroup.append(black_sprite)
    hw.displayGroup.pop()
    hw.display.refresh()

def show_device_ip():
    """Show the device's IP address."""
    # TODO: Implement IP display
    pass

def show_connected_devices():
    """Show list of connected devices."""
    # TODO: Implement connected devices display
    pass

def set_device_mode(mode_id):
    """Set the device mode."""
    # TODO: Implement mode setting
    pass


# Define error classes
class PatternError(Exception):
    """Base exception for pattern mode errors."""
    pass

class PatternStateError(PatternError):
    """Exception for pattern state errors."""
    pass

class PatternDisplayError(PatternError):
    """Exception for pattern display errors."""
    pass

class PatternPlaybackError(PatternError):
    """Exception for pattern playback errors."""
    pass

class PatternPacketError(PatternError):
    """Exception for pattern packet errors."""
    pass

def report_error(display_manager, error_msg, is_fatal=False):
    """
    Report an error to the display and console.
    
    Args:
        display_manager: DisplayManager instance
        error_msg: Error message to display
        is_fatal: Whether this is a fatal error
    """
    # Always print to serial console
    print(f"{'FATAL ERROR' if is_fatal else 'Error'}: {error_msg}")
    
    # Print to display if available
    if display_manager:
        try:
            prefix = "FATAL: " if is_fatal else "Error: "
            display_manager.show_debug_message(prefix + error_msg[:18])
        except Exception as e:
            print(f"Error displaying error message: {e}")

# ------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

def main():
    """Main application entry point."""
    try:
        # Initialize display manager
        display_manager = DisplayManager(hw.display, hw)
        
        # Load sprite_sheets from file
        try:
            sprite_sheet, palette = adafruit_imageload.load("assets/images/10x10.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
        except Exception as e:
            report_error(display_manager, f"Failed to load sprites: {e}", True)
            raise

        # Create a black background
        black_sprite = displayio.TileGrid(displayio.Bitmap(160, 128, 1), pixel_shader=displayio.Palette(1), x=0, y=0)
        hw.displayGroup.append(black_sprite)
        
        x_start, y_start = config.XSTART, config.YSTART
        field = Field(hw.displayGroup, sprite_sheet, palette, x_start, y_start, config.FIELD_X_MAX, config.FIELD_Y_MAX)
        display_manager.initialize_pattern_field(sprite_sheet, palette, x_start, y_start)

        # Initialize text fields
        display_manager.create_text_fields(MODE + " (CH" + str(INSTRUMENT_ID) + ")")
        hw.display.refresh()

        # Initialize menu manager with action dispatch table
        try:
            menu_actions = {
                'send_song': lambda: packet_handler.send_song() if packet_handler else None,
                'set_channel': lambda: set_channel(),
                'show_my_ip': lambda: show_device_ip(),
                'send_pair': lambda: packet_handler.send_pair() if packet_handler else None,
                'show_paired_devices': lambda: show_connected_devices(),
                'set_mode': lambda mode_id: set_device_mode(mode_id)
            }
            menu_manager = MenuManager(config.MENU_FILE, display_manager, config.MENU_ACTIONS)
        except Exception as e:
            report_error(display_manager, f"Menu init error: {e}", True)
            raise

        print("waiting for packets...")
        
        # Initialize pattern state
        state = PatternState(INSTRUMENT_ID)
        
        # init song
        try:
            song = LocalSong(INSTRUMENT_ID)
        except Exception as e:
            report_error(display_manager, f"Song init error: {e}", True)
            raise
        
        # Initialize timing variables from song metadata
        tick_to_time = song.get_metadata('tick_to_time')
        time_to_tick = song.get_metadata('time_to_tick')
        ticks_per_pixel = song.get_metadata('ticks_per_pixel')
        max_pixels = song.get_metadata('max_pixels')
        
        """Send a pair request packet."""
        try:
            packet_handler.send_pair()
        except Exception as e:
            report_error(display_manager, f"Failed to send pair request: {e}")

        # Initialize pattern hardware
        pattern_hw = PatternHardware(hw)
        
        # Initialize pattern display first since it's needed by packet handler
        pattern_display = PatternDisplay(display_manager, field, state, song)
        
        # Initialize pattern packet handler
        pattern_packet_handler = PatternPacketHandler(packet_handler, INSTRUMENT_ID, display_manager, field, song, state, pattern_display)
        
        # Initialize pattern playback
        pattern_playback = PatternPlayback(song, state, display_manager, field, midi)
        
        while True:
            try:
                pattern_playback.update()
                
                if esp:
                    try:
                        packet = packet_handler.read_packet()
                    except PacketReadError as e:
                        report_error(display_manager, f"Failed to read packet: {e}")
                        pattern_display.show_debug_message("packet error")
                    else:
                        if packet:
                            try:
                                pattern_packet_handler.handle_packet(packet)
                            except PatternPacketError as e:
                                report_error(display_manager, f"Failed to handle packet: {e}")
                                pattern_display.show_debug_message("packet error")
                
                
                
                # check key input
                pattern_hw.handle_key_input(state.current_pixel, state.selected_channel, song, state, field, display_manager)
                
                # Handle menu navigation
                pattern_hw.handle_menu_navigation(menu_manager)
                
                # Handle drum selection
                pattern_hw.handle_drum_selection(state, song, field, display_manager)
            except PatternError as e:
                report_error(display_manager, str(e))
                pattern_display.show_debug_message("error")
            except Exception as e:
                report_error(display_manager, f"Unexpected error: {e}")
                pattern_display.show_debug_message("error")
    except Exception as e:
        report_error(display_manager, f"Fatal error: {e}", True)
        raise

if __name__ == "__main__":
    main() 