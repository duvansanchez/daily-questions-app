#!/usr/bin/env python3
"""
Script para crear la tabla de audios inspiracionales
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daily_questions_app.app import get_db_connection
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_audios_table():
    """Crear la tabla de audios"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Crear tabla de audios
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'audios')
                BEGIN
                    CREATE TABLE audios (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        user_id INT NOT NULL,
                        titulo NVARCHAR(255) NOT NULL,
                        descripcion NVARCHAR(1000),
                        archivo_nombre NVARCHAR(255) NOT NULL,
                        archivo_url NVARCHAR(500) NOT NULL,
                        duracion_segundos INT,
                        categoria NVARCHAR(255),
                        subcategoria NVARCHAR(255),
                        notas NVARCHAR(500),
                        total_reproducciones INT DEFAULT 0,
                        ultima_reproduccion DATETIME,
                        activa BIT DEFAULT 1,
                        fecha_creacion DATETIME DEFAULT GETDATE(),
                        FOREIGN KEY (user_id) REFERENCES [user](id)
                    )
                END
            ''')
            
            conn.commit()
            logger.info("Tabla 'audios' creada exitosamente!")
            
    except Exception as e:
        logger.error(f"Error creando tabla audios: {str(e)}")
        raise

if __name__ == "__main__":
    create_audios_table()
    print("Script completado!")