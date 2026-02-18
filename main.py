import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QStackedWidget
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *

class SphereGLWidget(QOpenGLWidget):
    """Виджет для отрисовки 3D сцены с шаром"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.zoom = -5.0
        self.last_pos = None
        self.quadric = None

    def initializeGL(self):
        self.init_resources()

    def init_resources(self):
        """Инициализации ресурсов OpenGL"""
        if self.quadric is not None:
            gluDeleteQuadric(self.quadric)
            
        self.quadric = gluNewQuadric()
        
        glClearColor(0.1, 0.1, 0.1, 2.0)  # фон
        glEnable(GL_DEPTH_TEST)          # проверка глубины
        
        # освещение
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

    def resizeGL(self, w, h):
        """Вызывается при изменении размера окна"""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        """Основной цикл отрисовки"""
        if self.quadric is None:
            self.init_resources()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)

        glTranslatef(0.0, 0.0, self.zoom)

        glLightfv(GL_LIGHT0, GL_POSITION, (0, 10, 10, 1))

        glColor3f(0.0, 0.7, 1.0)
        gluSphere(self.quadric, 1.0, 32, 32)

    def cleanup(self):
        """Очистка ресурсов OpenGL при уничтожении контекста"""
        if self.quadric is not None:
            self.makeCurrent()
            gluDeleteQuadric(self.quadric)
            self.quadric = None
            self.doneCurrent()

    def hideEvent(self, event):
        """Вызывается при скрытии виджета"""
        self.cleanup()
        super().hideEvent(event)

    def mousePressEvent(self, event):
        self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        if self.last_pos is not None:
            diff = event.position() - self.last_pos
            
            self.rotation_x += diff.y() * 0.5
            self.rotation_y += diff.x() * 0.5
            
            self.last_pos = event.position()
            self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120
        self.zoom += delta * 0.5
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LiDAR Simulator")
        self.resize(800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)

        # Главное окно
        self.menu_page = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_page)
        self.start_button = QPushButton("Открыть симуляцию")
        self.start_button.setFixedSize(250, 50)
        self.start_button.clicked.connect(self.show_simulation)
        self.menu_layout.addWidget(self.start_button)
        
        # Окно симуляции
        self.sim_page = QWidget()
        self.sim_layout = QVBoxLayout(self.sim_page)
        
        self.back_button = QPushButton("Назад")
        self.back_button.setFixedSize(150, 30)
        self.back_button.clicked.connect(self.show_menu)
        self.sim_layout.addWidget(self.back_button)
        
        self.gl_scene = SphereGLWidget()
        self.sim_layout.addWidget(self.gl_scene)

        self.stacked_widget.addWidget(self.menu_page)
        self.stacked_widget.addWidget(self.sim_page)

    def show_simulation(self):
        """Переключает интерфейс на окно симуляции"""
        self.stacked_widget.setCurrentWidget(self.sim_page)

    def show_menu(self):
        """Возвращает в главное меню"""
        self.stacked_widget.setCurrentWidget(self.menu_page)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())