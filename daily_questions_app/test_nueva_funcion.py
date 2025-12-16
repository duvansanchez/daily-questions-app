#!/usr/bin/env python3
"""
Script para probar la nueva función de subobjetivos
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

def test_nueva_funcion():
    """Prueba la nueva función de obtener todos los subobjetivos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        fecha = '2025-12-15'
        user_id = 3
        
        print(f"🧪 Probando nueva función para fecha: {fecha}, user_id: {user_id}")
        
        # Simular datos de entrada (objetivos vacíos para simplificar)
        objetivos_creados = []
        objetivos_completados = []
        objetivos_recurrentes_pendientes = []
        
        # Obtener subobjetivos completados
        subobjetivos_completados = [
            {'objetivo_id': 1015, 'id': 6034, 'titulo': 'Test sub 1'},
            {'objetivo_id': 1015, 'id': 7056, 'titulo': 'Test sub 2'},
            {'objetivo_id': 1015, 'id': 7065, 'titulo': 'Test sub 3'}
        ]
        
        # Probar la query directamente
        objetivos_ids = {1015}  # Solo el objetivo que tiene subobjetivos
        objetivos_ids_str = ','.join(map(str, objetivos_ids))
        
        query_todos_subobjetivos = f"""
            SELECT s.id, s.titulo, s.objetivo_id, s.completado as estado_actual,
                   o.titulo as objetivo_titulo,
                   CASE 
                       WHEN scl.subobjetivo_id IS NOT NULL THEN 1 
                       ELSE 0 
                   END as completado_en_fecha,
                   FORMAT(scl.fecha_creacion, 'HH:mm:ss') as hora_completado
            FROM subobjetivos s
            INNER JOIN objetivos o ON s.objetivo_id = o.id
            LEFT JOIN subobjetivos_completados_log scl ON s.id = scl.subobjetivo_id 
                AND CAST(scl.fecha_completado AS DATE) = CAST(? AS DATE)
            WHERE s.objetivo_id IN ({objetivos_ids_str})
            ORDER BY s.objetivo_id, s.orden ASC, s.id ASC
        """
        
        print("📡 Ejecutando query...")
        print(f"Query: {query_todos_subobjetivos}")
        print(f"Parámetros: {fecha}")
        
        cursor.execute(query_todos_subobjetivos, (fecha,))
        resultados = cursor.fetchall()
        
        print(f"📊 Resultados encontrados: {len(resultados)}")
        
        for row in resultados:
            print(f"   - ID: {row.id}")
            print(f"     Título: {row.titulo}")
            print(f"     Objetivo ID: {row.objetivo_id}")
            print(f"     Objetivo: {row.objetivo_titulo}")
            print(f"     Estado actual: {row.estado_actual}")
            print(f"     Completado en fecha: {row.completado_en_fecha}")
            print(f"     Hora completado: {row.hora_completado}")
            print()
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_nueva_funcion()