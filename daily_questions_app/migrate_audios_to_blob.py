#!/usr/bin/env python3
"""
Script para migrar la tabla de audios para guardar archivos como BLOB
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_audios_table():
    """Agregar columnas para contenido binario a la tabla audios"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si las columnas ya existen
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'audios' AND COLUMN_NAME IN ('contenido_binario', 'tipo_mime')
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            # Agregar columna contenido_binario si no existe
            if 'contenido_binario' not in existing_columns:
                logger.info("Agregando columna contenido_binario...")
                cursor.execute("""
                    ALTER TABLE audios 
                    ADD contenido_binario VARBINARY(MAX)
                """)
                logger.info("✅ Columna contenido_binario agregada")
            else:
                logger.info("✅ Columna contenido_binario ya existe")
            
            # Agregar columna tipo_mime si no existe
            if 'tipo_mime' not in existing_columns:
                logger.info("Agregando columna tipo_mime...")
                cursor.execute("""
                    ALTER TABLE audios 
                    ADD tipo_mime NVARCHAR(100)
                """)
                logger.info("✅ Columna tipo_mime agregada")
            else:
                logger.info("✅ Columna tipo_mime ya existe")
            
            # Hacer archivo_url opcional (ya no será necesario)
            cursor.execute("""
                SELECT COLUMN_NAME, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'audios' AND COLUMN_NAME = 'archivo_url'
            """)
            url_column = cursor.fetchone()
            
            if url_column and url_column[1] == 'NO':
                logger.info("Haciendo archivo_url opcional...")
                cursor.execute("""
                    ALTER TABLE audios 
                    ALTER COLUMN archivo_url NVARCHAR(500) NULL
                """)
                logger.info("✅ Columna archivo_url ahora es opcional")
            
            conn.commit()
            logger.info("🎉 Migración completada exitosamente")
            
    except Exception as e:
        logger.error(f"❌ Error en migración: {str(e)}")
        raise

if __name__ == '__main__':
    migrate_audios_table()