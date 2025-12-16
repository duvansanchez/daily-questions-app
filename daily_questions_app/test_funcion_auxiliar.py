#!/usr/bin/env python3
"""
Script para probar directamente la función auxiliar de subobjetivos
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

def test_funcion_auxiliar():
    """Prueba la función auxiliar directamente"""
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
        
        print(f"🧪 Probando función auxiliar con user_id={user_id}, fecha={fecha}")
        
        # Ejecutar la misma consulta que la función auxiliar
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
        
        print("📡 Ejecutando consulta...")
        cursor.execute(query_subobjetivos, (user_id, fecha))
        resultados = cursor.fetchall()
        
        print(f"📊 Resultados encontrados: {len(resultados)}")
        
        if resultados:
            print("✅ Subobjetivos completados encontrados:")
            for row in resultados:
                print(f"   - ID: {row.id}")
                print(f"     Título: {row.titulo}")
                print(f"     Objetivo: {row.objetivo_titulo}")
                print(f"     Fecha: {row.fecha_completado}")
                print(f"     Hora: {row.hora_completado}")
                print()
        else:
            print("❌ No se encontraron subobjetivos completados")
            
            # Verificar si hay datos en la tabla
            cursor.execute("SELECT COUNT(*) FROM subobjetivos_completados_log WHERE user_id = ?", (user_id,))
            total_user = cursor.fetchone()[0]
            print(f"📊 Total registros para user_id {user_id}: {total_user}")
            
            cursor.execute("SELECT COUNT(*) FROM subobjetivos_completados_log")
            total_general = cursor.fetchone()[0]
            print(f"📊 Total registros en la tabla: {total_general}")
            
            if total_general > 0:
                cursor.execute("""
                    SELECT TOP 3 scl.*, s.titulo, o.titulo as obj_titulo
                    FROM subobjetivos_completados_log scl
                    INNER JOIN subobjetivos s ON scl.subobjetivo_id = s.id
                    INNER JOIN objetivos o ON scl.objetivo_id = o.id
                    ORDER BY scl.fecha_creacion DESC
                """)
                
                ejemplos = cursor.fetchall()
                print("📋 Ejemplos de registros existentes:")
                for ej in ejemplos:
                    print(f"   - {ej.titulo} ({ej.obj_titulo}) - User: {ej.user_id} - Fecha: {ej.fecha_completado}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_funcion_auxiliar()