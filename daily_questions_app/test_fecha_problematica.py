#!/usr/bin/env python3
"""
Test específico para fechas problemáticas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from datetime import datetime, timedelta

def test_fecha_especifica(fecha, user_id=3):
    """Probar una fecha específica que está causando problemas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print(f"🧪 Probando fecha problemática: {fecha}")
            
            # Primero, veamos qué objetivos existen para esta fecha
            cursor.execute("""
                SELECT id, titulo, fecha_creacion, fecha_completado, completado, recurrente
                FROM objetivos 
                WHERE user_id = ? 
                AND (CAST(fecha_creacion AS DATE) = ? OR CAST(fecha_completado AS DATE) = ?)
            """, (user_id, fecha, fecha))
            
            objetivos = cursor.fetchall()
            print(f"📋 Objetivos encontrados: {len(objetivos)}")
            
            for obj in objetivos:
                print(f"  - ID: {obj.id}, Título: {obj.titulo}")
                print(f"    Creación: {obj.fecha_creacion}")
                print(f"    Completado: {obj.fecha_completado}")
                print(f"    Estado: {'Completado' if obj.completado else 'Pendiente'}")
                print(f"    Recurrente: {'Sí' if obj.recurrente else 'No'}")
                print()
            
            # Ahora probemos la consulta de objetivos completados paso a paso
            print("🔍 Probando consulta de objetivos completados...")
            
            # Parte 1: Objetivos normales completados
            try:
                cursor.execute("""
                    SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                           o.parte_dia, o.horas_estimadas,
                           'normal' as tipo,
                           ISNULL(FORMAT(o.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                           ISNULL(FORMAT(o.fecha_completado, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_completado
                    FROM objetivos o
                    WHERE o.user_id = ? 
                    AND (o.recurrente = 0 OR o.recurrente IS NULL)
                    AND o.fecha_completado IS NOT NULL
                    AND TRY_CAST(o.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                    AND o.completado = 1
                """, (user_id, fecha))
                
                normales = cursor.fetchall()
                print(f"✅ Objetivos normales completados: {len(normales)}")
                for obj in normales:
                    print(f"  - {obj.titulo} ({obj.hora_completado})")
                    
            except Exception as e:
                print(f"❌ Error en objetivos normales: {e}")
            
            # Parte 2: Objetivos recurrentes completados
            try:
                cursor.execute("""
                    SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                           o.parte_dia, o.horas_estimadas,
                           'recurrente' as tipo,
                           ISNULL(FORMAT(ocl.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                           ISNULL(FORMAT(ocl.fecha_completado, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_completado
                    FROM objetivos o
                    INNER JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
                    WHERE o.user_id = ? 
                    AND o.recurrente = 1
                    AND ocl.fecha_completado IS NOT NULL
                    AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                """, (user_id, fecha))
                
                recurrentes = cursor.fetchall()
                print(f"✅ Objetivos recurrentes completados: {len(recurrentes)}")
                for obj in recurrentes:
                    print(f"  - {obj.titulo} ({obj.hora_completado})")
                    
            except Exception as e:
                print(f"❌ Error en objetivos recurrentes: {e}")
            
            # Ahora probemos la consulta completa
            print("\n🔄 Probando consulta completa...")
            try:
                query_completados = """
                    SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                           o.parte_dia, o.horas_estimadas,
                           'normal' as tipo,
                           ISNULL(FORMAT(o.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                           ISNULL(FORMAT(o.fecha_completado, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_completado
                    FROM objetivos o
                    WHERE o.user_id = ? 
                    AND (o.recurrente = 0 OR o.recurrente IS NULL)
                    AND o.fecha_completado IS NOT NULL
                    AND TRY_CAST(o.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                    AND o.completado = 1
                    
                    UNION ALL
                    
                    SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                           o.parte_dia, o.horas_estimadas,
                           'recurrente' as tipo,
                           ISNULL(FORMAT(ocl.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                           ISNULL(FORMAT(ocl.fecha_completado, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_completado
                    FROM objetivos o
                    INNER JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
                    WHERE o.user_id = ? 
                    AND o.recurrente = 1
                    AND ocl.fecha_completado IS NOT NULL
                    AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                    
                    ORDER BY fecha_completado DESC
                """
                
                cursor.execute(query_completados, (user_id, fecha, user_id, fecha))
                todos_completados = cursor.fetchall()
                print(f"✅ Consulta completa exitosa: {len(todos_completados)} objetivos")
                
                return True
                
            except Exception as e:
                print(f"❌ Error en consulta completa: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Probar fechas problemáticas
    fechas_problema = [
        '2025-10-31',  # Esta fecha estaba dando problemas
        '2025-10-30',
        '2025-11-01',
        '2024-10-31',  # Fecha del año pasado
        '2024-11-01'
    ]
    
    for fecha in fechas_problema:
        print(f"\n{'='*60}")
        print(f"PROBANDO FECHA PROBLEMÁTICA: {fecha}")
        print('='*60)
        
        resultado = test_fecha_especifica(fecha)
        if resultado:
            print("✅ Fecha procesada correctamente")
        else:
            print("❌ Error en el procesamiento de la fecha")
        
        print()