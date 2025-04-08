import sys
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (
    QApplication, QGraphicsLineItem, QGraphicsScene, QGraphicsView, QPushButton, QGraphicsTextItem, QGraphicsEllipseItem, QSlider
)
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPainter
from PyQt5.QtCore import QLineF, QPointF, QRectF, QTimer, Qt
from Hrycyna_Julia_193272 import ClickableCell


class ReplayScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 900, 900)
        self.setBackgroundBrush(QBrush(QColor(20, 20, 60)))
        self.steps = []
        self.current_step = 0
        self.cell_map = {}
        self.line_map = []
        self.mini_cells = []
        self.mini_timer = QTimer()
        self.mini_timer.timeout.connect(self.animate_mini_cells)

        self.turn_display = QGraphicsTextItem("")
        self.turn_display.setFont(QFont("Arial", 14, QFont.Bold))
        self.turn_display.setDefaultTextColor(Qt.white)
        self.turn_display.setPos(700, 20)
        self.addItem(self.turn_display)

        self.timer_display = QGraphicsTextItem("")
        self.timer_display.setFont(QFont("Arial", 14, QFont.Bold))
        self.timer_display.setDefaultTextColor(Qt.white)
        self.timer_display.setPos(700, 50)
        self.addItem(self.timer_display)

        self.load_history()

    def load_history(self):
        try:
            tree = ET.parse("history.xml")
            root = tree.getroot()
        except Exception as e:
            print("Błąd odczytu XML:", e)
            return

        for step_el in root.findall("step"):
            step = {
                "cells": [],
                "lines": [],
                "turn": step_el.get("turn"),
                "timer": int(step_el.get("timer", 0))
            }


            for cell_el in step_el.findall("cell"):
                cell_data = {
                    "x": int(cell_el.get("x")),
                    "y": int(cell_el.get("y")),
                    "value": int(cell_el.get("value")),
                    "color": cell_el.get("color"),
                    "level": int(cell_el.get("level"))
                }

                circles = cell_el.get("circles")
                if circles:
                    cell_data["circles"] = circles.split(",")

                top_value = cell_el.get("top_value")
                if top_value is not None:
                    cell_data["top_value"] = int(top_value)

                step["cells"].append(cell_data)

            for line_el in step_el.findall("line"):
                step["lines"].append({
                    "start_x": int(line_el.get("start_x")),
                    "start_y": int(line_el.get("start_y")),
                    "end_x": int(line_el.get("end_x")),
                    "end_y": int(line_el.get("end_y")),
                    "color": line_el.get("color") if line_el.get("color") else "#ffffff"
                })

            self.steps.append(step)

        if self.steps:
            self.init_cells(self.steps[0]["cells"])

    def init_cells(self, first_step):
        for cell_data in first_step:
            rect = QRectF(cell_data["x"], cell_data["y"], 100, 100)
            color = QColor(cell_data["color"])
            cell = ClickableCell(rect, color, cell_data["value"])
            cell.level = cell_data["level"]
            cell.update_level_display()
            
            cell.setAcceptedMouseButtons(Qt.NoButton)
            self.addItem(cell)
            self.cell_map[(cell_data["x"], cell_data["y"])] = cell

            if color != Qt.gray:
                value_text = QGraphicsTextItem(str(cell.value))
                value_text.setFont(QFont("Arial", 14, QFont.Bold))
                value_text.setDefaultTextColor(Qt.white)
                value_text.setPos(
                    rect.x() + 50 - value_text.boundingRect().width() / 2,
                    rect.y() + 50 - value_text.boundingRect().height() / 2
                )
                self.addItem(value_text)
                cell.set_value_text(value_text)

            level_text = QGraphicsTextItem(f"LVL {cell.level}")
            level_text.setFont(QFont("Arial", 10))
            level_text.setDefaultTextColor(Qt.white)
            level_text.setPos(rect.x() + 50 - level_text.boundingRect().width() / 2, rect.y() + 90)
            self.addItem(level_text)
            cell.set_level_text(level_text)

            if color != Qt.gray:
                circle_colors = cell_data.get("circles", ["#ffffff", "#ffffff"])
                for i, (dx, dy) in enumerate([(-20, -20), (20, 20)]):
                    circle = QGraphicsEllipseItem(rect.x() + 50 + dx - 10, rect.y() + 50 + dy - 10, 20, 20)
                    color_str = circle_colors[i] if i < len(circle_colors) else "#ffffff"
                    circle.setBrush(QBrush(QColor(color_str)))
                    circle.setPen(QPen(Qt.black, 1))
                    circle.setZValue(1)
                    self.addItem(circle)
                    cell.inner_circles.append(circle)


            if color == Qt.gray:
                top_value = cell_data.get("top_value", 0)
                cell._actual_top_value = top_value
                top_text = QGraphicsTextItem(str(top_value))
                top_text.setFont(QFont("Arial", 14, QFont.Bold))
                top_text.setDefaultTextColor(Qt.white)
                top_text.setPos(rect.x() + 50 - top_text.boundingRect().width() / 2, rect.y() + 10)
                self.addItem(top_text)
                cell.set_top_text(top_text)

                bottom_text = QGraphicsTextItem("8")
                bottom_text.setFont(QFont("Arial", 14, QFont.Bold))
                bottom_text.setDefaultTextColor(Qt.white)
                bottom_text.setPos(rect.x() + 50 - bottom_text.boundingRect().width() / 2, rect.y() + 55)
                self.addItem(bottom_text)
                cell.bottom_text = bottom_text

    def apply_step(self, step_data):
        for cell_data in step_data["cells"]:
            key = (cell_data["x"], cell_data["y"])
            if key in self.cell_map:
                cell = self.cell_map[key]

                if cell.inner_circles:
                    for circle in cell.inner_circles:
                        self.removeItem(circle)
                    cell.inner_circles = []

                if cell.base_color != Qt.gray and "circles" in cell_data:
                    for i, (dx, dy) in enumerate([(-20, -20), (20, 20)]):
                        circle = QGraphicsEllipseItem(cell.rect().x() + 50 + dx - 10, cell.rect().y() + 50 + dy - 10, 20, 20)
                        color_str = cell_data["circles"][i] if i < len(cell_data["circles"]) else "#ffffff"
                        circle.setBrush(QBrush(QColor(color_str)))
                        circle.setPen(QPen(Qt.black, 1))
                        circle.setZValue(1)
                        self.addItem(circle)
                        cell.inner_circles.append(circle)

                cell.value = cell_data["value"]
                cell.level = cell_data["level"]

                new_color = QColor(cell_data["color"])
                if cell.base_color != new_color:
                    cell.base_color = new_color
                    cell.set_gradient()

                    if new_color != Qt.gray:
                        if hasattr(cell, "top_text"):
                            self.removeItem(cell.top_text)
                            del cell.top_text
                        if hasattr(cell, "bottom_text"):
                            self.removeItem(cell.bottom_text)
                            del cell.bottom_text

                    if new_color != Qt.gray and cell.value_text is None:
                        value_text = QGraphicsTextItem(str(cell.value))
                        value_text.setFont(QFont("Arial", 14, QFont.Bold))
                        value_text.setDefaultTextColor(Qt.white)
                        value_text.setPos(
                            cell.rect().x() + 50 - value_text.boundingRect().width() / 2,
                            cell.rect().y() + 50 - value_text.boundingRect().height() / 2
                        )
                        self.addItem(value_text)
                        cell.set_value_text(value_text)

                if cell.value_text:
                    cell.value_text.setPlainText(str(cell.value))

                cell.update_level_display()

                new_color = QColor(cell_data["color"])
                if cell.base_color != new_color:
                    cell.base_color = new_color
                    cell.set_gradient()

                if cell.base_color == Qt.gray and "top_value" in cell_data:
                    cell._actual_top_value = cell_data["top_value"]
                    cell.top_text.setPlainText(str(abs(cell._actual_top_value)))

        for item in self.items():
            if isinstance(item, QGraphicsLineItem):
                self.removeItem(item)
            if isinstance(item, QGraphicsEllipseItem) and item in [mc[0] for mc in self.mini_cells]:
                self.removeItem(item)
        self.line_map = []
        self.mini_cells = []

        for line_data in step_data.get("lines", []):
            start = QPointF(line_data["start_x"] + 50, line_data["start_y"] + 50)
            end = QPointF(line_data["end_x"] + 50, line_data["end_y"] + 50)
            color = QColor(line_data["color"])

            line_item = QGraphicsLineItem(QLineF(start, end))
            line_item.setPen(QPen(color, 8))
            line_item.setZValue(-1)
            self.addItem(line_item)
            self.line_map.append((line_item, start, end, color))

            mini = QGraphicsEllipseItem(-5, -5, 10, 10)
            if color.name().lower() == "#d8177e":
                mini_color = QColor("#7D1B4F")
            elif color.name().lower() == "#66c676":
                mini_color = QColor("#186527")
            else:
                mini_color = QColor("#FFFFFF")  # domyślny (biały) w razie czego

            mini.setBrush(QBrush(mini_color))
            mini.setPen(QPen(mini_color))

            mini.setZValue(1)
            mini.setPos(start)
            self.addItem(mini)
            self.mini_cells.append((mini, end))

        if self.mini_cells:
            self.mini_timer.start(30)
        else:
            self.mini_timer.stop()

        turn = step_data.get("turn", "")
        self.turn_display.setPlainText(f"Tura: {turn.capitalize()}" if turn else "")

        timer = step_data.get("timer", "")
        self.timer_display.setPlainText(f"Czas: {timer}s" if timer else "")


    def animate_mini_cells(self):
        finished = []
        for i, (mini, target) in enumerate(self.mini_cells):
            current = mini.pos()
            direction = target - current
            step = direction / 10.0
            mini.setPos(current + step)
            if (current - target).manhattanLength() < 5:
                self.removeItem(mini)
                finished.append(i)
        self.mini_cells = [mc for j, mc in enumerate(self.mini_cells) if j not in finished]
        if not self.mini_cells:
            self.mini_timer.stop()


class ReplayView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Replay [XML]")
        self.setFixedSize(900, 900)
        self.scene_obj = ReplayScene()
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.Antialiasing)

        self.button = QPushButton("Start", self)
        self.button.setGeometry(370, 20, 160, 40)
        self.button.setStyleSheet("background-color: #333; color: white; font-weight: bold;")
        self.button.clicked.connect(self.start_replay)

        self.replay_button = QPushButton("REPLAY", self)
        self.replay_button.setGeometry(370, 70, 160, 40)
        self.replay_button.setStyleSheet("background-color: #333; color: white; font-weight: bold;")
        self.replay_button.clicked.connect(self.replay)

        self.speed_slider = QSlider(Qt.Horizontal, self)
        self.speed_slider.setGeometry(370, 120, 160, 20)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(5)
        self.speed_slider.setValue(1)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setStyleSheet("background-color: #555;")
        self.speed_slider.valueChanged.connect(self.update_speed)

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_step)

        self.update_speed()

    def start_replay(self):
        print("▶️ Rozpoczynam odtwarzanie")
        self.scene_obj.current_step = 0
        self.scene_obj.apply_step(self.scene_obj.steps[0])
        self.timer.start()
        self.button.setEnabled(False)

    def next_step(self):
        self.scene_obj.current_step += 1
        if self.scene_obj.current_step >= len(self.scene_obj.steps):
            print("⏹️ Koniec odtwarzania")
            self.timer.stop()
            self.button.setEnabled(True)
            return
        self.scene_obj.apply_step(self.scene_obj.steps[self.scene_obj.current_step])

    
    def replay(self):
        self.timer.stop()
        self.scene_obj = ReplayScene()  
        self.setScene(self.scene_obj) 
        self.scene_obj.current_step = 0
        if self.scene_obj.steps:
            self.scene_obj.apply_step(self.scene_obj.steps[0])
        self.button.setEnabled(True)

    def update_speed(self):
        speed = self.speed_slider.value()
        interval = int(1000 / speed)
        self.timer.setInterval(interval)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = ReplayView()
    view.show()
    sys.exit(app.exec_())
