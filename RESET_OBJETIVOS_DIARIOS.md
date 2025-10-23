# Reset Automático de Objetivos Diarios Recurrentes

## Descripción

Se ha implementado una funcionalidad que automáticamente desmarca (resetea) todos los objetivos diarios recurrentes al inicio de cada día (medianoche). Esto permite que los usuarios tengan una "pizarra limpia" cada día para sus objetivos recurrentes.

## Funcionalidad Implementada

### 1. Reset Automático
- **Horario**: Todos los días a las 00:00 (medianoche)
- **Zona horaria**: America/Bogota
- **Acción**: Desmarca todos los objetivos que cumplan:
  - Categoría = 'diario'
  - Recurrente = true
  - Completado = true
  - Estado ≠ 'histórico'

### 2. Reset Manual
- **Botón**: "Reset diarios" en la página de objetivos
- **Ubicación**: Junto al botón "Desmarcar todos los recurrentes"
- **Función**: Permite ejecutar manualmente el reset sin esperar a medianoche

### 3. API Endpoint
- **Ruta**: `POST /api/reset-objetivos-diarios`
- **Autenticación**: Requerida
- **Uso**: Permite ejecutar el reset programáticamente

## Archivos Modificados

### `daily_questions_app/app.py`
- ✅ Agregada función `reset_objetivos_diarios_recurrentes()`
- ✅ Modificado scheduler para incluir tarea de reset a las 00:00
- ✅ Agregado endpoint API `/api/reset-objetivos-diarios`

### `daily_questions_app/templates/objetivos.html`
- ✅ Agregado botón "Reset diarios" en la interfaz

### `daily_questions_app/static/js/main.js`
- ✅ Agregado handler para el botón de reset manual

### Scripts de Prueba
- ✅ `scripts/test_reset_objetivos.py` - Prueba la funcionalidad de reset
- ✅ `scripts/test_scheduler.py` - Prueba el scheduler

## Cómo Funciona

1. **Automático**: Cada día a medianoche, el scheduler ejecuta `reset_objetivos_diarios_recurrentes()`
2. **Manual**: Los usuarios pueden hacer clic en "Reset diarios" para ejecutar inmediatamente
3. **Programático**: Se puede llamar al endpoint `/api/reset-objetivos-diarios` desde scripts externos

## Verificación

### Para verificar que funciona:

1. **Iniciar la aplicación**:
   ```bash
   cd daily_questions_app
   python app.py
   ```

2. **Buscar en los logs**:
   ```
   [Scheduler] Tareas programadas:
     - Reset objetivos diarios recurrentes: 00:00 todos los días
     - Notificaciones de proyecciones: 00:01 y 12:00 todos los días
   ```

3. **Probar manualmente**:
   ```bash
   python scripts/test_reset_objetivos.py
   ```

### Ejemplo de uso del botón manual:
1. Ve a la página de Objetivos
2. Marca algunos objetivos diarios recurrentes como completados
3. Haz clic en "Reset diarios"
4. Confirma la acción
5. Los objetivos diarios recurrentes completados se desmarcarán

## Beneficios

- ✅ **Automatización**: No requiere intervención manual diaria
- ✅ **Consistencia**: Todos los objetivos diarios se resetean al mismo tiempo
- ✅ **Flexibilidad**: Opción manual disponible cuando sea necesario
- ✅ **Mantenibilidad**: Código limpio siguiendo patrones existentes
- ✅ **Seguridad**: Solo afecta objetivos diarios recurrentes, no históricos

## Consideraciones Técnicas

- La función usa transacciones para garantizar consistencia
- Se incluye logging para monitoreo
- Manejo de errores robusto
- Compatible con la estructura existente de la base de datos
- No afecta objetivos no recurrentes o de otras categorías (semanal, mensual, anual)

## Patrón de Diseño Aplicado

Se utilizó el **patrón Strategy** para separar la lógica de reset de la lógica del scheduler, permitiendo reutilizar la función tanto automática como manualmente.