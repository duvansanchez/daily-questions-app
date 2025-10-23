# Preguntas Semanales y Mensuales

## Descripción

Se ha implementado la funcionalidad para configurar y ejecutar preguntas con diferentes frecuencias: diarias, semanales y mensuales. Esto permite a los usuarios tener diferentes tipos de reflexiones según la periodicidad que deseen.

## Funcionalidades Implementadas

### 1. Campo de Frecuencia en Base de Datos
- ✅ Agregado campo `frecuencia` a la tabla `question`
- ✅ Valores posibles: 'diaria', 'semanal', 'mensual'
- ✅ Valor por defecto: 'diaria'

### 2. Interfaz de Administración
- ✅ Campo de frecuencia en formulario de nueva pregunta
- ✅ Campo de frecuencia en formulario de edición
- ✅ Selector dropdown con opciones: Diaria, Semanal, Mensual

### 3. Rutas y Templates
- ✅ Ruta `/` - Preguntas diarias (modificada para filtrar por frecuencia)
- ✅ Ruta `/preguntas-semanales` - Preguntas semanales
- ✅ Ruta `/preguntas-mensuales` - Preguntas mensuales
- ✅ Templates específicos para cada frecuencia con diseños diferenciados

### 4. Navegación
- ✅ Dropdown en navbar con opciones para cada frecuencia
- ✅ Iconos distintivos para cada tipo de pregunta
- ✅ Enlaces directos a cada sección

### 5. Estadísticas por Frecuencia
- ✅ Sección nueva en estadísticas mostrando completitud por frecuencia
- ✅ Contadores separados para preguntas diarias, semanales y mensuales
- ✅ Barras de progreso individuales

## Archivos Modificados

### Backend (`daily_questions_app/app.py`)
- ✅ Actualizada clase `Question` para incluir campo `frecuencia`
- ✅ Agregado método `get_by_user_and_frequency()`
- ✅ Modificadas rutas existentes y agregadas nuevas rutas
- ✅ Actualizada función `add_question()` para manejar frecuencia
- ✅ Agregada función `get_stats_by_frequency()` para estadísticas

### Frontend Templates
- ✅ `templates/admin.html` - Agregados campos de frecuencia
- ✅ `templates/preguntas_semanales.html` - Nuevo template
- ✅ `templates/preguntas_mensuales.html` - Nuevo template
- ✅ `templates/base.html` - Actualizada navegación con dropdown
- ✅ `templates/stats.html` - Agregada sección de estadísticas por frecuencia

### Base de Datos
- ✅ `add_frecuencia_column.py` - Script para agregar campo frecuencia

### Scripts de Prueba
- ✅ `scripts/test_preguntas_frecuencia.py` - Verificación de funcionalidad

## Cómo Usar

### 1. Crear Preguntas con Frecuencia
1. Ve a **Administrar** en el menú
2. Haz clic en **Nueva Pregunta**
3. Llena los campos normales (texto, tipo, etc.)
4. **Selecciona la frecuencia**: Diaria, Semanal o Mensual
5. Guarda la pregunta

### 2. Responder Preguntas por Frecuencia
- **Diarias**: Ve a **Preguntas > Diarias** o la página principal
- **Semanales**: Ve a **Preguntas > Semanales**
- **Mensuales**: Ve a **Preguntas > Mensuales**

### 3. Ver Estadísticas
- Ve a **Estadísticas** en el menú
- En la sección **"Preguntas por Frecuencia"** verás:
  - Cuántas preguntas de cada tipo has respondido hoy
  - Porcentaje de completitud por frecuencia
  - Barras de progreso visuales

## Características Técnicas

### Diseño Visual Diferenciado
- **Diarias**: Azul (`#0d6efd`) con icono de sol
- **Semanales**: Verde (`#28a745`) con icono de calendario semanal
- **Mensuales**: Naranja (`#fd7e14`) con icono de calendario mensual

### Funcionalidad JavaScript
- Cada template tiene su propio JavaScript adaptado
- Manejo de respuestas idéntico al sistema original
- Navegación fluida entre preguntas
- Mensajes de completitud personalizados

### Base de Datos
```sql
-- Campo agregado a la tabla question
ALTER TABLE question ADD frecuencia NVARCHAR(20) DEFAULT 'diaria'
```

### Métodos de la Clase Question
```python
# Nuevo método para obtener preguntas por frecuencia
Question.get_by_user_and_frequency(user_id, frecuencia)

# Método create actualizado para incluir frecuencia
Question.create(..., frecuencia='diaria', ...)
```

## Beneficios

- ✅ **Flexibilidad**: Diferentes tipos de reflexión según periodicidad
- ✅ **Organización**: Separación clara entre preguntas diarias, semanales y mensuales
- ✅ **Estadísticas**: Seguimiento independiente por frecuencia
- ✅ **Experiencia de Usuario**: Interfaces diferenciadas y navegación intuitiva
- ✅ **Escalabilidad**: Fácil agregar nuevas frecuencias en el futuro

## Casos de Uso

### Preguntas Diarias
- Reflexiones cotidianas
- Hábitos diarios
- Estado de ánimo
- Productividad del día

### Preguntas Semanales
- Evaluación de objetivos semanales
- Reflexión sobre logros de la semana
- Planificación para la siguiente semana
- Balance trabajo-vida personal

### Preguntas Mensuales
- Revisión de metas mensuales
- Análisis de crecimiento personal
- Evaluación de hábitos a largo plazo
- Planificación estratégica personal

## Próximos Pasos Sugeridos

1. **Preguntas Anuales**: Agregar frecuencia anual para reflexiones de largo plazo
2. **Recordatorios**: Sistema de notificaciones para preguntas semanales/mensuales
3. **Plantillas**: Preguntas predefinidas por frecuencia
4. **Análisis Comparativo**: Comparar respuestas entre diferentes períodos
5. **Exportación**: Generar reportes por frecuencia

## Verificación

Para verificar que todo funciona correctamente:

```bash
# 1. Ejecutar script de prueba
python scripts/test_preguntas_frecuencia.py

# 2. Iniciar aplicación
python daily_questions_app/app.py

# 3. Probar en navegador
# - http://localhost:5000/admin (crear preguntas)
# - http://localhost:5000/ (preguntas diarias)
# - http://localhost:5000/preguntas-semanales
# - http://localhost:5000/preguntas-mensuales
# - http://localhost:5000/stats (ver estadísticas)
```

La implementación está completa y lista para usar. Los usuarios ahora pueden configurar preguntas con diferentes frecuencias y tener experiencias de reflexión más organizadas y específicas según sus necesidades.