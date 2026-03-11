import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QWidget, QStackedWidget, QFileDialog, QMessageBox
)
from gl_widget import SceneGLWidget
from config_loader import ConfigLoader


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

        self.load_camera_button = QPushButton("Загрузить конфиг камеры")
        self.load_camera_button.setFixedSize(250, 30)
        self.load_camera_button.clicked.connect(self.load_camera_config)
        self.sim_layout.addWidget(self.load_camera_button)

        self.gl_scene = SceneGLWidget()
        self.sim_layout.addWidget(self.gl_scene)

        self.stacked_widget.addWidget(self.menu_page)
        self.stacked_widget.addWidget(self.sim_page)

        self._load_configs()

    def show_simulation(self):
        """Переключает интерфейс на окно симуляции"""
        self.stacked_widget.setCurrentWidget(self.sim_page)

    def show_menu(self):
        """Возвращает в главное меню"""
        self.stacked_widget.setCurrentWidget(self.menu_page)

    def load_camera_config(self):
        """Открывает диалог выбора файла конфига камеры и применяет параметры к сцене"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл конфигурации камеры",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configs'),
            "Config files (*.yaml *.yml *.toml);;All files (*.*)"
        )
        if not path:
            return  # пользователь отменил диалог
        try:
            config = ConfigLoader.load(path)
            if config.get('type', '').lower() not in ('camera', ''):
                # Предупреждаем, но всё равно применяем — на случай конфига без поля type
                pass
            self.gl_scene.apply_camera_config(config)
            name = config.get('name', os.path.basename(path))
            QMessageBox.information(
                self,
                "Конфиг применён",
                f"Камера \«{name}\» загружена.\n"
                f"FOV: {self.gl_scene.cam_fov}°  "
                f"Near: {self.gl_scene.cam_near}  "
                f"Far: {self.gl_scene.cam_far}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", str(e))

    def _load_configs(self):
        """Загрузка конфигураций сенсоров"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(base_dir, 'configs', 'sensor.yaml')
        toml_path = os.path.join(base_dir, 'configs', 'sensor.toml')
        
        try:
            lidar_config = ConfigLoader.load(yaml_path)
            print(f"Loaded YAML config (LiDAR): {lidar_config}")
        except Exception as e:
            print(f"Error loading YAML config: {e}")
            
        try:
            camera_config = ConfigLoader.load(toml_path)
            print(f"Loaded TOML config (Camera): {camera_config}")
        except Exception as e:
            print(f"Error loading TOML config: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())