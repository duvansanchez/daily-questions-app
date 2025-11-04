#!/usr/bin/env python3
"""
Script para probar directamente la base de datos
"""

import pyodbc
import sys
import os

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-2MR0PJ6;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def test_db_direct():
    """Prueba directa de la base de datos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔍 Probando actualización directa en la base de datos...")
        
        # Obtener un subobjetivo para probar
        cursor.execute("SELECT TOP 1 id, titulo, tiempo_focus FROM subobjetivos WHERE completado = 0")
        row = cursor.fetchone()
        
        if not row:
            print("❌ No hay subobjetivos incompletos para probar")
            return
        
        subobjetivo_id, titulo, tiempo_actual = row
        print(f"📊 Subobjetivo de prueba: ID={subobjetivo_id}, Título='{titulo}', Tiempo actual={tiempo_actual}")
        
        # Actualizar con un tiempo de prueba
        nuevo_tiempo = 150  # 2.5 minutos
        print(f"💾 Actualizando tiempo_focus a {nuevo_tiempo} segundos...")
        
        cursor.execute("UPDATE subobjetivos SET tiempo_focus = ? WHERE id = ?", (nuevo_tiempo, subobjetivo_id))
        conn.commit()
        
        # Verificar que se actualizó
        cursor.execute("SELECT tiempo_focus FROM subobjetivos WHERE id = ?", (subobjetivo_id,))
        tiempo_verificado = cursor.fetchone()[0]
        
        if tiempo_verificado == nuevo_tiempo:
            print(f"✅ Actualización exitosa: {tiempo_verificado} segundos")
        else:
            print(f"❌ Error en actualización: esperado {nuevo_tiempo}, obtenido {tiempo_verificado}")
        
        # Restaurar valor original
        cursor.execute("UPDATE subobjetivos SET tiempo_focus = ? WHERE id = ?", (tiempo_actual or 0, subobjetivo_id))
        conn.commit()
        print(f"🔄 Valor restaurado a {tiempo_actual or 0}")
        
        conn.close()
        print("🎉 Prueba de base de datos completada!")
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_db_direct()