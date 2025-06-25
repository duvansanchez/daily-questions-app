# Daily Questions App

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