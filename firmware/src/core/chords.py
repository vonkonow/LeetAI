#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************                                                              
#
#                   _/                                  _/            
#          _/_/_/  _/_/_/      _/_/    _/  _/_/    _/_/_/    _/_/_/   
#       _/        _/    _/  _/    _/  _/_/      _/    _/  _/_/        
#      _/        _/    _/  _/    _/  _/        _/    _/      _/_/     
#       _/_/_/  _/    _/    _/_/    _/          _/_/_/  _/_/_/        
#                                                                                                                              
# Chords is a mockup that generates a chord progression (hardcoded for demovideo)
# It sends "chord packets" to an arp unit that transposes the arpeggio.
#
# Todo:
#   * proper graphics (uses fake images today)
#   * add support for 1.1 hardware (only tested on 1.0)
#   * fix mute leds
#   * fix menu and debug graphics (reduce markov size)
#
# Done:
#   250426:
#     x major code refactoring and cleanup:
#       directory structure, common modules, manager classes and error handling
#   250303
#   *   updated LEDs
#   250308
#   *   hard coded UI
#   *   code clean (removed unused functions and variables)
#
# ******************************************************************************
import config.config as config
import espnow									                  # type: ignore
from src.common import hw										                  # type: ignore
import time										                  # type: ignore
import usb_midi
import adafruit_midi
from src.common.network import PacketHandler
from src.common.ui import DisplayManager, Sprite, Image, colorwheel
from src.common.menu import MenuManager

class ChordConfig:
    """Configuration management for chord playback."""
    def __init__(self):
        self.mode = config.MODE
        self.instrument_id = config.INSTRUMENT_ID
        self.hw_version = config.HW_VERSION
        self.nr_keys = config.NR_KEYS
        self.midi_channel = config.MIDI_CHANNEL
        self.default_intensity = config.DEFAULT_INTENSITY
        self.mac_broadcast = config.MAC_BROADCAST

# Initialize configuration
chord_config = ChordConfig()

class ChordLEDManager:
    """Manages LED states for chord visualization."""
    def __init__(self, nr_keys):
        self.nr_keys = nr_keys

    def clear_all(self):
        """Clear all LEDs."""
        for i in range(self.nr_keys):
            hw.pixels[i] = 0x000000

    def set_chord_leds(self, chord):
        """Set LEDs for a chord pattern."""
        # Clear all LEDs first
        self.clear_all()
        
        # Set chord pattern LEDs
        for i in range(2, 9):
            hw.pixels[(chord[1] + chord[i]) % 12] = 0x200010
        
        # Set root note LED with color based on octave
        hw.pixels[chord[1] % 12] = colorwheel(int(chord[1] / 12) * 20 & 255)

class ChordNetworkHandler:
    """Handles all network-related operations for chord playback."""
    def __init__(self, esp, instrument_id, peer_broadcast):
        self.packet_handler = PacketHandler(esp, instrument_id, peer_broadcast)
        self.esp = esp
        self.peer_broadcast = peer_broadcast

    def send_chord(self, chord):
        """Send a chord packet."""
        packet = bytearray()
        packet.append(ord('n'))
        packet.extend(bytearray(chord))
        self.esp.send(packet, self.peer_broadcast)

    def send_note(self, note, intensity):
        """Send a note packet."""
        packet = bytearray()
        packet.append(ord('l'))
        packet.append(chord_config.instrument_id)
        packet.append(note)
        packet.append(intensity)
        self.esp.send(packet, self.peer_broadcast)

    def read_packet(self):
        """Read a packet from the network."""
        return self.packet_handler.read_packet()

    def handle_packet(self, packet):
        """Handle a received packet."""
        return self.packet_handler.handle_packet(packet)

    def send_pair(self):
        """Send a pair request packet."""
        self.packet_handler.send_pair()

# Initialize ESP-NOW if in chords mode
if chord_config.mode == "chords":
    esp = espnow.ESPNow()
    peer_broadcast = espnow.Peer(mac=chord_config.mac_broadcast)
    esp.peers.append(peer_broadcast)
    network_handler = ChordNetworkHandler(esp, chord_config.instrument_id, peer_broadcast)

# Initialize LED manager
led_manager = ChordLEDManager(chord_config.nr_keys)

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=chord_config.midi_channel-1)
old_note = 0

class TimingManager:
    """Manages timing and synchronization."""
    def __init__(self):
        self.tick_delta = 0
        self.ticks_per_beat = 480
        self.max_tick = 47522
        self.tempo = 160
        self.denominator = 4
        self.start_time = time.monotonic()
        self._update_timing()

    def _update_timing(self):
        """Update timing calculations."""
        self.tick_to_time = (60 * 4) / (self.tempo * self.ticks_per_beat * self.denominator)
        self.time_to_tick = (self.tempo * self.ticks_per_beat * self.denominator) / (60 * 4)

    def update_from_packet(self, args):
        """Update timing from packet data."""
        self.ticks_per_beat = args[0]
        self.max_tick = args[1]
        self.tempo = args[2]
        self.numerator = args[3]
        self.denominator = args[4]
        self.nr_instruments = args[5]
        self._update_timing()

    def get_current_tick(self):
        """Get current tick based on elapsed time."""
        return int(self.time_to_tick * (time.monotonic() - self.start_time))

    def reset(self):
        """Reset timing to start."""
        self.start_time = time.monotonic()

class ChordState:
    """State management for chord playback."""
    def __init__(self):
        self.old_note = 0
        self.mute = 0
        self.modes = {"paused": 0, "playing": 1, "reset": 2, "clear": 3}
        self.mode = self.modes["clear"]
        self.bar_count = 0
        self.arp_pos = 3
        self.arp_pos_new = 0
        self.tick_offset = 250
        self.timing = TimingManager()

class ChordManager:
    """Manages chord progression and playback."""
    def __init__(self):
        self.chords = self._initialize_chords()
        
    def _initialize_chords(self):
        """Initialize chord progression."""
        return [
            [36, 60, 0, 2, 4, 5, 7, 9, 11],  # C major
            [40, 55, 0, 2, 4, 5, 7, 9, 11],  # Em7
            [45, 57, 0, 2, 3, 5, 7, 8, 10],  # Am
            [41, 65, 0, 2, 4, 5, 7, 9, 11]   # F major
        ]
    
    def get_chord(self, index):
        """Get chord at specified index."""
        return self.chords[index % len(self.chords)]
    
    def get_current_chord(self, bar_count):
        """Get current chord based on bar count."""
        return self.get_chord(bar_count)

class ChordPlayer:
    """Handles chord playback and state management."""
    
    def __init__(self, display_manager):
        """Initialize the chord player with default settings."""
        self.display_manager = display_manager
        self.state = ChordState()
        self.chord_manager = ChordManager()

    def _update_display(self, chord, arp_pos):
        """Update display with current chord and position."""
        if not self.display_manager:
            return
            
        self.display_manager.sprites['background'].replace(f"assets/images/chord{arp_pos}.bmp")
        self.display_manager.update_channel_info(chord[1], chord[2], chord[3])

    def handle_playback(self):
        """Handle chord playback and display updates."""
        if self.state.mode != self.state.modes["playing"]:
            return

        now = time.monotonic()
        arp_tick = int(((now - self.state.timing.start_time) * self.state.timing.time_to_tick + self.state.tick_offset) % 
                      (self.state.timing.ticks_per_beat * 16))
        self.state.arp_pos_new = int(arp_tick/(self.state.timing.ticks_per_beat*4))
        
        if self.state.arp_pos_new > self.state.arp_pos or (self.state.arp_pos == 3 and self.state.arp_pos_new == 0):
            chord = self.chord_manager.get_current_chord(self.state.bar_count)
            new_chord(chord, False)

            print("arp_tick", arp_tick, "arp_pos_new", self.state.arp_pos_new, "arp_pos", self.state.arp_pos)
            self.state.arp_pos = self.state.arp_pos_new
            self.state.bar_count += 1
            
            if self.display_manager:
                self._update_display(chord, self.state.arp_pos_new)

    def handle_packet(self, packet):
        """Handle incoming network packets."""
        if not packet or not network_handler:
            return

        result = network_handler.handle_packet(packet)
        if not result:
            return

        packet_type, *args = result
        
        if packet_type == 'tick':
            tick = args[0]
            now_tick = self.state.timing.get_current_tick()
            self.state.timing.tick_delta = tick - now_tick
            
        elif packet_type == 'begin':
            self.state.timing.reset()
            self.state.mode = self.state.modes["playing"]
            if self.display_manager:
                self.display_manager.show_debug_message("playing")
            
        elif packet_type == 'stop':
            self.state.mode = self.state.modes["paused"]
            if self.display_manager:
                self.display_manager.show_debug_message("paused")
            
        elif packet_type == 'header':
            self.state.timing.update_from_packet(args)
            
        elif packet_type == 'live':
            ch, note, intensity = args
            if ch == chord_config.instrument_id:
                self.state.mute = intensity
                if self.display_manager:
                    self.display_manager.show_debug_message("muted" if self.state.mute else " ")
                
        elif packet_type == 'mute':
            ch, intensity = args
            if ch == chord_config.instrument_id:
                self.state.mute = intensity
                if self.display_manager:
                    self.display_manager.show_debug_message("muted" if self.state.mute else " ")
                
        elif packet_type == 'update':
            if self.display_manager:
                self.display_manager.show_debug_message("update")
                self.display_manager.show_debug_message(" ")
                self.display_manager.sprites['background'].clear(0)
                self.display_manager.update_channel_info(0, 0, 0)
            
        elif packet_type == 'reset':
            self.state.timing.reset()
            if self.display_manager:
                self.display_manager.show_debug_message("reset")
            self.state.arp_pos = 3
            self.state.bar_count = 0
            chord = self.chord_manager.get_chord(0)
            new_chord(chord, True)
            if self.display_manager:
                self.display_manager.update_channel_info(0, 0, 0)
                self.display_manager.sprites['background'].replace("assets/images/chord0.bmp")
            
        elif packet_type == 'clear':
            if args[0] == chord_config.instrument_id or args[0] == 255:
                self.state.mode = self.state.modes["clear"]

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

def initialize_display():
    """Initialize display components."""
    try:
        display_manager = DisplayManager(hw.display, hw)
        
        # Load initial background
        display_manager.sprites['background'] = Image(display_manager.display_group, "assets/images/chord0.bmp")
        
        return display_manager
    except Exception as e:
        report_error(None, f"Display initialization error: {e}", True)
        raise


def new_chord(chord, mute):
    """Handle new chord events."""
    global old_note
    print("chord", chord)
    
    # Send chord packet
    if network_handler:
        network_handler.send_chord(chord)

    if not mute:
        if old_note != 0:
            # Turn off previous note
            if network_handler:
                network_handler.send_note(old_note, 0)

        # Send new note
        if network_handler:
            network_handler.send_note(chord[0], chord_config.default_intensity)
        old_note = chord[0]

    # Update LEDs using LED manager
    if led_manager:
        led_manager.set_chord_leds(chord)    

# ------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

def main():
    """Main function for chord playback and control."""
    try:
        # Initialize display
        display_manager = initialize_display()
        if not display_manager:
            report_error(None, "Failed to initialize display", True)
            return

        # Initialize menu manager
        menu_manager = MenuManager(config.MENU_FILE, display_manager)
        if not menu_manager:
            report_error(display_manager, "Failed to initialize menu manager", True)
            return

        print("waiting for packets...")
        
        # Initialize chord player
        player = ChordPlayer(display_manager)
        if not player:
            report_error(display_manager, "Failed to initialize chord player", True)
            return
        
        # Send pair request if network is initialized
        if 'network_handler' in globals():
            network_handler.send_pair()

        while True:
            try:
                # Handle playback
                if player:
                    player.handle_playback()

                # Handle network packets
                if esp and 'network_handler' in globals():
                    packet = network_handler.read_packet()
                    if packet:
                        print(packet)
                        if player:
                            player.handle_packet(packet)

                # Handle menu navigation
                if menu_manager:
                    try:
                        rotation = 0  # Initialize rotation to 0
                        
                        if chord_config.hw_version == 1.1:
                            rotation = hw.check_rotation(0, 512)
                        elif chord_config.hw_version == 1.0:
                            if hw.check_rotation(config.ROTATION_CW):
                                rotation = 1
                            elif hw.check_rotation(config.ROTATION_CCW):
                                rotation = -1
                        
                        if rotation:
                            menu_manager.handle_rotation(rotation)
                        if hw.key_new(config.KEY_BACK):
                            menu_manager.handle_back()
                        if hw.key_new(config.KEY_SELECT):
                            menu_manager.handle_select()
                    except Exception as e:
                        report_error(display_manager, f"Menu navigation error: {e}")

            except Exception as e:
                report_error(display_manager, f"Main loop error: {e}")
                time.sleep(0.1)  # Brief pause to prevent tight error loop

    except Exception as e:
        report_error(display_manager, f"Fatal error: {e}", True)
        try:
            if 'display_manager' in locals() and display_manager:
                display_manager.show_debug_message("Fatal error")
        except:
            pass  # Ignore any errors in error handling

if __name__ == "__main__":
    main()
