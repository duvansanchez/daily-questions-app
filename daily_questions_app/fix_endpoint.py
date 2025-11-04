@app.route('/api/objetivos/dia/<fecha>', methods=['GET'])
@login_required
def objetivos_detalle_dia(fecha):
    """Obtiene el detalle completo de objetivos para un día específico."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener objetivos creados en esta fecha
            query_creados = """
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad, 
                       o.recurrente, o.parte_dia, o.horas_estimadas,
                       CONVERT(varchar, o.fecha_creacion, 120) as fecha_creacion
                FROM objetivos o
                WHERE o.usuario_id = ? AND CAST(o.fecha_creacion AS DATE) = ?
                ORDER BY o.fecha_creacion DESC
            """
            
            cursor.execute(query_creados, (current_user.id, fecha))
            objetivos_creados = []
            for row in cursor.fetchall():
                objetivos_creados.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'categoria': row.categoria,
                    'prioridad': row.prioridad,
                    'recurrente': bool(row.recurrente),
                    'parte_dia': row.parte_dia,
                    'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                    'fecha_creacion': row.fecha_creacion
                })
            
            # Obtener objetivos completados en esta fecha
            query_completados = """
                SELECT DISTINCT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       o.parte_dia, o.horas_estimadas,
                       CASE WHEN o.recurrente = 1 THEN 'recurrente' ELSE 'normal' END as tipo,
                       COALESCE(CONVERT(varchar, ocl.fecha_completado, 108),
                               CONVERT(varchar, o.fecha_completado, 108), 'N/A') as hora_completado,
                       COALESCE(CONVERT(varchar, ocl.fecha_completado, 120),
                               CONVERT(varchar, o.fecha_completado, 120), 'N/A') as fecha_completado
                FROM objetivos o
                LEFT JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id 
                    AND CAST(ocl.fecha_completado AS DATE) = ?
                WHERE o.usuario_id = ?
                AND ((o.recurrente = 0 AND CAST(o.fecha_completado AS DATE) = ?)
                     OR (o.recurrente = 1 AND ocl.objetivo_id IS NOT NULL))
                ORDER BY COALESCE(ocl.fecha_completado, o.fecha_completado) DESC
            """
            
            cursor.execute(query_completados, (fecha, current_user.id, fecha))
            objetivos_completados = []
            for row in cursor.fetchall():
                objetivos_completados.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'categoria': row.categoria,
                    'prioridad': row.prioridad,
                    'parte_dia': row.parte_dia,
                    'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                    'tipo': row.tipo,
                    'hora_completado': row.hora_completado,
                    'fecha_completado': row.fecha_completado
                })
            
            resumen = {
                'total_creados': len(objetivos_creados),
                'total_completados': len(objetivos_completados)
            }
            
            return jsonify({
                'status': 'success',
                'fecha': fecha,
                'resumen': resumen,
                'objetivos_creados': objetivos_creados,
                'objetivos_completados': objetivos_completados
            })
            
    except Exception as e:
        logger.error(f"Error en objetivos_detalle_dia: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500