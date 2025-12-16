#!/usr/bin/env python3
"""
Script para probar el endpoint directamente simulando la función
"""

import pyodbc
import sys
import os
from datetime import datetime

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-2MR0PJ6;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def simular_endpoint_completo():
    """Simula exactamente el endpoint con la nueva función comentada"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        fecha = '2025-12-15'
        user_id = 3
        
        print(f"🧪 Simulando endpoint completo para fecha: {fecha}, user_id: {user_id}")
        
        # 1. Objetivos creados
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
                'recurrente': bool(row.recurrente),
                'parte_dia': row.parte_dia,
                'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                'fecha_creacion': row.fecha_creacion
            })
        
        print(f"✅ Objetivos creados: {len(objetivos_creados)}")
        
        # 2. Objetivos completados (query simplificada)
        objetivos_completados = []
        print(f"✅ Objetivos completados: {len(objetivos_completados)}")
        
        # 3. Objetivos recurrentes pendientes (query simplificada)
        objetivos_recurrentes_pendientes = []
        print(f"✅ Objetivos recurrentes pendientes: {len(objetivos_recurrentes_pendientes)}")
        
        # 4. Subobjetivos completados
        query_subobjetivos = """
            SELECT s.id, s.titulo, s.objetivo_id, o.titulo as objetivo_titulo,
                   scl.fecha_completado, 
                   FORMAT(scl.fecha_creacion, 'HH:mm:ss') as hora_completado
            FROM subobjetivos s
            INNER JOIN subobjetivos_completados_log scl ON s.id = scl.subobjetivo_id
            INNER JOIN objetivos o ON s.objetivo_id = o.id
            WHERE scl.user_id = ? 
              AND CAST(scl.fecha_completado AS DATE) = CAST(? AS DATE)
            ORDER BY scl.fecha_creacion ASC
        """
        
        cursor.execute(query_subobjetivos, (user_id, fecha))
        subobjetivos_completados = []
        for row in cursor.fetchall():
            subobjetivos_completados.append({
                'id': row.id,
                'titulo': row.titulo,
                'objetivo_id': row.objetivo_id,
                'objetivo_titulo': row.objetivo_titulo,
                'fecha_completado': fecha,
                'hora_completado': row.hora_completado
            })
        
        print(f"✅ Subobjetivos completados: {len(subobjetivos_completados)}")
        
        # 5. Todos los subobjetivos (comentado)
        todos_los_subobjetivos = []
        print(f"✅ Todos los subobjetivos: {len(todos_los_subobjetivos)} (comentado)")
        
        # 6. Resumen
        resumen = {
            'total_creados': len(objetivos_creados),
            'total_completados': len(objetivos_completados),
            'total_recurrentes_pendientes': len(objetivos_recurrentes_pendientes),
            'total_subobjetivos_completados': len(subobjetivos_completados)
        }
        
        # 7. Respuesta simulada
        respuesta = {
            'status': 'success',
            'fecha': fecha,
            'resumen': resumen,
            'objetivos_creados': objetivos_creados,
            'objetivos_completados': objetivos_completados,
            'objetivos_recurrentes_pendientes': objetivos_recurrentes_pendientes,
            'subobjetivos_completados': subobjetivos_completados,
            'todos_los_subobjetivos': todos_los_subobjetivos
        }
        
        print("\n📦 RESPUESTA SIMULADA:")
        print(f"   Status: {respuesta['status']}")
        print(f"   Fecha: {respuesta['fecha']}")
        print("   Resumen:")
        for key, value in respuesta['resumen'].items():
            print(f"     - {key}: {value}")
        
        conn.close()
        print("\n✅ Simulación completada sin errores")
        return True
        
    except Exception as e:
        print(f"❌ Error en simulación: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    simular_endpoint_completo()