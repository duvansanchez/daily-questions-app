"""
Script de prueba para verificar el funcionamiento del calendario de objetivos
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from datetime import datetime, timedelta
from app import get_db_connection

def test_calendario_data():
    """Prueba los datos del calendario"""
    print("=== PRUEBA DEL CALENDARIO DE OBJETIVOS ===")
    
    try:
        # Simular parámetros del calendario
        ahora = datetime.now()
        mes = ahora.month - 1  # 0-11
        anio = ahora.year
        
        print(f"Consultando datos para mes {mes} (0-11), año {anio}")
        
        # Calcular fechas
        inicio = datetime(anio, mes + 1, 1)
        if mes == 11:
            fin = datetime(anio + 1, 1, 1)
        else:
            fin = datetime(anio, mes + 2, 1)
        
        dias_en_mes = (fin - inicio).days
        
        print(f"Período: {inicio} a {fin}")
        print(f"Días en el mes: {dias_en_mes}")
        
        # Probar conexión a la base de datos
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si hay objetivos en la base de datos
            cursor.execute("SELECT COUNT(*) FROM objetivos")
            total_objetivos = cursor.fetchone()[0]
            print(f"Total de objetivos en la base de datos: {total_objetivos}")
            
            # Verificar objetivos por usuario (simulando user_id = 1)
            cursor.execute("SELECT COUNT(*) FROM objetivos WHERE user_id = 1")
            objetivos_usuario = cursor.fetchone()[0]
            print(f"Objetivos del usuario 1: {objetivos_usuario}")
            
            if objetivos_usuario > 0:
                # Probar consulta de creados
                cursor.execute(
                    """
                    SELECT DAY(fecha_creacion) AS dia, COUNT(*)
                    FROM objetivos
                    WHERE user_id = 1
                      AND fecha_creacion >= ? AND fecha_creacion < ?
                      AND COALESCE(estado, '') != 'histórico'
                    GROUP BY DAY(fecha_creacion)
                    """,
                    (inicio, fin)
                )
                creados_rows = cursor.fetchall()
                print(f"Días con objetivos creados: {len(creados_rows)}")
                for row in creados_rows:
                    print(f"  Día {row[0]}: {row[1]} objetivos creados")
                
                # Probar consulta de completados
                cursor.execute(
                    """
                    SELECT DAY(fecha_completado) AS dia, COUNT(*)
                    FROM objetivos
                    WHERE user_id = 1
                      AND completado = 1
                      AND fecha_completado >= ? AND fecha_completado < ?
                      AND COALESCE(estado, '') != 'histórico'
                    GROUP BY DAY(fecha_completado)
                    """,
                    (inicio, fin)
                )
                completados_rows = cursor.fetchall()
                print(f"Días con objetivos completados: {len(completados_rows)}")
                for row in completados_rows:
                    print(f"  Día {row[0]}: {row[1]} objetivos completados")
            else:
                print("No hay objetivos para el usuario de prueba")
                
        print("\n✅ Prueba completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error en la prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_calendario_data()