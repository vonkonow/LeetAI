"""
Audio components for the core module.

This module provides audio-related classes for sample playback, wavetable synthesis,
and MIDI control.
"""

import audiocore
import audiomixer
import audiobusio
import synthio
import board
from assets.audio.waveforms_akwf_granular import waveforms
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
import usb_midi
from src.common.ui import colorwheel
import config.config as config

class AudioManager:
    """
    A class for managing all audio components.
    
    This class handles the initialization and management of:
    - Audio output (I2S)
    - Mixer configuration
    - Channel setup (wavetable and sample)
    - Envelope settings
    - Playback control
    
    Attributes:
        sample_rate: Audio sample rate in Hz
        mixer: Audio mixer instance
        channels: List of audio channels
        envelopes: Dictionary of envelope settings
    """
    
    def __init__(self, hw):
        """Initialize a new audio manager."""
        self.sample_rate = config.DEFAULT_SAMPLE_RATE
        self.mixer = audiomixer.Mixer(
            voice_count=config.DEFAULT_MIXER_VOICES,
            sample_rate=self.sample_rate,
            channel_count=config.MIXER_CHANNEL_COUNT,
            bits_per_sample=config.MIXER_BITS_PER_SAMPLE,
            samples_signed=config.MIXER_SAMPLES_SIGNED
        )
        self.channels = []
        self.envelopes = {
            'fast': synthio.Envelope(
                attack_time=0.05,
                decay_time=0.1,
                release_time=0.1,
                attack_level=1.0,
                sustain_level=0.8
            )
        }
        self.hw = hw
        self._initialize_audio()
        self._initialize_channels()  # Initialize channels and create play attribute
    
    def _initialize_audio(self):
        """Initialize audio output and mixer."""
        try:
            self.audio = audiobusio.I2SOut(
                config.I2S_BCLK_PIN,  # BCLK
                config.I2S_WS_PIN,    # LRCK (Word Select)
                config.I2S_DATA_PIN   # DIN (Data In)
            )
            self.audio.play(self.mixer)
            self.mixer.voice[0].level = config.DEFAULT_MIXER_VOLUME
        except Exception as e:
            print(f"Audio initialization error: {e}")
            raise
    
    def _initialize_channels(self):
        """
        Initialize all audio channels.
        
        Sets up:
        - 3 wavetable channels for melodic instruments
        - 1 sample channel for drums
        """
        # Wavetable channels for melodic instruments
        for voice_num, waveform_idx in zip(config.WAVETABLE_VOICE_NUMBERS, config.WAVETABLE_WAVEFORM_INDICES):
            channel = Wavetable(
                synthio.Synthesizer(
                    sample_rate=self.sample_rate,
                    waveform=waveforms[waveform_idx],
                    envelope=self.envelopes['fast']
                ),
                voice_num,
                self.mixer
            )
            self.channels.append(channel)
        
        # Sample channel for drums
        ch3 = Sample(
            config.SAMPLE_FILES,
            config.SAMPLE_VOLUMES,
            config.SAMPLE_MAP,
            self.mixer
        )
        
        self.channels.append(ch3)
        self.play = Play(self.channels, self.mixer, self.hw)
    
    def get_channel_count(self) -> int:
        """
        Get the number of audio channels.
        
        Returns:
            int: Number of channels
        """
        return len(self.channels)
    
    def toggle_mute(self, channel_index: int) -> bool:
        """
        Toggle mute state for a channel.
        
        Args:
            channel_index: Index of the channel to toggle
            
        Returns:
            bool: New mute state
        """
        if 0 <= channel_index < len(self.channels):
            self.play.mute[channel_index] ^= 1
            return self.play.mute[channel_index]
        return False
    
    def get_mute_states(self) -> list:
        """
        Get the mute states of all channels.
        
        Returns:
            list: List of mute states
        """
        return self.play.mute
    
    def play_event(self, channel: int, note: int, intensity: int):
        """
        Play a note event on a channel.
        
        Args:
            channel: Channel number
            note: Note number
            intensity: Note intensity (0-127)
        """
        self.play.event(channel, note, intensity)
    
    def stop_all_notes(self):
        """Stop all currently playing notes."""
        self.play.stop_all_notes()

class Sample:
    """
    A class for playing audio samples.
    
    Attributes:
        last: Index of the last used voice
        sample: List of loaded audio samples
        volume_dict: Dictionary mapping note numbers to volume levels
        sample_map: Dictionary mapping note numbers to sample indices
    """
    
    def __init__(self, sample_files: list, volume_dict: dict, sample_map: dict, mixer: audiomixer.Mixer):
        """
        Initialize a new sample player.
        
        Args:
            sample_files: List of paths to sample files
            volume_dict: Dictionary mapping note numbers to volume levels
            sample_map: Dictionary mapping note numbers to sample indices
            mixer: Audio mixer to play through
        """
        self.last = 0
        self.sample = [audiocore.WaveFile(open(f, "rb")) for f in sample_files]
        self.volume_dict = volume_dict
        self.sample_map = sample_map
        self.mixer = mixer

    def on(self, note: int) -> None:
        """
        Play a sample for a given note.
        
        Args:
            note: MIDI note number
        """
        sample_id = self.sample_map[note]
        self.last = (self.last + 1) % len(self.sample)
        self.mixer.voice[self.last].play(self.sample[sample_id])
        self.mixer.voice[self.last].level = self.volume_dict[note]

    def off(self, note: int) -> None:
        """
        Stop playing a sample for a given note.
        
        Args:
            note: MIDI note number
        """
        pass

class Wavetable:
    """
    A class for wavetable synthesis.
    
    Attributes:
        synth: The synthio synthesizer instance
    """
    
    def __init__(self, synth: synthio.Synthesizer, voice: int, mixer: audiomixer.Mixer):
        """
        Initialize a new wavetable synthesizer.
        
        Args:
            synth: synthio synthesizer instance
            voice: Voice number to use
            mixer: Audio mixer to play through
        """
        self.synth = synth
        self.voice = voice
        mixer.voice[voice].play(self.synth)
        mixer.voice[voice].level = config.DEFAULT_MIXER_VOLUME

    def on(self, note: int) -> None:
        """
        Play a note on the synthesizer.
        
        Args:
            note: MIDI note number
        """
        self.synth.press([note])

    def off(self, note: int) -> None:
        """
        Stop playing a note on the synthesizer.
        
        Args:
            note: MIDI note number
        """
        self.synth.release([note])

class Silent:
    """
    A silent instrument that does nothing.
    
    This class is used as a placeholder for unused instrument slots.
    """
    
    def __init__(self):
        """Initialize a new silent instrument."""
        pass

    def on(self, note: int) -> None:
        """
        Do nothing when a note is played.
        
        Args:
            note: MIDI note number
        """
        pass

    def off(self, note: int) -> None:
        """
        Do nothing when a note is released.
        
        Args:
            note: MIDI note number
        """
        pass

class Play:
    """
    A class for managing multiple instruments and MIDI output.
    
    Attributes:
        instruments: List of instrument instances
        mixer: Audio mixer instance
        hw: Hardware interface instance
        mute: List of mute states for each instrument
        playing: List of currently playing notes for each instrument
        midi_enabled: Whether MIDI output is enabled
        midi: List of MIDI output channels
    """
    
    def __init__(self, instruments: list, mixer: audiomixer.Mixer, hw, midi_enabled: bool = True):
        """
        Initialize a new play manager.
        
        Args:
            instruments: List of instrument instances
            mixer: Audio mixer instance
            hw: Hardware interface instance
            midi_enabled: Whether to enable MIDI output
        """
        self.instruments = instruments
        self.mixer = mixer
        self.hw = hw
        self.mute = [False] * len(instruments)
        self.playing = [[] for _ in instruments]
        self.midi_enabled = midi_enabled
        self.midi = []
        if midi_enabled:
            for ch in range(len(instruments)):
                self.midi.append(adafruit_midi.MIDI(midi_out=usb_midi.ports[1], 
                                                   out_channel=ch))

    def event(self, ch: int, note: int, intensity: int) -> None:
        """
        Handle a MIDI event.
        
        Args:
            ch: MIDI channel
            note: MIDI note number
            intensity: Note intensity (0-127)
        """
        if intensity == 0:
            self.off(ch, note)
        else:
            self.on(ch, note, intensity)

    def on(self, ch: int, note: int, intensity: int) -> None:
        """
        Handle a note-on event.
        
        Args:
            ch: MIDI channel
            note: MIDI note number
            intensity: Note intensity (0-127)
        """
        if not self.mute[ch]:
            if self.midi_enabled:
                self.midi[ch].send(NoteOn(note, intensity))
            self.instruments[ch].on(note)
            self.hw.pixels[ch] = colorwheel(note * 2 & 255)
            self.playing[ch].append(note)

    def off(self, ch: int, note: int) -> None:
        """
        Handle a note-off event.
        
        Args:
            ch: MIDI channel
            note: MIDI note number
        """
        if not self.mute[ch]:
            if self.midi_enabled:
                self.midi[ch].send(NoteOff(note, 0))
            self.instruments[ch].off(note)
            self.hw.pixels[ch] = 0x000000
            try:
                self.playing[ch].remove(note)
            except:
                pass

    def stop_all_notes(self) -> None:
        """Stop all currently playing notes."""
        for ch, inst in enumerate(self.instruments):
            for note in self.playing[ch]:
                if self.midi_enabled:
                    self.midi[ch].send(NoteOff(note, 0))
                self.instruments[ch].off(note)
            self.playing[ch] = []
            if not self.mute[ch]:
                self.hw.pixels[ch] = 0x000000 