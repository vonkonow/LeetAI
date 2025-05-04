"""
Song handling components for the core module.

This module provides functionality for loading, managing, and playing song data.
"""

import time
from .audio import Play
from .network import PacketHandler
import config.config as config

class Song:
    """
    A class for managing song data and metadata.
    
    Attributes:
        file_path: Path to the song file (optional)
        file_name: Name of the song file (without extension, optional)
        instrument_id: ID of the instrument this song is for (optional)
        events: List of song events
        metadata: Dictionary of song metadata
    """
    
    def __init__(self, file_path: str = None, file_name: str = None, instrument_id: int = None):
        """
        Initialize a new song.
        
        Args:
            file_path: Path to the song file (optional)
            file_name: Name of the song file (without extension, optional)
            instrument_id: ID of the instrument this song is for (optional)
        """
        self.file_path = file_path
        self.file_name = file_name
        self.instrument_id = instrument_id
        self.events = []
        self.metadata = config.DEFAULT_SONG_METADATA.copy()
        self._update_metadata()
        
        if file_path and file_name:
            self.load()
    
    def load(self):
        """Load song from file and parse metadata and events."""
        with open(self.file_path + self.file_name + ".bin", 'rb') as f:
            data = f.read()
            self._parse_header(data)
            self._parse_events(data)
    
    def _parse_header(self, data: bytes):
        """
        Parse song header metadata.
        
        Args:
            data: Raw song data
        """
        self.metadata = {
            'ticks_per_beat': int.from_bytes(data[0:2], "big"),
            'max_ticks': int.from_bytes(data[2:6], "big"),
            'tempo': int.from_bytes(data[6:8], "big"),
            'numerator': data[8],
            'denominator': data[9],
            'nr_instruments': data[10]
        }
        self._update_metadata()
    
    def _update_metadata(self):
        """Update derived metadata values."""
        # Calculate basic timing values
        self.metadata['tick_to_time'] = 60 * 4 / (self.metadata['tempo'] * 
                                                 self.metadata['ticks_per_beat'] * 
                                                 self.metadata['denominator'])
        self.metadata['song_length'] = self.metadata['max_ticks'] * self.metadata['tick_to_time']
        
        # Ensure max_ticks is valid before calculating sprite values
        if self.metadata['max_ticks'] > 0:
            self.metadata['sprite_tick'] = self.metadata['max_ticks'] / (160-4)
            self.metadata['sprite_time'] = self.metadata['sprite_tick'] * self.metadata['tick_to_time']
        else:
            # Set safe default values if max_ticks is invalid
            self.metadata['sprite_tick'] = 1
            self.metadata['sprite_time'] = self.metadata['tick_to_time']
    
    def _parse_events(self, data: bytes):
        """
        Parse song events.
        
        Args:
            data: Raw song data
        """
        for i in range(11, len(data), 7):
            tick_start = int.from_bytes(data[i + 0: i + 2], "big")
            tick_end = int.from_bytes(data[i + 2: i + 4], "big")
            ch = data[i + 4]
            note = data[i + 5]
            intensity = data[i + 6]
            add_event_last(self.events, [tick_start, ch, note, intensity])
            add_event_last(self.events, [tick_end, ch, note, 0])
    
    def add_event(self, tick_start: int, tick_end: int, note: int, intensity: int):
        """
        Add an event to the song.
        
        Args:
            tick_start: Start tick of the event
            tick_end: End tick of the event
            note: Note number
            intensity: Note intensity
        """
        if self.instrument_id is not None:
            ch = self.instrument_id
        else:
            ch = 0  # Default channel if no instrument_id specified
            
        # Add note on event
        add_event_last(self.events, [tick_start, ch, note, intensity])
        # Add note off event
        add_event_last(self.events, [tick_end, ch, note, 0])
        # Update max_ticks if needed
        if tick_end > self.metadata['max_ticks']:
            self.metadata['max_ticks'] = tick_end
            self._update_metadata()
    
    def get_event(self, index: int) -> tuple:
        """
        Get event at specified index.
        
        Args:
            index: Event index
            
        Returns:
            tuple: (tick, channel, note, intensity)
        """
        if 0 <= index < len(self.events):
            return tuple(self.events[index])
        return None
    
    def get_metadata(self, key: str) -> any:
        """
        Get metadata value.
        
        Args:
            key: Metadata key
            
        Returns:
            any: Metadata value
        """
        return self.metadata.get(key)
    
    def get_event_count(self) -> int:
        """
        Get total number of events.
        
        Returns:
            int: Number of events
        """
        return len(self.events)
    
    def clear(self):
        """Clear all events and reset metadata."""
        self.events = []
        self.metadata['max_ticks'] = 0
        self._update_metadata()

class SongPlayer:
    """
    A class for managing song playback.
    
    Attributes:
        song: Song instance
        audio_system: Play instance for audio output
        network_manager: PacketHandler instance for network communication
        playback_state: Current playback state
        song_index: Current position in song
        start_time: Time when playback started
        sprite_last_pos: Last sprite position
    """
    
    def __init__(self, song: Song, audio_system: Play, network_manager: PacketHandler):
        """
        Initialize a new song player.
        
        Args:
            song: Song instance
            audio_system: Play instance for audio output
            network_manager: PacketHandler instance for network communication
        """
        self.song = song
        self.audio_system = audio_system
        self.network_manager = network_manager
        self.playback_state = "paused"
        self.song_index = 0
        self.start_time = 0
        self.sprite_last_pos = 0
    
    def play(self):
        """Start or resume playback."""
        if self.playback_state == "paused":
            self.start_time = time.monotonic() - self.song.get_event(self.song_index)[0] * self.song.get_metadata('tick_to_time')
            self.playback_state = "playing"
            self.network_manager.send_packet('b', self.network_manager.PAYLOAD, retransmission=2)
    
    def pause(self):
        """Pause playback."""
        if self.playback_state == "playing":
            self.playback_state = "paused"
            self.network_manager.send_packet('s', self.network_manager.PAYLOAD, retransmission=2)
            self.audio_system.stop_all_notes()
    
    def reset(self):
        """Reset to beginning."""
        self.song_index = 0
        self.sprite_last_pos = 0
        self.start_time = time.monotonic()
        self.network_manager.send_packet('r', self.network_manager.PAYLOAD, retransmission=2)
    
    def update(self):
        """
        Update playback state.
        
        Returns:
            tuple: (sprite_pos, channel, note, intensity) if an event was processed,
                  None otherwise
        """
        if self.playback_state != "playing":
            return None
            
        # Check if we've reached the end of the song
        if self.song_index >= self.song.get_event_count():
            print("end of song")
            # Stop playback
            self.playback_state = "paused"
            # Stop all notes
            self.audio_system.stop_all_notes()
            # Reset song position
            self.song_index = 0
            self.sprite_last_pos = 0
            # Send stop packet
            self.network_manager.send_packet('s', self.network_manager.PAYLOAD, retransmission=2)
            # Return final position update
            return (0, 0, 0, 0)
            
        # Process events
        while self.song_index < self.song.get_event_count():
            event = self.song.get_event(self.song_index)
            now = time.monotonic()
            
            if now >= (self.start_time + event[0] * self.song.get_metadata('tick_to_time')):
                ch, note, intensity = event[1:]
                self.audio_system.event(ch, note, intensity)
                if intensity > 0:
                    self.network_manager.send_packet('t', 
                                                   bytearray(event[0].to_bytes(2, 'big')), 
                                                   retransmission=1)
                self.song_index += 1
                
                # Calculate sprite position safely
                try:
                    sprite_pos = int((now - self.start_time) / self.song.get_metadata('sprite_time'))
                    return (sprite_pos, ch, note, intensity)
                except (ZeroDivisionError, TypeError):
                    # If calculation fails, return a safe position
                    return (0, ch, note, intensity)
        
        return None

class LocalSong:
    """
    A lightweight song class for instruments that only need to handle their own events.
    
    Attributes:
        instrument_id: ID of the instrument this song is for
        events: List of song events for this instrument
        metadata: Dictionary of song metadata
        pattern_roll: List of lists for pattern display
    """
    
    def __init__(self, instrument_id: int):
        """
        Initialize a new local song.
        
        Args:
            instrument_id: ID of the instrument this song is for
        """
        self.instrument_id = instrument_id
        self.events = []
        self.pattern_roll = []
        self.metadata = config.DEFAULT_SONG_METADATA.copy()
        self.metadata.update({
            'pixels_per_beat': 4,
            'tick_to_time': 0,
            'time_to_tick': 0,
            'song_length': 0,
            'sprite_tick': 0,
            'sprite_time': 0,
            'ticks_per_pixel': 0,
            'max_pixels': 0
        })
        self._update_metadata()
    
    def _update_metadata(self):
        """Update derived metadata values."""
        self.metadata['tick_to_time'] = 60 * 4 / (self.metadata['tempo'] * 
                                                 self.metadata['ticks_per_beat'] * 
                                                 self.metadata['denominator'])
        self.metadata['time_to_tick'] = (self.metadata['tempo'] * 
                                        self.metadata['ticks_per_beat'] * 
                                        self.metadata['denominator']) / (60 * 4)
        self.metadata['song_length'] = self.metadata['max_ticks'] * self.metadata['tick_to_time']
        self.metadata['sprite_tick'] = self.metadata['max_ticks'] / (160-4)
        self.metadata['sprite_time'] = self.metadata['sprite_tick'] * self.metadata['tick_to_time']
        self.metadata['ticks_per_pixel'] = self.metadata['ticks_per_beat'] / self.metadata['pixels_per_beat']
        self.metadata['max_pixels'] = int(self.metadata['max_ticks'] / self.metadata['ticks_per_pixel'])
        
        # Initialize pattern roll if needed
        if self.metadata['max_pixels'] > 0 and len(self.pattern_roll) != self.metadata['max_pixels']:
            self.pattern_roll = [[] for _ in range(self.metadata['max_pixels'])]
    
    def update_header(self, ticks_per_beat: int, max_ticks: int, tempo: int, 
                     numerator: int, denominator: int, nr_instruments: int):
        """
        Update song metadata from header packet.
        
        Args:
            ticks_per_beat: Number of ticks per beat
            max_ticks: Maximum number of ticks in song
            tempo: Song tempo in BPM
            numerator: Time signature numerator
            denominator: Time signature denominator
            nr_instruments: Number of instruments
        """
        self.metadata.update({
            'ticks_per_beat': ticks_per_beat,
            'max_ticks': max_ticks,
            'tempo': tempo,
            'numerator': numerator,
            'denominator': denominator,
            'nr_instruments': nr_instruments
        })
        self._update_metadata()
    
    def add_event(self, tick_start: int, tick_end: int, note: int, intensity: int):
        """
        Add an event to the song and pattern roll.
        
        Args:
            tick_start: Start tick of the event
            tick_end: End tick of the event
            note: Note number
            intensity: Note intensity
        """
        # Add note on event
        add_event_last(self.events, [tick_start, self.instrument_id, note, intensity])
        # Add note off event
        add_event_last(self.events, [tick_end, self.instrument_id, note, 0])
        
        # Update max_ticks if needed
        if tick_end > self.metadata['max_ticks']:
            self.metadata['max_ticks'] = tick_end
            self._update_metadata()
            
        # Add to pattern roll
        pixel_start = int(tick_start / self.metadata['ticks_per_pixel'])
        if pixel_start < len(self.pattern_roll):
            if note not in self.pattern_roll[pixel_start]:
                self.pattern_roll[pixel_start].append(note)
    
    def clear(self):
        """Clear all events and reset metadata."""
        self.events = []
        self.pattern_roll = []
        self.metadata['max_ticks'] = 0
        self._update_metadata()
    
    def get_event(self, index: int) -> tuple:
        """
        Get event at specified index.
        
        Args:
            index: Event index
            
        Returns:
            tuple: (tick, channel, note, intensity)
        """
        if 0 <= index < len(self.events):
            return tuple(self.events[index])
        return None
    
    def get_metadata(self, key: str) -> any:
        """
        Get metadata value.
        
        Args:
            key: Metadata key
            
        Returns:
            any: Metadata value
        """
        return self.metadata.get(key)
    
    def get_event_count(self) -> int:
        """
        Get total number of events.
        
        Returns:
            int: Number of events
        """
        return len(self.events)
    
    def remove_note(self, pixel_pos: int, note: int):
        """
        Remove a note from the pattern roll at the specified position.
        
        Args:
            pixel_pos: Position in pattern roll
            note: Note to remove
        """
        if 0 <= pixel_pos < len(self.pattern_roll):
            if note in self.pattern_roll[pixel_pos]:
                self.pattern_roll[pixel_pos].remove(note)

def add_event_last(array: list, packet: list) -> None:
    """
    Add an event packet to a sorted array of events.
    Keeps events sorted by tick time and skips redundant events.
    """
    # If array empty, append
    if not array:
        array.append(packet)
        return
    # Fast path: new latest tick
    if packet[0] > array[-1][0]:
        array.append(packet)
        return
    # Find insertion index
    p = len(array) - 1
    # Move backwards while packet tick is less than current
    while p >= 0 and packet[0] < array[p][0]:
        p -= 1
    # Skip redundant packets at same tick
    while p >= 0 and packet[0] == array[p][0]:
        if packet[1:] == array[p][1:]:
            return  # redundant event
        p -= 1
    # Insert after last smaller tick (or at front if p == -1)
    array.insert(p+1, packet)
