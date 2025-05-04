# 🎛️ 133741: Wireless Ensemble Synthesizer with AI Composition

**133741** is a wireless ensemble synthesizer concept featuring AI-powered composition for endless musical inspiration.

---

## 🎹 Introduction

Most modern synthesizers are powerful (and often complicated) all-in-one units. With **133741**, I explored the opposite: a modular system where multiple small, dedicated units work together like an orchestra—each handling a specific instrument.

### 🎶 Leet AI Synth – Design Goals

- 🧸 **Cute, compact, playful, and affordable**  
  *(So you can have one per instrument!)*
- 🛠️ **Open source & customizable**  
  *(Written in Python using COTS modules)*
- 🧭 **User-friendly**  
  *(Clear display for modes & options—no weird button combos!)*
- 📡 **Wireless & battery-powered**
- 🤖 **AI-powered**  
  *(Generates melodies for inspiration)*

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

## 🧰 Hardware Versions

| Version | Features |
|---------|----------|
| **1.0** | 12 keys + analog encoders |
| **1.1** | 16 keys (new layout) + digital encoders |

---

## 🧪 Development Notes

I've used AI extensively for:
- Code refactoring  
- Error handling  
- Test generation  

It’s a work in progress—there’s room for improvement, and likely a few bugs left—but it’s definitely more robust than when it started.

---

## 🚀 Future Development

Plenty remains to be done. The current demo uses mostly hard-coded elements, so unlocking its full potential will require:

- 🎧 **Audio optimization**  
  *(Better sample rates, pitch control, lower CPU usage)*
- 🎼 **Melody & pattern editor**
- 🖼️ **Optimized graphics**  
  *(Smoother animations with less CPU load)*
- 🥁 **Sound selection per instrument**
- 🎚️ **Parameter tuning**  
  *(Velocity, bend, swing, ADSR, filters)*
- 🐛 **Bug fixes & test automation**
- 🔀 **Stacked octave mode**  
  *(Multiple units act as one extended synth)*
- 🌐 **Wi-Fi integration**  
  *(Connect to generative AI server – currently manual)*
- 🔊 **Maybe a built-in speaker?**
- 🎵 **AMY synth library integration?**

---
