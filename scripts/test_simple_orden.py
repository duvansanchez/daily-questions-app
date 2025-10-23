#!/usr/bin/env python3
"""
Test simple para verificar el orden de objetivos
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'daily_questions_app'))

from datetime import datetime, date
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

def test_orden_simple():
    """
    Test simple del orden
    """
    print("=== Test Simple de Orden ===")
    print()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoy = date.today()
        user_id = 3
        
        print("Ejecutando la misma consulta que usa la aplicación:")
        cursor.execute('''
            SELECT o.id, o.titulo, o.completado, o.orden,
                   CASE WHEN os.objetivo_id IS NOT NULL THEN 1 ELSE 0 END as saltado_hoy
            FROM objetivos o
            LEFT JOIN objetivos_saltados os ON o.id = os.objetivo_id AND os.user_id = o.user_id AND os.fecha_saltada = ?
            WHERE o.user_id = ? 
            ORDER BY 
                o.completado ASC,
                o.orden ASC, 
                o.fecha_creacion DESC
        ''', (hoy, user_id))
        
        objetivos = cursor.fetchall()
        
        print(f"Total objetivos: {len(objetivos)}")
        print()
        
        # Mostrar los primeros 15 para ver el patrón
        print("Primeros 15 objetivos:")
        for i, obj in enumerate(objetivos[:15]):
            completado = "✅ COMPLETADO" if obj[2] else "⭕ PENDIENTE"
            saltado = " (SALTADO)" if obj[4] else ""
            print(f"  {i+1:2d}. ID {obj[0]} - {completado}{saltado} - Orden: {obj[3]} - {obj[1][:35]}...")
        
        print()
        
        # Verificar si hay completados en los primeros 15
        completados_en_primeros = sum(1 for obj in objetivos[:15] if obj[2])
        if completados_en_primeros > 0:
            print(f"❌ PROBLEMA: Hay {completados_en_primeros} objetivos completados en los primeros 15")
        else:
            print("✅ CORRECTO: No hay objetivos completados en los primeros 15")
        
        print()
        
        # Mostrar los últimos 10
        print("Últimos 10 objetivos:")
        for i, obj in enumerate(objetivos[-10:], len(objetivos)-9):
            completado = "✅ COMPLETADO" if obj[2] else "⭕ PENDIENTE"
            saltado = " (SALTADO)" if obj[4] else ""
            print(f"  {i:2d}. ID {obj[0]} - {completado}{saltado} - Orden: {obj[3]} - {obj[1][:35]}...")
        
        print()
        
        # Contar completados en los últimos 10
        completados_en_ultimos = sum(1 for obj in objetivos[-10:] if obj[2])
        print(f"Completados en los últimos 10: {completados_en_ultimos}")
        
        # Estadísticas finales
        total_completados = sum(1 for obj in objetivos if obj[2])
        total_saltados = sum(1 for obj in objetivos if obj[4])
        total_activos = len(objetivos) - total_completados
        
        print()
        print("=== RESUMEN ===")
        print(f"Total objetivos: {len(objetivos)}")
        print(f"Activos (incluye saltados): {total_activos}")
        print(f"Completados: {total_completados}")
        print(f"Saltados hoy: {total_saltados}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_orden_simple()