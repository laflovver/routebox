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
    QScrollArea, QFrame, QGraphicsDropShadowEffect, QListWidget, QListWidgetItem, QMenu,
    QSizePolicy, QGraphicsOpacityEffect
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QPoint


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

        # Route list slots
        self.route_list = QListWidget()
        self.route_list.setSpacing(4)
        self.route_list.setStyleSheet("""
            QListWidget {
                padding: 4px;
                border: none;
            }
            QListWidget::item {
                margin: 2px 0;
                height: 32px;
                font-size: 14pt;
                border-radius: 6px;
                background-color: transparent;
            }
            QListWidget::item:hover {
                background-color: #E5E5EA;
            }
            QListWidget::item:selected {
                background-color: #007AFF;
                color: white;
                font-weight: bold;
                border: 1px solid #004080;
            }
            QListWidget::item:focus {
                outline: none;
            }
            QListWidget::item:!selected:!hover {
                background-color: transparent;
            }
        """)
        self.route_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.route_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.route_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.route_list.itemSelectionChanged.connect(self.display_route)
        self.route_list.itemDoubleClicked.connect(self.rename_route)
        self.route_list.itemActivated.connect(self.rename_route)
        # enable custom context menu
        self.route_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.route_list.customContextMenuRequested.connect(self.show_route_context_menu)
        left_panel.addWidget(self.route_list)

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
                # assign random color and darker NameColor to each option
                for geojson in geojson_list:
                    # generate maximally contrasting vivid color
                    hue = random.randint(0, 359)
                    color = QColor.fromHsv(hue, 255, 255).name()
                    # darker shade for border
                    darker = QColor.fromHsv(hue, 255, 180).name()
                    for feat in geojson.get("features", []):
                        props = feat.setdefault("properties", {})
                        props["color"] = color
                        props["nameColor"] = darker
                total_loaded += len(geojson_list)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load {file_path}:\n{str(e)}")

        self.status.setText(f"Loaded {total_loaded} route(s)")
        self.route_list.clear()
        for base, options in self.routes.items():
            item = QListWidgetItem(base)
            # create widget container
            widget = QWidget()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            hl = QHBoxLayout(widget)
            hl.setContentsMargins(6, 0, 6, 0)
            hl.setSpacing(6)
            hl.setSizeConstraint(QHBoxLayout.SetMinimumSize)
            hl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lbl = QLabel()
            fm = lbl.fontMetrics()
            lbl.setText(fm.elidedText(base, Qt.ElideRight, 100))
            lbl.setToolTip(base)
            lbl.setStyleSheet("font-size: 14pt; padding-right: 4px;")
            lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            lbl.setMaximumWidth(140)
            lbl.setWordWrap(False)
            hl.addWidget(lbl)
            hl.addSpacing(6)
            # variant circle buttons
            for idx, geojson in enumerate(options):
                props = geojson["features"][0]["properties"]
                color = props.get("color")
                darker = props.get("nameColor")
                btn = CircleButton(str(idx+1))
                # style circle; highlight active variant with border
                style = f"background-color: {color};"
                if idx == self.current_option_index.get(base, 0):
                    style += f" border: 2px solid {darker};"
                btn.setStyleSheet(style)
                btn.clicked.connect(lambda _, b=base, i=idx: self.on_option_selected(b,i))
                hl.addWidget(btn)
            hl.addStretch()
            self.route_list.addItem(item)
            item.setText("")  # prevent default text display behind custom widget
            self.route_list.setItemWidget(item, widget)

    def display_route(self):
        selected_items = self.route_list.selectedItems()
        if not selected_items:
            return

        self.selected_routes = set()
        for item in selected_items:
            widget = self.route_list.itemWidget(item)
            if widget:
                label = widget.findChild(QLabel)
                if label and label.toolTip():
                    self.selected_routes.add(label.toolTip())

        # Animation disabled for stability on macOS
        pass

        # Update option label using the first selected route (not used now)
        try:
            first_base = next(iter(self.selected_routes))
        except StopIteration:
            return
        first_options = self.routes.get(first_base, [])
        if first_options:
            idx_first = self.current_option_index.get(first_base, 0)
            # self.option_label.setText(f"Option: {idx_first+1} of {len(first_options)}")
        else:
            pass
            # self.option_label.setText("Option: -")

        # Draw all selected routes on one map
        all_points = []
        routes_data = []
        for base in self.selected_routes:
            options = self.routes.get(base, [])
            if not options:
                continue
            idx = self.current_option_index.get(base, 0)
            geojson = options[idx]
            feats = geojson.get("features", [])
            # Add check for features, geometry, coordinates
            if not feats or "geometry" not in feats[0] or "coordinates" not in feats[0]["geometry"]:
                print(f"Missing geometry in route: {base}")
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
        # Ensure file is flushed and synced before loading
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
        if not self.selected_routes:
            return
        # Only rename first selected route
        base = next(iter(self.selected_routes))
        old_name = base
        new_name, ok = QInputDialog.getText(self, "Rename Route", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            self.routes[new_name] = self.routes.pop(old_name)
            self.current_option_index[new_name] = self.current_option_index.pop(old_name)
            if old_name in self.selected_routes:
                self.selected_routes.remove(old_name)
                self.selected_routes.add(new_name)
            # Update list widget
            self.route_list.clear()
            for base, options in self.routes.items():
                item = QListWidgetItem(base)
                # create widget container
                widget = QWidget()
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                hl = QHBoxLayout(widget)
                hl.setContentsMargins(2,2,2,2)
                hl.setSpacing(4)
                hl.setSizeConstraint(QHBoxLayout.SetMinimumSize)
                hl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                lbl = QLabel()
                fm = lbl.fontMetrics()
                elided = fm.elidedText(base, Qt.ElideRight, 100)
                lbl.setText(elided)
                lbl.setToolTip(base)
                lbl.setStyleSheet("font-size: 14pt; padding-right: 4px;")
                lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                lbl.setMaximumWidth(140)
                lbl.setWordWrap(False)
                hl.addWidget(lbl)
                hl.addSpacing(6)
                # variant circle buttons
                for idx, geojson in enumerate(options):
                    props = geojson["features"][0]["properties"]
                    color = props.get("color")
                    darker = props.get("nameColor")
                    btn = CircleButton(str(idx+1))
                    # style circle; highlight active variant with border
                    style = f"background-color: {color};"
                    if idx == self.current_option_index.get(base, 0):
                        style += f" border: 2px solid {darker};"
                    btn.setStyleSheet(style)
                    btn.clicked.connect(lambda _, b=base, i=idx: self.on_option_selected(b,i))
                    hl.addWidget(btn)
                hl.addStretch()
                self.route_list.addItem(item)
                item.setText("")  # prevent default text display behind custom widget
                self.route_list.setItemWidget(item, widget)
            self.display_route()

    def export_route(self):
        if not self.selected_routes:
            return

        # Ask user to select an export directory
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not dir_path:
            return

        exported = 0
        for base in self.selected_routes:
            options = self.routes.get(base, [])
            if not options:
                continue
            idx = self.current_option_index.get(base, 0)
            geojson = options[idx]
            # Get current display name from the QListWidget label
            display_name = None
            for i in range(self.route_list.count()):
                item = self.route_list.item(i)
                widget = self.route_list.itemWidget(item)
                if widget:
                    label = widget.findChild(QLabel)
                    if label and label.toolTip() == base:
                        display_name = label.text()
                        break
            if not display_name:
                display_name = base
            # Record current route name into each feature’s properties
            for feat in geojson.get("features", []):
                feat["properties"] = feat.get("properties", {})
                feat["properties"]["name"] = display_name

            # Use display name for filename
            filename = f"{display_name}.geojson"
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
            # also compute darker color for nameColor
            darker_color = QColor.fromHsv(color.hue(), color.saturation(), 180).name()
            for feat in geojson.get("features", []):
                feat["properties"] = feat.get("properties", {})
                feat["properties"]["color"] = hex_color
                feat["properties"]["nameColor"] = darker_color
            # refresh the variant buttons color, but only if method exists
            if hasattr(self, "refresh_route_list"):
                self.refresh_route_list()
            self.display_route()

    def show_route_context_menu(self, pos: QPoint):
        item = self.route_list.itemAt(pos)
        if not item:
            return
        base = item.text()
        menu = QMenu(self)
        color_action = menu.addAction("Change Route Color")
        action = menu.exec_(self.route_list.viewport().mapToGlobal(pos))
        if action == color_action:
            # call choose_color for this route
            self.choose_color_for_base(base)

    def on_option_selected(self, base, idx):
        self.current_option_index[base] = idx
        # Ensure the selected item visually matches selection state
        for i in range(self.route_list.count()):
            item = self.route_list.item(i)
            widget = self.route_list.itemWidget(item)
            label = widget.findChild(QLabel) if widget else None
            if label and label.toolTip() == base:
                self.route_list.setCurrentItem(item)
                item.setSelected(True)
            else:
                item.setSelected(False)
        self.display_route()


    def refresh_route_list(self):
        self.route_list.clear()
        for base, options in self.routes.items():
            item = QListWidgetItem(base)
            widget = QWidget()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            hl = QHBoxLayout(widget)
            hl.setContentsMargins(6, 0, 6, 0)
            hl.setSpacing(6)
            hl.setSizeConstraint(QHBoxLayout.SetMinimumSize)
            hl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            lbl = QLabel()
            fm = lbl.fontMetrics()
            lbl.setText(fm.elidedText(base, Qt.ElideRight, 100))
            lbl.setToolTip(base)
            lbl.setStyleSheet("font-size: 14pt; padding-right: 4px;")
            lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            lbl.setMaximumWidth(140)
            lbl.setWordWrap(False)
            hl.addWidget(lbl)

            for idx, geojson in enumerate(options):
                props = geojson["features"][0]["properties"]
                color = props.get("color")
                darker = props.get("nameColor")
                btn = CircleButton(str(idx+1))
                style = f"background-color: {color};"
                if idx == self.current_option_index.get(base, 0):
                    style += f" border: 2px solid {darker};"
                btn.setStyleSheet(style)
                btn.clicked.connect(lambda _, b=base, i=idx: self.on_option_selected(b,i))
                hl.addWidget(btn)

            hl.addStretch()
            self.route_list.addItem(item)
            item.setText("")
            # Restore selection state if base is in self.selected_routes
            if base in self.selected_routes:
                item.setSelected(True)
            self.route_list.setItemWidget(item, widget)


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