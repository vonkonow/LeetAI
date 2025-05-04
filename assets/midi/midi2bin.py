#------10|-------20|-------30|-------40|-------50|-------60|-------70|-------80|
# ******************************************************************************
# Converts a midi song to a binary format, an image and a json with midi details.
# Binary file format:
# - Header (11 bytes):  ticks/beat (2), nr ticks (4), tempo (2), numerator (1), 
#                       denominator (1), nr instruments (1)
# - Song:  start_tick (2), end_tick (2), instrument (1), pitch (1), velocity (1)
#
# MIT License (attribution optional, but appreciated - Johan von Konow :)
# ******************************************************************************

import sys
import json
import argparse
import logging
from miditoolkit.midi import parser as mid_parser
from PIL import Image

# Constants
JSON_EXTENSION = ".json"
BIN_EXTENSION = ".bin"
BMP_EXTENSION = ".bmp"
NUM_SECTIONS = 160

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Convert a MIDI song to binary format, image, and JSON.")
    parser.add_argument("midi_file", help="Path to the MIDI file")
    return parser.parse_args()

def serialize_midi_data(mido_obj, data_type):
    """Generic function to serialize MIDI data based on the data type."""
    if data_type == "time_signatures":
        return [{"numerator": t.numerator, "denominator": t.denominator, "time": t.time} for t in mido_obj.time_signature_changes]
    elif data_type == "key_signatures":
        return [{"key_name": k.key_name, "time": k.time} for k in mido_obj.key_signature_changes]
    elif data_type == "tempo_changes":
        return [{"tempo": t.tempo, "time": t.time} for t in mido_obj.tempo_changes]
    elif data_type == "markers":
        return [{"text": m.text, "time": m.time} for m in mido_obj.markers]
    elif data_type == "instruments":
        instruments = []
        note_array = []
        for id, inst in enumerate(mido_obj.instruments):
            instruments.append({
                "id": id,
                "type": str(inst.program),
                "name": str(inst.name),
                "drum": inst.is_drum,
                "notes": []
            })
            for n in inst.notes:
                note_array.append([n.start, n.end, id, n.pitch, n.velocity])
        return instruments, note_array
    else:
        raise ValueError(f"Unknown data type: {data_type}")

def hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    """Convert HSV to RGB."""
    if s:
        if h == 1.0: h = 0.0
        i = int(h*6.0); f = h*6.0 - i
        w = int(255*( v * (1.0 - s) ))
        q = int(255*( v * (1.0 - s * f) ))
        t = int(255*( v * (1.0 - s * (1.0 - f)) ))
        v = int(255*v)
        if i==0: return (v, t, w)
        if i==1: return (q, v, w)
        if i==2: return (w, v, t)
        if i==3: return (w, q, v)
        if i==4: return (t, w, v)
        if i==5: return (v, w, q)
    else: v = int(255*v); return (v, v, v)

def create_byte_song(mido_obj, note_array, time_tempo, time_numerator, time_denominator):
    """Create a byte array representing the song."""
    byte_song = bytearray()
    byte_song.extend(mido_obj.ticks_per_beat.to_bytes(2, byteorder='big'))
    byte_song.extend(mido_obj.max_tick.to_bytes(4, byteorder='big'))
    byte_song.extend(round(time_tempo).to_bytes(2, byteorder='big'))
    byte_song.extend(time_numerator.to_bytes(1, byteorder='big'))
    byte_song.extend(time_denominator.to_bytes(1, byteorder='big'))
    byte_song.extend(len(mido_obj.instruments).to_bytes(1, byteorder='big'))
    for n in note_array:
        byte_song.extend(n[0].to_bytes(2, byteorder ='big'))
        byte_song.extend(n[1].to_bytes(2, byteorder ='big'))
        byte_song.extend(n[2:5])
    return byte_song

def generate_image(note_array, mido_obj, file_name):
    """Generate an image showing the number of notes per section for each instrument."""
    pixel_array = [[] * NUM_SECTIONS for i in range(NUM_SECTIONS)]
    song_index = 0
    max_count = [0] * len(mido_obj.instruments)
    for x in range(NUM_SECTIONS):
        note_count = [0] * len(mido_obj.instruments)
        while note_array[song_index][0] < x*(mido_obj.max_tick / NUM_SECTIONS):
            note_count[note_array[song_index][2]] += 1
            song_index += 1
            if song_index > len(note_array) - 4:
                break
        for id, n in enumerate(note_count):
            if n > max_count[id]:
                max_count[id] = n
        pixel_array[x] = list(note_count)
    img = Image.new('RGB', (NUM_SECTIONS, 64), "black")
    pixels = img.load()
    for x, instrument_count in enumerate(pixel_array):
        for y, intensity in enumerate(instrument_count):
            for l in range(4):
                pixels[x, y*4+l] = hsv_to_rgb(y/len(max_count), 0.8, intensity/max_count[y])
    img.save(file_name + BMP_EXTENSION)

def main():
    args = parse_arguments()
    file_name = args.midi_file.split(".")[0]
    try:
        mido_obj = mid_parser.MidiFile(args.midi_file)
        logging.info(mido_obj)
        song = {
            "ticks": str(mido_obj.ticks_per_beat),
            "max_tick": str(mido_obj.max_tick),
            "time_signatures": serialize_midi_data(mido_obj, "time_signatures"),
            "key_signatures": serialize_midi_data(mido_obj, "key_signatures"),
            "tempo_changes": serialize_midi_data(mido_obj, "tempo_changes"),
            "markers": serialize_midi_data(mido_obj, "markers"),
            "instruments": []
        }
        song["instruments"], note_array = serialize_midi_data(mido_obj, "instruments")
        with open(file_name + JSON_EXTENSION, "w") as f:
            f.write(json.dumps(song, indent=4))
        note_array.sort(key=lambda n: n[0])
        time_tempo = mido_obj.tempo_changes[0].tempo
        time_numerator = mido_obj.time_signature_changes[0].numerator
        time_denominator = mido_obj.time_signature_changes[0].denominator
        byte_song = create_byte_song(mido_obj, note_array, time_tempo, time_numerator, time_denominator)
        with open(file_name + BIN_EXTENSION, "wb") as binary_file:
            binary_file.write(byte_song)
        generate_image(note_array, mido_obj, file_name)
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()