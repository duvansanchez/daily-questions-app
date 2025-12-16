#!/usr/bin/env python3
"""
Script para debuggear el endpoint completo simulando la consulta exacta
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
    """Simula exactamente lo que hace el endpoint /api/objetivos/dia/<fecha>"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener un user_id válido
        cursor.execute("SELECT TOP 1 id FROM [user] WHERE id IS NOT NULL")
        user_row = cursor.fetchone()
        if not user_row:
            print("❌ No se encontró ningún usuario")
            return False
        
        user_id = user_row.id
        fecha = datetime.now().strftime('%Y-%m-%d')
        
        print(f"🧪 Simulando endpoint para user_id={user_id}, fecha={fecha}")
        print("=" * 60)
        
        # 1. Objetivos creados
        print("📋 1. OBJETIVOS CREADOS:")
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
        print(f"   Encontrados: {len(objetivos_creados)}")
        for obj in objetivos_creados:
            print(f"   - {obj.titulo}")
        
        # 2. Objetivos completados
        print("\n✅ 2. OBJETIVOS COMPLETADOS:")
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
        print(f"   Encontrados: {len(objetivos_completados)}")
        for obj in objetivos_completados:
            print(f"   - {obj.titulo} ({obj.tipo}) - {obj.hora_completado}")
        
        # 3. Objetivos recurrentes pendientes
        print("\n⏳ 3. OBJETIVOS RECURRENTES PENDIENTES:")
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
        print(f"   Encontrados: {len(objetivos_recurrentes)}")
        for obj in objetivos_recurrentes:
            print(f"   - {obj.titulo}")
        
        # 4. SUBOBJETIVOS COMPLETADOS (LA NUEVA FUNCIONALIDAD)
        print("\n🎯 4. SUBOBJETIVOS COMPLETADOS:")
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
        print(f"   Encontrados: {len(subobjetivos_completados)}")
        for sub in subobjetivos_completados:
            print(f"   - {sub.titulo} ({sub.objetivo_titulo}) - {sub.hora_completado}")
        
        # 5. Simular la respuesta JSON completa
        print("\n📦 5. RESPUESTA JSON SIMULADA:")
        respuesta_simulada = {
            'status': 'success',
            'fecha': fecha,
            'resumen': {
                'total_creados': len(objetivos_creados),
                'total_completados': len(objetivos_completados),
                'total_recurrentes_pendientes': len(objetivos_recurrentes),
                'total_subobjetivos_completados': len(subobjetivos_completados)
            },
            'objetivos_creados': len(objetivos_creados),
            'objetivos_completados': len(objetivos_completados),
            'objetivos_recurrentes_pendientes': len(objetivos_recurrentes),
            'subobjetivos_completados': len(subobjetivos_completados)
        }
        
        print(f"   Status: {respuesta_simulada['status']}")
        print(f"   Fecha: {respuesta_simulada['fecha']}")
        print("   Resumen:")
        for key, value in respuesta_simulada['resumen'].items():
            print(f"     - {key}: {value}")
        
        # 6. Verificar si hay objetivos con subobjetivos completados
        if len(subobjetivos_completados) > 0:
            print(f"\n🔍 6. ANÁLISIS DE SUBOBJETIVOS POR OBJETIVO:")
            objetivos_con_subs = {}
            for sub in subobjetivos_completados:
                obj_id = sub.objetivo_id
                if obj_id not in objetivos_con_subs:
                    objetivos_con_subs[obj_id] = {
                        'titulo': sub.objetivo_titulo,
                        'subobjetivos': []
                    }
                objetivos_con_subs[obj_id]['subobjetivos'].append({
                    'titulo': sub.titulo,
                    'hora': sub.hora_completado
                })
            
            for obj_id, data in objetivos_con_subs.items():
                print(f"   Objetivo ID {obj_id}: {data['titulo']}")
                for sub in data['subobjetivos']:
                    print(f"     ✅ {sub['titulo']} - {sub['hora']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    simular_endpoint_completo()