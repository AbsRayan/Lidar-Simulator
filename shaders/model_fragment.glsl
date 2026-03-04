#version 330 compatibility

in vec4 ProjCoords;
in vec3 Normal;
in vec4 FragPos;
in vec4 BaseColor;

uniform sampler2D projectorTexture;
uniform bool useProjector;

out vec4 FragColor;

void main() {
    // Освещение
    vec3 n = normalize(Normal);
    vec3 lightPos = gl_LightSource[0].position.xyz;
    vec3 l;
    if (gl_LightSource[0].position.w == 0.0) {
        l = normalize(lightPos);
    } else {
        l = normalize(lightPos - FragPos.xyz);
    }
    float diff = max(dot(n, l), 0.0);
    
    vec4 ambient = BaseColor * 0.4;
    vec4 diffuse = BaseColor * diff * 0.8;
    vec4 finalColor = ambient + diffuse;
    finalColor.a = BaseColor.a;
    
    // Проекция
    if (useProjector) {
        if (ProjCoords.w > 0.0) {
            vec3 proj = ProjCoords.xyz / ProjCoords.w;
            
            // Проверка попадания в frustum проектора ([0, 1] по X, Y и Z > 0)
            if (proj.x >= 0.0 && proj.x <= 1.0 && 
                proj.y >= 0.0 && proj.y <= 1.0 && 
                proj.z >= 0.0) {
                
                vec4 texColor = texture(projectorTexture, proj.xy);
                // Смешиваем цвет с текстурой по ее альфа-каналу
                finalColor = mix(finalColor, texColor, texColor.a);
            }
        }
    }
    
    FragColor = vec4(finalColor.rgb, 1.0);
}
