#!/usr/bin/env python3
"""
Script para debuggear el objetivo específico que tiene subobjetivos completados
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

def debug_objetivo_especifico():
    """Debuggea el objetivo específico que tiene subobjetivos completados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user_id = 3  # Del debug anterior
        fecha = datetime.now().strftime('%Y-%m-%d')
        objetivo_id = 1015  # "Trabajar en el proyecto de Daily Questions"
        
        print(f"🔍 Debuggeando objetivo ID {objetivo_id} para fecha {fecha}")
        print("=" * 60)
        
        # 1. Verificar información básica del objetivo
        print("📋 1. INFORMACIÓN DEL OBJETIVO:")
        cursor.execute("""
            SELECT id, titulo, descripcion, categoria, prioridad, recurrente, 
                   estado, fecha_creacion, fecha_completado, completado, user_id
            FROM objetivos 
            WHERE id = ?
        """, (objetivo_id,))
        
        objetivo = cursor.fetchone()
        if objetivo:
            print(f"   ID: {objetivo.id}")
            print(f"   Título: {objetivo.titulo}")
            print(f"   Categoría: {objetivo.categoria}")
            print(f"   Recurrente: {objetivo.recurrente}")
            print(f"   Estado: {objetivo.estado}")
            print(f"   Completado: {objetivo.completado}")
            print(f"   User ID: {objetivo.user_id}")
            print(f"   Fecha creación: {objetivo.fecha_creacion}")
            print(f"   Fecha completado: {objetivo.fecha_completado}")
        else:
            print("   ❌ Objetivo no encontrado")
            return False
        
        # 2. Verificar si aparece en "objetivos creados"
        print(f"\n📅 2. ¿APARECE EN OBJETIVOS CREADOS PARA {fecha}?")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM objetivos o
            WHERE o.id = ? AND o.user_id = ? AND CAST(o.fecha_creacion AS DATE) = ?
        """, (objetivo_id, user_id, fecha))
        
        en_creados = cursor.fetchone()[0]
        print(f"   En objetivos creados: {'✅ SÍ' if en_creados > 0 else '❌ NO'}")
        
        # 3. Verificar si aparece en "objetivos completados"
        print(f"\n✅ 3. ¿APARECE EN OBJETIVOS COMPLETADOS PARA {fecha}?")
        
        # Verificar objetivos normales completados
        cursor.execute("""
            SELECT COUNT(*) 
            FROM objetivos o
            WHERE o.id = ? AND o.user_id = ? 
            AND (o.recurrente = 0 OR o.recurrente IS NULL)
            AND o.fecha_completado IS NOT NULL
            AND TRY_CAST(o.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
            AND o.completado = 1
        """, (objetivo_id, user_id, fecha))
        
        en_completados_normal = cursor.fetchone()[0]
        print(f"   En completados normales: {'✅ SÍ' if en_completados_normal > 0 else '❌ NO'}")
        
        # Verificar objetivos recurrentes completados
        cursor.execute("""
            SELECT COUNT(*) 
            FROM objetivos o
            INNER JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
            WHERE o.id = ? AND o.user_id = ? 
            AND o.recurrente = 1
            AND ocl.fecha_completado IS NOT NULL
            AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
        """, (objetivo_id, user_id, fecha))
        
        en_completados_recurrente = cursor.fetchone()[0]
        print(f"   En completados recurrentes: {'✅ SÍ' if en_completados_recurrente > 0 else '❌ NO'}")
        
        # 4. Verificar si aparece en "objetivos recurrentes pendientes"
        print(f"\n⏳ 4. ¿APARECE EN OBJETIVOS RECURRENTES PENDIENTES PARA {fecha}?")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM objetivos o
            WHERE o.id = ? AND o.user_id = ?
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
        """, (objetivo_id, user_id, fecha, fecha))
        
        en_recurrentes_pendientes = cursor.fetchone()[0]
        print(f"   En recurrentes pendientes: {'✅ SÍ' if en_recurrentes_pendientes > 0 else '❌ NO'}")
        
        # 5. Verificar subobjetivos completados
        print(f"\n🎯 5. SUBOBJETIVOS COMPLETADOS:")
        cursor.execute("""
            SELECT s.id, s.titulo, scl.fecha_completado, 
                   FORMAT(scl.fecha_creacion, 'HH:mm:ss') as hora_completado
            FROM subobjetivos s
            INNER JOIN subobjetivos_completados_log scl ON s.id = scl.subobjetivo_id
            WHERE s.objetivo_id = ? AND scl.user_id = ? 
              AND CAST(scl.fecha_completado AS DATE) = CAST(? AS DATE)
            ORDER BY scl.fecha_creacion ASC
        """, (objetivo_id, user_id, fecha))
        
        subobjetivos = cursor.fetchall()
        print(f"   Total subobjetivos completados: {len(subobjetivos)}")
        for sub in subobjetivos:
            print(f"     ✅ {sub.titulo} - {sub.hora_completado}")
        
        # 6. CONCLUSIÓN
        print(f"\n🔍 6. CONCLUSIÓN:")
        aparece_en_modal = en_creados > 0 or en_completados_normal > 0 or en_completados_recurrente > 0 or en_recurrentes_pendientes > 0
        
        if aparece_en_modal:
            print(f"   ✅ El objetivo SÍ debería aparecer en el modal")
            if len(subobjetivos) > 0:
                print(f"   ✅ Y SÍ tiene {len(subobjetivos)} subobjetivos completados")
                print(f"   🎯 Los subobjetivos DEBERÍAN mostrarse en el modal")
            else:
                print(f"   ❌ Pero NO tiene subobjetivos completados")
        else:
            print(f"   ❌ El objetivo NO aparece en el modal para esta fecha")
            print(f"   ℹ️ Por eso no se ven los subobjetivos completados")
            
            # Sugerir fechas donde sí aparece
            print(f"\n💡 SUGERENCIA: Verificar otras fechas donde sí aparezca el objetivo")
            cursor.execute("""
                SELECT DISTINCT CAST(fecha_creacion AS DATE) as fecha
                FROM objetivos 
                WHERE id = ? AND user_id = ?
                ORDER BY fecha DESC
            """, (objetivo_id, user_id))
            
            fechas_creacion = cursor.fetchall()
            if fechas_creacion:
                print(f"   Fechas donde fue creado:")
                for f in fechas_creacion:
                    print(f"     - {f.fecha}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    debug_objetivo_especifico()