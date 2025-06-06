import sys
import os
import json
import folium
import random
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, 
    QFileDialog, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox, QInputDialog, QColorDialog,
    QScrollArea, QFrame, QGraphicsDropShadowEffect, QMenu,
    QSizePolicy, QGraphicsOpacityEffect, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QPoint, QSize


class CircleButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedSize(20, 20)
        self.setStyleSheet("border-radius: 10px; font-size:10pt; color:white;")

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
        self.selected_routes = set()

        self.init_ui()

        # Apply global modern macOS-style stylesheet
        self.setStyleSheet("""
            QWidget { background-color: #F2F2F5; font-family: Menlo, Monaco, Consolas, "Courier New", monospace; }
            QPushButton { background-color: #FFFFFF; border: none; border-radius: 8px; padding: 8px 12px; color: #000000; }
            QPushButton:hover { background-color: #E5E5EA; }
            QLabel { color: #1C1C1E; font-size: 13px; }
            QScrollArea { background: transparent; border: none; }
        """)

    def init_ui(self):
        layout = QHBoxLayout(self)

        # Left panel
        left_panel = QVBoxLayout()

        self.load_button = QPushButton("Load JSON Routes")
        self.load_button.clicked.connect(self.load_json)
        left_panel.addWidget(self.load_button)

        # Route tree widget
        self.route_tree = QTreeWidget()
        self.route_tree.setHeaderLabel("Routes and Variants")
        self.route_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.route_tree.itemSelectionChanged.connect(self.display_route)
        self.route_tree.itemDoubleClicked.connect(self.rename_route)
        self.route_tree.itemChanged.connect(self.on_variant_check_changed)
        left_panel.addWidget(self.route_tree)

        self.rename_button = QPushButton("Rename Route")
        self.rename_button.clicked.connect(self.rename_route)
        left_panel.addWidget(self.rename_button)

        self.color_button = QPushButton("Choose Route Color")
        self.color_button.clicked.connect(self.choose_color)
        left_panel.addWidget(self.color_button)

        self.export_button = QPushButton("Export Selected Route")
        self.export_button.clicked.connect(self.export_route)
        left_panel.addWidget(self.export_button)


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
                # генерируем яркие и разные цвета для каждого маршрута и его вариантов
                base_hue = random.randint(0, 179) * 2  # Ensures full 180-degree complementarity
                hue_step = 180 // max(1, len(geojson_list) - 1 or 1)
                total = len(geojson_list)
                for idx, geojson in enumerate(geojson_list):
                    hue = (base_hue + (180 * idx) // max(1, total)) % 360
                    color = QColor.fromHsv(hue, 255, 255).name()
                    darker = QColor.fromHsv(hue, 255, 180).name()
                    for feat in geojson.get("features", []):
                        props = feat.setdefault("properties", {})
                        props["color"] = color
                        props["nameColor"] = darker
                total_loaded += len(geojson_list)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load {file_path}:\n{str(e)}")

        self.status.setText(f"Loaded {total_loaded} route(s)")
        self.route_tree.clear()
        for base, options in self.routes.items():
            route_item = QTreeWidgetItem([base])
            route_item.setToolTip(0, base)
            route_item.setData(0, Qt.UserRole, (base, None))
            self.route_tree.addTopLevelItem(route_item)
            for idx, geojson in enumerate(options):
                props = geojson["features"][0].get("properties", {})
                color = props.get("color", "#000000")
                variant_item = QTreeWidgetItem([f"Variant {idx + 1}"])
                variant_item.setData(0, Qt.UserRole, (base, idx))
                variant_item.setForeground(0, QColor(color))
                variant_item.setFlags(variant_item.flags() | Qt.ItemIsUserCheckable)
                variant_item.setCheckState(0, Qt.Checked if idx == self.current_option_index[base] else Qt.Unchecked)
                route_item.addChild(variant_item)
                if idx == self.current_option_index[base]:
                    variant_item.setSelected(True)
        self.route_tree.expandAll()

    def display_route(self):
        # Show all checked variants on the map
        self.selected_routes = set()
        routes_data = []
        all_points = []

        for i in range(self.route_tree.topLevelItemCount()):
            route_item = self.route_tree.topLevelItem(i)
            base = route_item.data(0, Qt.UserRole)[0]
            options = self.routes.get(base, [])
            has_checked = False
            for j in range(route_item.childCount()):
                child = route_item.child(j)
                base_idx = child.data(0, Qt.UserRole)
                if not base_idx:
                    continue
                _, idx = base_idx
                # PATCH: skip if idx out of range
                if idx < 0 or idx >= len(options):
                    continue
                if idx is not None and child.checkState(0) == Qt.Checked:
                    geojson = options[idx]
                    for feat in geojson.get("features", []):
                        geom = feat.get("geometry")
                        if not geom or "coordinates" not in geom:
                            continue
                        if geom.get("type") != "LineString":
                            continue
                        coords = geom["coordinates"]
                        latlngs = [(c[1], c[0]) for c in coords]
                        color = feat.get("properties", {}).get("color", "blue")
                        all_points.extend(latlngs)
                        routes_data.append((latlngs, color))
                    has_checked = True
            if has_checked:
                self.selected_routes.add(base)

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
        with open(output_file, 'w', encoding='utf-8') as f:
            html = m.get_root().render()
            f.write(html)
            f.flush()
            os.fsync(f.fileno())
        print("Loading map from:", os.path.abspath(output_file))
        self.web_view.load(QUrl.fromLocalFile(os.path.abspath(output_file)))

    def prev_option(self):
        # Not used now
        pass

    def next_option(self):
        # Not used now
        pass

    def rename_route(self):
        selected_items = self.route_tree.selectedItems()
        base = None
        for item in selected_items:
            data = item.data(0, Qt.UserRole)
            if data:
                base, idx = data
                if idx is None:
                    break
        if not base:
            return
        old_name = base
        new_name, ok = QInputDialog.getText(self, "Rename Route", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            self.routes[new_name] = self.routes.pop(old_name)
            self.current_option_index[new_name] = self.current_option_index.pop(old_name)
            # PATCH: update child variant UserRole data to use new_name
            for i in range(self.route_tree.topLevelItemCount()):
                item = self.route_tree.topLevelItem(i)
                if item.data(0, Qt.UserRole)[0] == new_name:
                    for j in range(item.childCount()):
                        child = item.child(j)
                        _, idx = child.data(0, Qt.UserRole)
                        child.setData(0, Qt.UserRole, (new_name, idx))
            if old_name in self.selected_routes:
                self.selected_routes.remove(old_name)
                self.selected_routes.add(new_name)
            # Refresh tree
            self.refresh_route_list()
            self.display_route()

    def export_route(self):
        if not self.selected_routes:
            return

        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not dir_path:
            return

        exported = 0
        for base in self.selected_routes:
            options = self.routes.get(base, [])
            if not options:
                continue
            # Find the corresponding top-level route_item
            route_item = None
            for i in range(self.route_tree.topLevelItemCount()):
                item = self.route_tree.topLevelItem(i)
                if item.data(0, Qt.UserRole)[0] == base:
                    route_item = item
                    break
            if route_item is None:
                continue
            display_name = base
            # New logic: collect checked indices, then export each with suffixes if needed
            checked_indices = []
            for idx, geojson in enumerate(options):
                child = route_item.child(idx)
                if child is not None and child.checkState(0) == Qt.Checked:
                    checked_indices.append(idx)

            for export_count, idx in enumerate(checked_indices):
                geojson = options[idx]
                for feat in geojson.get("features", []):
                    feat["properties"] = feat.get("properties", {})
                    suffix = f"_v{export_count + 1}" if len(checked_indices) > 1 else ""
                    feat["properties"]["name"] = f"{display_name}{suffix}"
                filename = f"{display_name}{suffix}.geojson"
                file_path = os.path.join(dir_path, filename)
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(geojson, f, ensure_ascii=False, indent=2)
                    exported += 1
                except Exception as e:
                    QMessageBox.warning(self, "Export Error", f"Failed to export {filename}:\n{e}")

        QMessageBox.information(self, "Export Complete", f"Exported {exported} route(s) to:\n{dir_path}")

    def choose_color(self):
        if not self.selected_routes:
            return
        # Only use first selected route
        base = next(iter(self.selected_routes))
        self.choose_color_for_base(base)

    def choose_color_for_base(self, base):
        options = self.routes.get(base, [])
        if not options:
            return
        idx = self.current_option_index.get(base, 0)
        geojson = options[idx]
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            darker_color = QColor.fromHsv(color.hue(), color.saturation(), 180).name()
            for feat in geojson.get("features", []):
                feat["properties"] = feat.get("properties", {})
                feat["properties"]["color"] = hex_color
                feat["properties"]["nameColor"] = darker_color
            # Instead of refreshing the whole route list, update only the relevant variant colors in the tree
            for i in range(self.route_tree.topLevelItemCount()):
                item = self.route_tree.topLevelItem(i)
                if item.data(0, Qt.UserRole)[0] == base:
                    for j in range(item.childCount()):
                        child = item.child(j)
                        b, idx2 = child.data(0, Qt.UserRole)
                        if idx2 is not None:
                            props = self.routes[base][idx2]["features"][0].get("properties", {})
                            color = props.get("color", "#000000")
                            child.setForeground(0, QColor(color))
            self.display_route()

    def show_route_context_menu(self, pos: QPoint):
        item = self.route_tree.itemAt(pos)
        if not item:
            return
        # Only allow color change for variants
        parent = item.parent()
        if parent:
            base, idx = item.data(0, Qt.UserRole)
            menu = QMenu(self)
            color_action = menu.addAction("Change Route Color")
            action = menu.exec_(self.route_tree.viewport().mapToGlobal(pos))
            if action == color_action:
                self.choose_color_for_base(base)

    def on_option_selected(self, base, idx):
        self.current_option_index[base] = idx
        # Update check states
        for i in range(self.route_tree.topLevelItemCount()):
            route_item = self.route_tree.topLevelItem(i)
            if route_item.data(0, Qt.UserRole)[0] == base:
                for j in range(route_item.childCount()):
                    variant_item = route_item.child(j)
                    b, idx2 = variant_item.data(0, Qt.UserRole)
                    variant_item.setCheckState(0, Qt.Checked if idx == idx2 else Qt.Unchecked)
        # self.refresh_route_list()  # Disabled to prevent UI refresh loop
        self.route_tree.expandAll()
        self.display_route()

    def refresh_route_list(self):
        self.route_tree.clear()
        for base, options in self.routes.items():
            route_item = QTreeWidgetItem([base])
            route_item.setToolTip(0, base)
            route_item.setData(0, Qt.UserRole, (base, None))
            if 0 == self.current_option_index.get(base, 0):
                route_item.setSelected(True)
            self.route_tree.addTopLevelItem(route_item)
            for idx, geojson in enumerate(options):
                props = geojson["features"][0].get("properties", {})
                color = props.get("color", "#000000")
                variant_item = QTreeWidgetItem([f"Variant {idx + 1}"])
                variant_item.setData(0, Qt.UserRole, (base, idx))
                variant_item.setForeground(0, QColor(color))
                variant_item.setFlags(variant_item.flags() | Qt.ItemIsUserCheckable)
                variant_item.setCheckState(0, Qt.Checked if idx == self.current_option_index[base] else Qt.Unchecked)
                route_item.addChild(variant_item)
                if idx == self.current_option_index[base]:
                    variant_item.setSelected(True)

    def on_variant_check_changed(self, item, column):
        parent = item.parent()
        if not parent:
            return
        base, idx = item.data(0, Qt.UserRole)
        if idx is None:
            return
        # Refresh map on any checkbox toggle
        self.display_route()


if __name__ == "__main__":
    import traceback

    try:
        app = QApplication(sys.argv)
        window = RouteApp()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        with open("routebox_error.log", "w") as f:
            f.write("Unhandled exception:\n")
            traceback.print_exc(file=f)
        raise