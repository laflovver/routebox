import sys
import os
import json
import folium
import random
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QListWidget,
    QFileDialog, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QInputDialog, QColorDialog
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

from logic import extract_route

class RouteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RouteBox (PyQt5)")
        self.resize(1000, 600)

        # base filename -> list of geojson options
        self.routes = {}
        # current selected option per base filename
        self.current_option_index = {}

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)

        # Left panel
        left_panel = QVBoxLayout()

        self.load_button = QPushButton("Load JSON Routes")
        self.load_button.clicked.connect(self.load_json)
        left_panel.addWidget(self.load_button)

        self.route_list = QListWidget()
        # allow multi-selection of routes
        self.route_list.setSelectionMode(QListWidget.ExtendedSelection)
        # update display when selection changes
        self.route_list.itemSelectionChanged.connect(self.display_route)
        self.route_list.currentItemChanged.connect(self.display_route)
        self.route_list.itemDoubleClicked.connect(self.rename_route)
        left_panel.addWidget(self.route_list)

        # Option navigation
        self.prev_button = QPushButton("Prev Option")
        self.prev_button.clicked.connect(self.prev_option)
        left_panel.addWidget(self.prev_button)

        self.option_label = QLabel("Option: -")
        left_panel.addWidget(self.option_label)

        self.next_button = QPushButton("Next Option")
        self.next_button.clicked.connect(self.next_option)
        left_panel.addWidget(self.next_button)

        self.rename_button = QPushButton("Rename Route")
        self.rename_button.clicked.connect(self.rename_route)
        left_panel.addWidget(self.rename_button)

        self.color_button = QPushButton("Choose Route Color")
        self.color_button.clicked.connect(self.choose_color)
        left_panel.addWidget(self.color_button)

        self.export_button = QPushButton("Export Selected Route")
        self.export_button.clicked.connect(self.export_route)
        left_panel.addWidget(self.export_button)

        self.preview_all_button = QPushButton("Preview All Routes")
        self.preview_all_button.clicked.connect(self.preview_all)
        left_panel.addWidget(self.preview_all_button)

        self.status = QLabel("No routes loaded")
        left_panel.addWidget(self.status)

        # Right panel
        self.web_view = QWebEngineView()

        layout.addLayout(left_panel, 2)
        layout.addWidget(self.web_view, 5)

    def load_json(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select JSON Files", "", "JSON Files (*.json)")
        if not file_paths:
            return

        total_loaded = 0
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                geojson_list = extract_route(data, return_all=True, route_name=os.path.basename(file_path))
                base = os.path.basename(file_path)
                self.routes[base] = geojson_list
                self.current_option_index[base] = 0
                # assign random color and darker NameColor to each option
                for geojson in geojson_list:
                    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
                    darker = QColor(color).darker(120).name()
                    for feat in geojson.get("features", []):
                        props = feat.setdefault("properties", {})
                        props["color"] = color
                        props["nameColor"] = darker
                self.route_list.addItem(base)
                total_loaded += len(geojson_list)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load {file_path}:\n{str(e)}")

        self.status.setText(f"Loaded {total_loaded} route(s)")

    def display_route(self):
        items = self.route_list.selectedItems()
        if not items:
            return

        # Update option label using the first selected route
        first_base = items[0].text()
        first_options = self.routes.get(first_base, [])
        if first_options:
            idx_first = self.current_option_index.get(first_base, 0)
            self.option_label.setText(f"Option: {idx_first+1} of {len(first_options)}")
        else:
            self.option_label.setText("Option: -")

        # Draw all selected routes on one map
        all_points = []
        routes_data = []
        for item in items:
            base = item.text()
            options = self.routes.get(base, [])
            if not options:
                continue
            idx = self.current_option_index.get(base, 0)
            geojson = options[idx]
            feats = geojson.get("features", [])
            if not feats:
                continue
            coords = feats[0]["geometry"]["coordinates"]
            latlngs = [(c[1], c[0]) for c in coords]
            color = feats[0].get("properties", {}).get("color", "blue")
            all_points.extend(latlngs)
            routes_data.append((latlngs, color))

        if not routes_data:
            return

        # Compute map bounds
        min_lat = min(pt[0] for pt in all_points)
        max_lat = max(pt[0] for pt in all_points)
        min_lon = min(pt[1] for pt in all_points)
        max_lon = max(pt[1] for pt in all_points)
        bounds = [[min_lat, min_lon], [max_lat, max_lon]]

        # Initialize map centered around bounds
        center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
        m = folium.Map(location=center, zoom_start=14)

        # Draw each route
        for latlngs, color in routes_data:
            folium.PolyLine(latlngs, color=color, weight=4).add_to(m)

        # Fit map to bounds
        m.fit_bounds(bounds)

        # Save and load
        output_file = "map_preview.html"
        m.save(output_file)
        self.web_view.load(QUrl.fromLocalFile(os.path.abspath(output_file)))

    def prev_option(self):
        item = self.route_list.currentItem()
        if not item:
            return
        base = item.text()
        count = len(self.routes.get(base, []))
        if count < 2:
            return
        idx = (self.current_option_index[base] - 1) % count
        self.current_option_index[base] = idx
        self.display_route()

    def next_option(self):
        item = self.route_list.currentItem()
        if not item:
            return
        base = item.text()
        count = len(self.routes.get(base, []))
        if count < 2:
            return
        idx = (self.current_option_index[base] + 1) % count
        self.current_option_index[base] = idx
        self.display_route()

    def rename_route(self):
        item = self.route_list.currentItem()
        if not item:
            return
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Route", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            self.routes[new_name] = self.routes.pop(old_name)
            self.current_option_index[new_name] = self.current_option_index.pop(old_name)
            item.setText(new_name)

    def export_route(self):
        item = self.route_list.currentItem()
        if not item:
            return
        base = item.text()
        options = self.routes.get(base, [])
        if not options:
            return
        idx = self.current_option_index.get(base, 0)
        geojson = options[idx]
        path, _ = QFileDialog.getSaveFileName(self, "Export GeoJSON", f"{base}.geojson", "GeoJSON Files (*.geojson)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)

    def choose_color(self):
        item = self.route_list.currentItem()
        if not item:
            return
        base = item.text()
        options = self.routes.get(base, [])
        if not options:
            return
        idx = self.current_option_index.get(base, 0)
        geojson = options[idx]

        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            if geojson.get("type") == "FeatureCollection":
                for feat in geojson.get("features", []):
                    feat["properties"] = feat.get("properties", {})
                    feat["properties"]["color"] = hex_color
            self.display_route()

    def preview_all(self):
        # Show all currently selected options on one map
        all_routes = []
        for base, options in self.routes.items():
            idx = self.current_option_index.get(base, 0)
            geojson = options[idx]
            feats = geojson.get("features", [])
            if not feats:
                continue
            coords = feats[0]["geometry"]["coordinates"]
            latlngs = [(c[1], c[0]) for c in coords]
            color = feats[0].get("properties", {}).get("color", "blue")
            all_routes.append((latlngs, color))

        if not all_routes:
            return

        # initialize map at first route start
        m = folium.Map(location=all_routes[0][0][0], zoom_start=12)
        for latlngs, color in all_routes:
            folium.PolyLine(latlngs, color=color, weight=4).add_to(m)

        output_file = "map_preview_all.html"
        m.save(output_file)
        self.web_view.load(QUrl.fromLocalFile(os.path.abspath(output_file)))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RouteApp()
    window.show()
    sys.exit(app.exec_())