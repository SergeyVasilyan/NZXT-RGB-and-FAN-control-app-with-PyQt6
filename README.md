# 🌀 NZXT FAN Control App (PyQt6)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-blue?logo=gnu&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Open Source](https://img.shields.io/badge/Open%20Source-Friendly-blueviolet?logo=github&logoColor=white)

I got fed up with being forced to use NZXT CAM or pay 5$ to SingalRGB so I created my own app and decided to share it with the community. Enjoy it.

A free, open-source alternative to NZXT CAM and SignalRGB—built with PyQt6 to give you full control over your NZXT fans, without paywalls or proprietary lock-in.

---

## 🚀 Features

- 🎛️ Real-time fan speed control
- 🧠 PyQt6 GUI with responsive layout and dynamic feedback
- 🔁 Live device polling and status updates
- 🧰 GPL-3.0 licensed for full openness and community reuse

---

## 📸 Screenshots

> Coming soon! Want to contribute a screenshot? See [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 🧪 Installation

### Requirements

- Python 3.10+
- PyQt6
- liquidctl
- LibreHardwareMonitor

### Setup

```bash
git clone https://github.com/SergeyVasilyan/NZXT-RGB-and-FAN-control-app-with-PyQt6.git
cd NZXT-RGB-and-FAN-control-app-with-PyQt6
pip install -r requirements.txt
python fan_control_gui.py
```

---

## 🧩 Architecture

- fan_control_gui.py: Main GUI logic and hardware interface
- icons/: UI assets (SVG/PNG)
- LICENSE: GPL-3.0 license
- CONTRIBUTING.md: Guidelines for contributing
- SECURITY.md: Responsible disclosure policy

---

## 🛠️ Roadmap

- [x] Device auto-discovery
- [ ] Graphical fan curve editor
- [ ] Fan curve presets (Silent, Normal, Aggressive)
- [ ] Startup automation toggle

---

## 🤝 Contributing

We welcome pull requests, feature ideas, and bug reports. Please read [CONTRIBUTING.md](./CONTRIBUTING.md) before submitting code.

---

## 🔐 Security

If you discover a vulnerability, please report it responsibly via GitHub private message. See [SECURITY.md](./SECURITY.md) for details.

---

## 📜 License
This project is licensed under the GNU General Public License v3.0 (GPL-3.0). You are free to use, modify, and distribute it—so long as derivative works remain open-source.

---

## 🙌 Acknowledgments

Built by Sergey Vasilyan to empower users and challenge proprietary ecosystems. Inspired by the open-source community and the belief that hardware control should be free and transparent.

---

Let’s build something powerful, elegant, and open—together.
