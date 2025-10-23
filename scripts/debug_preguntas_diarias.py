#!/usr/bin/env python3
"""
Script para debuggear el problema con preguntas diarias.
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

def debug_preguntas():
    """
    Debug del problema con preguntas diarias
    """
    print("=== Debug Preguntas Diarias ===")
    print(f"Fecha y hora: {datetime.now()}")
    print()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Ver todas las preguntas activas
        print("1. Todas las preguntas activas:")
        cursor.execute("""
            SELECT id, text, frecuencia, assigned_user_id, active
            FROM question 
            WHERE active = 1
            ORDER BY assigned_user_id, id
        """)
        
        preguntas = cursor.fetchall()
        if preguntas:
            for p in preguntas:
                freq = p[2] if p[2] else "NULL"
                print(f"   ID {p[0]} - User {p[3]} - Freq: {freq} - {p[1][:50]}...")
        else:
            print("   No hay preguntas activas")
        
        print()
        
        # 2. Contar preguntas por frecuencia (incluyendo NULL)
        print("2. Conteo por frecuencia:")
        cursor.execute("""
            SELECT 
                COALESCE(frecuencia, 'NULL') as freq,
                COUNT(*) as count
            FROM question 
            WHERE active = 1
            GROUP BY frecuencia
            ORDER BY count DESC
        """)
        
        counts = cursor.fetchall()
        for c in counts:
            print(f"   {c[0]}: {c[1]} preguntas")
        
        print()
        
        # 3. Ver qué devuelve la consulta de preguntas diarias
        print("3. Consulta de preguntas diarias (frecuencia = 'diaria'):")
        cursor.execute("""
            SELECT id, text, frecuencia
            FROM question 
            WHERE active = 1 AND frecuencia = 'diaria'
        """)
        
        diarias = cursor.fetchall()
        if diarias:
            for d in diarias:
                print(f"   ID {d[0]} - {d[1][:50]}...")
        else:
            print("   No hay preguntas con frecuencia = 'diaria'")
        
        print()
        
        # 4. Ver qué devuelve la consulta original (sin filtro de frecuencia)
        print("4. Consulta original (sin filtro de frecuencia):")
        cursor.execute("""
            SELECT id, text, frecuencia
            FROM question 
            WHERE active = 1
        """)
        
        todas = cursor.fetchall()
        if todas:
            for t in todas:
                freq = t[2] if t[2] else "NULL"
                print(f"   ID {t[0]} - Freq: {freq} - {t[1][:50]}...")
        else:
            print("   No hay preguntas activas")
        
        print()
        
        # 5. Proponer solución
        print("5. Análisis y solución:")
        if not diarias and todas:
            print("   ❌ PROBLEMA: Hay preguntas activas pero ninguna tiene frecuencia = 'diaria'")
            print("   💡 SOLUCIÓN: Actualizar preguntas existentes para que tengan frecuencia = 'diaria'")
            print()
            print("   ¿Quieres actualizar las preguntas existentes? (y/n): ", end="")
            respuesta = input().lower().strip()
            
            if respuesta == 'y':
                cursor.execute("""
                    UPDATE question 
                    SET frecuencia = 'diaria' 
                    WHERE frecuencia IS NULL AND active = 1
                """)
                affected = cursor.rowcount
                conn.commit()
                print(f"   ✅ {affected} preguntas actualizadas a frecuencia 'diaria'")
            else:
                print("   ⏭️ No se realizaron cambios")
        elif diarias:
            print("   ✅ Hay preguntas diarias configuradas correctamente")
        else:
            print("   ⚠️ No hay preguntas activas en el sistema")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error durante el debug: {str(e)}")
        return False

if __name__ == "__main__":
    debug_preguntas()