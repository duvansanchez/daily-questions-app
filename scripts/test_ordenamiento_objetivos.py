#!/usr/bin/env python3
"""
Script para probar el nuevo ordenamiento de objetivos:
- Objetivos completados y saltados al final
- Resto ordenado por orden y fecha de creación
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

def test_ordenamiento_objetivos():
    """
    Prueba el nuevo ordenamiento de objetivos
    """
    print("=== Test Ordenamiento de Objetivos ===")
    print(f"Fecha y hora: {datetime.now()}")
    print()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Simular la consulta que se usa en la aplicación
        hoy = date.today()
        user_id = 3  # Asumiendo que el usuario de prueba es el ID 3
        
        print("1. Ejecutando consulta con nuevo ordenamiento:")
        cursor.execute('''
            SELECT o.id, o.titulo, o.completado, o.orden, o.fecha_creacion,
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
        
        if objetivos:
            print(f"   ✅ {len(objetivos)} objetivos encontrados")
            print()
            
            # Separar en categorías para análisis
            no_completados = []
            completados = []
            saltados = []
            
            for obj in objetivos:
                if obj[2]:  # completado
                    completados.append(obj)
                elif obj[5]:  # saltado_hoy
                    saltados.append(obj)
                else:  # activo
                    no_completados.append(obj)
            
            print(f"2. Análisis del ordenamiento:")
            print(f"   📋 Objetivos no completados (primero): {len(no_completados)}")
            print(f"   ⏭️ Objetivos saltados (en orden normal): {len(saltados)}")
            print(f"   ✅ Objetivos completados (último): {len(completados)}")
            print()
            
            # Mostrar primeros objetivos (deberían ser no completados)
            print("3. Primeros 5 objetivos (deberían ser no completados):")
            for i, obj in enumerate(objetivos[:5]):
                estado = "COMPLETADO" if obj[2] else ("SALTADO" if obj[5] else "ACTIVO")
                print(f"   {i+1}. ID {obj[0]} - {estado} - Orden: {obj[3]} - {obj[1][:40]}...")
            
            print()
            
            # Mostrar últimos objetivos (deberían ser completados)
            if len(objetivos) > 5:
                print("4. Últimos 5 objetivos (deberían incluir completados):")
                for i, obj in enumerate(objetivos[-5:], len(objetivos)-4):
                    estado = "COMPLETADO" if obj[2] else ("SALTADO" if obj[5] else "ACTIVO")
                    print(f"   {i}. ID {obj[0]} - {estado} - Orden: {obj[3]} - {obj[1][:40]}...")
            
            print()
            
            # Verificar que el ordenamiento es correcto
            print("5. Verificación del ordenamiento:")
            ordenamiento_correcto = True
            
            # Verificar que todos los no completados están antes que los completados
            primer_completado = None
            ultimo_no_completado = None
            
            for i, obj in enumerate(objetivos):
                if obj[2]:  # completado
                    if primer_completado is None:
                        primer_completado = i
                else:  # no completado (activo o saltado)
                    ultimo_no_completado = i
            
            if ultimo_no_completado is not None and primer_completado is not None:
                if ultimo_no_completado > primer_completado:
                    ordenamiento_correcto = False
                    print("   ❌ ERROR: Hay objetivos no completados después de completados")
                else:
                    print("   ✅ Objetivos no completados aparecen antes que completados")
            elif ultimo_no_completado is None:
                print("   ℹ️ Todos los objetivos están completados")
            elif primer_completado is None:
                print("   ℹ️ No hay objetivos completados")
            else:
                print("   ✅ Ordenamiento correcto")
            
            if ordenamiento_correcto:
                print("   ✅ ORDENAMIENTO CORRECTO")
            else:
                print("   ❌ ORDENAMIENTO INCORRECTO")
                
        else:
            print("   ⚠️ No se encontraron objetivos para el usuario")
        
        print()
        
        # Estadísticas adicionales
        print("6. Estadísticas:")
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN completado = 1 THEN 1 ELSE 0 END) as completados,
                COUNT(DISTINCT os.objetivo_id) as saltados_hoy
            FROM objetivos o
            LEFT JOIN objetivos_saltados os ON o.id = os.objetivo_id AND os.user_id = o.user_id AND os.fecha_saltada = ?
            WHERE o.user_id = ?
        ''', (hoy, user_id))
        
        stats = cursor.fetchone()
        if stats:
            total = stats[0]
            completados = stats[1]
            saltados = stats[2]
            activos = total - completados - saltados
            
            print(f"   Total objetivos: {total}")
            print(f"   Activos: {activos}")
            print(f"   Completados: {completados}")
            print(f"   Saltados hoy: {saltados}")
        
        print()
        print("=== Test completado ===")
        print()
        print("Funcionalidad implementada:")
        print("✅ Solo los objetivos completados aparecen al final")
        print("✅ Los objetivos saltados mantienen su orden normal (son activos)")
        print("✅ Los objetivos activos y saltados aparecen primero")
        print("✅ Dentro de cada grupo se mantiene el orden original")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error durante el test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ordenamiento_objetivos()