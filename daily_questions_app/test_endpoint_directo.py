#!/usr/bin/env python3
"""
Script para probar directamente el endpoint que está fallando
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

def test_endpoint_directo():
    """Prueba directamente la lógica del endpoint que está fallando"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Simular el endpoint /api/objetivos/dia/2025-12-10
        fecha = '2025-12-10'
        user_id = 3  # Usuario de prueba
        
        print(f"🧪 Probando endpoint para fecha: {fecha}, user_id: {user_id}")
        
        # 1. Objetivos creados
        print("📋 1. Probando query objetivos creados...")
        query_creados = """
            SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad, 
                   o.recurrente, o.parte_dia, o.horas_estimadas,
                   CONVERT(varchar, o.fecha_creacion, 120) as fecha_creacion
            FROM objetivos o
            WHERE o.user_id = ? AND CAST(o.fecha_creacion AS DATE) = ?
            ORDER BY o.fecha_creacion DESC
        """
        
        cursor.execute(query_creados, (user_id, fecha))
        objetivos_creados = cursor.fetchall()
        print(f"   ✅ Objetivos creados: {len(objetivos_creados)}")
        
        # 2. Objetivos completados
        print("✅ 2. Probando query objetivos completados...")
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
        objetivos_completados = cursor.fetchall()
        print(f"   ✅ Objetivos completados: {len(objetivos_completados)}")
        
        # 3. Objetivos recurrentes pendientes
        print("⏳ 3. Probando query objetivos recurrentes pendientes...")
        query_recurrentes_pendientes = """
            SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad, 
                   o.recurrente, o.parte_dia, o.horas_estimadas,
                   CONVERT(varchar, o.fecha_creacion, 120) as fecha_creacion
            FROM objetivos o
            WHERE o.user_id = ?
              AND o.recurrente = 1
              AND o.estado != 'histórico'
              AND LOWER(COALESCE(o.categoria, '')) = 'diario'
              AND CAST(o.fecha_creacion AS DATE) <= ?
              AND NOT EXISTS (
                  SELECT 1 FROM objetivos_completados_log ocl 
                  WHERE ocl.objetivo_id = o.id 
                    AND ocl.user_id = o.user_id 
                    AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
              )
            ORDER BY o.fecha_creacion DESC
        """
        
        cursor.execute(query_recurrentes_pendientes, (user_id, fecha, fecha))
        objetivos_recurrentes = cursor.fetchall()
        print(f"   ✅ Objetivos recurrentes pendientes: {len(objetivos_recurrentes)}")
        
        # 4. NUEVA FUNCIONALIDAD: Subobjetivos completados
        print("🎯 4. Probando query subobjetivos completados...")
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
        subobjetivos_completados = cursor.fetchall()
        print(f"   ✅ Subobjetivos completados: {len(subobjetivos_completados)}")
        
        print("\n📊 RESUMEN:")
        print(f"   - Objetivos creados: {len(objetivos_creados)}")
        print(f"   - Objetivos completados: {len(objetivos_completados)}")
        print(f"   - Objetivos recurrentes pendientes: {len(objetivos_recurrentes)}")
        print(f"   - Subobjetivos completados: {len(subobjetivos_completados)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_endpoint_directo()