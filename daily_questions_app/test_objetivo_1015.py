#!/usr/bin/env python3
"""
Script para probar el endpoint /api/objetivos/1015 específicamente
"""

import pyodbc
import sys
import os

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

def test_objetivo_1015():
    """Prueba obtener el objetivo 1015 directamente de la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        objetivo_id = 1015
        user_id = 3  # Usuario de prueba
        
        print(f"🧪 Probando obtener objetivo {objetivo_id} para user_id {user_id}")
        
        # Simular la query del endpoint /api/objetivos/<id>
        cursor.execute("""
            SELECT id, titulo, descripcion, categoria, prioridad, 
                   recurrente, parte_dia, horas_estimadas,
                   CONVERT(varchar, fecha_creacion, 120) as fecha_creacion,
                   completado, estado
            FROM objetivos 
            WHERE id = ? AND user_id = ?
        """, (objetivo_id, user_id))
        
        row = cursor.fetchone()
        
        if row:
            objetivo = {
                'id': row.id,
                'titulo': row.titulo,
                'descripcion': row.descripcion,
                'categoria': row.categoria,
                'prioridad': row.prioridad,
                'recurrente': bool(row.recurrente),
                'parte_dia': row.parte_dia,
                'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                'fecha_creacion': row.fecha_creacion,
                'completado': bool(row.completado),
                'estado': row.estado
            }
            
            print("✅ Objetivo encontrado:")
            for key, value in objetivo.items():
                print(f"   {key}: {value}")
                
        else:
            print("❌ Objetivo no encontrado")
            
            # Verificar si existe pero con otro user_id
            cursor.execute("SELECT id, titulo, user_id FROM objetivos WHERE id = ?", (objetivo_id,))
            row_any_user = cursor.fetchone()
            
            if row_any_user:
                print(f"⚠️ El objetivo existe pero pertenece al user_id {row_any_user.user_id}")
            else:
                print("❌ El objetivo no existe en la base de datos")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_objetivo_1015()