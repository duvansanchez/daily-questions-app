#!/usr/bin/env python3
"""
Script para debuggear objetivos programados para mañana
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from datetime import datetime, timedelta

def main():
    print("🔍 Debuggeando objetivos programados para mañana...")
    
    hoy = datetime.now().date()
    mañana = hoy + timedelta(days=1)
    
    print(f"📅 Hoy: {hoy}")
    print(f"📅 Mañana: {mañana}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Buscar objetivos programados para mañana
            print("\n🔍 Buscando objetivos programados...")
            cursor.execute("""
                SELECT id, titulo, fecha_programada, programado_para, user_id, completado
                FROM objetivos 
                WHERE (fecha_programada = ? OR programado_para = 'mañana')
                ORDER BY id DESC
            """, (mañana,))
            
            objetivos = cursor.fetchall()
            print(f"📊 Objetivos encontrados: {len(objetivos)}")
            
            for obj in objetivos:
                print(f"  - ID: {obj.id}")
                print(f"    Título: {obj.titulo}")
                print(f"    Fecha programada: {obj.fecha_programada}")
                print(f"    Programado para: {obj.programado_para}")
                print(f"    User ID: {obj.user_id}")
                print(f"    Completado: {obj.completado}")
                print()
            
            # Buscar todos los objetivos recientes para ver si se están guardando
            print("\n🔍 Últimos 5 objetivos modificados...")
            cursor.execute("""
                SELECT TOP 5 id, titulo, fecha_programada, programado_para, user_id
                FROM objetivos 
                ORDER BY id DESC
            """)
            
            recientes = cursor.fetchall()
            for obj in recientes:
                print(f"  - ID: {obj.id}, Título: {obj.titulo[:30]}..., Programado: {obj.programado_para}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()