# Daily Questions App

## 🚀 ¿Qué es este proyecto?
Una aplicación web para gestionar objetivos, preguntas diarias y desarrollo personal, con notificaciones automáticas por correo.

---

## 📦 Estructura del Proyecto

```
daily-questions-app/
│
├── backup/                  # Archivos de respaldo (ej: app.py.bak)
├── daily_questions_app/     # Código principal de la app
│   ├── app.py               # Servidor Flask principal
│   ├── requirements.txt     # Dependencias del proyecto
│   ├── templates/           # Plantillas HTML (Jinja2)
│   ├── static/              # Archivos estáticos (CSS, JS, imágenes)
│   ├── ...
│
├── scripts/                 # Scripts utilitarios y de mantenimiento
│   ├── update_database.py
│   ├── verificar_proyecciones.py
│   ├── test_notificacion.py
│   └── ...
│
├── README_NOTIFICACIONES.md # Documentación específica del sistema de notificaciones
├── env_example.txt          # Ejemplo de archivo de variables de entorno
└── README.md                # (Este archivo)
```

---

## 🛠️ ¿Cómo empezar?

1. **Clona el repositorio**
2. **Instala las dependencias**:
   ```bash
   pip install -r daily_questions_app/requirements.txt
   ```
3. **Configura tus variables de entorno**:
   - Copia `env_example.txt` a `.env` y edítalo con tus datos reales.
4. **Inicializa la base de datos** (si es necesario):
   ```bash
   python scripts/update_database.py
   ```
5. **Ejecuta la app**:
   ```bash
   python daily_questions_app/app.py
   ```

---

## 📚 Recursos útiles
- `README_NOTIFICACIONES.md`: Documentación sobre el sistema de notificaciones por correo.
- `scripts/`: Scripts para mantenimiento, pruebas y utilidades.
- `backup/`: Archivos de respaldo (no necesarios para producción).

---

## 🧑‍💻 Buenas prácticas
- Mantén tus variables sensibles solo en `.env` (no lo subas a GitHub).
- Usa la carpeta `scripts/` para cualquier script auxiliar.
- Si haces cambios grandes, considera modularizar la lógica en subcarpetas como `modules/` o `services/`.

---

¿Dudas? ¿Sugerencias? ¡Abre un issue o contacta al autor!

## Requisitos

- Python 3.8+
- SQL Server (local o remoto)
- Controlador ODBC para SQL Server (ODBC Driver 18 recomendado)
- Paquetes Python (ver `requirements.txt`)

## Instalación del controlador ODBC

1. Descarga el controlador ODBC Driver 18 para SQL Server desde:
   https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Instálalo siguiendo las instrucciones del instalador.
3. Verifica la instalación abriendo el "Administrador de origen de datos ODBC" y revisando la pestaña de "Controladores".

## Configuración de la base de datos

- Asegúrate de tener una base de datos llamada `DailyQuestions` y la tabla `question` con las columnas necesarias (`descripcion`, `is_required`, `categoria`, etc).
- Si necesitas crear las columnas, ejecuta este script en tu SQL Server:

```sql
ALTER TABLE question
ADD
    descripcion NVARCHAR(255) NULL,
    is_required BIT NOT NULL DEFAULT 0,
    categoria NVARCHAR(100) NOT NULL DEFAULT 'General';
```

## Instalación de dependencias Python

```bash
pip install -r requirements.txt
```

## Ejecución de la aplicación

```bash
python daily_questions_app/app.py
```

La app se ejecuta por defecto en el puerto 5000: http://localhost:5000

## Notas

- Si tienes problemas de conexión, revisa el nombre del servidor en la cadena de conexión y que el servicio de SQL Server esté activo.
- Si agregas nuevas columnas a la tabla, asegúrate de actualizar la base de datos. 