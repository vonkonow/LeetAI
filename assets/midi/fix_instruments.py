#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************
# Inspect and change instruments in MIDI files for GetMusic AI compatibility.
# Example: change instrument 0 to piano: python fix_instruments.py test.mid 0 p
# MIT License (attribution optional, but appreciated - Johan von Konow :)
# ******************************************************************************

#!/usr/bin/env python3
import sys
import argparse
from miditoolkit.midi import parser as mid_parser

# Instrument mapping for shorthand codes
INSTRUMENT_MAP = {
    "p": (0, "Piano"),
    "g": (25, "Guitar"),
    "b": (32, "Bass"),
    "s": (48, "String"),
    "l": (80, "Lead"),
    "d": (None, "Drums")  # Special case for drums
}

def display_midi_info(midi_obj):
    """Display information about the MIDI file."""
    print(f"-- Ticks per beat: {midi_obj.ticks_per_beat}")
    
    # Signatures
    print(f"-- Time signatures: {len(midi_obj.time_signature_changes)} | {midi_obj.time_signature_changes[0]}")
    print(f"-- Key signatures: {len(midi_obj.key_signature_changes)}")
    
    # Sample note timing
    if midi_obj.instruments and midi_obj.instruments[0].notes:
        note = midi_obj.instruments[0].notes[min(20, len(midi_obj.instruments[0].notes)-1)]
        mapping = midi_obj.get_tick_to_time_mapping()
        tick = note.start
        sec = mapping[tick]
        print(f"-- Length: {tick} tick at {sec} seconds")
    
    # Tempo changes
    print(f"-- Tempo changes: {len(midi_obj.tempo_changes)} | {midi_obj.tempo_changes[0]}")
    
    # Markers
    print(f"-- Markers: {len(midi_obj.markers)}")
    if midi_obj.markers:
        print(midi_obj.markers[0])
    
    # Instruments
    print("\n-- Instruments --")
    for idx, instrument in enumerate(midi_obj.instruments):
        print(f"{idx} {instrument}")

def change_instrument(midi_obj, instrument_idx, new_instrument, custom_name=None):
    """Change the instrument for a specific MIDI track."""
    try:
        instrument_idx = int(instrument_idx)
        if instrument_idx < 0 or instrument_idx >= len(midi_obj.instruments):
            print(f"Error: Instrument index {instrument_idx} out of range (0-{len(midi_obj.instruments)-1})")
            return False
    except ValueError:
        print(f"Error: Instrument index must be an integer, got {instrument_idx}")
        return False
    
    instrument = midi_obj.instruments[instrument_idx]
    
    # Handle instrument shorthand codes
    if new_instrument in INSTRUMENT_MAP:
        program, name = INSTRUMENT_MAP[new_instrument]
        if new_instrument == "d":
            instrument.is_drum = True
        else:
            instrument.program = program
            instrument.name = name
    # Handle numeric program changes
    elif new_instrument.isnumeric():
        program = int(new_instrument)
        if program < 0 or program > 127:
            print(f"Error: Program number must be between 0-127, got {program}")
            return False
        instrument.program = program
        instrument.name = custom_name if custom_name else f"Instrument {program}"
    else:
        print(f"Error: Unknown instrument code '{new_instrument}'")
        return False
    
    print(f"Changed instrument {instrument_idx} to {instrument.name} (program: {instrument.program})")
    return True

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MIDI file inspector and instrument modifier")
    parser.add_argument("midi_file", help="Path to the MIDI file")
    parser.add_argument("instrument_idx", nargs='?', help="Index of the instrument to modify (0-based)")
    parser.add_argument("new_instrument", nargs='?', 
                        help="New instrument code (p=Piano, g=Guitar, b=Bass, s=String, l=Lead, d=Drums) or program number (0-127)")
    parser.add_argument("custom_name", nargs='?', help="Custom name for the instrument (only used with numeric program)")
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    try:
        # Load MIDI file
        midi_obj = mid_parser.MidiFile(args.midi_file)
    except Exception as e:
        print(f"Error loading MIDI file: {e}")
        return 1
    
    # Display MIDI information
    display_midi_info(midi_obj)
    
    # Change instrument if arguments provided
    if args.instrument_idx and args.new_instrument:
        print(f"\nChanging instrument {args.instrument_idx} to {args.new_instrument}")
        if change_instrument(midi_obj, args.instrument_idx, args.new_instrument, args.custom_name):
            try:
                midi_obj.dump(args.midi_file)
                print(f"Updated MIDI file saved to {args.midi_file}")
            except Exception as e:
                print(f"Error saving MIDI file: {e}")
                return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())