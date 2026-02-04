# from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QVBoxLayout, QWidget

# import sys


# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()

#         self.setWindowTitle("My App")

#         self.label = QLabel()

#         self.input = QLineEdit()
#         self.input.textChanged.connect(self.label.setText)

#         layout = QVBoxLayout()
#         layout.addWidget(self.input)
#         layout.addWidget(self.label)

#         container = QWidget()
#         container.setLayout(layout)

#         # Set the central widget of the Window.
#         self.setCentralWidget(container)


# app = QApplication(sys.argv)

# window = MainWindow()
# window.show()

# app.exec()

import sys
import random

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLineEdit, QPushButton, QLabel, QMenu
)
from PySide6.QtGui import QAction

# Matplotlib imports pro Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    """
    Vlastní widget pro graf, dědící od FigureCanvas.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Moje Diplomová Práce")
        self.resize(800, 600)

        # 1. SETUP CENTRAL WIDGETU A LAYOUTU
        # QMainWindow potřebuje "central widget", do kterého vkládáme layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Hlavní layout (Vertical)
        main_layout = QVBoxLayout(central_widget)

        # 2. MENU
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&Soubor") # &S znamená Alt+S zkratku
        
        # Vytvoření Action
        exit_action = QAction("Ukončit", self)
        exit_action.setStatusTip("Zavřít aplikaci")
        exit_action.triggered.connect(self.close) # Signal -> Slot
        file_menu.addAction(exit_action)

        # 3. MATPLOTLIB WIDGET
        # Vytvoříme instanci našeho plátna a přidáme do layoutu
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        main_layout.addWidget(self.canvas)

        # 4. OVLÁDACÍ PRVKY (TEXT INPUT + BUTTON)
        # Uděláme si menší horizontální layout pro ovládání dole
        controls_layout = QHBoxLayout()
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Zadejte počet bodů...")
        
        self.plot_button = QPushButton("Překreslit graf")
        self.plot_button.clicked.connect(self.update_plot) # Signal -> Slot

        # Přidání do horizontálního layoutu
        controls_layout.addWidget(QLabel("Data:"))
        controls_layout.addWidget(self.text_input)
        controls_layout.addWidget(self.plot_button)

        # Vložení controls layoutu do hlavního layoutu
        main_layout.addLayout(controls_layout)

        # Prvotní vykreslení
        self.update_plot()

    def update_plot(self):
        # Vyčistit starý graf (axes)
        self.canvas.axes.cla()
        
        # Získání dat (s ošetřením chyb)
        try:
            n_points = int(self.text_input.text())
        except ValueError:
            n_points = 10 # Default value
        
        data = [random.randint(0, 100) for _ in range(n_points)]
        
        # Vykreslení
        self.canvas.axes.plot(data, 'r-')
        self.canvas.axes.set_title(f"Náhodná data ({n_points} bodů)")
        
        # Trigger překreslení canvasu
        self.canvas.draw()

if __name__ == "__main__":
    # Vytvoření instance aplikace (Singleton)
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    # Spuštění Event Loop
    app.exec()