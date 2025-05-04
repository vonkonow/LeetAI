#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************
#                                                                                          
#              /$$$$$$   /$$$$$$   /$$$$$$ 
#             |____  $$ /$$__  $$ /$$__  $$
#              /$$$$$$$| $$  \__/| $$  \ $$
#             /$$__  $$| $$      | $$  | $$
#            |  $$$$$$$| $$      | $$$$$$$/
#             \_______/|__/      | $$____/ 
#                                | $$      
#                                |__/      
# Mockup to show how an arpeggiator could work, (hardcoded for demovideo)
# It recieves "scale packets" from chords unit that transposes the arpeggio
# 
# Todo:
#   *   proper graphics (uses fake images today)
#   *   add support for 1.1 hardware (only tested on 1.0)
# Done:
#   250501:
#     x major code refactoring and cleanup:
#       directory structure, common modules, manager classes and error handling
#
# ******************************************************************************
import config.config as config
from src.common import hw
import espnow									                  # type: ignore
import time										                  # type: ignore
import displayio                       		                      # type: ignore
import adafruit_imageload                                         # type: ignore
from src.common.ui import DisplayManager, colorwheel
from src.common.network import PacketHandler, NetworkError, PacketSendError, PacketReadError, SongSendError
from src.common.menu import MenuManager


class Field:
    """Handles the display field for the arpeggiator pattern"""
    def __init__(self, display_group=None, sprite_sheet=None, palette=None, x_start=40, y_start=0, x_max=8, y_max=8, tile_width=10, tile_height=10):
        self.display_group = display_group
        self.sprite_sheet = sprite_sheet
        self.palette = palette
        self.x_start = x_start
        self.y_start = y_start
        self.x_max = x_max
        self.y_max = y_max
        self.tile_width = tile_width
        self.tile_height = tile_height
        
        # Create sprite grid
        self.grid = displayio.TileGrid(
            self.sprite_sheet,
            pixel_shader=self.palette,
            width=self.x_max,
            height=self.y_max,
            tile_width=self.tile_width,
            tile_height=self.tile_height,
            x=self.x_start,
            y=self.y_start
        )
        self.display_group.append(self.grid)

    def reset(self, value=0):
        """Reset all tiles to the given value"""
        for y in range(self.y_max):
            for x in range(self.x_max):
                self.grid[x, y] = value

    def setBlock(self, x, y, value):
        """Set a specific tile to the given value"""
        self.grid[x, y] = value

    def hLine(self):
        """Draw a horizontal line"""
        for x in range(self.x_max):
            self.grid[x, 0] = config.DEFAULT_TILE_VALUE

class Image:
    """Handles background images for the arpeggiator"""
    def __init__(self, filename, display_group=None):
        self.display_group = display_group
        self.filename = f"assets/images/{filename}"  # Add assets/images/ prefix
        self.sprite = None
        self.sprite_grid = None
        self.load_image()

    def load_image(self):
        """Load the background image"""
        if self.sprite_grid:
            self.display_group.remove(self.sprite_grid)
        self.sprite = displayio.OnDiskBitmap(self.filename)
        self.sprite_grid = displayio.TileGrid(
            self.sprite,
            pixel_shader=self.sprite.pixel_shader,
            x=0,
            y=config.BACKGROUND_Y_OFFSET  # Use config value for y-offset
        )
        self.display_group.append(self.sprite_grid)

    def replace(self, filename):
        """Replace the current background image"""
        self.filename = f"assets/images/{filename}"  # Add assets/images/ prefix
        self.load_image()

class ArpeggiatorState:
    """Manages the arpeggiator's internal state"""
    def __init__(self):
        self.mode = config.PLAYBACK_STATES["clear"]
        self.mute = 0
        self.ticks_per_beat = config.TICKS_PER_BEAT
        self.max_ticks = config.MAX_TICKS
        self.tempo = config.TEMPO
        self.denominator = config.DENOMINATOR
        self.start_time = time.monotonic()
        self.old_note = 0
        self.arp_pos = 0
        self.arp_notes = []
        self.chord_notes = []
        self.scale_notes = []
        self.arp2d = [[],[],[],[]]
        self.pos = 0
        
        # Calculate time conversion factors
        self.tick_to_time = (60 * 4) / (self.tempo * self.ticks_per_beat * self.denominator)
        self.time_to_tick = (self.tempo * self.ticks_per_beat * self.denominator) / (60 * 4)

    def update_scale(self, scale_start, scale):
        """Update scale and chord notes based on new scale"""
        self.scale_notes = [s + scale_start for s in scale]
        
        # Update chord notes
        self.chord_notes = []
        for a in range(0,5,2):
            note = scale[a] + scale_start
            while note > config.MAX_NOTE:
                note -= 12
            while note < config.MIN_NOTE:
                note += 12
            self.chord_notes.append(note)
        self.chord_notes.sort()

        # Update arpeggiator notes
        arp = config.DEFAULT_ARP_PATTERN
        self.arp_notes = [self.chord_notes[a] for a in arp]

    def reset(self):
        """Reset state to initial values"""
        self.start_time = time.monotonic()
        self.arp_pos = len(self.arp_notes) - 1 if self.arp_notes else 0
        self.pos = 0
        self.arp2d = [[],[],[],[]]

    def initialize_scale(self, scale_start=60):
        """Initialize scale with default values"""
        scale = [0, 2, 4, 5, 7, 9, 11]
        self.update_scale(scale_start, scale)

class ArpeggiatorUI:
    """Handles all UI-related operations for the arpeggiator"""
    def __init__(self, display_manager, hw):
        self.display_manager = display_manager
        self.hw = hw
        self.field = None
        self.background = None
        
        # Load sprite sheet
        self.sprite_sheet, self.palette = adafruit_imageload.load(
            "assets/images/10x10.bmp",
            bitmap=displayio.Bitmap,
            palette=displayio.Palette
        )
        
        self.initialize_ui()

    def initialize_ui(self):
        """Initialize UI components"""
        # Create field
        self.field = Field(
            display_group=self.hw.displayGroup,
            sprite_sheet=self.sprite_sheet,
            palette=self.palette,
            x_start=config.XSTART,
            y_start=config.YSTART,
            x_max=config.FIELD_X_MAX,
            y_max=config.FIELD_Y_MAX,
            tile_width=config.FIELD_TILE_WIDTH,
            tile_height=config.FIELD_TILE_HEIGHT
        )
        
        # Create background
        self.background = Image("arp0.bmp", self.hw.displayGroup)
        self.hw.display.refresh()

    def update_pattern(self, field, arp2d, pos):
        """Update the pattern display"""
        field.reset(0)
        for y in range(4):
            for x in arp2d[y]:
                field.setBlock(x, y, config.PATTERN_ACTIVE_TILE)
        field.setBlock(pos % config.FIELD_X_MAX, int(pos / config.FIELD_X_MAX), config.PATTERN_CURRENT_TILE)
        self.hw.display.refresh()

    def update_leds(self, notes, active_notes=None):
        """Update LED states"""
        if active_notes is None:
            active_notes = []
            
        # Clear all LEDs first
        for i in range(config.NEOPIXEL_NUM):
            self.hw.pixels[i] = config.LED_OFF_COLOR
            
        # Update LEDs for active notes
        for note in active_notes:
            self.hw.pixels[note % config.NEOPIXEL_NUM] = config.LED_ACTIVE_COLOR
            
        # Update LEDs for arpeggiator notes
        for note in notes:
            self.hw.pixels[note % config.NEOPIXEL_NUM] = config.LED_ACTIVE_COLOR

    def update_background(self, scale_start):
        """Update background image based on scale"""
        if scale_start == config.SCALE_C:
            self.background.replace("arp0.bmp")
        elif scale_start == config.SCALE_G:
            self.background.replace("arp1.bmp")
        elif scale_start == config.SCALE_A:
            self.background.replace("arp2.bmp")
        elif scale_start == config.SCALE_F:
            self.background.replace("arp3.bmp")
        self.hw.display.refresh()

class ArpeggiatorNetwork:
    """Handles all network-related operations for the arpeggiator"""
    def __init__(self, hw, instrument_id, peer_broadcast):
        self.hw = hw
        self.instrument_id = instrument_id
        self.peer_broadcast = peer_broadcast
        self.esp = None
        self.packet_handler = None
        self.initialize_network()

    def initialize_network(self):
        """Initialize ESP-NOW and packet handler"""
        if config.MODE == "arp":
            try:
                self.esp = espnow.ESPNow()
                self.peer_broadcast = espnow.Peer(mac=config.MAC_BROADCAST)
                self.esp.peers.append(self.peer_broadcast)
                self.packet_handler = PacketHandler(self.esp, self.instrument_id, self.peer_broadcast)
            except RuntimeError as e:
                if "Already running" in str(e):
                    # ESP-NOW is already initialized, reuse the instance
                    self.esp = espnow.ESPNow()
                    self.packet_handler = PacketHandler(self.esp, self.instrument_id, self.peer_broadcast)
                else:
                    raise

    def handle_packet(self, packet):
        """Process incoming network packet"""
        try:
            return self.packet_handler.handle_packet(packet)
        except PacketReadError as e:
            raise
        except Exception as e:
            raise

    def send_packet(self, packet_type, args):
        """Send a packet over the network"""
        try:
            self.packet_handler.send_packet(packet_type, args)
        except PacketSendError as e:
            raise
        except Exception as e:
            raise

    def send_note(self, note, intensity):
        """Send a note packet"""
        self.send_packet('l', [self.instrument_id, note, intensity])

class ArpeggiatorInput:
    """Handles all input-related operations for the arpeggiator"""
    def __init__(self, hw, state, ui, network):
        self.hw = hw
        self.state = state
        self.ui = ui
        self.network = network

    def handle_key_input(self):
        """Process key input events"""
        for i in range(12):
            val, new = self.hw.key_change(i)
            if new and val:
                self.state.arp2d, self.state.pos, old_pos, remove, add = newKey(self.state.arp2d, i, self.state.pos)
                self.ui.update_pattern(self.ui.field, self.state.arp2d, self.state.pos)
                if not self.state.mute:
                    self.network.send_note(self.state.arp_notes[i], config.DEFAULT_INTENSITY)
                
            elif new and not val:
                if not self.state.mute:
                    self.network.send_note(self.state.arp_notes[i], 0)

    def handle_menu_input(self, menu_manager):
        """Process menu navigation input"""
        rotation = 0  # Initialize rotation to 0
        if config.HW_VERSION == 1.1:
            rotation = self.hw.check_rotation(0, 512)
        elif config.HW_VERSION == 1.0:
            if self.hw.check_analog_rotation(config.ROTATION_CW):
                rotation = 1
            elif self.hw.check_analog_rotation(config.ROTATION_CCW):
                rotation = -1

        if rotation:
            menu_manager.handle_rotation(rotation)
        if self.hw.key_new(config.KEY_BACK):
            menu_manager.handle_back()
        if self.hw.key_new(config.KEY_SELECT):
            menu_manager.handle_select()

class ArpeggiatorPlayback:
    """Handles all playback-related operations for the arpeggiator"""
    def __init__(self, hw, state, ui, network):
        self.hw = hw
        self.state = state
        self.ui = ui
        self.network = network

    def update(self):
        """Update playback state"""
        if self.state.mode != config.PLAYBACK_STATES["playing"]:
            return

        now = time.monotonic()
        arp_tick = int((now - self.state.start_time) * self.state.time_to_tick % (self.state.ticks_per_beat*2))
        arp_pos_new = int(arp_tick * 2 / self.state.ticks_per_beat)
        
        if arp_pos_new > self.state.arp_pos or (self.state.arp_pos == len(self.state.arp_notes)-1 and arp_pos_new == 0):
            self._play_note(arp_pos_new)

    def _play_note(self, arp_pos_new):
        """Play a new note and update UI"""
        packet = bytearray()
        
        # Turn off previous note
        if self.state.old_note != 0:
            ch = config.INSTRUMENT_ID
            note = self.state.old_note
            intensity = 0
            packet.append(ord('l'))
            packet.append(ch)
            packet.append(note)
            packet.append(intensity)
            i = note % 12
            if not self.state.mute:
                if note in self.state.arp_notes:
                    self.hw.pixels[i] = 0x200010
                else:
                    self.hw.pixels[i] = 0x000000                            

        # Send new note
        ch = config.INSTRUMENT_ID
        note = self.state.arp_notes[arp_pos_new]
        intensity = config.DEFAULT_INTENSITY
        packet.append(ord('l'))
        packet.append(ch)
        packet.append(note)
        packet.append(intensity)
        i = note % 12
        if not self.state.mute:
            self.hw.pixels[i] = colorwheel(int(note / 12) * 20  & 255)
            self.network.esp.send(packet, self.network.peer_broadcast)
        
        # Update pattern display
        for n in self.state.arp2d[self.state.arp_pos]:
            self.ui.field.setBlock(n, self.state.arp_pos, 2)
        for n in self.state.arp2d[arp_pos_new]:
            self.ui.field.setBlock(n, arp_pos_new, 1)
            
        # Update state
        self.state.arp_pos = arp_pos_new
        self.state.old_note = note

        # Update display
        self.ui.display_manager.update_channel_info(ch, note, intensity)
        self.hw.display.refresh()

class Arpeggiator:
    """Main class coordinating all arpeggiator components"""
    def __init__(self, hw, display_manager, instrument_id, peer_broadcast):
        try:
            self.hw = hw
            self.display_manager = display_manager
            self.instrument_id = instrument_id
            self.peer_broadcast = peer_broadcast
            
            # Initialize components
            self.state = ArpeggiatorState()
            self.ui = ArpeggiatorUI(display_manager, hw)
            self.network = ArpeggiatorNetwork(hw, instrument_id, peer_broadcast)
            self.input_handler = ArpeggiatorInput(hw, self.state, self.ui, self.network)
            self.playback = ArpeggiatorPlayback(hw, self.state, self.ui, self.network)
            
            # Initialize menu
            self.menu_actions = {
                'send_song': lambda: self.network.packet_handler.send_song() if self.network.packet_handler else None,
                'set_channel': lambda: set_channel(),
                'show_my_ip': lambda: show_device_ip(),
                'send_pair': lambda: self.network.packet_handler.send_pair() if self.network.packet_handler else None,
                'show_paired_devices': lambda: show_connected_devices(),
                'set_mode': lambda mode_id: set_device_mode(mode_id)
            }
            self.menu_manager = MenuManager(config.MENU_FILE, display_manager, self.menu_actions)
            
            # Initialize state
            self.state.initialize_scale()
            self.send_pair()
        except Exception as e:
            report_error(display_manager, f"Arpeggiator initialization error: {e}", True)
            raise

    def run(self):
        """Main loop"""
        while True:
            try:
                # Update playback
                self.playback.update()

                # Handle network packets
                if self.network.esp:
                    try:
                        packet = self.network.packet_handler.read_packet()
                        if packet:
                            result = self.network.handle_packet(packet)
                            if result:
                                self._handle_packet_result(result)
                                    
                    except PacketReadError as e:
                        report_error(self.display_manager, f"Packet read error: {e}")
                    except Exception as e:
                        report_error(self.display_manager, f"Network error: {e}")

                # Handle input
                try:
                    self.input_handler.handle_key_input()
                    self.input_handler.handle_menu_input(self.menu_manager)
                except Exception as e:
                    report_error(self.display_manager, f"Input error: {e}")

            except KeyboardInterrupt:
                report_error(self.display_manager, "User interrupted")
                break
            except Exception as e:
                report_error(self.display_manager, f"Main loop error: {e}")
                # Continue running despite errors

    def _handle_packet_result(self, result):
        """Handle packet processing result"""
        try:
            packet_type, *args = result
            
            # Handle tick packet
            if packet_type == 'tick':
                tick = args[0]
                now_tick = int(self.state.time_to_tick * (time.monotonic() - self.state.start_time))
                tick_delta = tick - now_tick
                
            # Handle begin packet
            elif packet_type == 'begin':
                self.state.start_time = time.monotonic()
                self.state.mode = config.PLAYBACK_STATES["playing"]
                self.display_manager.show_debug_message("playing")
                
            # Handle stop packet
            elif packet_type == 'stop':
                self.state.mode = config.PLAYBACK_STATES["paused"]
                self.display_manager.show_debug_message("paused")
                if self.state.old_note != 0:
                    self.network.send_note(self.state.old_note, 0)
                    
            # Handle header packet
            elif packet_type == 'header':
                self.state.ticks_per_beat, self.state.max_ticks, self.state.tempo, numerator, self.state.denominator, nr_instruments = args
                self.state.tick_to_time = 60 * 4 / (self.state.tempo * self.state.ticks_per_beat * self.state.denominator)
                self.state.time_to_tick = (self.state.tempo * self.state.ticks_per_beat * self.state.denominator) / (60 * 4)
                song_length = self.state.max_ticks * self.state.tick_to_time
                self.state.mode = config.PLAYBACK_STATES["paused"]
                
            # Handle mute packet
            elif packet_type == 'mute':
                ch, intensity = args
                if ch == self.instrument_id:
                    self.state.mute = intensity
                    if self.state.mute:
                        for i in range(12):
                            self.hw.pixels[i] = (0,20,0)
                        self.display_manager.show_debug_message("muted")
                    else:
                        for i in range(12):
                            self.hw.pixels[i] = (0,0,0)
                        self.display_manager.show_debug_message(" ")
                        
            # Handle update packet
            elif packet_type == 'update':
                self.display_manager.show_debug_message("update")
                self.display_manager.show_debug_message(" ")
                redraw()
                self.display_manager.update_channel_info(0, 0, 0)
                
            # Handle reset packet
            elif packet_type == 'reset':
                self.state.reset()
                self.display_manager.show_debug_message("reset")
                self.ui.background.replace("arp0.bmp")
                self.display_manager.update_channel_info(0, 0, 0)
                if not self.state.mute:
                    self.ui.update_leds(self.state.arp_notes)
                self.ui.update_pattern(self.ui.field, self.state.arp2d, 0)
                
            # Handle clear packet
            elif packet_type == 'clear':
                id = args[0]
                if id == self.instrument_id or id == 255:
                    self.display_manager.show_debug_message("receiving")
                    self.state.arp_notes = [55, 60, 64, 60]
                    if not self.state.mute:
                        self.ui.update_leds(self.state.arp_notes)
                    self.state.mode = config.PLAYBACK_STATES["clear"]

            # Handle scale packet
            elif packet_type == 'scale':
                scale_start, scale = args
                self.state.update_scale(scale_start, scale)
                if not self.state.mute:
                    self.ui.update_leds(self.state.arp_notes)
                # Update background based on scale_start
                if scale_start == 60:
                    self.ui.background.replace("arp0.bmp")
                elif scale_start == 55:
                    self.ui.background.replace("arp1.bmp")
                elif scale_start == 57:
                    self.ui.background.replace("arp2.bmp")
                elif scale_start == 65:
                    self.ui.background.replace("arp3.bmp")
                self.hw.display.refresh()
                self.display_manager.show_debug_message(f"scale: {scale_start}")

        except Exception as e:
            report_error(self.display_manager, f"Packet handling error: {e}")

    def send_pair(self):
        """Send a pair packet to broadcast address"""
        if self.network.esp:
            packet = bytearray('p', 'utf-8')
            packet.append(self.instrument_id)
            self.network.esp.send(packet, self.peer_broadcast)

# ------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

def newKey(arp2d, key, pos):
    remove = []
    add = []
    if key in arp2d[pos]:
        arp2d[pos].remove(key)
        remove.append(key)
    else:
        arp2d[pos].append(key)
        add.append(key)
    old_pos = pos
    pos += 1
    if pos >= len(arp2d):
        pos = 0
    return(arp2d, pos, old_pos, remove, add)

# unused...
def update_ui(field, arp2d, pos):
    # clear all leds
    for i in range(12):
        hw.pixels[i] = (0,0,0)
    # clear field (slow, but fast enought)
    for y in range(config.FIELD_Y_MAX):
        for x in range(config.FIELD_X_MAX):
            field.setBlock(x, y, 0)
    # add new sprites and leds
    for y, a in enumerate(arp2d):
        for x in a:
            if y != pos:
                field.setBlock(x, y, 2)
                hw.pixels[x] = 0x200010
    for n in arp2d[pos]:
        field.setBlock(n, pos, 1)
        hw.pixels[n] = (0,20,10)
    hw.display.refresh()

# unused...
def send_packet(id, payload, addr):
    packet = bytearray(id, 'utf-8')
    packet.extend(payload)
    esp.send(packet, addr)

# unused...
def send_pair():
    send_packet('p', [config.INSTRUMENT_ID], peer_broadcast)
    #send_packet('p', bytearray(wifi.radio.mac_address), peer_broadcast)

# Create and remove a black sprite to refresh the screen 
# unused...
def redraw():
    black_sprite = displayio.TileGrid(displayio.Bitmap(160, 128, 1), pixel_shader=displayio.Palette(1), x=0, y=0)
    hw.displayGroup.append(black_sprite)
    hw.displayGroup.pop()
    hw.display.refresh()

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

def cleanup(display_manager, esp):
    """Cleanup resources."""
    try:
        # Reset display state
        if display_manager:
            try:
                display_manager.show_debug_message("Shutting down...")
            except Exception as e:
                report_error(display_manager, f"Display reset error: {e}")

        # Cleanup network
        if esp:
            try:
                esp.deinit()
            except Exception as e:
                report_error(display_manager, f"Network cleanup error: {e}")

    except Exception as e:
        report_error(display_manager, f"Cleanup error: {e}")

# ------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

def main():
    """Main application entry point."""
    # Initialize managers as None to ensure proper cleanup
    display_manager = None
    esp = None
    packet_handler = None
    menu_manager = None
    arpeggiator = None
    
    try:
        # Initialize display manager
        display_manager = DisplayManager(hw.display, hw)
        
        # Load sprite_sheets from file
        sprite_sheet, palette = adafruit_imageload.load("assets/images/10x10.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)

        # Initialize text fields
        display_manager.create_text_fields(config.MODE + " (CH" + str(config.INSTRUMENT_ID) + ")")

        # Create a black background
        black_sprite = displayio.TileGrid(displayio.Bitmap(160, 128, 1), pixel_shader=displayio.Palette(1), x=0, y=0)
        hw.displayGroup.append(black_sprite)

        # Create peer broadcast object
        peer_broadcast = espnow.Peer(mac=config.MAC_BROADCAST)

        # Initialize and run arpeggiator
        arpeggiator = Arpeggiator(hw, display_manager, config.INSTRUMENT_ID, peer_broadcast)
        arpeggiator.run()

    except Exception as e:
        report_error(display_manager, f"Fatal error: {e}", True)
    finally:
        cleanup(display_manager, esp)

if __name__ == "__main__":
    main()
