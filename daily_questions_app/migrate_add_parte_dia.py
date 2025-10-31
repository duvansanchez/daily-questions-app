#!/usr/bin/env python3
"""
Migración para agregar el campo 'parte_dia' a la tabla objetivos
"""

import pyodbc
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Obtener conexión a SQL Server"""
    # Intentar con ODBC 18 primero, luego 17, luego el genérico
    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server"  # Último recurso
    ]
    
    for driver in drivers:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};"
                "SERVER=DESKTOP-2MR0PJ6;"
                "DATABASE=DailyQuestions;"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
                "Connection Timeout=30;"
                "charset=UTF-8;"
                "encoding=UTF-8;"
                "MARS_Connection=yes;"
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f"Error con driver {driver}: {e}")
            continue
    
    raise Exception("No se pudo conectar con ningún driver disponible")

def migrate_add_parte_dia():
    """Agregar columna parte_dia a la tabla objetivos"""
    
    try:
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'objetivos' 
            AND COLUMN_NAME = 'parte_dia'
        """)
        
        column_exists = cursor.fetchone()[0] > 0
        
        if not column_exists:
            print("Agregando columna 'parte_dia' a la tabla objetivos...")
            
            # Agregar la columna parte_dia
            cursor.execute('''
                ALTER TABLE objetivos 
                ADD parte_dia NVARCHAR(10) NULL
            ''')
            
            conn.commit()
            print("✅ Columna 'parte_dia' agregada exitosamente")
        else:
            print("ℹ️ La columna 'parte_dia' ya existe")
            
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_add_parte_dia()