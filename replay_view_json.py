import sys
import json
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem, QPushButton, QSlider
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPainter
from PyQt5.QtCore import Qt, QRectF, QTimer, QPointF, QLineF
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
            with open("history.json") as f:
                data = json.load(f)
                for step in data["steps"]:
                    for cell in step.get("cells", []):
                        if "circles" in cell and isinstance(cell["circles"], str):
                            cell["circles"] = cell["circles"].split(",")
                self.steps = data["steps"]
        except Exception as e:
            print("Błąd odczytu JSON:", e)
            return

        if self.steps:
            self.init_cells(self.steps[0]["cells"])

    def init_cells(self, cells_data):
        for cell_data in cells_data:
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
                value_text.setPos(rect.x() + 50 - value_text.boundingRect().width() / 2,
                                  rect.y() + 50 - value_text.boundingRect().height() / 2)
                self.addItem(value_text)
                cell.set_value_text(value_text)

                circle_colors = cell_data.get("circles", ["#ffffff", "#ffffff"])
                for i, (dx, dy) in enumerate([(-20, -20), (20, 20)]):
                    circle = QGraphicsEllipseItem(rect.x() + 50 + dx - 10, rect.y() + 50 + dy - 10, 20, 20)
                    color_str = circle_colors[i] if i < len(circle_colors) else "#ffffff"
                    circle.setBrush(QBrush(QColor(color_str)))
                    circle.setPen(QPen(Qt.black, 1))
                    circle.setZValue(1)
                    self.addItem(circle)
                    cell.inner_circles.append(circle)
            else:
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
                    
                if new_color != Qt.gray:
                    if hasattr(cell, 'top_text'):
                        self.removeItem(cell.top_text)
                        del cell.top_text
                    if hasattr(cell, 'bottom_text'):
                        self.removeItem(cell.bottom_text)
                        del cell.bottom_text

                
                if new_color != Qt.gray:
                    if hasattr(cell, 'top_text'):
                        self.removeItem(cell.top_text)
                        del cell.top_text
                    if hasattr(cell, 'bottom_text'):
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

                
                if new_color == Qt.gray:
                    cell.base_color = new_color
                    cell.set_gradient()

                    if hasattr(cell, 'value_text') and cell.value_text:
                        self.removeItem(cell.value_text)
                        cell.value_text = None

                    if hasattr(cell, 'level_text') and cell.level_text:
                        self.removeItem(cell.level_text)
                        cell.level_text = None

                    if cell.inner_circles:
                        for circle in cell.inner_circles:
                            self.removeItem(circle)
                        cell.inner_circles = []

                    if hasattr(cell, 'top_text') and cell.top_text:
                        self.removeItem(cell.top_text)
                    if hasattr(cell, 'bottom_text') and cell.bottom_text:
                        self.removeItem(cell.bottom_text)

                    cell._actual_top_value = cell_data.get("top_value", 0)

                    top_text = QGraphicsTextItem(str(abs(cell._actual_top_value)))
                    top_text.setFont(QFont("Arial", 14, QFont.Bold))
                    top_text.setDefaultTextColor(Qt.white)
                    top_text.setPos(cell.rect().x() + 50 - top_text.boundingRect().width() / 2, cell.rect().y() + 10)
                    self.addItem(top_text)
                    cell.set_top_text(top_text)

                    bottom_text = QGraphicsTextItem("8")
                    bottom_text.setFont(QFont("Arial", 14, QFont.Bold))
                    bottom_text.setDefaultTextColor(Qt.white)
                    bottom_text.setPos(cell.rect().x() + 50 - bottom_text.boundingRect().width() / 2, cell.rect().y() + 55)
                    self.addItem(bottom_text)
                    cell.bottom_text = bottom_text

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
                mini_color = QColor("#FFFFFF")  

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
        self.setWindowTitle("Replay [JSON]")
        self.setFixedSize(900, 900)
        self.scene_obj = ReplayScene()
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.Antialiasing)

        self.button = QPushButton("Start", self)
        self.button.setGeometry(370, 20, 160, 40)
        self.button.setStyleSheet("background-color: #333; color: white; font-weight: bold;")
        self.button.clicked.connect(self.start_replay)

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_step)
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

        self.update_speed() 


    def start_replay(self):
        self.scene_obj.current_step = 0
        self.scene_obj.apply_step(self.scene_obj.steps[0])
        self.timer.start(1000)
        self.button.setEnabled(False)

    def next_step(self):
        self.scene_obj.current_step += 1
        if self.scene_obj.current_step >= len(self.scene_obj.steps):
            self.timer.stop()
            return
        step_data = self.scene_obj.steps[self.scene_obj.current_step]
        self.scene_obj.apply_step(step_data)


    def replay(self):
        self.timer.stop()
        self.scene_obj.current_step = 0
        self.scene_obj.apply_step(self.scene_obj.steps[0])
        self.button.setEnabled(True)

    def update_speed(self):
        speed = self.speed_slider.value()
        self.timer.setInterval(1000 // speed)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = ReplayView()
    view.show()
    sys.exit(app.exec_())
