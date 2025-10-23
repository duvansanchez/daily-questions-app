"""
Sistema de Caché para Daily Questions App
========================================

Implementa un sistema de caché inteligente para mejorar el rendimiento:
1. Caché en memoria para consultas frecuentes
2. Invalidación automática de caché
3. Métricas de rendimiento
4. Configuración flexible
"""

import time
import threading
from datetime import datetime, timedelta
from functools import wraps
import logging
import json

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, default_ttl=300):  # 5 minutos por defecto
        self.cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
    
    def _is_expired(self, entry):
        """Verifica si una entrada del caché ha expirado"""
        return datetime.now() > entry['expires_at']
    
    def get(self, key):
        """Obtiene un valor del caché"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not self._is_expired(entry):
                    self.cache_stats['hits'] += 1
                    return entry['value']
                else:
                    # Entrada expirada, eliminarla
                    del self.cache[key]
            
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, key, value, ttl=None):
        """Establece un valor en el caché"""
        if ttl is None:
            ttl = self.default_ttl
        
        with self.lock:
            self.cache[key] = {
                'value': value,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=ttl)
            }
    
    def invalidate(self, pattern=None):
        """Invalida entradas del caché"""
        with self.lock:
            if pattern is None:
                # Limpiar todo el caché
                count = len(self.cache)
                self.cache.clear()
            else:
                # Limpiar entradas que coincidan con el patrón
                keys_to_delete = [key for key in self.cache.keys() if pattern in key]
                count = len(keys_to_delete)
                for key in keys_to_delete:
                    del self.cache[key]
            
            self.cache_stats['invalidations'] += count
            logger.info(f"Invalidadas {count} entradas del caché")
    
    def cleanup_expired(self):
        """Limpia entradas expiradas del caché"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items() 
                if self._is_expired(entry)
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Limpiadas {len(expired_keys)} entradas expiradas del caché")
    
    def get_stats(self):
        """Obtiene estadísticas del caché"""
        with self.lock:
            total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
            hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'entries': len(self.cache),
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'invalidations': self.cache_stats['invalidations']
            }

# Instancia global del caché
cache_manager = CacheManager()

def cached(ttl=300, key_prefix=""):
    """Decorador para cachear resultados de funciones"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de caché
            cache_key = f"{key_prefix}{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Intentar obtener del caché
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Ejecutar función y cachear resultado
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Solo cachear si la ejecución fue exitosa y no demoró mucho
            if result is not None and execution_time < 10:  # No cachear consultas muy lentas
                cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

class SmartCacheInvalidator:
    """Invalidador inteligente de caché basado en operaciones"""
    
    @staticmethod
    def invalidate_objetivos(user_id):
        """Invalida caché relacionado con objetivos"""
        patterns = [
            f"objetivos_{user_id}",
            f"stats_{user_id}",
            f"objetivos_stats_summary"
        ]
        for pattern in patterns:
            cache_manager.invalidate(pattern)
    
    @staticmethod
    def invalidate_preguntas(user_id):
        """Invalida caché relacionado con preguntas"""
        patterns = [
            f"preguntas_{user_id}",
            f"stats_{user_id}",
            f"admin_{user_id}"
        ]
        for pattern in patterns:
            cache_manager.invalidate(pattern)
    
    @staticmethod
    def invalidate_frases(user_id):
        """Invalida caché relacionado con frases"""
        patterns = [
            f"frases_{user_id}",
            f"categorias_{user_id}"
        ]
        for pattern in patterns:
            cache_manager.invalidate(pattern)

# Funciones de utilidad para integrar con Flask
def cache_key_for_user(user_id, operation):
    """Genera una clave de caché específica para un usuario y operación"""
    return f"{operation}_{user_id}_{datetime.now().strftime('%Y%m%d')}"

def invalidate_user_cache(user_id):
    """Invalida todo el caché de un usuario específico"""
    cache_manager.invalidate(f"_{user_id}_")

# Middleware para limpieza automática del caché
class CacheCleanupMiddleware:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa el middleware con la aplicación Flask"""
        @app.before_request
        def cleanup_cache():
            # Limpiar caché expirado cada 100 requests (aproximadamente)
            import random
            if random.randint(1, 100) == 1:
                cache_manager.cleanup_expired()
        
        @app.route('/api/cache/stats')
        def cache_stats():
            """Endpoint para obtener estadísticas del caché"""
            from flask import jsonify
            from flask_login import login_required
            
            @login_required
            def get_stats():
                return jsonify(cache_manager.get_stats())
            
            return get_stats()
        
        @app.route('/api/cache/clear', methods=['POST'])
        def clear_cache():
            """Endpoint para limpiar el caché manualmente"""
            from flask import jsonify
            from flask_login import login_required, current_user
            
            @login_required
            def clear():
                cache_manager.invalidate()
                return jsonify({'status': 'success', 'message': 'Caché limpiado'})
            
            return clear()

# Funciones específicas para cachear consultas comunes
@cached(ttl=600, key_prefix="stats_")
def get_cached_user_stats(user_id, get_db_connection):
    """Obtiene estadísticas del usuario con caché"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Estadísticas básicas
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM objetivos WHERE user_id = ? AND completado = 0) as objetivos_activos,
                    (SELECT COUNT(*) FROM question WHERE assigned_user_id = ? AND active = 1) as preguntas_activas,
                    (SELECT COUNT(*) FROM frases WHERE user_id = ? AND COALESCE(activa, 1) = 1) as frases_activas
            """, (user_id, user_id, user_id))
            
            result = cursor.fetchone()
            return {
                'objetivos_activos': result[0] if result else 0,
                'preguntas_activas': result[1] if result else 0,
                'frases_activas': result[2] if result else 0
            }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas cacheadas: {str(e)}")
        return None

@cached(ttl=300, key_prefix="categorias_")
def get_cached_categorias(user_id, get_db_connection):
    """Obtiene categorías del usuario con caché"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT categoria 
                FROM question 
                WHERE assigned_user_id = ? AND categoria IS NOT NULL AND categoria != ''
                ORDER BY categoria
            """, (user_id,))
            
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error obteniendo categorías cacheadas: {str(e)}")
        return []