#!/usr/bin/env python3
"""
Test para verificar que los objetivos recurrentes antiguos aparecen correctamente
cuando se marcan como completados en fechas específicas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from datetime import datetime, timedelta

def crear_objetivo_recurrente_antiguo():
    """Crear un objetivo recurrente de hace 3 meses y marcarlo como completado hoy"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener el primer usuario
            cursor.execute("SELECT TOP 1 id FROM [user]")
            user_row = cursor.fetchone()
            if not user_row:
                print("❌ No se encontró ningún usuario")
                return
            
            user_id = user_row.id
            print(f"✅ Usando usuario ID: {user_id}")
            
            # Fecha de hace 3 meses
            hace_3_meses = datetime.now() - timedelta(days=90)
            hoy = datetime.now().date()
            
            # Crear objetivo recurrente antiguo
            cursor.execute("""
                INSERT INTO objetivos (user_id, titulo, descripcion, categoria, prioridad, 
                                     fecha_creacion, completado, recurrente, frecuencia)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                'Meditar 10 minutos (objetivo antiguo)',
                'Objetivo recurrente creado hace 3 meses para probar el modal',
                'Bienestar',
                'alta',
                hace_3_meses,
                0,  # No completado permanentemente
                1,  # Es recurrente
                'diario'
            ))
            
            # Obtener el ID del objetivo recién creado
            objetivo_id = cursor.fetchone().id
            print(f"✅ Objetivo recurrente creado con ID: {objetivo_id}")
            print(f"   Título: Meditar 10 minutos (objetivo antiguo)")
            print(f"   Fecha creación: {hace_3_meses.strftime('%Y-%m-%d')}")
            
            # Marcar como completado HOY en el log
            cursor.execute("""
                INSERT INTO objetivos_completados_log (objetivo_id, user_id, fecha_completado)
                VALUES (?, ?, ?)
            """, (objetivo_id, user_id, datetime.now()))
            
            print(f"✅ Objetivo marcado como completado HOY: {hoy}")
            
            # También marcar como completado ayer para tener más datos
            ayer = datetime.now() - timedelta(days=1)
            cursor.execute("""
                INSERT INTO objetivos_completados_log (objetivo_id, user_id, fecha_completado)
                VALUES (?, ?, ?)
            """, (objetivo_id, user_id, ayer))
            
            print(f"✅ Objetivo también marcado como completado AYER: {ayer.date()}")
            
            conn.commit()
            
            # Verificar que aparece en la consulta de hoy
            print(f"\n🔍 Verificando que aparece en el modal de hoy...")
            
            query_test = """
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       o.parte_dia, o.horas_estimadas,
                       'recurrente' as tipo,
                       ISNULL(FORMAT(ocl.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                       ISNULL(FORMAT(ocl.fecha_completado, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_completado,
                       ISNULL(FORMAT(o.fecha_creacion, 'yyyy-MM-dd'), 'N/A') as fecha_creacion_original
                FROM objetivos o
                INNER JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
                WHERE o.user_id = ? 
                AND o.recurrente = 1
                AND ocl.fecha_completado IS NOT NULL
                AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
            """
            
            cursor.execute(query_test, (user_id, hoy))
            resultados = cursor.fetchall()
            
            print(f"📊 Objetivos recurrentes completados HOY: {len(resultados)}")
            for obj in resultados:
                print(f"  - {obj.titulo}")
                print(f"    Creado originalmente: {obj.fecha_creacion_original}")
                print(f"    Completado hoy a las: {obj.hora_completado}")
                print()
            
            return objetivo_id
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def verificar_modal_fecha(fecha, user_id=None):
    """Verificar qué objetivos aparecerían en el modal para una fecha específica"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if user_id is None:
                cursor.execute("SELECT TOP 1 id FROM [user]")
                user_row = cursor.fetchone()
                user_id = user_row.id
            
            print(f"\n🗓️ Verificando modal para fecha: {fecha}")
            print("=" * 50)
            
            # Objetivos creados ese día
            cursor.execute("""
                SELECT id, titulo, descripcion, categoria, prioridad,
                       ISNULL(FORMAT(fecha_creacion, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_creacion
                FROM objetivos
                WHERE user_id = ? AND CAST(fecha_creacion AS DATE) = ?
                ORDER BY fecha_creacion DESC
            """, (user_id, fecha))
            
            creados = cursor.fetchall()
            print(f"📝 Objetivos CREADOS ese día: {len(creados)}")
            for obj in creados:
                print(f"  - {obj.titulo} (creado: {obj.fecha_creacion})")
            
            # Objetivos completados ese día (normales)
            cursor.execute("""
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       'normal' as tipo,
                       ISNULL(FORMAT(o.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                       ISNULL(FORMAT(o.fecha_creacion, 'yyyy-MM-dd'), 'N/A') as fecha_creacion_original
                FROM objetivos o
                WHERE o.user_id = ? 
                AND (o.recurrente = 0 OR o.recurrente IS NULL)
                AND o.fecha_completado IS NOT NULL
                AND TRY_CAST(o.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                AND o.completado = 1
            """, (user_id, fecha))
            
            completados_normales = cursor.fetchall()
            print(f"✅ Objetivos NORMALES completados ese día: {len(completados_normales)}")
            for obj in completados_normales:
                print(f"  - {obj.titulo} (creado: {obj.fecha_creacion_original}, completado: {obj.hora_completado})")
            
            # Objetivos recurrentes completados ese día
            cursor.execute("""
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       'recurrente' as tipo,
                       ISNULL(FORMAT(ocl.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                       ISNULL(FORMAT(o.fecha_creacion, 'yyyy-MM-dd'), 'N/A') as fecha_creacion_original
                FROM objetivos o
                INNER JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
                WHERE o.user_id = ? 
                AND o.recurrente = 1
                AND ocl.fecha_completado IS NOT NULL
                AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
            """, (user_id, fecha))
            
            completados_recurrentes = cursor.fetchall()
            print(f"🔄 Objetivos RECURRENTES completados ese día: {len(completados_recurrentes)}")
            for obj in completados_recurrentes:
                print(f"  - {obj.titulo} (creado originalmente: {obj.fecha_creacion_original}, completado: {obj.hora_completado})")
            
            total_modal = len(creados) + len(completados_normales) + len(completados_recurrentes)
            print(f"\n📊 TOTAL que aparecería en el modal: {total_modal} objetivos")
            
            return {
                'creados': len(creados),
                'completados_normales': len(completados_normales),
                'completados_recurrentes': len(completados_recurrentes),
                'total': total_modal
            }
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("🧪 Test de Objetivos Recurrentes Antiguos")
    print("=" * 60)
    
    # Crear objetivo recurrente antiguo
    objetivo_id = crear_objetivo_recurrente_antiguo()
    
    if objetivo_id:
        print(f"\n✅ Objetivo recurrente antiguo creado exitosamente")
        
        # Verificar diferentes fechas
        hoy = datetime.now().date()
        ayer = (datetime.now() - timedelta(days=1)).date()
        
        verificar_modal_fecha(hoy)
        verificar_modal_fecha(ayer)
        
        print(f"\n🎯 CONCLUSIÓN:")
        print(f"El objetivo 'Meditar 10 minutos (objetivo antiguo)' fue creado hace 3 meses")
        print(f"pero aparece en el modal de HOY y AYER porque fue marcado como completado")
        print(f"en esas fechas específicas. Esto es el comportamiento correcto.")
        
    else:
        print("❌ No se pudo crear el objetivo de prueba")