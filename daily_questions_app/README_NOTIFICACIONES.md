# Sistema de Notificaciones por Correo - Daily Questions App

## 📧 Configuración del Sistema de Notificaciones

### 1. Configuración de Gmail

Para usar Gmail como servidor SMTP, necesitas configurar una "Contraseña de aplicación":

1. **Habilitar verificación en dos pasos**:
   - Ve a tu cuenta de Google
   - Seguridad > Verificación en dos pasos
   - Activa la verificación en dos pasos

2. **Generar contraseña de aplicación**:
   - Ve a Seguridad > Verificación en dos pasos
   - Contraseñas de aplicación
   - Selecciona "Otra" y nombra la aplicación (ej: "Daily Questions App")
   - Copia la contraseña generada

### 2. Configuración de Variables de Entorno

Crea un archivo `.env` en el directorio `daily_questions_app/` con el siguiente contenido:

```env
# Configuración de correo electrónico
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion_generada
```

### 3. Instalación de Dependencias

Instala la nueva dependencia para el envío de correos:

```bash
pip install Flask-Mail==0.9.1
```

### 4. Actualización de la Base de Datos

Ejecuta el script de actualización para agregar el nuevo campo:

```bash
python update_database.py
```

## 🔔 Funcionalidades Implementadas

### Campo "Fecha Proyección Comienzo"

- **Ubicación**: Se encuentra en ambos modales (nuevo y editar objetivo)
- **Posición**: Después de las fechas de inicio y fin
- **Descripción**: Campo opcional para establecer cuándo planeas comenzar el objetivo

### Sistema de Notificaciones

- **Verificación automática**: El sistema verifica diariamente los objetivos con fecha de proyección para hoy
- **Notificaciones por correo**: Envía correos HTML con información del objetivo
- **Endpoint API**: `/api/verificar-proyecciones` para verificación manual

### Script Independiente

El archivo `verificar_proyecciones.py` puede ejecutarse independientemente:

```bash
python verificar_proyecciones.py
```

## ⏰ Programación Automática

### Windows (Programador de Tareas)

1. Abre "Programador de tareas"
2. Crea una nueva tarea básica
3. Configura para ejecutar diariamente
4. Acción: Iniciar programa
5. Programa: `python`
6. Argumentos: `C:\ruta\a\verificar_proyecciones.py`

### Linux/Mac (Cron)

Agrega esta línea a tu crontab (`crontab -e`):

```bash
0 9 * * * /usr/bin/python3 /ruta/a/verificar_proyecciones.py
```

Esto ejecutará la verificación todos los días a las 9:00 AM.

## 📋 Estructura de la Base de Datos

### Nuevo Campo Agregado

```sql
ALTER TABLE objetivos 
ADD fecha_proyeccion_comienzo DATETIME NULL
```

### Campos en la Tabla objetivos

- `id` - Identificador único
- `user_id` - ID del usuario
- `titulo` - Título del objetivo
- `descripcion` - Descripción del objetivo
- `prioridad` - Prioridad (alta/media/baja)
- `categoria` - Categoría (diario/semanal/mensual/anual/general)
- `completado` - Estado de completado
- `fecha_creacion` - Fecha de creación
- `fecha_completado` - Fecha de completado
- `objetivo_padre_id` - ID del objetivo padre
- `es_padre` - Si es objetivo padre
- `estado` - Estado del objetivo
- `fecha_inicio` - Fecha de inicio
- `fecha_fin` - Fecha de fin
- **`fecha_proyeccion_comienzo`** - **NUEVO: Fecha proyectada para comenzar**
- `horas_estimadas` - Horas estimadas
- `dificultad` - Nivel de dificultad
- `etiquetas` - Etiquetas del objetivo
- `recompensa` - Recompensa por completar
- `notas_adicionales` - Notas adicionales
- `recurrente` - Si es recurrente
- `frecuencia` - Frecuencia si es recurrente

## 🎯 Patrones de Diseño Aplicados

### Strategy Pattern
- **Contexto**: Organización de campos en modales
- **Estrategia**: Layout consistente entre modales de crear y editar
- **Beneficio**: Mantenibilidad y escalabilidad del código

### Observer Pattern
- **Contexto**: Sistema de notificaciones por correo
- **Observador**: Sistema de correo que reacciona a fechas de proyección
- **Sujeto**: Objetivos con fecha de proyección de comienzo
- **Beneficio**: Desacoplamiento entre la lógica de objetivos y notificaciones

## 🔧 Troubleshooting

### Error de Conexión SMTP

Si tienes problemas con Gmail:

1. Verifica que la verificación en dos pasos esté activada
2. Usa una contraseña de aplicación, no tu contraseña normal
3. Verifica que el puerto 587 esté abierto

### Error de Base de Datos

Si el campo no se agrega:

1. Ejecuta manualmente: `python update_database.py`
2. Verifica que tienes permisos de administrador en SQL Server
3. Revisa los logs de error

### Logs

Los logs se guardan en:
- `proyecciones.log` - Para el script independiente
- Consola de la aplicación Flask - Para el endpoint API

## 📞 Soporte

Para problemas o preguntas sobre el sistema de notificaciones:

1. Revisa los logs de error
2. Verifica la configuración de variables de entorno
3. Asegúrate de que todas las dependencias estén instaladas 