#!/usr/bin/env python3
"""
Script para probar el endpoint de objetivos de mañana
"""

import pyodbc
from datetime import datetime, timedelta

def test_objetivos_manana():
    """Prueba directa del endpoint"""
    try:
        conn_str = (
            "DRIVER={SQL Server};"
            "SERVER=DESKTOP-2MR0PJ6;"
            "DATABASE=DailyQuestions;"
            "Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Calcular fecha de mañana
        manana = datetime.now() + timedelta(days=1)
        fecha_manana = manana.strftime('%Y-%m-%d')
        
        print(f"📅 Fecha de mañana: {fecha_manana}")
        
        # Obtener un user_id válido
        cursor.execute("SELECT TOP 1 id FROM [user]")
        user_row = cursor.fetchone()
        if not user_row:
            print("❌ No hay usuarios en la base de datos")
            return
        
        user_id = user_row[0]
        print(f"👤 Usando user_id: {user_id}")
        
        # Probar la consulta
        cursor.execute('''
            SELECT o.id, o.titulo, o.descripcion, o.prioridad, o.categoria, 
                   o.horas_estimadas, o.parte_dia, o.fecha_programada, o.programado_para, o.recurrente
            FROM objetivos o
            WHERE o.user_id = ? 
            AND o.completado = 0 
            AND (
                o.fecha_programada = ?
                OR (o.recurrente = 1 AND o.programado_para = 'diario')
            )
            ORDER BY o.prioridad, o.titulo
        ''', (user_id, fecha_manana))
        
        rows = cursor.fetchall()
        print(f"📊 Encontrados {len(rows)} objetivos")
        
        for i, row in enumerate(rows):
            print(f"  {i+1}. {row[1]} - Programado: {row[8]} - Fecha: {row[7]}")
        
        # También buscar objetivos diarios
        cursor.execute('''
            SELECT COUNT(*) FROM objetivos 
            WHERE user_id = ? AND completado = 0 AND recurrente = 1 AND programado_para = 'diario'
        ''', (user_id,))
        
        diarios = cursor.fetchone()[0]
        print(f"📅 Objetivos diarios encontrados: {diarios}")
        
        conn.close()
        print("✅ Test completado")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_objetivos_manana()