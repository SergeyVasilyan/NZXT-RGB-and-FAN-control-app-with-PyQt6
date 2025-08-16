# Contributing to NZXT RGB and FAN Control App

🎉 Thank you for your interest in contributing! This project exists to give users full control over NZXT hardware without relying on proprietary software. Whether you're fixing bugs, adding features, or improving documentation, your help is welcome.

---

## 🛠️ Getting Started

1. **Fork the repository**
2. **Clone your fork**
```bash
git clone https://github.com/<your-username>/NZXT-RGB-and-FAN-control-app-with-PyQt6.git
```
3. **Create a new branch**
```bash
git checkout -b feature/my-new-feature
```
4. **Make your changes**
5. **Test thoroughly**
6. **Commit and push**
```bash
git commit -m "Add: brief description of your change"
git push origin feature/my-new-feature
```
7. **Open a pull request**

---

## 🧪 Code Guideline

- Use **Python3.10+** and **PyQt6**
- Follow **PEP8** style conventions
- Keep UI logic modular - separate classes for widgets and hardware control
- Avoid hardcoding device paths or value
- Include docstrings and inline comments for clarity

---

## 🎨 UI Contributions

If you're improving the GUI:

- Use responsive layouts (`QVBoxLayout`, `QHBoxLayout`, `QGridLayout`)
- Prefer dynamic styling via `.setStyleSheet()` or QSS
- Test on multiple DPI/resolutions
- Keep icons in the `/icon` folder and use SVG when possible

---

## 📦 Feature Ideas

Looking for inspiration? Here are some welcome additions:
- Fan curve presets (Silent, Normal, Aggressive)
- RGB color picker with live preview
- Device auto-discovery
- Startup daemon integration
- Graphical fan curve editor using pyqtgraph

---

## 🧑‍⚖️ Licensing

This project is licensed under GPL-3.0. By contributing, you agree that your code will also be released under GPL-3.0 to preserve openness and community access.

---

## 💬 Need Help?

Open an issue for bugs, questions, or feature requests. You can also start a discussion if you're unsure how best to contribute.
