"""
Script de migración para agregar columna 'descripcion' a la tabla subcategorias
"""
import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

def migrate():
    try:
        # Conectar a la base de datos
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER=.\\SQLEXPRESS;"
            f"DATABASE=DailyQuestions;"
            f"UID=sa;"
            f"PWD=123;"
            f"TrustServerCertificate=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("🔍 Verificando si la columna 'descripcion' existe en subcategorias...")
        
        # Verificar si la columna ya existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'subcategorias' 
            AND COLUMN_NAME = 'descripcion'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✅ La columna 'descripcion' ya existe en la tabla subcategorias")
        else:
            print("📝 Agregando columna 'descripcion' a la tabla subcategorias...")
            
            # Agregar la columna descripcion
            cursor.execute("""
                ALTER TABLE subcategorias
                ADD descripcion NVARCHAR(500) NULL
            """)
            
            conn.commit()
            print("✅ Columna 'descripcion' agregada exitosamente")
        
        # Mostrar estructura actualizada
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'subcategorias'
            ORDER BY ORDINAL_POSITION
        """)
        
        print("\n📋 Estructura actual de la tabla subcategorias:")
        for row in cursor.fetchall():
            nullable = "NULL" if row[3] == "YES" else "NOT NULL"
            max_length = f"({row[2]})" if row[2] else ""
            print(f"  - {row[0]}: {row[1]}{max_length} {nullable}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Migración completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
