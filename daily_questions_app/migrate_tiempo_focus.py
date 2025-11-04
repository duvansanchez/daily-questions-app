#!/usr/bin/env python3
"""
Migración para agregar campo tiempo_focus a la tabla subobjetivos
"""

import pyodbc
import sys
import os

# Agregar el directorio padre al path para importar la configuración
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-2MR0PJ6;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def migrate():
    """Ejecuta la migración"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔄 Iniciando migración para agregar tiempo_focus a subobjetivos...")
        
        # Verificar si la columna ya existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'subobjetivos' 
            AND COLUMN_NAME = 'tiempo_focus'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists > 0:
            print("✅ La columna tiempo_focus ya existe en subobjetivos")
        else:
            # Agregar la columna tiempo_focus
            cursor.execute("""
                ALTER TABLE subobjetivos 
                ADD tiempo_focus INT DEFAULT 0
            """)
            
            print("✅ Columna tiempo_focus agregada a subobjetivos")
        
        # También verificar que existe en objetivos
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'objetivos' 
            AND COLUMN_NAME = 'tiempo_focus'
        """)
        
        exists_obj = cursor.fetchone()[0]
        
        if exists_obj == 0:
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD tiempo_focus INT DEFAULT 0
            """)
            print("✅ Columna tiempo_focus agregada a objetivos")
        else:
            print("✅ La columna tiempo_focus ya existe en objetivos")
        
        conn.commit()
        conn.close()
        
        print("🎉 Migración completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    migrate()