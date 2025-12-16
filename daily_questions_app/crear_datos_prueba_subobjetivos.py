#!/usr/bin/env python3
"""
Script para crear datos de prueba de subobjetivos completados
"""

import pyodbc
import sys
import os
from datetime import datetime, timedelta

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

def crear_datos_prueba():
    """Crea datos de prueba para subobjetivos completados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🧪 Creando datos de prueba para subobjetivos completados...")
        
        # 1. Buscar objetivos existentes con subobjetivos
        cursor.execute("""
            SELECT DISTINCT o.id, o.titulo, o.user_id, s.id as subobjetivo_id, s.titulo as sub_titulo
            FROM objetivos o
            INNER JOIN subobjetivos s ON o.id = s.objetivo_id
            WHERE o.user_id IS NOT NULL
            ORDER BY o.id, s.id
        """)
        
        objetivos_con_subs = cursor.fetchall()
        
        if not objetivos_con_subs:
            print("❌ No se encontraron objetivos con subobjetivos")
            return False
        
        print(f"📋 Encontrados {len(objetivos_con_subs)} subobjetivos en objetivos existentes")
        
        # 2. Crear registros de completado para los últimos 3 días
        fechas_prueba = []
        for i in range(3):
            fecha = datetime.now() - timedelta(days=i)
            fechas_prueba.append(fecha.strftime('%Y-%m-%d'))
        
        print(f"📅 Creando registros para fechas: {fechas_prueba}")
        
        registros_creados = 0
        
        # 3. Para cada fecha, marcar algunos subobjetivos como completados
        for fecha in fechas_prueba:
            # Tomar algunos subobjetivos (no todos)
            subobjetivos_a_completar = objetivos_con_subs[:min(3, len(objetivos_con_subs))]
            
            for obj in subobjetivos_a_completar:
                try:
                    # Crear registro en subobjetivos_completados_log
                    cursor.execute("""
                        INSERT INTO subobjetivos_completados_log 
                        (subobjetivo_id, objetivo_id, user_id, fecha_completado, fecha_creacion)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        obj.subobjetivo_id,
                        obj.id,
                        obj.user_id,
                        fecha,
                        datetime.now()
                    ))
                    
                    registros_creados += 1
                    print(f"✅ Creado: {obj.sub_titulo} ({obj.titulo}) - {fecha}")
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                        print(f"ℹ️ Ya existe: {obj.sub_titulo} - {fecha}")
                    else:
                        print(f"⚠️ Error: {e}")
        
        conn.commit()
        print(f"🎉 Creados {registros_creados} registros de prueba")
        
        # 4. Verificar los datos creados
        cursor.execute("""
            SELECT scl.fecha_completado, COUNT(*) as total,
                   STRING_AGG(s.titulo, ', ') as subobjetivos
            FROM subobjetivos_completados_log scl
            INNER JOIN subobjetivos s ON scl.subobjetivo_id = s.id
            GROUP BY scl.fecha_completado
            ORDER BY scl.fecha_completado DESC
        """)
        
        resumen = cursor.fetchall()
        print("\n📊 Resumen de datos creados:")
        for row in resumen:
            print(f"   {row.fecha_completado}: {row.total} subobjetivos")
            print(f"      → {row.subobjetivos}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creando datos de prueba: {str(e)}")
        return False

if __name__ == "__main__":
    crear_datos_prueba()