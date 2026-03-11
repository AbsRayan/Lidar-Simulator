import os
import sys
import yaml
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QWidget, QStackedWidget, QFileDialog, QMessageBox,
    QDoubleSpinBox, QLabel, QHBoxLayout, QGroupBox, QSpacerItem, QSizePolicy
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
        self.sim_layout = QHBoxLayout(self.sim_page)

        # Боковая панель управления
        self.control_panel_widget = QWidget()
        self.control_panel_widget.setFixedWidth(280)
        self.control_layout = QVBoxLayout(self.control_panel_widget)
        self.control_layout.setContentsMargins(0, 0, 0, 0)

        self.back_button = QPushButton("Назад")
        self.back_button.clicked.connect(self.show_menu)
        self.control_layout.addWidget(self.back_button)

        self.load_camera_button = QPushButton("Загрузить конфиг камеры")
        self.load_camera_button.clicked.connect(self.load_camera_config)
        self.control_layout.addWidget(self.load_camera_button)

        self.save_button = QPushButton("Сохранить параметры и кадр")
        self.save_button.clicked.connect(self.save_data)
        self.save_button.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        self.control_layout.addWidget(self.save_button)

        # Панель управления камерой
        self.camera_group = QGroupBox("Управление камерой (Позиция / Цель)")
        self.camera_layout = QVBoxLayout(self.camera_group)

        # Камера Позиция
        self.cam_pos_layout = QHBoxLayout()
        self.cam_pos_layout.addWidget(QLabel("Позиция:"))
        self.cam_pos_spins = []
        for i in range(3):
            spin = QDoubleSpinBox()
            spin.setRange(-100.0, 100.0)
            spin.setSingleStep(0.5)
            val = 8.0 if i == 2 else 0.0
            spin.setValue(val)
            spin.valueChanged.connect(self._update_camera_pos)
            self.cam_pos_spins.append(spin)
            self.cam_pos_layout.addWidget(spin)
        self.camera_layout.addLayout(self.cam_pos_layout)

        # Камера Цель
        self.cam_target_layout = QHBoxLayout()
        self.cam_target_layout.addWidget(QLabel("Цель:"))
        self.cam_target_spins = []
        for i in range(3):
            spin = QDoubleSpinBox()
            spin.setRange(-100.0, 100.0)
            spin.setSingleStep(0.5)
            spin.setValue(0.0)
            spin.valueChanged.connect(self._update_camera_target)
            self.cam_target_spins.append(spin)
            self.cam_target_layout.addWidget(spin)
        self.camera_layout.addLayout(self.cam_target_layout)
        
        self.control_layout.addWidget(self.camera_group)

        # Панель управления позициями объектов
        self.objects_group = QGroupBox("Позиции объектов (X, Y, Z)")
        self.objects_layout = QVBoxLayout(self.objects_group)
        
        # Шар
        self.sphere_layout = QHBoxLayout()
        self.sphere_layout.addWidget(QLabel("Шар:"))
        self.sphere_spins = []
        for i in range(3):
            spin = QDoubleSpinBox()
            spin.setRange(-100.0, 100.0)
            spin.setSingleStep(0.5)
            # Начальное значение из gl_widget по умолчанию [-2.0, 0.0, 0.0]
            val = -2.0 if i == 0 else 0.0
            spin.setValue(val)
            spin.valueChanged.connect(self._update_sphere_pos)
            self.sphere_spins.append(spin)
            self.sphere_layout.addWidget(spin)
        self.objects_layout.addLayout(self.sphere_layout)

        # Самолёт
        self.airplane_layout = QHBoxLayout()
        self.airplane_layout.addWidget(QLabel("Самолёт:"))
        self.airplane_spins = []
        for i in range(3):
            spin = QDoubleSpinBox()
            spin.setRange(-100.0, 100.0)
            spin.setSingleStep(0.5)
            # Начальное значение из gl_widget по умолчанию [2.0, 0.0, 0.0]
            val = 2.0 if i == 0 else 0.0
            spin.setValue(val)
            spin.valueChanged.connect(self._update_airplane_pos)
            self.airplane_spins.append(spin)
            self.airplane_layout.addWidget(spin)
        self.objects_layout.addLayout(self.airplane_layout)

        self.control_layout.addWidget(self.objects_group)
        self.control_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        self.sim_layout.addWidget(self.control_panel_widget)

        # Окно OpenGL занимает оставшееся место
        self.gl_scene = SceneGLWidget()
        self.sim_layout.addWidget(self.gl_scene, stretch=1)

        self.stacked_widget.addWidget(self.menu_page)
        self.stacked_widget.addWidget(self.sim_page)

        self._load_configs()

    def show_simulation(self):
        """Переключает интерфейс на окно симуляции"""
        self.stacked_widget.setCurrentWidget(self.sim_page)

    def show_menu(self):
        """Возвращает в главное меню"""
        self.stacked_widget.setCurrentWidget(self.menu_page)

    def _update_sphere_pos(self):
        """Обновление позиции шара"""
        if hasattr(self, 'gl_scene'):
            pos = [spin.value() for spin in self.sphere_spins]
            self.gl_scene.sphere_pos = pos
            self.gl_scene.update()

    def _update_airplane_pos(self):
        """Обновление позиции самолёта"""
        if hasattr(self, 'gl_scene'):
            pos = [spin.value() for spin in self.airplane_spins]
            self.gl_scene.airplane_pos = pos
            self.gl_scene.update()

    def _update_camera_pos(self):
        """Обновление позиции камеры"""
        if hasattr(self, 'gl_scene'):
            pos = [spin.value() for spin in self.cam_pos_spins]
            self.gl_scene.camera_pos = pos
            self.gl_scene.update()

    def _update_camera_target(self):
        """Обновление точки обзора камеры"""
        if hasattr(self, 'gl_scene'):
            target = [spin.value() for spin in self.cam_target_spins]
            self.gl_scene.camera_target = target
            self.gl_scene.update()

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

    def save_data(self):
        """Сохраняет изображение сцены и конфигурационный YAML файл"""
        if not hasattr(self, 'gl_scene'):
            return

        # Выбор каталога куда сохранять
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить параметры сцены",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_scene"),
            "PNG Image (*.png)"
        )
        if not save_path:
            return

        base_name = os.path.splitext(save_path)[0]
        png_path = f"{base_name}.png"
        yaml_path = f"{base_name}.yaml"

        try:
            # 1. Захват изображения из FBO (или всего виджета)
            img = self.gl_scene.grabFramebuffer()
            img.save(png_path)

            # 2. Формируем конфиг текущей сцены
            scene_data = {
                "camera": {
                    "fov": float(self.gl_scene.cam_fov),
                    "near": float(self.gl_scene.cam_near),
                    "far": float(self.gl_scene.cam_far),
                    "position": [float(x) for x in self.gl_scene.camera_pos],
                    "target": [float(x) for x in self.gl_scene.camera_target]
                },
                "objects": {
                    "sphere": {
                        "position": [float(x) for x in self.gl_scene.sphere_pos]
                    },
                    "airplane": {
                        "position": [float(x) for x in self.gl_scene.airplane_pos]
                    }
                }
            }

            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(scene_data, f, allow_unicode=True, default_flow_style=False)

            QMessageBox.information(self, "Успешно", f"Сохранено:\n{png_path}\n{yaml_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

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