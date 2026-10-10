"""Native Python/PyVista/Qt port of battery_cell_transfer_line_3d_v0_4_1_cell_flat.html.

Run: python battery_line_3d.py
"""

import sys
import time
import argparse

from battery_line import BatteryLine
from line_datasheet import DEFAULT_DATASHEET


def main():
    parser = argparse.ArgumentParser(description="Battery line 3D simulator")
    parser.add_argument("--datasheet", default=DEFAULT_DATASHEET, help="Frame/unit CSV file")
    args = parser.parse_args()
    try:
        model = BatteryLine(args.datasheet)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    try:
        import pyvista as pv
        from pyvistaqt import QtInteractor
        from PySide6 import QtCore, QtWidgets
    except ImportError as exc:
        raise SystemExit("3D dependencies missing. Run: python -m pip install -r requirements-3d.txt") from exc

    class Window(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.model = model
            self.actors = {}
            self.setWindowTitle("Battery Cell Transfer Line — Python 3D")
            self.resize(1500, 900)
            central = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(central)
            self.setCentralWidget(central)
            self.plot = QtInteractor(central)
            layout.addWidget(self.plot.interactor, 1)
            panel = QtWidgets.QWidget()
            panel.setFixedWidth(310)
            ui = QtWidgets.QVBoxLayout(panel)
            layout.addWidget(panel)
            title = QtWidgets.QLabel("<b>Battery Cell Transfer Line</b><br>Python / PyVista / Qt")
            ui.addWidget(title)
            ui.addWidget(QtWidgets.QLabel("Belt Speed (mm/s)"))
            self.speed = QtWidgets.QDoubleSpinBox()
            self.speed.setRange(0, 3000)
            self.speed.setValue(300)
            self.speed.valueChanged.connect(lambda v: self.model.configure(speed=v))
            ui.addWidget(self.speed)
            ui.addWidget(QtWidgets.QLabel("7-Cell Batch Pitch (mm)"))
            self.pitch = QtWidgets.QDoubleSpinBox()
            self.pitch.setRange(123, 1000)
            self.pitch.setValue(180)
            self.pitch.valueChanged.connect(lambda v: self.model.configure(pitch=v))
            ui.addWidget(self.pitch)
            for label, action in [("7셀 투입 START", self.feed), ("이송 STOP", self.model.pause),
                                  ("셀 초기화", self.clear)]:
                button = QtWidgets.QPushButton(label)
                button.clicked.connect(action)
                ui.addWidget(button)
            for label, name in [("Top view", "top"), ("Front view", "front"), ("ISO view", "iso")]:
                button = QtWidgets.QPushButton(label)
                button.clicked.connect(lambda checked=False, n=name: self.view(n))
                ui.addWidget(button)
            frame_info = "\n".join(f"{f.name}: {f.length:g} × {f.width:g} × {f.height:g} mm" for f in self.model.frames)
            unit_info = "\n".join(f"{u.name}: {u.kind}" for u in self.model.units)
            info = QtWidgets.QLabel(
                frame_info + "\n\n" + unit_info + "\n\n"
                f"Belt: 폭 30 mm / C-C {self.model.conveyor.width - 30:g} mm\n\n"
                "Cell: X 123 / Y 600 / Z 17.8 mm\nLead: 폭 45 / 돌출 22 mm, 양끝\n\n"
                "START 1회 = 7셀 투입\nSTOP 후 START = 추가 투입 및 재개\n\n"
                "좌클릭: 회전\nShift+좌클릭 / 가운데 버튼: 이동\n휠: 확대/축소")
            info.setWordWrap(True)
            ui.addWidget(info)
            self.status = QtWidgets.QLabel()
            ui.addWidget(self.status)
            ui.addStretch()
            self.plot.set_background("white")
            self.plot.enable_trackball_style()
            self.build_scene()
            self.view("iso")
            self.last = time.perf_counter()
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self.tick)
            self.timer.start(16)

        def box(self, size, center, color):
            mesh = pv.Cube(center=center, x_length=size[0], y_length=size[1], z_length=size[2])
            return self.plot.add_mesh(mesh, color=color, smooth_shading=False, render=False)

        def build_scene(self):
            ivory, brace = "#dacaa8", "#bbaa83"
            self.box((30000, 10000, 1), (0, 0, -1), "#f8f8f6")
            for component in self.model.frames:
                length, width = component.length, component.width
                cursor, end, cx = component.x_start, component.x_end, component.coordinate.x
                cy, base = component.coordinate.y, component.coordinate.z
                top = base + component.height
                for y in (cy - width / 2 + 45, cy + width / 2 - 45):
                    self.box((length, 80, 80), (cx, y, top - 85), ivory)
                    self.box((length, 65, 65), (cx, y, base + 260), brace)
                n = max(4, int(length / 800 + 0.5))
                for i in range(n + 1):
                    x = cursor + i * length / n
                    self.box((70, width - 90, 70), (x, cy, top - 85), ivory)
                    self.box((55, width - 120, 55), (x, cy, base + 260), brace)
                for x in (cursor + 120, end - 120):
                    for y in (cy - width / 2 + 120, cy + width / 2 - 120):
                        leg_height = component.height - 280
                        self.box((75, 75, leg_height), (x, y, base + 240 + leg_height / 2), ivory)
                        for z in (base + 350, top - 280):
                            self.box((55, 420, 50), (x, y, z), brace)
                        foot = pv.Cylinder(center=(x, y, base + 18), direction=(0, 0, 1), radius=48, height=35, resolution=20)
                        self.plot.add_mesh(foot, color="#55585b", render=False)
                self.box((length - 110, width - 110, 35), (cx, cy, top - 17.5), ivory)
            for component in self.model.units:
                p = component.coordinate
                if component.kind == "conveyor":
                    for side in (-1, 1):
                        y = p.y + side * (component.width - 30) / 2
                        self.box((component.length, 30, component.height), (p.x, y, p.z), "#30363a")
                        self.box((component.length, 8, 30), (p.x, y, p.z - component.height / 2 - 10), "#697177")
                else:
                    self.box((component.length, component.width, component.height), (p.x, p.y, p.z), "#8c9eac")

        def feed(self):
            self.model.inject_batch()
            self.sync_cells()

        def clear(self):
            self.model.clear()
            self.sync_cells()

        def sync_cells(self):
            live = {c.id for c in self.model.cells}
            for key in list(self.actors):
                if key not in live:
                    for actor in self.actors.pop(key):
                        self.plot.remove_actor(actor, render=False)
            for cell in self.model.cells:
                if cell.id not in self.actors:
                    belt_top = self.model.BELT_TOP
                    actors = [self.box(self.model.CELL_SIZE, (0, 0, belt_top + 8.9), "#67b7dc")]
                    for side in (-1, 1):
                        actors.append(self.box((45, 22, 3.5), (0, side * 311, belt_top + 19.8), "#c8a54d"))
                    self.actors[cell.id] = actors
                for actor in self.actors[cell.id]:
                    actor.SetPosition(cell.x, self.model.conveyor.coordinate.y, 0)

        def view(self, name):
            positions = {"top": (0, -50, 11000), "front": (0, -11000, 1450), "iso": (7300, -7300, 5200)}
            center = self.model.conveyor.coordinate
            offset = (center.x, center.y, self.model.BELT_TOP - 1280)
            camera = tuple(value + shift for value, shift in zip(positions[name], offset))
            target = (center.x, center.y, self.model.BELT_TOP - 630)
            self.plot.camera_position = [camera, target, (0, 0, 1)]
            self.plot.camera.view_angle = 42
            self.plot.reset_camera_clipping_range()
            self.plot.render()

        def tick(self):
            now = time.perf_counter()
            self.model.step(min(max(now - self.last, 1e-6), 0.05))
            self.last = now
            self.sync_cells()
            self.status.setText(f"상태: {self.model.state.value} | 셀: {len(self.model.cells)}")
            self.plot.render()

        def closeEvent(self, event):
            self.timer.stop()
            self.plot.close()
            event.accept()

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
