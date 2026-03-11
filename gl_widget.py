"""
OpenGL-виджет для отрисовки 3D сцены.
"""
import os
import ctypes

import numpy as np
import stl_loader
from PyQt6.QtGui import QImage
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GL import shaders as gl_shaders
from OpenGL.GLU import *


_SHADER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shaders')


def _load_shader_source(filename: str) -> str:
    path = os.path.join(_SHADER_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


VERTEX_SHADER_SRC = _load_shader_source('vertex.glsl')
FRAGMENT_SHADER_SRC = _load_shader_source('fragment.glsl')
MODEL_VERTEX_SHADER_SRC = _load_shader_source('model_vertex.glsl')
MODEL_FRAGMENT_SHADER_SRC = _load_shader_source('model_fragment.glsl')

# Каждая строка: posX, posY, texU, texV
QUAD_VERTICES = np.array([
    # Первый треугольник
    -1.0,  1.0,  0.0, 1.0,
    -1.0, -1.0,  0.0, 0.0,
     1.0, -1.0,  1.0, 0.0,
    # Второй треугольник
    -1.0,  1.0,  0.0, 1.0,
     1.0, -1.0,  1.0, 0.0,
     1.0,  1.0,  1.0, 1.0,
], dtype=np.float32)


class SceneGLWidget(QOpenGLWidget):
    """Виджет для отрисовки 3D сцены """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Положение камеры (для gluLookAt)
        self.camera_pos = [0.0, 0.0, 8.0]
        self.camera_target = [0.0, 0.0, 0.0]

        # Параметры перспективы (можно обновить через apply_camera_config)
        self.cam_fov = 45.0
        self.cam_near = 0.1
        self.cam_far = 100.0

        # Позиции объектов в сцене (X, Y, Z)
        self.sphere_pos = [-2.0, 0.0, 0.0]
        self.airplane_pos = [2.0, 0.0, 0.0]

        # OpenGL ресурсы (создаются в initializeGL)
        self.quadric = None
        self.airplane_list = None
        self.airplane_loaded = False

        # FBO ресурсы
        self.fbo = None
        self.fbo_texture = None
        self.fbo_depth = None
        self.fbo_width = 800
        self.fbo_height = 600

        # Шейдер и fullscreen quad
        self.shader_program = None
        self.model_shader_program = None
        self.quad_vao = None
        self.quad_vbo = None

        # Текстура проектора
        self.projector_texture = None
        self.texture_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'base_texture.png')

        # Загрузка STL-модели
        self.airplane_mesh = stl_loader.load_stl('models/Mig29.stl')
        self.airplane_loaded = self.airplane_mesh is not None


    def initializeGL(self):
        self._init_scene_resources()
        self._build_airplane_display_list()
        self._create_shader()
        self._create_fullscreen_quad()
        self._create_fbo(self.width() or 800, self.height() or 600)
        if self.projector_texture is None:
            self.projector_texture = self._load_texture(self.texture_path)

    def _init_scene_resources(self):
        """Инициализация ресурсов для 3D-сцены"""
        if self.quadric is not None:
            gluDeleteQuadric(self.quadric)
        self.quadric = gluNewQuadric()

        glClearColor(0.3, 0.3, 0.3, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    def _build_airplane_display_list(self):
        """Создание display list для быстрой отрисовки модели самолёта"""
        if not self.airplane_loaded:
            return
        self.airplane_list = stl_loader.build_display_list(self.airplane_mesh)


    def _create_fbo(self, w, h):
        """Создание / пересоздание Frame Buffer Object"""
        # Удаляем старые ресурсы
        if self.fbo is not None:
            glDeleteFramebuffers(1, [self.fbo])
        if self.fbo_texture is not None:
            glDeleteTextures(1, [self.fbo_texture])
        if self.fbo_depth is not None:
            glDeleteRenderbuffers(1, [self.fbo_depth])

        dpr = self.devicePixelRatioF()
        self.fbo_width = max(int(w * dpr), 1)
        self.fbo_height = max(int(h * dpr), 1)

        # Цветовая текстура
        self.fbo_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.fbo_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.fbo_width, self.fbo_height,
                     0, GL_RGB, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

        # Renderbuffer для глубины
        self.fbo_depth = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self.fbo_depth)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24,
                              self.fbo_width, self.fbo_height)
        glBindRenderbuffer(GL_RENDERBUFFER, 0)

        # Собираем FBO
        self.fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, self.fbo_texture, 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                                  GL_RENDERBUFFER, self.fbo_depth)

        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            print(f"Ошибка FBO! Статус: {status}")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)


    def _load_texture(self, file_path):
        """Загружает текстуру из файла для проектора."""
        img = QImage(file_path)
        if img.isNull():
            print(f"Failed to load image: {file_path}")
            return None
            
        img = img.convertToFormat(QImage.Format.Format_RGBA8888)
        width = img.width()
        height = img.height()
        
        ptr = img.constBits()
        ptr.setsize(width * height * 4)
        data = np.frombuffer(ptr, dtype=np.uint8).copy()
        
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, [0.0, 0.0, 0.0, 0.0])
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D, 0)
        
        return tex_id

    def _get_projector_matrix(self, is_airplane=False):
        """Вычисляет матрицу проектора для переданного объекта (в локальных координатах объекта)"""
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        
        # Bias (переход в диапазон [0, 1] для текстурных координат)
        glTranslatef(0.5, 0.5, 0.5)
        glScalef(0.5, 0.5, 0.5)
        
        # Проекция проектора (угол обзора)
        gluPerspective(30.0, 1.0, 0.1, 100.0)
        
        # Вид проектора
        gluLookAt(2.0, 3.0, 4.0,  # позиция проектора
                  2.0, 0.0, 0.0,  # точка, куда он смотрит 
                  0.0, 1.0, 0.0)  # вектор "вверх"
        
        # Перенос из локальных координат модели в мировые, 
        # чтобы координаты вершин совпадали с пространством проектора.
        if is_airplane:
            glTranslatef(self.airplane_pos[0], self.airplane_pos[1], self.airplane_pos[2])
        else:
            glTranslatef(self.sphere_pos[0], self.sphere_pos[1], self.sphere_pos[2])
            
        proj_matrix = glGetFloatv(GL_PROJECTION_MATRIX)
        
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        return proj_matrix

    def _create_shader(self):
        """Компиляция шейдерной программы"""
        vertex = gl_shaders.compileShader(VERTEX_SHADER_SRC, GL_VERTEX_SHADER)
        fragment = gl_shaders.compileShader(FRAGMENT_SHADER_SRC, GL_FRAGMENT_SHADER)
        self.shader_program = gl_shaders.compileProgram(vertex, fragment)
        
        m_vertex = gl_shaders.compileShader(MODEL_VERTEX_SHADER_SRC, GL_VERTEX_SHADER)
        m_fragment = gl_shaders.compileShader(MODEL_FRAGMENT_SHADER_SRC, GL_FRAGMENT_SHADER)
        self.model_shader_program = gl_shaders.compileProgram(m_vertex, m_fragment)


    def _create_fullscreen_quad(self):
        """Создание VAO/VBO для полноэкранного прямоугольника"""
        self.quad_vao = glGenVertexArrays(1)
        self.quad_vbo = glGenBuffers(1)

        glBindVertexArray(self.quad_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.quad_vbo)
        glBufferData(GL_ARRAY_BUFFER, QUAD_VERTICES.nbytes, QUAD_VERTICES, GL_STATIC_DRAW)

        stride = 4 * ctypes.sizeof(ctypes.c_float)  # 4 floats per vertex
        # Позиция (location = 0)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        # Текстурные координаты (location = 1)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride,
                              ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_float)))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)


    def resizeGL(self, w, h):
        """Вызывается при изменении размера окна"""
        if self.fbo is not None:
            self._create_fbo(w, h)


    def paintGL(self):
        """Основной цикл отрисовки"""
        if self.fbo is None:
            return

        if self.quadric is None:
            self._init_scene_resources()

        dpr = self.devicePixelRatioF()
        w = int(self.width() * dpr)
        h = int(self.height() * dpr)

        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.fbo_width, self.fbo_height)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.fbo_width / max(self.fbo_height, 1)
        gluPerspective(self.cam_fov, aspect, self.cam_near, self.cam_far)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        gluLookAt(
            self.camera_pos[0], self.camera_pos[1], self.camera_pos[2],
            self.camera_target[0], self.camera_target[1], self.camera_target[2],
            0.0, 1.0, 0.0
        )

        glLightfv(GL_LIGHT0, GL_POSITION, (5, 5, -5, 1))

        # Настраиваем шейдер для проекции на модели
        glUseProgram(self.model_shader_program)
        
        loc_tex = glGetUniformLocation(self.model_shader_program, "projectorTexture")
        loc_use_proj = glGetUniformLocation(self.model_shader_program, "useProjector")
        loc_mat = glGetUniformLocation(self.model_shader_program, "projectorMatrix")
        
        glUniform1i(loc_tex, 1) # Текстурный юнит 1
        
        glActiveTexture(GL_TEXTURE1)
        if self.projector_texture is not None:
            glBindTexture(GL_TEXTURE_2D, self.projector_texture)
            glUniform1i(loc_use_proj, 1)
        else:
            glBindTexture(GL_TEXTURE_2D, 0)
            glUniform1i(loc_use_proj, 0)
        glActiveTexture(GL_TEXTURE0)

        # Шар
        sphere_proj = self._get_projector_matrix(is_airplane=False)
        glUniformMatrix4fv(loc_mat, 1, GL_FALSE, sphere_proj)
        
        glPushMatrix()
        glTranslatef(self.sphere_pos[0], self.sphere_pos[1], self.sphere_pos[2])
        glColor3f(0.1, 0.7, 0.4)
        gluSphere(self.quadric, 1.0, 32, 32)
        glPopMatrix()

        # Самолёт
        if self.airplane_list is not None:
            airplane_proj = self._get_projector_matrix(is_airplane=True)
            glUniformMatrix4fv(loc_mat, 1, GL_FALSE, airplane_proj)
            
            glPushMatrix()
            glTranslatef(self.airplane_pos[0], self.airplane_pos[1], self.airplane_pos[2])
            glColor3f(0.1, 0.8, 0.7)
            glCallList(self.airplane_list)
            glPopMatrix()

        glUseProgram(0)

        glBindFramebuffer(GL_FRAMEBUFFER, self.defaultFramebufferObject())
        glViewport(0, 0, w, h)

        glClear(GL_COLOR_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        glUseProgram(self.shader_program)

        # Привязываем текстуру FBO
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.fbo_texture)
        loc = glGetUniformLocation(self.shader_program, "screenTexture")
        glUniform1i(loc, 0)

        # Рисуем quad
        glBindVertexArray(self.quad_vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

        glUseProgram(0)
        glBindTexture(GL_TEXTURE_2D, 0)


    def apply_camera_config(self, config: dict):
        """
        Применяет параметры камеры из словаря конфигурации.
        Поддерживаемые ключи: fov, near, far, resolution.
        Вызывает обновление сцены сразу после применения.
        """
        if 'fov' in config:
            self.cam_fov = float(config['fov'])
        if 'near' in config:
            self.cam_near = float(config['near'])
        if 'far' in config:
            self.cam_far = float(config['far'])
        # resolution влияет только на aspect ratio FBO — пересоздавать FBO не нужно,
        # т.к. aspect ratio берётся из реального размера виджета.
        # Но сохраняем значение для возможного будущего использования.
        if 'resolution' in config:
            res = config['resolution']
            if isinstance(res, (list, tuple)) and len(res) == 2:
                self._config_resolution = (int(res[0]), int(res[1]))
        if 'position' in config:
            pos = config['position']
            if isinstance(pos, (list, tuple)) and len(pos) == 3:
                self.camera_pos = [float(pos[0]), float(pos[1]), float(pos[2])]
        if 'target' in config:
            tgt = config['target']
            if isinstance(tgt, (list, tuple)) and len(tgt) == 3:
                self.camera_target = [float(tgt[0]), float(tgt[1]), float(tgt[2])]
                
        print(f"[Camera] pos={self.camera_pos} fov={self.cam_fov}° near={self.cam_near} far={self.cam_far}")
        self.update()

    def cleanup(self):
        """Очистка всех OpenGL ресурсов"""
        self.makeCurrent()
        if self.quadric is not None:
            gluDeleteQuadric(self.quadric)
            self.quadric = None
        if self.airplane_list is not None:
            glDeleteLists(self.airplane_list, 1)
            self.airplane_list = None
        if self.fbo is not None:
            glDeleteFramebuffers(1, [self.fbo])
            self.fbo = None
        if self.fbo_texture is not None:
            glDeleteTextures(1, [self.fbo_texture])
            self.fbo_texture = None
        if self.fbo_depth is not None:
            glDeleteRenderbuffers(1, [self.fbo_depth])
            self.fbo_depth = None
        if self.shader_program is not None:
            glDeleteProgram(self.shader_program)
            self.shader_program = None
        if self.model_shader_program is not None:
            glDeleteProgram(self.model_shader_program)
            self.model_shader_program = None
        if self.projector_texture is not None:
            glDeleteTextures(1, [self.projector_texture])
            self.projector_texture = None
        if self.quad_vao is not None:
            glDeleteVertexArrays(1, [self.quad_vao])
            self.quad_vao = None
        if self.quad_vbo is not None:
            glDeleteBuffers(1, [self.quad_vbo])
            self.quad_vbo = None
        self.doneCurrent()

    def hideEvent(self, event):
        """Вызывается при скрытии виджета"""
        self.cleanup()
        super().hideEvent(event)

    def showEvent(self, event):
        """Пересоздаём GL-ресурсы при повторном показе виджета"""
        super().showEvent(event)
        if self.fbo is None:
            self.makeCurrent()
            self._init_scene_resources()
            self._build_airplane_display_list()
            self._create_shader()
            self._create_fullscreen_quad()
            self._create_fbo(self.width() or 800, self.height() or 600)
            if self.projector_texture is None:
                self.projector_texture = self._load_texture(self.texture_path)
            self.doneCurrent()
            self.update()

    def mousePressEvent(self, event):
        pass # Управление перенесено в UI панели настроек

    def mouseMoveEvent(self, event):
        pass

    def wheelEvent(self, event):
        pass

