#!/usr/bin/env python3
"""
Test específico para la función obtener_todos_subobjetivos_objetivos_modal
usando SQL Server (como en el sistema real)
"""

import pyodbc
from datetime import datetime

def get_connection():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-2MR0PJ6;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def obtener_todos_subobjetivos_objetivos_modal(cursor, objetivos_creados, objetivos_completados, objetivos_recurrentes_pendientes, subobjetivos_completados, fecha):
    """
    Función auxiliar para obtener TODOS los subobjetivos de los objetivos que aparecen en el modal,
    marcando cuáles se completaron en la fecha específica.
    Sigue el principio de función pequeña con una sola responsabilidad.
    """
    # Recopilar todos los IDs de objetivos que aparecen en el modal
    objetivos_ids = set()
    
    # Agregar IDs de objetivos creados
    for obj in objetivos_creados:
        objetivos_ids.add(obj['id'])
    
    # Agregar IDs de objetivos completados
    for obj in objetivos_completados:
        objetivos_ids.add(obj['id'])
    
    # Agregar IDs de objetivos recurrentes pendientes
    for obj in objetivos_recurrentes_pendientes:
        objetivos_ids.add(obj['id'])
    
    # Agregar IDs de objetivos que tienen subobjetivos completados
    for sub in subobjetivos_completados:
        objetivos_ids.add(sub['objetivo_id'])
    
    if not objetivos_ids:
        return []
    
    # Obtener todos los subobjetivos de estos objetivos
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
    
    cursor.execute(query_todos_subobjetivos, (fecha,))
    todos_subobjetivos = []
    
    for row in cursor.fetchall():
        todos_subobjetivos.append({
            'id': row.id,
            'titulo': row.titulo,
            'objetivo_id': row.objetivo_id,
            'objetivo_titulo': row.objetivo_titulo,
            'estado_actual': bool(row.estado_actual),
            'completado_en_fecha': bool(row.completado_en_fecha),
            'hora_completado': row.hora_completado if row.completado_en_fecha else None
        })
    
    return todos_subobjetivos

def main():
    print("🧪 Test de obtener_todos_subobjetivos_objetivos_modal")
    
    # Conectar a la base de datos
    conn = get_connection()
    cursor = conn.cursor()
    
    # Simular datos de entrada como los que llegan al endpoint
    objetivos_creados = []
    objetivos_completados = []
    objetivos_recurrentes_pendientes = [
        {'id': 6096}, {'id': 6154}, {'id': 6152}, {'id': 5067}, {'id': 1015}
    ]
    subobjetivos_completados = [
        {'objetivo_id': 1015}, {'objetivo_id': 1015}, {'objetivo_id': 1015}
    ]
    fecha = '2025-12-15'
    
    print(f"📅 Fecha: {fecha}")
    print(f"📋 Objetivos recurrentes pendientes: {[obj['id'] for obj in objetivos_recurrentes_pendientes]}")
    print(f"📋 Subobjetivos completados (objetivo_ids): {[sub['objetivo_id'] for sub in subobjetivos_completados]}")
    
    # Ejecutar la función
    resultado = obtener_todos_subobjetivos_objetivos_modal(
        cursor, objetivos_creados, objetivos_completados, 
        objetivos_recurrentes_pendientes, subobjetivos_completados, fecha
    )
    
    print(f"\n📊 Resultados encontrados: {len(resultado)}")
    
    # Agrupar por objetivo
    por_objetivo = {}
    for sub in resultado:
        obj_id = sub['objetivo_id']
        if obj_id not in por_objetivo:
            por_objetivo[obj_id] = {'objetivo_titulo': sub['objetivo_titulo'], 'subobjetivos': []}
        por_objetivo[obj_id]['subobjetivos'].append(sub)
    
    # Mostrar resultados agrupados
    for obj_id, data in por_objetivo.items():
        print(f"\n🎯 Objetivo {obj_id}: {data['objetivo_titulo']}")
        completados = [s for s in data['subobjetivos'] if s['completado_en_fecha']]
        pendientes = [s for s in data['subobjetivos'] if not s['completado_en_fecha']]
        
        print(f"   ✅ Completados en fecha ({len(completados)}):")
        for sub in completados:
            print(f"      - {sub['titulo']} ({sub['hora_completado']})")
        
        print(f"   ⭕ Pendientes ({len(pendientes)}):")
        for sub in pendientes:
            print(f"      - {sub['titulo']}")
    
    # Simular la estructura JSON que se envía al frontend
    print(f"\n📤 Estructura JSON para frontend:")
    print(f"   'todos_los_subobjetivos': {len(resultado)} elementos")
    
    conn.close()
    print("\n✅ Test completado")

if __name__ == "__main__":
    main()