#!/usr/bin/env python3
"""
Script para verificar la estructura de la base de datos
"""

import pyodbc
import sys
import os

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-2MR0PJ6;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def verify_db():
    """Verifica la estructura de la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔍 Verificando estructura de la tabla subobjetivos...")
        
        # Obtener columnas de la tabla subobjetivos
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'subobjetivos'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print(f"📊 Columnas encontradas en subobjetivos ({len(columns)}):")
        for col in columns:
            print(f"  - {col[0]} ({col[1]}) - Nullable: {col[2]} - Default: {col[3]}")
        
        # Verificar si existe tiempo_focus
        tiempo_focus_exists = any(col[0] == 'tiempo_focus' for col in columns)
        if tiempo_focus_exists:
            print("✅ La columna tiempo_focus existe en subobjetivos")
        else:
            print("❌ La columna tiempo_focus NO existe en subobjetivos")
        
        # Verificar datos de ejemplo
        print("\n🔍 Verificando datos de subobjetivos...")
        cursor.execute("SELECT TOP 5 id, titulo, completado, tiempo_focus FROM subobjetivos")
        rows = cursor.fetchall()
        
        if rows:
            print(f"📊 Primeros {len(rows)} subobjetivos:")
            for row in rows:
                print(f"  - ID: {row[0]}, Título: {row[1]}, Completado: {row[2]}, Tiempo Focus: {row[3]}")
        else:
            print("📊 No hay subobjetivos en la base de datos")
        
        # Verificar objetivos también
        print("\n🔍 Verificando estructura de la tabla objetivos...")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'objetivos' AND COLUMN_NAME = 'tiempo_focus'
        """)
        
        obj_tiempo = cursor.fetchall()
        if obj_tiempo:
            print("✅ La columna tiempo_focus existe en objetivos")
            print(f"  - {obj_tiempo[0][0]} ({obj_tiempo[0][1]}) - Nullable: {obj_tiempo[0][2]} - Default: {obj_tiempo[0][3]}")
        else:
            print("❌ La columna tiempo_focus NO existe en objetivos")
        
        conn.close()
        print("\n🎉 Verificación completada!")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    verify_db()