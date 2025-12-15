#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento de subobjetivos completados por fecha
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

def test_subobjetivos_completados():
    """Prueba la funcionalidad de subobjetivos completados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🧪 Iniciando pruebas de subobjetivos completados...")
        
        # 1. Verificar que la tabla existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'subobjetivos_completados_log'
        """)
        
        table_exists = cursor.fetchone()[0]
        print(f"📋 Tabla subobjetivos_completados_log existe: {'✅' if table_exists else '❌'}")
        
        if not table_exists:
            print("❌ La tabla no existe. Ejecuta la migración primero.")
            return False
        
        # 2. Verificar estructura de la tabla
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'subobjetivos_completados_log'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print("📊 Estructura de la tabla:")
        for col in columns:
            print(f"   - {col.COLUMN_NAME}: {col.DATA_TYPE}")
        
        # 3. Contar registros existentes
        cursor.execute("SELECT COUNT(*) FROM subobjetivos_completados_log")
        total_registros = cursor.fetchone()[0]
        print(f"📈 Total de registros en subobjetivos_completados_log: {total_registros}")
        
        # 4. Mostrar algunos registros recientes si existen
        if total_registros > 0:
            cursor.execute("""
                SELECT TOP 5 scl.*, s.titulo as subobjetivo_titulo, o.titulo as objetivo_titulo
                FROM subobjetivos_completados_log scl
                INNER JOIN subobjetivos s ON scl.subobjetivo_id = s.id
                INNER JOIN objetivos o ON scl.objetivo_id = o.id
                ORDER BY scl.fecha_creacion DESC
            """)
            
            registros = cursor.fetchall()
            print("📋 Últimos registros:")
            for reg in registros:
                print(f"   - {reg.subobjetivo_titulo} ({reg.objetivo_titulo}) - {reg.fecha_completado}")
        
        # 5. Probar consulta por fecha (hoy)
        hoy = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) 
            FROM subobjetivos_completados_log 
            WHERE CAST(fecha_completado AS DATE) = CAST(? AS DATE)
        """, (hoy,))
        
        registros_hoy = cursor.fetchone()[0]
        print(f"📅 Subobjetivos completados hoy ({hoy}): {registros_hoy}")
        
        # 6. Probar la función auxiliar (simular)
        cursor.execute("""
            SELECT s.id, s.titulo, s.objetivo_id, o.titulo as objetivo_titulo,
                   scl.fecha_completado, 
                   FORMAT(scl.fecha_creacion, 'HH:mm:ss') as hora_completado
            FROM subobjetivos s
            INNER JOIN subobjetivos_completados_log scl ON s.id = scl.subobjetivo_id
            INNER JOIN objetivos o ON s.objetivo_id = o.id
            WHERE CAST(scl.fecha_completado AS DATE) = CAST(? AS DATE)
            ORDER BY scl.fecha_creacion ASC
        """, (hoy,))
        
        subobjetivos_hoy = cursor.fetchall()
        print(f"🎯 Consulta de subobjetivos para hoy:")
        for sub in subobjetivos_hoy:
            print(f"   - {sub.titulo} ({sub.objetivo_titulo}) a las {sub.hora_completado}")
        
        conn.close()
        print("✅ Pruebas completadas exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {str(e)}")
        return False

if __name__ == "__main__":
    test_subobjetivos_completados()