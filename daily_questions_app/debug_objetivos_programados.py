#!/usr/bin/env python3
"""
Script de debug para verificar objetivos programados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from datetime import datetime, timedelta

def debug_objetivos_programados():
    """Debug de objetivos programados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            hoy = datetime.now().date()
            mañana = hoy + timedelta(days=1)
            
            print(f"🗓️ Hoy: {hoy}")
            print(f"🗓️ Mañana: {mañana}")
            print("=" * 60)
            
            # Obtener todos los objetivos con programación
            cursor.execute("""
                SELECT id, titulo, fecha_programada, programado_para, completado,
                       CONVERT(varchar, fecha_creacion, 120) as fecha_creacion
                FROM objetivos 
                WHERE user_id = 3
                AND (fecha_programada IS NOT NULL OR programado_para IS NOT NULL)
                ORDER BY fecha_creacion DESC
            """)
            
            objetivos_programados = cursor.fetchall()
            
            print(f"📋 Objetivos con programación: {len(objetivos_programados)}")
            print("-" * 60)
            
            for obj in objetivos_programados:
                print(f"ID: {obj.id}")
                print(f"Título: {obj.titulo}")
                print(f"Fecha programada: {obj.fecha_programada}")
                print(f"Programado para: {obj.programado_para}")
                print(f"Completado: {obj.completado}")
                print(f"Fecha creación: {obj.fecha_creacion}")
                print("-" * 40)
            
            # Probar la consulta de objetivos de hoy
            print("\n🔍 Probando consulta de objetivos de HOY:")
            print("-" * 60)
            
            cursor.execute("""
                SELECT o.id, o.titulo, o.fecha_programada, o.programado_para, o.completado
                FROM objetivos o
                WHERE o.user_id = 3
                AND (
                    (o.fecha_programada IS NULL AND o.programado_para IS NULL) OR
                    (o.fecha_programada IS NOT NULL AND o.fecha_programada <= ?) OR
                    (o.programado_para IS NOT NULL AND o.programado_para != 'mañana')
                )
                ORDER BY o.fecha_creacion DESC
            """, (hoy,))
            
            objetivos_hoy = cursor.fetchall()
            
            print(f"📋 Objetivos que aparecen HOY: {len(objetivos_hoy)}")
            for obj in objetivos_hoy:
                print(f"  - {obj.titulo} (ID: {obj.id}) - Programado: {obj.programado_para} - Fecha: {obj.fecha_programada}")
            
            # Probar la consulta de objetivos de mañana
            print(f"\n🔍 Probando consulta de objetivos de MAÑANA:")
            print("-" * 60)
            
            cursor.execute("""
                SELECT id, titulo, fecha_programada, programado_para, completado
                FROM objetivos 
                WHERE user_id = 3
                AND (fecha_programada = ? OR programado_para = 'mañana')
                AND completado = 0
                ORDER BY fecha_creacion DESC
            """, (mañana,))
            
            objetivos_mañana = cursor.fetchall()
            
            print(f"📋 Objetivos programados para MAÑANA: {len(objetivos_mañana)}")
            for obj in objetivos_mañana:
                print(f"  - {obj.titulo} (ID: {obj.id}) - Programado: {obj.programado_para} - Fecha: {obj.fecha_programada}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🐛 Debug de Objetivos Programados")
    print("=" * 60)
    debug_objetivos_programados()