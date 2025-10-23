"""
Optimizaciones de Base de Datos para Daily Questions App
======================================================

Este módulo contiene optimizaciones para mejorar el rendimiento de la base de datos:
1. Índices optimizados
2. Consultas mejoradas
3. Cacheo de consultas frecuentes
4. Limpieza de datos obsoletos
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    def __init__(self, get_db_connection):
        self.get_db_connection = get_db_connection
    
    def create_optimized_indexes(self):
        """Crea índices optimizados para mejorar el rendimiento"""
        indexes = [
            # Índices para objetivos
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_objetivos_user_categoria_completado ON objetivos(user_id, categoria, completado) INCLUDE (fecha_creacion, orden)",
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_objetivos_user_fecha_completado ON objetivos(user_id, fecha_completado) WHERE completado = 1",
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_objetivos_recurrente_categoria ON objetivos(recurrente, categoria) WHERE recurrente = 1",
            
            # Índices para preguntas y respuestas
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_response_user_date ON response(user_id, date) INCLUDE (question_id, response)",
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_question_user_active_freq ON question(assigned_user_id, active, frecuencia) INCLUDE (text, type)",
            
            # Índices para frases
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_frases_user_categoria_activa ON frases(user_id, categoria_id, activa) INCLUDE (texto, total_repasos)",
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_frases_ultima_vez ON frases(user_id, ultima_vez) WHERE ultima_vez IS NOT NULL",
            
            # Índices para objetivos saltados
            "CREATE NONCLUSTERED INDEX IF NOT EXISTS IX_objetivos_saltados_user_fecha ON objetivos_saltados(user_id, fecha_saltada) INCLUDE (objetivo_id)",
        ]
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                        logger.info(f"Índice creado/verificado: {index_sql[:50]}...")
                    except Exception as e:
                        logger.warning(f"Error creando índice: {str(e)}")
                conn.commit()
                logger.info("Optimización de índices completada")
        except Exception as e:
            logger.error(f"Error en optimización de índices: {str(e)}")
    
    def optimize_objetivos_query(self, user_id, hoy):
        """Consulta optimizada para objetivos con mejor rendimiento"""
        query = """
        WITH ObjetivosBase AS (
            SELECT o.id, o.titulo, o.descripcion, o.prioridad, o.categoria, o.completado, 
                   o.fecha_creacion, o.fecha_completado, o.objetivo_padre_id, o.es_padre, 
                   o.estado, o.fecha_inicio, o.fecha_fin, o.fecha_proyeccion_comienzo, 
                   o.horas_estimadas, o.dificultad, o.etiquetas, o.recompensa, 
                   o.notas_adicionales, o.recurrente, o.frecuencia, o.orden,
                   CASE WHEN os.objetivo_id IS NOT NULL THEN 1 ELSE 0 END as saltado_hoy,
                   -- Calcular prioridad de ordenamiento
                   CASE 
                       WHEN o.completado = 1 THEN 3
                       WHEN os.objetivo_id IS NOT NULL THEN 2
                       ELSE 1
                   END as orden_prioridad
            FROM objetivos o WITH (INDEX(IX_objetivos_user_categoria_completado))
            LEFT JOIN objetivos_saltados os WITH (INDEX(IX_objetivos_saltados_user_fecha))
                ON o.id = os.objetivo_id AND os.user_id = o.user_id AND os.fecha_saltada = ?
            WHERE o.user_id = ? 
                AND (o.estado IS NULL OR o.estado != 'histórico')
        )
        SELECT * FROM ObjetivosBase
        ORDER BY orden_prioridad ASC, orden ASC, fecha_creacion DESC
        """
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (hoy, user_id))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error en consulta optimizada de objetivos: {str(e)}")
            return []
    
    def get_stats_summary_optimized(self, user_id):
        """Estadísticas optimizadas con una sola consulta"""
        query = """
        WITH FechasBase AS (
            SELECT 
                CAST(GETDATE() AS DATE) as hoy,
                DATEADD(day, -DATEPART(weekday, GETDATE()) + 1, CAST(GETDATE() AS DATE)) as inicio_semana,
                DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) as inicio_mes,
                DATEFROMPARTS(YEAR(GETDATE()), 1, 1) as inicio_anio
        ),
        EstadisticasBase AS (
            SELECT 
                f.hoy, f.inicio_semana, f.inicio_mes, f.inicio_anio,
                -- Objetivos esperados por categoría
                SUM(CASE WHEN LOWER(o.categoria) = 'diario' AND (o.recurrente = 1 OR o.fecha_creacion >= f.hoy) THEN 1 ELSE 0 END) as esperados_hoy,
                SUM(CASE WHEN LOWER(o.categoria) = 'semanal' AND (o.recurrente = 1 OR o.fecha_creacion >= f.inicio_semana) THEN 1 ELSE 0 END) as esperados_semana,
                SUM(CASE WHEN LOWER(o.categoria) = 'mensual' AND (o.recurrente = 1 OR o.fecha_creacion >= f.inicio_mes) THEN 1 ELSE 0 END) as esperados_mes,
                SUM(CASE WHEN LOWER(o.categoria) = 'anual' AND (o.recurrente = 1 OR o.fecha_creacion >= f.inicio_anio) THEN 1 ELSE 0 END) as esperados_anio,
                -- Objetivos cumplidos
                SUM(CASE WHEN LOWER(o.categoria) = 'diario' AND o.completado = 1 AND CAST(o.fecha_completado AS DATE) = f.hoy THEN 1 ELSE 0 END) as cumplidos_hoy,
                SUM(CASE WHEN LOWER(o.categoria) = 'semanal' AND o.completado = 1 AND o.fecha_completado >= f.inicio_semana THEN 1 ELSE 0 END) as cumplidos_semana,
                SUM(CASE WHEN LOWER(o.categoria) = 'mensual' AND o.completado = 1 AND o.fecha_completado >= f.inicio_mes THEN 1 ELSE 0 END) as cumplidos_mes,
                SUM(CASE WHEN LOWER(o.categoria) = 'anual' AND o.completado = 1 AND o.fecha_completado >= f.inicio_anio THEN 1 ELSE 0 END) as cumplidos_anio
            FROM FechasBase f
            CROSS JOIN objetivos o
            WHERE o.user_id = ? AND COALESCE(o.estado, '') != 'histórico'
            GROUP BY f.hoy, f.inicio_semana, f.inicio_mes, f.inicio_anio
        )
        SELECT * FROM EstadisticasBase
        """
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (user_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error en estadísticas optimizadas: {str(e)}")
            return None
    
    def cleanup_old_sessions(self, days_old=7):
        """Limpia sesiones antiguas para liberar espacio"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Limpiar respuestas muy antiguas (más de 1 año)
                cursor.execute("""
                    DELETE FROM response 
                    WHERE date < DATEADD(year, -1, GETDATE())
                """)
                
                # Limpiar objetivos saltados antiguos (más de 30 días)
                cursor.execute("""
                    DELETE FROM objetivos_saltados 
                    WHERE fecha_saltada < DATEADD(day, -30, GETDATE())
                """)
                
                conn.commit()
                logger.info("Limpieza de datos antiguos completada")
                
        except Exception as e:
            logger.error(f"Error en limpieza de datos: {str(e)}")
    
    def analyze_performance(self, user_id):
        """Analiza el rendimiento de consultas frecuentes"""
        queries = [
            ("Objetivos activos", "SELECT COUNT(*) FROM objetivos WHERE user_id = ? AND completado = 0"),
            ("Respuestas hoy", "SELECT COUNT(*) FROM response r JOIN question q ON r.question_id = q.id WHERE q.assigned_user_id = ? AND CAST(r.date AS DATE) = CAST(GETDATE() AS DATE)"),
            ("Frases activas", "SELECT COUNT(*) FROM frases WHERE user_id = ? AND COALESCE(activa, 1) = 1"),
        ]
        
        performance_results = {}
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                for query_name, query_sql in queries:
                    start_time = datetime.now()
                    cursor.execute(query_sql, (user_id,))
                    result = cursor.fetchone()
                    end_time = datetime.now()
                    
                    performance_results[query_name] = {
                        'duration_ms': (end_time - start_time).total_seconds() * 1000,
                        'result_count': result[0] if result else 0
                    }
                
                return performance_results
                
        except Exception as e:
            logger.error(f"Error en análisis de rendimiento: {str(e)}")
            return {}

def initialize_database_optimizations(get_db_connection):
    """Inicializa las optimizaciones de base de datos"""
    optimizer = DatabaseOptimizer(get_db_connection)
    optimizer.create_optimized_indexes()
    optimizer.cleanup_old_sessions()
    return optimizer