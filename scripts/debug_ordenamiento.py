#!/usr/bin/env python3
"""
Script para debuggear el ordenamiento de objetivos
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

def debug_ordenamiento():
    """
    Debug del ordenamiento de objetivos
    """
    print("=== Debug Ordenamiento Objetivos ===")
    print(f"Fecha y hora: {datetime.now()}")
    print()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoy = date.today()
        user_id = 3
        
        print("1. Consulta ANTES del cambio (orden original):")
        cursor.execute('''
            SELECT o.id, o.titulo, o.completado, o.orden
            FROM objetivos o
            WHERE o.user_id = ? 
            ORDER BY o.orden ASC, o.fecha_creacion DESC
        ''', (user_id,))
        
        objetivos_antes = cursor.fetchall()
        print("   Primeros 10 objetivos:")
        for i, obj in enumerate(objetivos_antes[:10]):
            estado = "COMPLETADO" if obj[2] else "ACTIVO"
            print(f"     {i+1}. ID {obj[0]} - {estado} - Orden: {obj[3]} - {obj[1][:30]}...")
        
        print()
        
        print("2. Consulta DESPUÉS del cambio (completados al final):")
        cursor.execute('''
            SELECT o.id, o.titulo, o.completado, o.orden
            FROM objetivos o
            WHERE o.user_id = ? 
            ORDER BY o.completado ASC, o.orden ASC, o.fecha_creacion DESC
        ''', (user_id,))
        
        objetivos_despues = cursor.fetchall()
        print("   Primeros 10 objetivos:")
        for i, obj in enumerate(objetivos_despues[:10]):
            estado = "COMPLETADO" if obj[2] else "ACTIVO"
            print(f"     {i+1}. ID {obj[0]} - {estado} - Orden: {obj[3]} - {obj[1][:30]}...")
        
        print()
        
        print("3. Comparación:")
        if objetivos_antes != objetivos_despues:
            print("   ✅ El ordenamiento SÍ cambió")
            
            # Encontrar diferencias
            completados_antes = [obj for obj in objetivos_antes if obj[2]]
            completados_despues = [obj for obj in objetivos_despues if obj[2]]
            
            print(f"   Completados antes: posiciones variadas")
            print(f"   Completados después: últimas {len(completados_despues)} posiciones")
            
        else:
            print("   ❌ El ordenamiento NO cambió")
        
        print()
        
        print("4. Verificar si hay objetivos completados:")
        cursor.execute('''
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN completado = 1 THEN 1 ELSE 0 END) as completados
            FROM objetivos 
            WHERE user_id = ?
        ''', (user_id,))
        
        stats = cursor.fetchone()
        print(f"   Total objetivos: {stats[0]}")
        print(f"   Objetivos completados: {stats[1]}")
        
        if stats[1] == 0:
            print("   ⚠️ No hay objetivos completados, por eso no se ve diferencia")
        
        print()
        
        print("5. Últimos 10 objetivos (deberían ser completados si los hay):")
        for i, obj in enumerate(objetivos_despues[-10:], len(objetivos_despues)-9):
            estado = "COMPLETADO" if obj[2] else "ACTIVO"
            print(f"     {i}. ID {obj[0]} - {estado} - Orden: {obj[3]} - {obj[1][:30]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error durante el debug: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_ordenamiento()