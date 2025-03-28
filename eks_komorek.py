import sys
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QMenu, QAction, QPushButton, QGraphicsRectItem, QGraphicsPixmapItem, QLabel
from PyQt5.QtGui import QBrush, QPen, QLinearGradient, QRadialGradient, QColor, QPainter, QFont, QTransform, QPixmap
from PyQt5.QtCore import Qt, QRectF, QLineF, QPointF, QTimer

# Import zasobów z pliku resources.py
import resources

class ClickableLine(QGraphicsLineItem):
    def __init__(self, line, start_cell, end_cell=None, parent=None):
        super().__init__(line, parent)
        color = "#D8177E" if start_cell.base_color == QColor("#D8177E") else "#66C676"
        self.setPen(QPen(QColor(color), 8))
        self.setZValue(-1)  # Linia jest pod komórkami
        self.start_cell = start_cell
        self.end_cell = end_cell
        self.mini_cells = []  # Przechowuje referencje do mini kółek
 
    def update_position(self):
        if self.start_cell and self.end_cell:
            start_pos = self.start_cell.scenePos() + self.start_cell.rect().center()
            end_pos = self.end_cell.scenePos() + self.end_cell.rect().center()
            print(f"Aktualizacja linii: start_pos={start_pos}, end_pos={end_pos}")  # Debugowanie
            self.setLine(QLineF(start_pos, end_pos))
        else:
            print("Brak start_cell lub end_cell w linii")  # Debugowanie

    def mousePressEvent(self, event):
        # Oblicz odległość od początku linii do punktu kliknięcia
        clicked_pos = event.scenePos()
        start_pos = self.line().p1()
        distance = QLineF(start_pos, clicked_pos).length()
        value_to_add = int(distance // 50)  # Zaokrąglij w dół do części całkowitych

        # Dodaj obliczoną wartość do komórki początkowej
        if self.start_cell:
            self.start_cell.update_value(value_to_add)

        # Zmiana jednego z wewnętrznych kółek z powrotem na białe
        for circle in self.start_cell.inner_circles:
            if circle.brush().color() == Qt.black:
                circle.setBrush(QBrush(Qt.white))
                break

        # Usuń linię ze sceny
        self.scene().removeItem(self)
        super().mousePressEvent(event)


class ClickableCell(QGraphicsEllipseItem):
    selected_green = None  # Przechowuje referencję do wybranej zielonej komórki
    is_creating_line = False  # Flaga informująca, czy trwa tworzenie linii
    moving_cell = None  # Przechowuje referencję do komórki w trybie przesuwania

    def __init__(self, rect, color, value, parent=None):
        super().__init__(rect, parent)
        self.base_color = QColor(color) if isinstance(color, str) else QColor(color)
        self.value = value
        self.set_gradient()
        self.setPen(QPen(Qt.black, 2))
        self.setAcceptHoverEvents(True)  # Włącz zdarzenia hover dla komórki
        self.is_selected = False
        self.inner_circles = []  # Przechowuje referencje do wewnętrznych kółek
        self.value_text = None  # Referencja do tekstu wyświetlającego wartość
    
    def set_gradient(self):
        if self.base_color == Qt.gray:
            gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
            if hasattr(self, 'fill_color'):
                fill_ratio = min(self.value / 8, 1)  # Calculate the ratio of fill color
                gradient.setColorAt(0, self.fill_color.lighter(150))  # Lighter fill center
                gradient.setColorAt(fill_ratio, self.fill_color.darker(150))  # Darker fill edge
                gradient.setColorAt(fill_ratio, self.base_color)  # Transition to gray
            gradient.setColorAt(1, self.base_color)  # Gray edge
            self.setBrush(QBrush(gradient))
        else:
            # Załaduj obrazek z zasobów
            if self.base_color == QColor("#66C676"):
                pixmap = QPixmap(":/images/green_cell.png")
            elif self.base_color == QColor("#D8177E"):
                pixmap = QPixmap(":/images/pink_cell.png")
            else:
                pixmap = QPixmap()
            
            # Przeskaluj obrazek do rozmiaru komórki
            if not pixmap.isNull():
                pixmap = pixmap.scaled(self.rect().size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Utwórz QBrush z obrazkiem i przesunięciem
                brush = QBrush(pixmap)
                
                # Oblicz przesunięcie, aby środek obrazka był na środku kółka
                offset_x = 50
                offset_y = 50
                
                # Ustaw przesunięcie
                brush.setTransform(QTransform().translate(offset_x, offset_y))
                
                self.setBrush(brush)
            else:
                gradient = QRadialGradient(self.rect().center(), self.rect().width() / 2)
                gradient.setColorAt(0, self.base_color.lighter(150))  # Lighter center
                gradient.setColorAt(1, self.base_color.darker(150))  # Darker edge
                self.setBrush(QBrush(gradient))
    
    def set_value_text(self, text_item):
        self.value_text = text_item
    
    def update_value(self, delta, fill_color=None):
        self.value += delta
        if self.value > 30:
            self.value = 30
        if self.value_text:
            self.value_text.setPlainText(str(self.value))
        if self.base_color == QColor("#D8177E") and self.value <= 0:
            self.convert_to_green()
        if self.base_color == Qt.gray:
            if fill_color:
                self.fill_color = fill_color
            self.set_gradient()  # Update gradient for gray cells
            if self.value >= 8 and self.fill_color == QColor("#D8177E"):
                self.convert_to_pink()
    
    def set_top_text(self, text_item):
        self.top_text = text_item

    def update_top_text(self, delta):
        if hasattr(self, 'top_text'):
            current_value = int(self.top_text.toPlainText())
            new_value = current_value + delta
            self.top_text.setPlainText(str(new_value))
    
    def convert_to_green(self):
        # Zmień kolor na zielony
        self.base_color = QColor("#66C676")
        self.set_gradient()
        
        # Ustaw wartość na 20
        self.value = 20
        if self.value_text:
            self.value_text.setPlainText("20")
        else:
            # Dodaj tekst wyświetlający wartość, jeśli go nie ma
            text_item = QGraphicsTextItem("20")
            text_item.setFont(QFont("Arial", 14, QFont.Bold))
            text_item.setDefaultTextColor(Qt.white)
            text_rect = text_item.boundingRect()
            text_item.setPos(
                self.rect().x() + 50 - text_rect.width() / 2,
                self.rect().y() + 50 - text_rect.height() / 2
            )
            self.scene().addItem(text_item)
            self.set_value_text(text_item)
        
        # Usuń liczby z szarej komórki
        if hasattr(self, 'top_text'):
            self.scene().removeItem(self.top_text)
            del self.top_text
        
        if hasattr(self, 'bottom_text'):
            self.scene().removeItem(self.bottom_text)
            del self.bottom_text
        
        # Dodaj dwa wewnętrzne kółka (jeśli ich nie ma)
        if not self.inner_circles:
            for dx, dy in [(-20, -20), (20, 20)]:
                inner_circle = QGraphicsEllipseItem(self.rect().x() + 50 + dx - 10, self.rect().y() + 50 + dy - 10, 20, 20)
                inner_circle.setBrush(QBrush(Qt.white))
                inner_circle.setPen(QPen(Qt.black, 1))
                inner_circle.setZValue(1)  # Kółka są na wierzchu komórek
                self.scene().addItem(inner_circle)
                self.inner_circles.append(inner_circle)
    
    def convert_to_pink(self):
        # Zmień kolor na różowy
        self.base_color = QColor("#D8177E")
        self.set_gradient()
        
        # Ustaw wartość na 20
        self.value = 20
        if self.value_text:
            self.value_text.setPlainText("20")
        else:
            # Dodaj tekst wyświetlający wartość, jeśli go nie ma
            text_item = QGraphicsTextItem("20")
            text_item.setFont(QFont("Arial", 14, QFont.Bold))
            text_item.setDefaultTextColor(Qt.white)
            text_rect = text_item.boundingRect()
            text_item.setPos(
                self.rect().x() + 50 - text_rect.width() / 2,
                self.rect().y() + 50 - text_rect.height() / 2
            )
            self.scene().addItem(text_item)
            self.set_value_text(text_item)
        
        # Usuń liczby z szarej komórki
        if hasattr(self, 'top_text'):
            self.scene().removeItem(self.top_text)
            del self.top_text
        
        if hasattr(self, 'bottom_text'):
            self.scene().removeItem(self.bottom_text)
            del self.bottom_text
        
        # Dodaj dwa wewnętrzne kółka (jeśli ich nie ma)
        if not self.inner_circles:
            for dx, dy in [(-20, -20), (20, 20)]:
                inner_circle = QGraphicsEllipseItem(self.rect().x() + 50 + dx - 10, self.rect().y() + 50 + dy - 10, 20, 20)
                inner_circle.setBrush(QBrush(QBrush(Qt.white)))
                inner_circle.setPen(QPen(Qt.black, 1))
                inner_circle.setZValue(1)  # Kółka są na wierzchu komórek
                self.scene().addItem(inner_circle)
                self.inner_circles.append(inner_circle)

    def mousePressEvent(self, event):
        if ClickableCell.moving_cell:
            # Usuń pomarańczową obwódkę z poprzedniej komórki
            ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))
            self.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))
            ClickableCell.moving_cell = self
            return

        if self.base_color == QColor("#66C676") or self.base_color == QColor("#D8177E"):  # Zielona lub różowa komórka
            if all(circle.brush().color() == Qt.black for circle in self.inner_circles):
                print("Oba wewnętrzne kółka są czarne, nie można wybrać komórki.")  # Debugowanie
                return
            
            if ClickableCell.is_creating_line:
                if ClickableCell.selected_green and ClickableCell.selected_green != self:
                    print(f"Tworzenie linii z1 {ClickableCell.selected_green.base_color.name()} do {self.base_color.name()}")  # Debugowanie
                    start_pos = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
                    end_pos = self.scenePos() + self.rect().center()
                    line_length = QLineF(start_pos, end_pos).length()
                    cost = int(line_length // 50)
                    print(f"Koszt stworzenia linii: {cost}, długość linii: {line_length}")  # Debugowanie

                    if cost > ClickableCell.selected_green.value:
                        print("Koszt stworzenia linii przekracza wartość komórki, linia nie może zostać utworzona.")  # Debugowanie
                        return

                    line = ClickableLine(QLineF(start_pos, end_pos), ClickableCell.selected_green, self)
                    self.scene().addItem(line)
                    
                    # Oblicz koszt stworzenia mostu dla wszystkich komórek
                    ClickableCell.selected_green.update_value(-cost)
                    
                    ClickableCell.selected_green.setPen(QPen(Qt.black, 2))
                    self.setPen(QPen(Qt.black, 2))
                    
                    for circle in ClickableCell.selected_green.inner_circles:
                        if circle.brush().color() != Qt.black:
                            circle.setBrush(QBrush(Qt.black))
                            break
                    
                    ClickableCell.selected_green = None
                    ClickableCell.is_creating_line = False
            else:
                print(f"Rozpoczęcie tworzenia linii z {self.base_color.name()}")  # Debugowanie
                self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
                ClickableCell.selected_green = self
                ClickableCell.is_creating_line = True

        elif self.base_color == Qt.gray and ClickableCell.selected_green:  # Szara komórka
            print(f"Tworzenie linii z2 {ClickableCell.selected_green.base_color.name()} do szarej komórki")  # Debugowanie
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                print("Oba wewnętrzne kółka w komórce startowej są czarne, nie można stworzyć linii.")  # Debugowanie
                return

            start_pos = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
            end_pos = self.scenePos() + self.rect().center()
            line_length = QLineF(start_pos, end_pos).length()
            cost = int(line_length // 50)
            print(f"Koszt stworzenia linii: {cost}, długość linii: {line_length}")  # Debugowanie

            if cost > ClickableCell.selected_green.value:
                print("Koszt stworzenia linii przekracza wartość komórki, linia nie może zostać utworzona.")  # Debugowanie
                return

            ClickableCell.selected_green.setPen(QPen(Qt.black, 2))
            line = ClickableLine(QLineF(start_pos, end_pos), ClickableCell.selected_green, self)
            self.scene().addItem(line)
            self.setPen(QPen(Qt.black, 2))
            ClickableCell.selected_green.update_value(-cost)

            for circle in ClickableCell.selected_green.inner_circles:
                if circle.brush().color() != Qt.black:
                    circle.setBrush(QBrush(Qt.black))
                    break

            ClickableCell.selected_green = None
            ClickableCell.is_creating_line = False

        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if self.base_color == QColor("#66C676") and ClickableCell.is_creating_line:
            self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
        elif (self.base_color == Qt.gray or self.base_color == QColor("#D8177E")) and ClickableCell.selected_green:
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                return  # Nie zmieniaj obwódki, jeśli oba kółka są czarne
            self.setPen(QPen(QColor("#A4DEFA"), 8, Qt.SolidLine))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if self.base_color == QColor("#66C676") and ClickableCell.is_creating_line:
            self.setPen(QPen(Qt.black, 2))
        elif (self.base_color == Qt.gray or self.base_color == QColor("#D8177E")) and ClickableCell.selected_green:
            self.setPen(QPen(Qt.black, 2))
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        menu = QMenu()
        move_cell_action = menu.addAction("Przesuń komórkę")
        resize_cell_action = menu.addAction("Zmień rozmiar komórek")
        
        action = menu.exec_(event.screenPos())
        if action == move_cell_action:
            view = self.scene().views()[0]
            view.display_message("TRYB PRZESUWANIA KOMÓRKI (OBSŁUGA STRZAŁKAMI NA KLAWIATURZE)")
            if ClickableCell.moving_cell:
                ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  # Usuń pomarańczową obwódkę z poprzedniej komórki
            self.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))  # Pomarańczowa obwódka
            ClickableCell.moving_cell = self  # Ustaw referencję do komórki w trybie przesuwania
        elif action == resize_cell_action:
            print("Zwiększ rozmiar komórki")

    def keyPressEvent(self, event):
        if ClickableCell.moving_cell:
            dx, dy = 0, 0
            if event.key() == Qt.Key_Left:
                dx = -5
            elif event.key() == Qt.Key_Right:
                dx = 5
            elif event.key() == Qt.Key_Up:
                dy = -5
            elif event.key() == Qt.Key_Down:
                dy = 5

            if dx != 0 or dy != 0:
                ClickableCell.moving_cell.moveBy(dx, dy)
                for circle in ClickableCell.moving_cell.inner_circles:
                    circle.moveBy(dx, dy)
                if ClickableCell.moving_cell.value_text:
                    ClickableCell.moving_cell.value_text.moveBy(dx, dy)
                if hasattr(ClickableCell.moving_cell, 'top_text'):
                    ClickableCell.moving_cell.top_text.moveBy(dx, dy)
                if hasattr(ClickableCell.moving_cell, 'bottom_text'):
                    ClickableCell.moving_cell.bottom_text.moveBy(dx, dy)
                
                # Wyświetl globalne współrzędne komórki
                global_pos = ClickableCell.moving_cell.scenePos() + ClickableCell.moving_cell.rect().center()
                print(f"Przesunięto komórkę: global_pos={global_pos}")  # Debugowanie
                self.scene().update_lines()  # Dodaj tę linię, aby zaktualizować linie

    def update_lines(self):
            print("Aktualizacja linii w scenie...")  # Debugowanie
            for item in self.items():
                if isinstance(item, ClickableLine):
                    print(f"Znaleziono linię: {item}")  # Debugowanie
                    item.update_position()  # Wywołaj update_position dla każdej linii

    
class GameScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 900, 900)
        self.init_background()
        self.create_cells()
        self.line = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.move_mini_cells)
        self.timer.start(30)  # Timer co 100 ms
        self.value_timer = QTimer()
        self.value_timer.timeout.connect(self.increase_cell_values)
        self.value_timer.start(1000)  # Timer co 1000 ms (1 sekunda)
        self.create_menu_button()  # Add this line to create the menu button
        self.create_restart_button()  # Add this line to create the restart button

    def init_background(self, color1=QColor(10, 10, 50), color2=QColor(20, 20, 100)):
        gradient = QLinearGradient(0, 0, 900, 900)
        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)
        self.setBackgroundBrush(QBrush(gradient))

    def update_lines(self):
            print("Aktualizacja linii w scenie...")  # Debugowanie
            for item in self.items():
                if isinstance(item, ClickableLine):
                    print(f"Znaleziono linię: {item}")  # Debugowanie
                    item.update_position()  # Wywołaj update_position dla każdej linii


    def create_cells(self):
        self.cells = []
        cell_positions = [
            (150, 650, "#66C676", 20),  # Zielona komórka
            (650, 150, "#D8177E", 20),  # Różowa komórka
            (250, 250, QColor(Qt.gray), 0),  # Szara komórka (wartość 0, ale nie używana)
            (550, 550, QColor(Qt.gray), 0),  # Szara komórka (wartość 0, ale nie używana)
        ]
        
        for x, y, color, value in cell_positions:
            cell_rect = QRectF(x, y, 100, 100)
            cell = ClickableCell(cell_rect, color, value)
            self.cells.append(cell)
            
            # Dodanie szarej komórki przed napisami
            if (color == QColor(Qt.gray)):
                self.addItem(cell)
            
            # Dodanie tekstu do komórki (jeśli nie jest szara)
            if color != QColor(Qt.gray):
                text_item = QGraphicsTextItem(str(value))
                text_item.setFont(QFont("Arial", 14, QFont.Bold))
                text_item.setDefaultTextColor(Qt.white)
                text_rect = text_item.boundingRect()
                text_item.setPos(
                    x + 50 - text_rect.width() / 2,
                    y + 50 - text_rect.height() / 2
                )
                self.addItem(cell)
                self.addItem(text_item)
                cell.set_value_text(text_item)
            
            # Dodanie dwóch małych kółek na komórce, jeśli nie jest szara
            if color != QColor(Qt.gray):
                for dx, dy in [(-20, -20), (20, 20)]:
                    inner_circle = QGraphicsEllipseItem(x + 50 + dx - 10, y + 50 + dy - 10, 20, 20)
                    inner_circle.setBrush(QBrush(Qt.white))
                    inner_circle.setPen(QPen(Qt.black, 1))
                    inner_circle.setZValue(1)  # Kółka są na wierzchu komórek
                    self.addItem(inner_circle)
                    cell.inner_circles.append(inner_circle)
            
            # Dodanie dwóch liczb na szarej komórce (0 u góry i 8 na dole)
            if color == QColor(Qt.gray):
                # Liczba u góry (0)
                top_text = QGraphicsTextItem("0")
                top_text.setFont(QFont("Arial", 14, QFont.Bold))
                top_text.setDefaultTextColor(Qt.white)
                top_text_rect = top_text.boundingRect()
                top_text.setPos(
                    x + 50 - top_text_rect.width() / 2,  # Wyśrodkowanie poziome
                    y + 10  # U góry komórki
                )
                self.addItem(top_text)
                cell.set_top_text(top_text)  # Set reference to top text
                
                # Liczba na dole (8)
                bottom_text = QGraphicsTextItem("8")
                bottom_text.setFont(QFont("Arial", 14, QFont.Bold))
                bottom_text.setDefaultTextColor(Qt.white)
                bottom_text_rect = bottom_text.boundingRect()
                bottom_text.setPos(
                    x + 50 - bottom_text_rect.width() / 2,  # Wyśrodkowanie poziome
                    y + 55  # Na dole komórki
                )
                self.addItem(bottom_text)
                cell.bottom_text = bottom_text  # Set reference to bottom text
        
    
    def mouseMoveEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if ClickableCell.selected_green and ClickableCell.is_creating_line:
            if all(circle.brush().color() == Qt.black for circle in ClickableCell.selected_green.inner_circles):
                return  # Nie twórz linii, jeśli oba kółka są czarne
            
            if not self.line:
                self.line = QGraphicsLineItem()
                color = "#D8177E" if ClickableCell.selected_green.base_color == QColor("#D8177E") else "#66C676"
                self.line.setPen(QPen(QColor(color), 8))
                self.addItem(self.line)
                self.line.setZValue(-1)  # Linia jest pod komórkami
            
            # Użyj globalnych współrzędnych
            start_point = ClickableCell.selected_green.scenePos() + ClickableCell.selected_green.rect().center()
            end_point = event.scenePos()
            self.line.setLine(QLineF(start_point, end_point)) 
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if ClickableCell.moving_cell:
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        if self.line:
            self.removeItem(self.line)
            self.line = None
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        if ClickableCell.moving_cell:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, ClickableCell):
                ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  # Usuń pomarańczową obwódkę z poprzedniej komórki
                item.setPen(QPen(QColor("#FFA500"), 8, Qt.SolidLine))  # Pomarańczowa obwódka
                ClickableCell.moving_cell = item  # Ustaw nową referencję do komórki w trybie przesuwania
            return  # Wyłącz pozostałą funkcjonalność, gdy tryb przesuwania jest włączony
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, ClickableLine):
            item.mousePressEvent(event)
        elif not isinstance(item, ClickableCell) and ClickableCell.selected_green:
            ClickableCell.selected_green.setPen(QPen(Qt.black, 2))  # Usunięcie obwódki z zielonego
            ClickableCell.selected_green = None  # Reset wyboru zielonego
            ClickableCell.is_creating_line = False  # Zakończ tworzenie linii
            if self.line:
                self.removeItem(self.line)
                self.line = None
        super().mousePressEvent(event)

    def move_mini_cells(self):
        for item in self.items():
            if isinstance(item, ClickableLine):
                if not item.mini_cells:
                    # Utwórz nowe mini kółko
                    color = "#7D1B4F" if item.start_cell.base_color == QColor("#D8177E") else "#186527"
                    mini_cell = QGraphicsEllipseItem(-5, -5, 10, 10, item)
                    mini_cell.setBrush(QBrush(QColor(color)))  # Nowy kolor
                    mini_cell.setPen(QPen(QColor(color), 1))  # Nowy kolor
                    mini_cell.setPos(item.line().p1())
                    mini_cell.setZValue(1)  # Upewnij się, że kółko jest nad linią
                    item.mini_cells.append(mini_cell)
                    print("Utworzono nowe mini kółko")  # Debugowanie
                for mini_cell in item.mini_cells:
                    # Przesuń mini kółko wzdłuż linii
                    current_pos = mini_cell.pos()
                    end_pos = item.line().p2()
                    direction = end_pos - current_pos
                    step = direction / 10  # Mały krok
                    mini_cell.setPos(current_pos + step)
                    if (current_pos - end_pos).manhattanLength() < 5:
                        # Usuń mini kółko, gdy dotrze do końca
                        self.removeItem(mini_cell)
                        item.mini_cells.remove(mini_cell)
                        print("Usunięto mini kółko")  # Debugowanie

                        # Znajdź komórkę, do której dotarło mini kółko
                        for cell in self.cells:
                            if cell.rect().contains(end_pos):
                                if cell.base_color == Qt.gray:
                                    # Zwiększ lub zmniejsz wartość na szarej komórce
                                    fill_color = QColor("#66C676") if item.start_cell.base_color == QColor("#66C676") else QColor("#D8177E")
                                    if hasattr(cell, 'fill_color'):
                                        if cell.fill_color != fill_color:
                                            cell.update_value(-1, cell.fill_color)
                                            cell.update_top_text(-1)  # Decrease the top text value
                                        else:
                                            cell.update_value(1, fill_color)
                                            cell.update_top_text(1)  # Increase the top text value
                                    else:
                                        cell.update_value(1, fill_color)
                                        cell.update_top_text(1)  # Increase the top text value
                                    
                                    # Sprawdź, czy górna liczba jest równa dolnej liczbie
                                    if hasattr(cell, 'top_text') and int(cell.top_text.toPlainText()) == 8 and fill_color == QColor("#66C676"):
                                        cell.convert_to_green()  # Zamień szarą komórkę na zieloną
                                    elif hasattr(cell, 'top_text') and int(cell.top_text.toPlainText()) == 8 and fill_color == QColor("#D8177E"):
                                        cell.convert_to_pink()  # Zamień szarą komórkę na różową
                                elif cell.base_color == QColor("#D8177E"):
                                    # Zmniejsz wartość na różowej komórce
                                    cell.update_value(-1)
                                elif cell.base_color == QColor("#66C676") and cell != item.start_cell:
                                    # Decrease value on the green cell
                                    cell.update_value(-1)
                                break

                        # Decrease value on the starting green cell
                        item.start_cell.update_value(-1)

    def increase_cell_values(self):
        for cell in self.cells:
            if cell.base_color == QColor("#66C676"):  # Zielona komórka
                cell.update_value(1)
            elif cell.base_color == QColor("#D8177E"):  # Różowa komórka
                cell.update_value(1)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, ClickableCell):
            item.contextMenuEvent(event)
        else:
            menu = QMenu()
            change_background_menu = menu.addMenu("Zmień tło")

            current_action = QAction("Obecne", self)
            current_action.setCheckable(True)
            current_action.setChecked(True)
            change_background_menu.addAction(current_action)

            orange_action = QAction("Pomarańczowe", self)
            orange_action.setCheckable(True)
            change_background_menu.addAction(orange_action)

            red_action = QAction("Czerwone", self)
            red_action.setCheckable(True)
            change_background_menu.addAction(red_action)

            beige_action = QAction("Beżowe", self)
            beige_action.setCheckable(True)
            change_background_menu.addAction(beige_action)

            action = menu.exec_(event.screenPos())
            if action == current_action:
                self.init_background(QColor(10, 10, 50), QColor(20, 20, 100))
            elif action == orange_action:
                self.init_background(QColor(255, 165, 0), QColor(255, 140, 0))
            elif action == red_action:
                self.init_background(QColor(255, 0, 0), QColor(139, 0, 0))
            elif action == beige_action:
                self.init_background(QColor(245, 245, 220), QColor(222, 184, 135))

    def create_menu_button(self):
        menu_button = HoverableRectItem(350, 20, 200, 40)
        menu_button.setBrush(QBrush(QColor(10, 10, 50)))
        menu_button.setPen(QPen(Qt.white, 2))
        self.addItem(menu_button)

        menu_text = QGraphicsTextItem("MENU", menu_button)
        menu_text.setFont(QFont("Arial", 20))
        menu_text.setDefaultTextColor(Qt.white)
        menu_text_rect = menu_text.boundingRect()
        menu_text.setPos(
            menu_button.rect().center().x() - menu_text_rect.width() / 2,
            menu_button.rect().center().y() - menu_text_rect.height() / 2
        )

        menu_button.mousePressEvent = self.back_to_main_menu

    def create_restart_button(self):
        restart_button = HoverableRectItem(400, 70, 100, 30)
        restart_button.setBrush(QBrush(QColor(10, 10, 50)))
        restart_button.setPen(QPen(Qt.white, 2))
        self.addItem(restart_button)

        restart_text = QGraphicsTextItem("RESTART", restart_button)
        restart_text.setFont(QFont("Arial", 10))
        restart_text.setDefaultTextColor(Qt.white)
        restart_text_rect = restart_text.boundingRect()
        restart_text.setPos(
            restart_button.rect().center().x() - restart_text_rect.width() / 2,
            restart_button.rect().center().y() - restart_text_rect.height() / 2
        )

        restart_button.mousePressEvent = self.restart_game

    def restart_game(self, event):
        self.clear()  # Clear the scene
        self.init_background()  # Reinitialize the background
        self.create_cells()  # Recreate the cells
        self.create_menu_button()  # Recreate the menu button
        self.create_restart_button()  # Recreate the restart button
        self.timer.start(30)  # Restart the mini cell movement timer
        self.value_timer.start(1000)  # Restart the cell value increase timer

    def back_to_main_menu(self, event):
        view = self.views()[0]
        view.setScene(MainMenuScene())

class LevelSelectionScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 900, 900)
        self.init_background()
        self.create_level_selection_menu()

    def init_background(self, color1=QColor(10, 10, 50), color2=QColor(20, 20, 100)):
        gradient = QLinearGradient(0, 0, 900, 900)
        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)
        self.setBackgroundBrush(QBrush(gradient))

    def create_level_selection_menu(self):
        title = QGraphicsTextItem("WYBÓR POZIOMU")
        title.setFont(QFont("Arial", 30, QFont.Bold))
        title.setDefaultTextColor(Qt.white)
        title_rect = title.boundingRect()
        title.setPos(450 - title_rect.width() / 2, 100)
        self.addItem(title)

        levels = ["POZIOM 1", "POZIOM 2", "POZIOM 3", "POZIOM 4", "POZIOM 5"]
        for i, level in enumerate(levels):
            level_button = HoverableRectItem(250, 200 + i * 100, 400, 50)
            level_button.setBrush(QBrush(QColor(10, 10, 50)))
            level_button.setPen(QPen(Qt.white, 2))
            self.addItem(level_button)

            level_text = QGraphicsTextItem(level, level_button)
            level_text.setFont(QFont("Arial", 20, QFont.Bold))
            level_text.setDefaultTextColor(Qt.white)
            level_text_rect = level_text.boundingRect()
            level_text.setPos(
                level_button.rect().center().x() - level_text_rect.width() / 2,
                level_button.rect().center().y() - level_text_rect.height() / 2
            )

            level_button.mousePressEvent = lambda event, lvl=level: self.start_game(event, lvl)

        back_button = HoverableRectItem(100, 700, 700, 50)
        back_button.setBrush(QBrush(QColor(10, 10, 50)))
        back_button.setPen(QPen(Qt.white, 2))
        self.addItem(back_button)

        back_text = QGraphicsTextItem("POWRÓT DO MENU GŁÓWNEGO", back_button)
        back_text.setFont(QFont("Arial", 20, QFont.Bold))
        back_text.setDefaultTextColor(Qt.white)
        back_text_rect = back_text.boundingRect()
        back_text.setPos(
            back_button.rect().center().x() - back_text_rect.width() / 2,
            back_button.rect().center().y() - back_text_rect.height() / 2
        )

        back_button.mousePressEvent = self.back_to_main_menu

    def start_game(self, event, level):
        view = self.views()[0]
        view.setScene(GameScene())

    def back_to_main_menu(self, event):
        view = self.views()[0]
        view.setScene(MainMenuScene())

class MainMenuScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 900, 900)
        self.init_background()
        self.create_menu()

    def init_background(self, color1=QColor(10, 10, 50), color2=QColor(20, 20, 100)):
        gradient = QLinearGradient(0, 0, 900, 900)
        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)
        self.setBackgroundBrush(QBrush(gradient))

    def create_menu(self):
        title = QGraphicsTextItem("MENU")
        title.setFont(QFont("Arial", 30, QFont.Bold))
        title.setDefaultTextColor(Qt.white)
        title_rect = title.boundingRect()
        title.setPos(450 - title_rect.width() / 2, 200)
        self.addItem(title)

        play_button = HoverableRectItem(250, 300, 400, 100)
        play_button.setBrush(QBrush(QColor(10, 10, 50)))
        play_button.setPen(QPen(Qt.white, 2))
        self.addItem(play_button)

        play_text = QGraphicsTextItem("GRAJ", play_button)
        play_text.setFont(QFont("Arial", 20, QFont.Bold))
        play_text.setDefaultTextColor(Qt.white)
        play_text_rect = play_text.boundingRect()
        play_text.setPos(
            play_button.rect().center().x() - play_text_rect.width() / 2,
            play_button.rect().center().y() - play_text_rect.height() / 2
        )

        level_button = HoverableRectItem(250, 450, 400, 100)
        level_button.setBrush(QBrush(QColor(10, 10, 50)))
        level_button.setPen(QPen(Qt.white, 2))
        self.addItem(level_button)

        level_text = QGraphicsTextItem("WYBIERZ POZIOM", level_button)
        level_text.setFont(QFont("Arial", 20, QFont.Bold))
        level_text.setDefaultTextColor(Qt.white)
        level_text_rect = level_text.boundingRect()
        level_text.setPos(
            level_button.rect().center().x() - level_text_rect.width() / 2,
            level_button.rect().center().y() - level_text_rect.height() / 2
        )

        play_button.mousePressEvent = self.start_game
        level_button.mousePressEvent = self.show_level_selection

    def start_game(self, event):
        view = self.views()[0]
        view.setScene(GameScene())

    def show_level_selection(self, event):
        view = self.views()[0]
        view.setScene(LevelSelectionScene())

class HoverableRectItem(QGraphicsRectItem):
    def __init__(self, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.default_brush = QBrush(QColor(10, 10, 50))
        self.setBrush(self.default_brush)
        self.setAcceptHoverEvents(True)  # Enable hover events

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#001E5A")))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.default_brush)
        super().hoverLeaveEvent(event)

class GameView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(MainMenuScene())
        self.setRenderHint(QPainter.Antialiasing)
        self.setFixedSize(900, 900)
        self.message_label = QGraphicsTextItem("")
        self.message_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.message_label.setDefaultTextColor(Qt.white)
        self.message_label.setPos(150, 20)  # Position at the top center
        self.scene().addItem(self.message_label)
        
        # Create a QLabel for the moving mode message
        self.moving_mode_label = QLabel("Tryb przesuwania komórek. Obsługa strzałkami na klawiaturze. Kliknij \"ZAKOŃCZ\", aby wyjść z trybu.", self)
        self.moving_mode_label.setStyleSheet("color: white; background-color: rgba(10, 10, 50, 200); padding: 5px;")
        self.moving_mode_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.moving_mode_label.setGeometry(40, 760, 820, 30)  # Position above the "ZAKOŃCZ" button
        self.moving_mode_label.setAlignment(Qt.AlignCenter)
        self.moving_mode_label.hide()  # Initially hide the label

        self.end_button = QPushButton("ZAKOŃCZ", self)
        self.end_button.setGeometry(400, 800, 100, 40)  # Position and size of the button
        font = self.end_button.font()
        font.setBold(True)  # Pogrubienie czcionki
        font.setPointSize(9)  # Zwiększenie rozmiaru czcionki
        self.end_button.setFont(font)
        self.end_button.setStyleSheet("background-color: rgb(10, 10, 50); color: white;")  # Kolor tła i tekstu przycisku
        self.end_button.clicked.connect(self.hide_message)
        self.end_button.hide()  # Initially hide the button
        
        self.show()

    def display_message(self, message):
        self.message_label.setPlainText(message)
        self.end_button.show()  # Show the button when displaying the message
        self.moving_mode_label.show()  # Show the moving mode label

    def hide_message(self):
        self.message_label.setPlainText("")
        self.end_button.hide()  # Hide the button when the message is hidden
        self.moving_mode_label.hide()  # Hide the moving mode label
        if ClickableCell.moving_cell:
            ClickableCell.moving_cell.setPen(QPen(Qt.black, 2))  # Usuń pomarańczową obwódkę
            ClickableCell.moving_cell = None  # Reset komórki w trybie przesuwania

    def keyPressEvent(self, event):
        if ClickableCell.moving_cell:
            ClickableCell.moving_cell.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = GameView()
    sys.exit(app.exec_())