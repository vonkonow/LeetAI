# 🎛️ CircuitPython code repository for the LeetAi devices. 
## Usage:
0. First time, you have to connect the device and flash a [CircuitPython image for ESP32S2](https://circuitpython.org/board/lolin_s2_mini/) with [this tool](https://adafruit.github.io/Adafruit_WebSerial_ESPTool/).
1. The device then appears as a new drive. Copy all files and folders in this directory to the device.
2. The code will run automatically and you now have a synth. Edit config/config.py to change its function (see below).

---

## ⚙️ Configuration

The file `config.py` defines each unit's role:

| Function | Description |
|----------|-------------|
| `boss`   | Manages the overall song structure |
| `pitch`  | Handles piano and bass lines |
| `pattern`| Drives drum patterns |
| `chords` | Generates chord progressions |
| `arp`    | Plays arpeggios that follow chords |

---
## 📁 folder structure:
```
firmware/
├── README.md             # CircuitPython usage & setup instructions
├── boot.py               # Auto-run stub to launch main code on reset
├── code.py               # Entry-point script that wires everything together
│
├── config/               # User-tweakable settings and menus
│   ├── config.py         # Role definitions (boss, arp, chords, etc.) & parameters
│   └── menu.txt          # Text menu definitions shown on the display
│
├── src/                  # Core application code broken into two layers
│   ├── core/             # High-level “unit” drivers (boss, arp, pitch, …)
│   │   ├── boss.py       # Master song/section manager
│   │   ├── chords.py     # Chord progression engine
│   │   ├── pattern.py    # Drum-pattern sequencer
│   │   ├── pitch.py      # Melody & bass line handler
│   │   └── arp.py        # Real-time arpeggiator
│   │
│   └── common/           # Shared utilities & hardware abstractions
│       ├── audio.py      # Synth/audio helper routines
│       ├── hw.py         # Pin/encoder/button abstraction
│       ├── menu.py       # On-screen menu rendering & logic
│       ├── network.py    # Networking (Wi-Fi/OSC/etc.) support
│       ├── song.py       # Song data structures & serialization
│       └── ui.py         # Display & UI primitives
│
├── lib/                  # Bundled 3rd-party CircuitPython libraries/drivers
│   ├── adafruit_midi/      # MIDI bindings
│   ├── adafruit_imageload/ # Image-loading helper
│   ├── adafruit_st7735r.mpy # ST7735 display driver
│   ├── adafruit_wave.mpy    # WAV-sample playback driver
│   ├── neopixel.mpy         # WS2812 “NeoPixel” LED driver
│   └── font.bmp             # Built-in font bitmap
│
└── assets/               # Static resources bundled into filesystem
    ├── images/           # UI graphics, icons, etc.
    ├── audio/            # Samples and wavetable files
    └── arpai.bin         # Demo song (used by boss)
```
---

## 🧰 Hardware Versions

| Version | Features |
|---------|----------|
| **1.0** | 12 keys + analog encoders |
| **1.1** | 16 keys (new layout) + digital encoders |

---

## 🧪 Development Notes

I've used AI extensively for code refactoring, improvements and error handling. It's a work in progress and likely a few bugs left — but it's definitely more robust than before :)

---
## ❤️ Special Thanks

Huge thanks to the creators and maintainers of open-source tools that made this project possible.  
- Special gratitude to [**Adafruit**](https://www.adafruit.com/) for developing [**CircuitPython**](https://circuitpython.org/board/lolin_s2_mini/), which made firmware development approachable, flexible, and fun—even for hardware newcomers.  
- Thanks also to the team behind [**synthio**](https://docs.circuitpython.org/en/latest/shared-bindings/synthio/), whose powerful audio capabilities laid the groundwork for expressive, real-time sound generation on microcontrollers.  
- And to Microsoft Research for [**getMusic**](https://github.com/microsoft/muzic), and to all the explorers at the intersection of music, AI, and creative technology—your curiosity and generosity continue to inspire.

---
## 🚀 Future Development

Plenty remains to be done. The current demo uses mostly hard-coded elements, so unlocking its full potential will require:

- 🎼 **Melody & pattern editor**
- 🎧 **Audio optimization**  *(Better sample rates, pitch control, lower CPU usage)*
- 🖼️ **Optimized graphics**  *(Smoother animations with less CPU load)*
- 🎚️ **Instrument sound selection and parameter tuning**  *(Velocity, bend, swing, ADSR, filters)*
- 🔀 **Stacked octave mode**  *(Multiple units act as one extended synth)*
- 🌐 **Ai server connection**  *(Currently manual)*
- 🔊 **Maybe a built-in speaker?**
- 🎵 **AMY synth library integration?**

I will probably start with a custom circuitpython fork with new libraries for audio and graphics...

---
## 💡 Contributing

Got ideas? Want to help improve the synth engine, optimize graphics, or design new enclosures? All contributions—code, hardware, or creative—are welcome!

### ➕ How to Contribute

1. Fork the repo  
2. Try the demo firmware  
3. Submit issues or pull requests  
4. Join the discussion on hardware, AI models, or interface design

### 🧠 Imagine What's Next

Leet AI is still early, but the concept is alive. With your feedback, forks, and experiments, this can grow into a truly modular, generative instrument playground.

---

🔗 [Visit the project website  ](https://vonkonow.com/leetai/)
📂 [Explore the GitHub repository  ](https://github.com/vonkonow/leetai)
📸 [Share your builds and music!](https://vonkonow.com/community/)