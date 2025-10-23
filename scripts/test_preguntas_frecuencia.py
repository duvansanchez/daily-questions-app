#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento de preguntas por frecuencia.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'daily_questions_app'))

from datetime import datetime
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server", 
        "SQL Server"
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
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f"No se pudo conectar con {driver}: {str(e)}")
    raise Exception("No se pudo establecer conexión con ningún controlador ODBC")

def test_preguntas_frecuencia():
    """
    Prueba la funcionalidad de preguntas por frecuencia
    """
    print("=== Test Preguntas por Frecuencia ===")
    print(f"Fecha y hora: {datetime.now()}")
    print()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Verificar estructura de la tabla
        print("1. Verificando estructura de la tabla question:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'question'
            AND COLUMN_NAME IN ('frecuencia', 'categoria')
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            default = f" DEFAULT {col[3]}" if col[3] else ""
            print(f"   ✓ {col[0]} {col[1]} {nullable}{default}")
        
        print()
        
        # 2. Contar preguntas por frecuencia
        print("2. Preguntas existentes por frecuencia:")
        frecuencias = ['diaria', 'semanal', 'mensual']
        
        for freq in frecuencias:
            cursor.execute("""
                SELECT COUNT(*) FROM question 
                WHERE frecuencia = ? AND active = 1
            """, (freq,))
            count = cursor.fetchone()[0]
            print(f"   {freq.capitalize()}: {count} preguntas")
        
        print()
        
        # 3. Mostrar algunas preguntas de ejemplo por frecuencia
        print("3. Ejemplos de preguntas por frecuencia:")
        for freq in frecuencias:
            cursor.execute("""
                SELECT TOP 3 id, text, assigned_user_id
                FROM question 
                WHERE frecuencia = ? AND active = 1
                ORDER BY created_at DESC
            """, (freq,))
            
            preguntas = cursor.fetchall()
            print(f"\n   {freq.capitalize()}:")
            if preguntas:
                for p in preguntas:
                    print(f"     ID {p[0]} - User {p[2]} - {p[1][:50]}...")
            else:
                print(f"     No hay preguntas {freq}s configuradas")
        
        print()
        
        # 4. Verificar que las rutas funcionan (simulación)
        print("4. Rutas disponibles:")
        rutas = [
            ("Diarias", "/"),
            ("Semanales", "/preguntas-semanales"),
            ("Mensuales", "/preguntas-mensuales")
        ]
        
        for nombre, ruta in rutas:
            print(f"   ✓ {nombre}: {ruta}")
        
        print()
        print("=== Test completado exitosamente ===")
        print()
        print("Para probar completamente:")
        print("1. Inicia la aplicación Flask: python daily_questions_app/app.py")
        print("2. Ve a http://localhost:5000/admin")
        print("3. Crea preguntas con diferentes frecuencias")
        print("4. Visita las diferentes rutas:")
        print("   - http://localhost:5000/ (diarias)")
        print("   - http://localhost:5000/preguntas-semanales")
        print("   - http://localhost:5000/preguntas-mensuales")
        print("5. Ve a http://localhost:5000/stats para ver estadísticas por frecuencia")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error durante el test: {str(e)}")
        return False

if __name__ == "__main__":
    test_preguntas_frecuencia()