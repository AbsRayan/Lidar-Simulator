#version 330 compatibility

uniform mat4 projectorMatrix;

out vec4 ProjCoords;
out vec3 Normal;
out vec4 FragPos;
out vec4 BaseColor;

void main() {
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    
    // Вычисляем координаты проекции из локальных координат модели
    ProjCoords = projectorMatrix * gl_Vertex;
    
    // Передаем нормаль и позицию в пространство камеры для освещения
    Normal = normalize(gl_NormalMatrix * gl_Normal);
    FragPos = gl_ModelViewMatrix * gl_Vertex;
    BaseColor = gl_Color;
}
