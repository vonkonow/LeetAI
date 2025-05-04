# 🎹 Leet AI – A Tiny Synth Ensemble with AI-Powered Inspiration

Leet AI is a playful, pocket-sized synthesizer concept that explores what happens when many simple instruments work together—like a miniature electronic orchestra. Unlike traditional synths that try to do everything, Leet AI embraces a modular philosophy: multiple open-source, affordable units, each with a specific voice, combining to create something greater than the sum of their parts.

![group photo](/assets/133741.jpg)

---

## 🌟 Why Leet AI?

Synthesizers can be intimidating. Menus, shift-buttons, and buried features can kill creative flow. Leet AI is an attempt to bring back the fun—tiny instruments you can pick up, jam with, and let the AI surprise you with new melodic ideas. Whether you're a tinkerer, a musician, or just curious about AI and music, this project is for you.

---

## ✨ Features

- 🎵 **AI-powered inspiration**  
  Generate unique melodies, drum patterns, and variations using a diffusion-based AI model.

- 🔧 **Hackable and open-source**  
  Built with CircuitPython on an ESP32-S2—plug it in, and you're editing the firmware like a USB stick.

- 🎛️ **Minimalist design with deep control**  
  Dual rotary encoders with tilt navigation, RGB-backlit keys, and a full-color display keep you focused and in control.

- 📶 **Wireless orchestration**  
  A low-latency protocol keeps multiple units in sync.

- 🔋 **Fully portable**  
  Runs on a rechargeable 1000mAh LiPo battery. Jam anywhere.

---

## 📦 Hardware Specs

- **Size:** 86 x 60 x 15 mm (smaller than a deck of cards!)
- **Keys:** 16 RGB-backlit mechanical keys
- **Microcontroller:** ESP32-S2 (CircuitPython firmware)
- **Display:** 1.8” 160x128 TFT color screen
- **Encoders:** Dual magnetic rotary encoders with tilt function
- **Audio:** High-quality 112dB SNR DAC
- **Connectivity:** MIDI over USB-C, ESP-Now wireless sync
- **Power:** 1000mAh LiPo battery with onboard charging

---

# ▶️ **Demo video** 
[![demo](https://img.youtube.com/vi/MnzYHhDXu_o/default.jpg )](https://youtu.be/MnzYHhDXu_o)

---

## 🧪 Build Difficulty 

**Medium.** You'll need SMD soldering skills, a 3D printer, and some patience and curiosity.

---

## 🛠️ Development History

Leet AI combines the best aspects of three earlier open hardware projects: [**leet**](https://vonkonow.com/leet-synthesizer/), [**leet modular**](https://vonkonow.com/leet-modular/), and [**chip champ**](https://vonkonow.com/chipchamp/). Prototypes have evolved through countless iterations—from hand-wired mock-ups to a 12-key prototype and finally to the 16-key design that bridges sequencer and keyboard layouts.

---

## 🚧 Limitations (For Now)

This is still a conceptual prototype. While it’s fully functional for the demo, many features are hardcoded. Here’s what’s next on the roadmap:

- 🎚️ Real-time editing and melody creation  
- 🎵 Higher-fidelity audio engine and custom graphic module
- 🎛️ Instrument selection and sound design (ADSR, filters, etc.)  
- 🧠 Smarter AI integration with automatic Wi-Fi server connection  
- 🎹 Stacked octave mode  
- 🔊 Optional speaker  
- 🎶 AMY synth library support?

---

## 🛒 BOM / Estimated Cost

**Total cost per unit:** ~$24

---

## 💡 Contributing

Got ideas? Want to help improve the synth engine, optimize graphics, or design new enclosures? All contributions—code, hardware, or creative—are welcome!

### ➕ How to Contribute

1. Fork the repo  
2. Try the demo firmware  
3. Submit issues or pull requests  
4. Join the discussion on hardware, AI models, or interface design

---

## 📁 Repository Structure

```
/
├── firmware/       → CircuitPython source code
├── hardware/       → KiCad files, schematics, and PCB layout
├── enclosure/      → 3D models (Rhino & STL)
├── ai-server/      → getMusic setup, scripts and generation tools
├── docs/           → Build guide, BOM, and reference images
└── README.md       → Project overview
```

---

## ❤️ Special Thanks

Huge thanks to the creators and maintainers of open-source tools that made this project possible.  
Special gratitude to [**Adafruit**](https://www.adafruit.com/) for developing [**CircuitPython**](https://circuitpython.org/board/lolin_s2_mini/), which made firmware development approachable, flexible, and fun—even for hardware newcomers.  
Thanks also to the team behind [**synthio**](https://docs.circuitpython.org/en/latest/shared-bindings/synthio/), whose powerful audio capabilities laid the groundwork for expressive, real-time sound generation on microcontrollers.  
And to Microsoft Research for [**getMusic**](https://github.com/microsoft/muzic), and to all the explorers at the intersection of music, AI, and creative technology—your curiosity and generosity continue to inspire.


---

## 🧠 Imagine What’s Next

Leet AI is still early, but the concept is alive. With your feedback, forks, and experiments, this can grow into a truly modular, generative instrument playground.

---

## 🔗 [Visit the project website  ](https://vonkonow.com/leetai/)
## 📂 [Explore the GitHub repository  ](https://github.com/vonkonow/leetai)
## 📸 [Share your builds and music!](https://vonkonow.com/community/)


![DnB](/assets/combo.jpg "DnB")