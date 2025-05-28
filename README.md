

# 🚀 RouteBox

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/) [![PyQt5](https://img.shields.io/badge/PyQt5-Yes-brightgreen.svg)](https://riverbankcomputing.com/software/pyqt/) [![Folium](https://img.shields.io/badge/Folium-Yes-orange.svg)](https://python-visualization.github.io/folium/)

---

## 🎯 Overview

**RouteBox** is a lightweight, interactive desktop application built with **PyQt5** and **Folium**. It enables you to:

- Convert Direction Debug JSON routes into GeoJSON seamlessly.
- Preview multiple route options side-by-side.
- Assign and customize route colors with a built-in color picker.
- Export individual routes as standalone GeoJSON files.
- Focus the map on selected routes or all routes at once.

---

## ✨ Features

- **Multi-Route Support**  
  Load multiple JSON files and switch between different route options effortlessly.

- **Interactive Map Preview**  
  Embedded map powered by **Folium** and **QWebEngineView**, right inside your desktop application.

- **Dynamic Coloring**  
  Assign random or custom colors to each route. Generates a darker shade (`nameColor`) for labels and overlays.

- **Batch Preview**  
  “Preview All Routes” to display every selected route simultaneously on a single map.

- **Easy Export**  
  Export any selected route or option as a clean GeoJSON file for further editing or Mapbox integration.

---

## 🛠️ Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/youruser/routebox.git
   cd routebox
   ```

2. **Create a virtual environment**  
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Quick Start

```bash
source .venv/bin/activate
python app.py
```

1. Click **Load JSON Routes** to import one or more Direction Debug JSON files.
2. Select a route slot from the list on the left.
3. Use **Prev Option** / **Next Option** to navigate between route alternatives.
4. Click **Choose Route Color** to open the color picker.
5. Press **Export Selected Route** to save as GeoJSON.
6. Use **Preview All Routes** to display every chosen route on one map.

---

## 📝 Project Structure

```
routebox/
├── app.py          # Main PyQt5 GUI application
├── logic.py        # JSON-to-GeoJSON conversion logic
├── requirements.txt
├── README.md
├── LICENSE
└── map_preview.html
```

---

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Commit your changes: `git commit -m "✨ Add new feature"`.
4. Push to the branch: `git push origin feature/my-feature`.
5. Open a Pull Request.

---

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

*Enjoy visualizing your routes with RouteBox!*  