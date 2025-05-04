#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************
#    ______  ______         ____                 _____             _____
#    \     \|\     \    ____\_  \__         _____\    \       _____\    \
#     |     |\|     |  /     /     \       /    / \    |     /    / \    |
#     |     |/____ /  /     /\      |     |    |  /___/|    |    |  /___/|
#     |     |\     \ |     |  |     |  ____\    \ |   || ____\    \ |   ||
#     |     | |     ||     |  |     | /    /\    \|___|//    /\    \|___|/
#     |     | |     ||     | /     /||    |/ \    \    |    |/ \    \
#    /_____/|/_____/||\     \_____/ ||\____\ /____/|   |\____\ /____/|
#    |    |||     | || \_____\   | / | |   ||    | |   | |   ||    | |
#    |____|/|_____|/  \ |    |___|/   \|___||____|/     \|___||____|/
#                      \|____|
#
# Boss hadles the playback of a song and does the following:
#   > sends song events and tick packets wirelessly to other devices
#   > outputs audio playback using the i2s DAC and a basic synth engine
#   > outputs MIDI events over USB
#   > visualizes the song playback and allows channels to be muted
#
# Todo:
#   * add support for 1.1 hardware (only tested on 1.0)
#   * increase sample frequency of i2s mixer (16kHz samples and wavetable)
#   * replace broadcast with network discovery and setup?
#   * custom library for more efficient display handling
#   * custom library for audio rendering (wavetable and samples)
#
# Done:
#   250424:
#     x major code refactoring and cleanup:
#       directory structure, common modules, manager classes and error handling
#   250329:
#     x stop active notes on mute
#     x fix pcb to use i2s ldo instead of s2mini (and ground i2s scl)
#     x fix standalone playback (without USB midi)
#   241226:
#     x build menu system
#     x implement file header on synths
#   240929:
#     x implement live keyboard backchannel
#   240922:
#     x added keyboard and led_pixel support
#     x implemented mute on synths
# ******************************************************************************

import config.config as config
import espnow
from src.common import hw
import time
from src.common.audio import AudioManager
from src.common.ui import DisplayManager
from src.common.network import PacketHandler, NetworkError, PacketSendError, PacketReadError, SongSendError
from src.common.song import Song, SongPlayer
from src.common.menu import MenuManager

# ------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

# load song
song_name = "arpai.bin"
#song_name = "ai&a_beat.bin"
song_name = song_name.split('.')
song_path = "assets/"

# ------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|

def initialize_audio():
    """Initialize audio system."""
    try:
        audio_manager = AudioManager(hw)
        return audio_manager
    except Exception as e:
        report_error(None, f"Audio init error: {e}", True)
        raise

def initialize_display():
    """Initialize display system."""
    try:
        display_manager = DisplayManager(hw.display, hw)
        display_manager.load_song_background(config.SONG_NAME)
        display_manager.create_position_sprite()
        display_manager.create_text_fields(config.SONG_NAME)
        
        return display_manager
    except Exception as e:
        report_error(None, f"Display init error: {e}", True)
        raise

def initialize_menu(display_manager):
    """Initialize menu system."""
    try:
        return MenuManager(config.MENU_FILE, display_manager)
    except Exception as e:
        report_error(display_manager, f"Menu init error: {e}", True)
        raise

def initialize_network():
    """Initialize network system."""
    try:
        if config.MODE == "boss":
            esp = espnow.ESPNow()
            BROADCAST = espnow.Peer(mac=config.MAC_BROADCAST)
            esp.peers.append(BROADCAST)
            packet_handler = PacketHandler(esp, config.INSTRUMENT_ID, BROADCAST)
            return esp, packet_handler
        return None, None
    except Exception as e:
        report_error(None, f"Network init error: {e}", True)
        raise

def handle_song_playback(player, display_manager):
    """Handle song playback updates."""
    try:
        result = player.update()
        if result:
            sprite_pos, ch, note, intensity = result
            if sprite_pos > player.sprite_last_pos:
                player.sprite_last_pos = sprite_pos
                display_manager.update_playback_position(sprite_pos)
            display_manager.update_channel_info(ch, note, intensity)
        return result
    except IndexError as e:
        # Handle out of range errors gracefully
        report_error(display_manager, "Playback position out of range")
        return None
    except Exception as e:
        report_error(display_manager, f"Playback error: {e}")
        return None

def handle_input(player, audio_manager, display_manager, menu_manager, song):
    """Handle user input."""
    try:
        # Handle reset button
        if hw.key_new(config.KEY_RESET):
            handle_reset(player, audio_manager, display_manager)
            return

        # Handle play/pause button
        if hw.key_new(config.KEY_PLAY_PAUSE):
            handle_play_pause(player, display_manager)
            return

        # Handle mute toggles
        for k in range(song.get_metadata('nr_instruments')):
            if hw.key_new(k):
                handle_mute_toggle(k, audio_manager, display_manager)
                return

        # Handle menu navigation
        handle_menu_navigation(menu_manager)
    except Exception as e:
        report_error(display_manager, f"Input error: {e}")

def handle_reset(player, audio_manager, display_manager):
    """Handle reset button press."""
    player.reset()
    display_manager.update_mute_leds(audio_manager.get_mute_states())
    display_manager.update_channel_info(0, 0, 0)
    display_manager.update_playback_position(0)

def handle_play_pause(player, display_manager):
    """Handle play/pause button press."""
    if player.playback_state == "playing":
        player.pause()
        display_manager.set_pause_led(True)
    else:
        player.play()
        display_manager.set_pause_led(False)

def handle_mute_toggle(channel, audio_manager, display_manager):
    """Handle mute toggle for a channel."""
    audio_manager.toggle_mute(channel)
    display_manager.update_mute_leds(audio_manager.get_mute_states())

def handle_menu_navigation(menu_manager):
    """Handle menu navigation input."""
    rotation = 0  # Initialize rotation to 0
    
    if config.HW_VERSION == 1.1:
        rotation = hw.check_rotation(0, 512)
    elif config.HW_VERSION == 1.0:
        if hw.check_analog_rotation(config.ROTATION_CW):
            rotation = 1
        elif hw.check_analog_rotation(config.ROTATION_CCW):
            rotation = -1
    
    if rotation:
        menu_manager.handle_rotation(rotation)
    if hw.key_new(config.KEY_BACK):
        menu_manager.handle_back()
    if hw.key_new(config.KEY_SELECT):
        menu_manager.handle_select()

def handle_network_packets(esp, packet_handler, audio_manager, display_manager, player):
    """Handle incoming network packets."""
    if not esp:
        return
        
    try:
        packet = esp.read()
        if not packet:
            return
            
        result = packet_handler.handle_packet(packet)
        if not result:
            return
            
        if result[0] == 'live':
            _, ch, note, intensity = result
            audio_manager.play.event(ch, note, intensity)
            display_manager.update_channel_info(ch, note, intensity)
        elif result[0] == 'pair':
            _, id = result
            # Read the song file and send it to the requesting device
            with open(player.song.file_path + player.song.file_name + ".bin", 'rb') as f:
                byte_song = f.read()
                packet_handler.send_song(id, byte_song, display_manager, hw)
    except PacketReadError as e:
        report_error(display_manager, f"Packet read error: {e}")
    except PacketSendError as e:
        report_error(display_manager, f"Packet send error: {e}")
    except SongSendError as e:
        report_error(display_manager, f"Song send error: {e}")
    except NetworkError as e:
        report_error(display_manager, f"Network error: {e}")
    except Exception as e:
        report_error(display_manager, f"Unexpected error: {e}")

def cleanup(audio_manager, display_manager, esp):
    """Cleanup resources."""
    try:
        # Stop all audio playback
        if audio_manager:
            try:
                audio_manager.play.stop_all_notes()
            except Exception as e:
                report_error(display_manager, f"Audio stop error: {e}")

        # Reset display state
        if display_manager:
            try:
                display_manager.set_pause_led(True)
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
    # Initialize managers as None to ensure proper cleanup
    audio_manager = None
    display_manager = None
    esp = None
    packet_handler = None
    menu_manager = None
    player = None
    
    try:
        # Initialize systems in order of dependency
        display_manager = initialize_display()
        audio_manager = initialize_audio()
        menu_manager = initialize_menu(display_manager)
        esp, packet_handler = initialize_network()

        # Initialize song and player
        try:
            song = Song(config.SONG_PATH, config.SONG_NAME)
            player = SongPlayer(song, audio_manager.play, packet_handler)
        except Exception as e:
            report_error(display_manager, f"Song init error: {e}", True)
            raise

        # Set initial LED states
        display_manager.set_pause_led(True)
        display_manager.update_mute_leds(audio_manager.get_mute_states())

        # Main loop
        while True:
            try:
                handle_song_playback(player, display_manager)
                handle_input(player, audio_manager, display_manager, menu_manager, song)
                handle_network_packets(esp, packet_handler, audio_manager, display_manager, player)
            except KeyboardInterrupt:
                report_error(display_manager, "User interrupted")
                break
            except Exception as e:
                report_error(display_manager, f"Main loop error: {e}")
                # Continue running despite errors

    except Exception as e:
        report_error(display_manager, f"Fatal error: {e}", True)
    finally:
        cleanup(audio_manager, display_manager, esp)

if __name__ == "__main__":
    main()
