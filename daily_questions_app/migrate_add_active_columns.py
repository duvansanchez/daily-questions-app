#!/usr/bin/env python3
"""
Script para agregar columnas 'activa' a las tablas de categorías y subcategorías
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_active_columns():
    """Agregar columnas activa a categorías y subcategorías"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si la columna activa ya existe en categorias
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'categorias' AND COLUMN_NAME = 'activa'
            """)
            categoria_activa_exists = cursor.fetchone()
            
            if not categoria_activa_exists:
                logger.info("Agregando columna 'activa' a tabla categorias...")
                cursor.execute("""
                    ALTER TABLE categorias 
                    ADD activa BIT NOT NULL DEFAULT 1
                """)
                logger.info("✅ Columna 'activa' agregada a categorias")
            else:
                logger.info("✅ Columna 'activa' ya existe en categorias")
            
            # Verificar si la columna activa ya existe en subcategorias
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'subcategorias' AND COLUMN_NAME = 'activa'
            """)
            subcategoria_activa_exists = cursor.fetchone()
            
            if not subcategoria_activa_exists:
                logger.info("Agregando columna 'activa' a tabla subcategorias...")
                cursor.execute("""
                    ALTER TABLE subcategorias 
                    ADD activa BIT NOT NULL DEFAULT 1
                """)
                logger.info("✅ Columna 'activa' agregada a subcategorias")
            else:
                logger.info("✅ Columna 'activa' ya existe en subcategorias")
            
            conn.commit()
            logger.info("🎉 Migración completada exitosamente")
            
    except Exception as e:
        logger.error(f"❌ Error en migración: {str(e)}")
        raise

if __name__ == '__main__':
    add_active_columns()