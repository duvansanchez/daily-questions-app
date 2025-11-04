#!/usr/bin/env python3
"""
Test directo del endpoint sin autenticación web
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from datetime import datetime

def test_endpoint_directo(fecha, user_id=3):
    """Simular el endpoint directamente"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print(f"🧪 Probando endpoint para fecha: {fecha}, usuario: {user_id}")
            
            # Obtener objetivos creados en esta fecha
            query_creados = """
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad, 
                       o.recurrente, o.parte_dia, o.horas_estimadas,
                       CONVERT(varchar, o.fecha_creacion, 120) as fecha_creacion
                FROM objetivos o
                WHERE o.user_id = ? AND CAST(o.fecha_creacion AS DATE) = ?
                ORDER BY o.fecha_creacion DESC
            """
            
            cursor.execute(query_creados, (user_id, fecha))
            objetivos_creados = []
            for row in cursor.fetchall():
                objetivos_creados.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'categoria': row.categoria,
                    'prioridad': row.prioridad,
                    'recurrente': bool(row.recurrente) if row.recurrente else False,
                    'parte_dia': row.parte_dia,
                    'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                    'fecha_creacion': row.fecha_creacion
                })
            
            print(f"📝 Objetivos creados: {len(objetivos_creados)}")
            for obj in objetivos_creados:
                print(f"  - {obj['titulo']} ({obj['categoria']})")
            
            # Obtener objetivos completados en esta fecha
            # Simplificamos la consulta para evitar problemas con DISTINCT y ORDER BY
            query_completados = """
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       o.parte_dia, o.horas_estimadas,
                       CASE WHEN o.recurrente = 1 THEN 'recurrente' ELSE 'normal' END as tipo,
                       CONVERT(varchar, o.fecha_completado, 108) as hora_completado,
                       CONVERT(varchar, o.fecha_completado, 120) as fecha_completado
                FROM objetivos o
                WHERE o.user_id = ? 
                AND o.recurrente = 0 
                AND CAST(o.fecha_completado AS DATE) = ?
                AND o.completado = 1
                
                UNION ALL
                
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       o.parte_dia, o.horas_estimadas,
                       'recurrente' as tipo,
                       CONVERT(varchar, ocl.fecha_completado, 108) as hora_completado,
                       CONVERT(varchar, ocl.fecha_completado, 120) as fecha_completado
                FROM objetivos o
                INNER JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
                WHERE o.user_id = ? 
                AND o.recurrente = 1
                AND CAST(ocl.fecha_completado AS DATE) = ?
                
                ORDER BY fecha_completado DESC
            """
            
            cursor.execute(query_completados, (user_id, fecha, user_id, fecha))
            objetivos_completados = []
            for row in cursor.fetchall():
                objetivos_completados.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'categoria': row.categoria,
                    'prioridad': row.prioridad,
                    'parte_dia': row.parte_dia,
                    'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                    'tipo': row.tipo,
                    'hora_completado': row.hora_completado,
                    'fecha_completado': row.fecha_completado
                })
            
            print(f"✅ Objetivos completados: {len(objetivos_completados)}")
            for obj in objetivos_completados:
                print(f"  - {obj['titulo']} ({obj['categoria']})")
            
            resumen = {
                'total_creados': len(objetivos_creados),
                'total_completados': len(objetivos_completados)
            }
            
            resultado = {
                'status': 'success',
                'fecha': fecha,
                'resumen': resumen,
                'objetivos_creados': objetivos_creados,
                'objetivos_completados': objetivos_completados
            }
            
            print(f"\n📊 Resumen:")
            print(f"  - Total creados: {resumen['total_creados']}")
            print(f"  - Total completados: {resumen['total_completados']}")
            
            return resultado
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Probar con diferentes fechas
    fechas = ['2025-11-01', '2025-10-31', '2025-10-30']
    
    for fecha in fechas:
        print(f"\n{'='*50}")
        print(f"PROBANDO FECHA: {fecha}")
        print('='*50)
        resultado = test_endpoint_directo(fecha)
        if resultado:
            print("✅ Endpoint funcionando correctamente")
        else:
            print("❌ Error en el endpoint")