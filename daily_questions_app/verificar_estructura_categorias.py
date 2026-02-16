#!/usr/bin/env python3
"""
Script para verificar estructura de tablas de categorías
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection

def verificar_estructura():
    """Verificar estructura de tablas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar columnas de categorias
            print("\n📋 ESTRUCTURA DE TABLA 'categorias':")
            print("=" * 60)
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'categorias'
                ORDER BY ORDINAL_POSITION
            """)
            columnas = cursor.fetchall()
            
            for col in columnas:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                length = f"({col[3]})" if col[3] else ""
                print(f"{col[0]:<30} {col[1]}{length:<20} {nullable}")
            
            # Verificar columnas de subcategorias
            print("\n📋 ESTRUCTURA DE TABLA 'subcategorias':")
            print("=" * 60)
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'subcategorias'
                ORDER BY ORDINAL_POSITION
            """)
            columnas = cursor.fetchall()
            
            for col in columnas:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                length = f"({col[3]})" if col[3] else ""
                print(f"{col[0]:<30} {col[1]}{length:<20} {nullable}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 VERIFICACIÓN DE ESTRUCTURA DE TABLAS")
    print("=" * 60)
    verificar_estructura()
