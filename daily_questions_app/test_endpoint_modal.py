#!/usr/bin/env python3
"""
Test directo de la función obtener_todos_subobjetivos_objetivos_modal
"""

import sqlite3
from datetime import datetime

def obtener_todos_subobjetivos_objetivos_modal(cursor, objetivos_creados, objetivos_completados, objetivos_recurrentes_pendientes, subobjetivos_completados, fecha):
    """
    Función auxiliar para obtener TODOS los subobjetivos de los objetivos que aparecen en el modal,
    marcando cuáles se completaron en la fecha específica.
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
               CASE 
                   WHEN scl.fecha_creacion IS NOT NULL THEN strftime('%H:%M:%S', scl.fecha_creacion)
                   ELSE NULL
               END as hora_completado
        FROM subobjetivos s
        INNER JOIN objetivos o ON s.objetivo_id = o.id
        LEFT JOIN subobjetivos_completados_log scl ON s.id = scl.subobjetivo_id 
            AND date(scl.fecha_completado) = date(?)
        WHERE s.objetivo_id IN ({objetivos_ids_str})
        ORDER BY s.objetivo_id, s.orden ASC, s.id ASC
    """
    
    cursor.execute(query_todos_subobjetivos, (fecha,))
    todos_subobjetivos = []
    
    for row in cursor.fetchall():
        todos_subobjetivos.append({
            'id': row[0],
            'titulo': row[1],
            'objetivo_id': row[2],
            'objetivo_titulo': row[4],
            'estado_actual': bool(row[3]),
            'completado_en_fecha': bool(row[5]),
            'hora_completado': row[6] if row[5] else None
        })
    
    return todos_subobjetivos

def main():
    # Conectar a la base de datos
    conn = sqlite3.connect('daily_questions.db')
    conn.row_factory = sqlite3.Row
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
    
    print(f"🧪 Probando obtener_todos_subobjetivos_objetivos_modal para fecha: {fecha}")
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
    
    conn.close()

if __name__ == "__main__":
    main()