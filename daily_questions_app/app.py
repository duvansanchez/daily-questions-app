from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from flask_session import Session
import pyodbc
from dotenv import load_dotenv
import logging
import sys
import traceback
from collections import defaultdict
from flask_babel import Babel, format_datetime
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.ERROR,  # Cambiado de DEBUG a ERROR para reducir el ruido
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configurar el logger de werkzeug
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)  # Reducir el nivel de registro de werkzeug

app = Flask(__name__)
app.config['BABEL_DEFAULT_LOCALE'] = 'es'
babel = Babel(app)

# Configuración de correo electrónico
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'tu_email@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'tu_password_app')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'tu_email@gmail.com')

mail = Mail(app)

@app.template_filter('format_datetime')
def jinja2_format_datetime(value, format="EEEE, dd 'de' MMMM 'de' yyyy"):
    if value is None:
        return ""
    return format_datetime(value, format)

# Configuración de la sesión
app.secret_key = os.urandom(24)  # Clave secreta aleatoria
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')

# Asegurarse de que el directorio de sesiones exista
try:
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
except Exception as e:
    print(f"Error al crear el directorio de sesiones: {e}")

# Inicializar la extensión de sesión
Session(app)

# Configuración de la base de datos
# La cadena de conexión ahora se maneja dentro de get_db_connection

# Función para obtener la conexión a la base de datos
def get_db_connection():
    """Obtiene una conexión a la base de datos con manejo de contexto"""
    class ConnectionContext:
        def __init__(self):
            self.conn = None
            
        def __enter__(self):
            # Intentar con ODBC 18 primero, luego 17, luego el genérico
            drivers = [
                "ODBC Driver 18 for SQL Server",
                "ODBC Driver 17 for SQL Server",
                "SQL Server"  # Último recurso
            ]
            
            last_error = None
            
            for driver in drivers:
                try:
                    # Configuración de conexión actualizada
                    conn_str = (
                        f"DRIVER={{{driver}}};"
                        "SERVER=DESKTOP-2MR0PJ6;"  # Solo el nombre del servidor
                        "DATABASE=DailyQuestions;"
                        "Trusted_Connection=yes;"  # Usando autenticación de Windows
                        "TrustServerCertificate=yes;"
                        "Connection Timeout=30;"
                        "charset=UTF-8;"
                        "encoding=UTF-8;"
                        "MARS_Connection=yes;"
                        "ApplicationIntent=ReadWrite;"
                    )
                    self.conn = pyodbc.connect(conn_str, autocommit=False)
                    
                    # Configurar el cursor para mejor manejo de errores
                    cursor = self.conn.cursor()
                    cursor.execute("SET ARITHABORT ON")
                    cursor.execute("SET ANSI_WARNINGS ON")
                    cursor.execute("SET ANSI_PADDING ON")
                    cursor.execute("SET ANSI_NULLS ON")
                    cursor.execute("SET CONCAT_NULL_YIELDS_NULL ON")
                    cursor.execute("SET QUOTED_IDENTIFIER ON")
                    cursor.execute("SET NOCOUNT ON")
                    return self.conn
                except Exception as e:
                    last_error = e
                    logger.error(f"No se pudo conectar con {driver}: {str(e)}")
            
            # Si llegamos aquí, todas las conexiones fallaron
            error_msg = "No se pudo establecer conexión con ningún controlador ODBC disponible"
            logger.error(error_msg)
            if last_error:
                logger.error(f"Último error: {str(last_error)}")
            raise Exception(error_msg)
                
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.conn:
                if exc_type is not None:  # Si hubo un error
                    logger.error(f"Error en la conexión: {str(exc_val)}")
                    self.conn.rollback()
                else:
                    self.conn.commit()
                self.conn.close()
    
    return ConnectionContext()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized():
    # Si es una petición AJAX o API que espera JSON
    if request.is_json or '/api/' in request.path:
        response = jsonify({
            'status': 'error', 
            'message': 'No autenticado. Por favor, inicie sesión de nuevo.'
        })
        response.status_code = 401
        return response
    
    # Para peticiones normales de navegador, redirigir al login
    try:
        # Guardar la URL actual para redirigir después del login
        if request.endpoint != 'login' and not request.path.startswith(('/static/', '/favicon.ico')):
            session['next_url'] = request.url
    except Exception as e:
        print(f"Error al guardar la URL de redirección: {e}")
    
    # Redirigir a la página de login
    return redirect(url_for('login'))

# =============================
# Estadísticas de Objetivos
# =============================
@app.route('/api/objetivos/stats_summary', methods=['GET'])
@login_required
def objetivos_stats_summary():
    """
    Devuelve resumen por período (hoy, semana, mes, año):
      - esperados: objetivos de la categoría correspondiente al período.
          * recurrentes: siempre cuentan como 1 por objetivo en el período
          * no recurrentes: cuentan si fueron creados dentro del período
          * excluye estado 'histórico'
      - cumplidos: completado = 1 y fecha_completado dentro del período
      - saltados: registros en objetivos_saltados dentro del período (cuenta objetivos únicos)
      - no_cumplidos = max(esperados - cumplidos - saltados, 0)
    """
    try:
        ahora = datetime.now()
        # Rango de HOY (cerrado-abierto)
        hoy_inicio = datetime(ahora.year, ahora.month, ahora.day)
        hoy_fin = hoy_inicio + timedelta(days=1)

        # Semana completa (lunes 00:00 a lunes siguiente 00:00)
        delta_lunes = timedelta(days=hoy_inicio.weekday())
        semana_inicio = hoy_inicio - delta_lunes
        semana_fin = semana_inicio + timedelta(days=7)

        # Mes completo
        mes_inicio = datetime(ahora.year, ahora.month, 1)
        if ahora.month == 12:
            mes_fin = datetime(ahora.year + 1, 1, 1)
        else:
            mes_fin = datetime(ahora.year, ahora.month + 1, 1)

        # Año completo
        anio_inicio = datetime(ahora.year, 1, 1)
        anio_fin = datetime(ahora.year + 1, 1, 1)

        periodos = {
            'hoy':        {'cat': 'diario',   'ini': hoy_inicio,    'fin': hoy_fin},
            'semana':     {'cat': 'semanal',  'ini': semana_inicio, 'fin': semana_fin},
            'mes':        {'cat': 'mensual',  'ini': mes_inicio,    'fin': mes_fin},
            'anio':       {'cat': 'anual',    'ini': anio_inicio,   'fin': anio_fin},
        }

        with get_db_connection() as conn:
            cursor = conn.cursor()

            def contar_esperados(cat, ini, fin):
                # Recurrentes de esa categoría (INCLUYE históricos)
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM objetivos
                    WHERE user_id = ?
                      AND LOWER(COALESCE(categoria,'')) = ?
                      AND COALESCE(recurrente, 0) = 1
                    """,
                    (current_user.id, cat)
                )
                rec = int(cursor.fetchone()[0])

                # No recurrentes creados en el período (INCLUYE históricos)
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM objetivos
                    WHERE user_id = ?
                      AND LOWER(COALESCE(categoria,'')) = ?
                      AND COALESCE(recurrente, 0) = 0
                      AND fecha_creacion >= ? AND fecha_creacion < ?
                    """,
                    (current_user.id, cat, ini, fin)
                )
                no_rec = int(cursor.fetchone()[0])
                return rec + no_rec

            def contar_cumplidos(cat, ini, fin):
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM objetivos
                    WHERE user_id = ?
                      AND LOWER(COALESCE(categoria,'')) = ?
                      AND completado = 1
                      AND fecha_completado >= ? AND fecha_completado < ?
                    """,
                    (current_user.id, cat, ini, fin)
                )
                return int(cursor.fetchone()[0])

            def contar_saltados(cat, ini, fin):
                # Cuenta objetivos únicos saltados en el período
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT os.objetivo_id)
                    FROM objetivos_saltados os
                    JOIN objetivos o ON o.id = os.objetivo_id AND o.user_id = os.user_id
                    WHERE os.user_id = ?
                      AND LOWER(COALESCE(o.categoria,'')) = ?
                      AND os.fecha_saltada >= ? AND os.fecha_saltada < ?
                    """,
                    (current_user.id, cat, ini, fin)
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

            resultado = {}
            for clave, cfg in periodos.items():
                cat = cfg['cat']
                ini = cfg['ini']
                fin = cfg['fin']
                esperados = contar_esperados(cat, ini, fin)
                cumplidos = contar_cumplidos(cat, ini, fin)
                saltados = contar_saltados(cat, ini, fin)
                no_cumplidos = max(esperados - cumplidos - saltados, 0)
                resultado[clave] = {
                    'esperados': esperados,
                    'cumplidos': cumplidos,
                    'no_cumplidos': no_cumplidos,
                    'saltados': saltados,
                }

        return jsonify({'status': 'success', 'data': resultado})
    except Exception as e:
        logger.error(f"Error en objetivos_stats_summary: {str(e)}")
        return jsonify({'status': 'error', 'message': 'No se pudieron calcular las estadísticas de objetivos'}), 500

def obtener_subobjetivos_completados_fecha(cursor, user_id, fecha):
    """
    Función auxiliar para obtener subobjetivos completados en una fecha específica.
    Sigue el principio de función pequeña con una sola responsabilidad.
    """
    query_subobjetivos = """
        SELECT s.id, s.titulo, s.objetivo_id, o.titulo as objetivo_titulo,
               scl.fecha_completado, 
               FORMAT(scl.fecha_creacion, 'HH:mm:ss') as hora_completado
        FROM subobjetivos s
        INNER JOIN subobjetivos_completados_log scl ON s.id = scl.subobjetivo_id
        INNER JOIN objetivos o ON s.objetivo_id = o.id
        WHERE scl.user_id = ? 
          AND CAST(scl.fecha_completado AS DATE) = CAST(? AS DATE)
        ORDER BY scl.fecha_creacion ASC
    """
    
    cursor.execute(query_subobjetivos, (user_id, fecha))
    subobjetivos_completados = []
    
    for row in cursor.fetchall():
        subobjetivos_completados.append({
            'id': row.id,
            'titulo': row.titulo,
            'objetivo_id': row.objetivo_id,
            'objetivo_titulo': row.objetivo_titulo,
            'fecha_completado': fecha,
            'hora_completado': row.hora_completado
        })
    
    return subobjetivos_completados

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
                WHERE o.user_id = ? AND CAST(o.fecha_creacion AS DATE) = ?
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
            # Consulta simplificada y robusta para evitar errores de conversión
            query_completados = """
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       o.parte_dia, o.horas_estimadas,
                       'normal' as tipo,
                       ISNULL(FORMAT(o.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                       ISNULL(FORMAT(o.fecha_completado, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_completado
                FROM objetivos o
                WHERE o.user_id = ? 
                AND (o.recurrente = 0 OR o.recurrente IS NULL)
                AND o.fecha_completado IS NOT NULL
                AND TRY_CAST(o.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                AND o.completado = 1
                
                UNION ALL
                
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad,
                       o.parte_dia, o.horas_estimadas,
                       'recurrente' as tipo,
                       ISNULL(FORMAT(ocl.fecha_completado, 'HH:mm:ss'), 'N/A') as hora_completado,
                       ISNULL(FORMAT(ocl.fecha_completado, 'yyyy-MM-dd HH:mm:ss'), 'N/A') as fecha_completado
                FROM objetivos o
                INNER JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
                WHERE o.user_id = ? 
                AND o.recurrente = 1
                AND ocl.fecha_completado IS NOT NULL
                AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                
                ORDER BY fecha_completado DESC
            """
            
            cursor.execute(query_completados, (current_user.id, fecha, current_user.id, fecha))
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
            
            # Obtener objetivos recurrentes pendientes para este día
            # (objetivos recurrentes activos que no fueron completados este día)
            # ACTUALIZADO: Usar la misma lógica que el calendario para consistencia
            query_recurrentes_pendientes = """
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad, 
                       o.recurrente, o.parte_dia, o.horas_estimadas,
                       CONVERT(varchar, o.fecha_creacion, 120) as fecha_creacion
                FROM objetivos o
                WHERE o.user_id = ?
                  AND o.recurrente = 1
                  AND (o.estado != 'histórico' OR o.estado IS NULL)
                  AND LOWER(COALESCE(o.categoria, '')) = 'diario'
                  AND CAST(o.fecha_creacion AS DATE) <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM objetivos_completados_log ocl 
                      WHERE ocl.objetivo_id = o.id 
                        AND ocl.user_id = o.user_id 
                        AND TRY_CAST(ocl.fecha_completado AS DATE) = TRY_CAST(? AS DATE)
                  )
                ORDER BY o.fecha_creacion DESC
            """
            
            cursor.execute(query_recurrentes_pendientes, (current_user.id, fecha, fecha))
            objetivos_recurrentes_pendientes = []
            for row in cursor.fetchall():
                objetivos_recurrentes_pendientes.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'categoria': row.categoria,
                    'prioridad': row.prioridad,
                    'recurrente': True,
                    'parte_dia': row.parte_dia,
                    'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                    'fecha_creacion': row.fecha_creacion,
                    'estado': 'pendiente',
                    'tipo_origen': 'recurrente_pendiente'
                })
            
            # Obtener subobjetivos completados en esta fecha
            subobjetivos_completados = obtener_subobjetivos_completados_fecha(cursor, current_user.id, fecha)
            
            resumen = {
                'total_creados': len(objetivos_creados),
                'total_completados': len(objetivos_completados),
                'total_recurrentes_pendientes': len(objetivos_recurrentes_pendientes),
                'total_subobjetivos_completados': len(subobjetivos_completados)
            }
            
            return jsonify({
                'status': 'success',
                'fecha': fecha,
                'resumen': resumen,
                'objetivos_creados': objetivos_creados,
                'objetivos_completados': objetivos_completados,
                'objetivos_recurrentes_pendientes': objetivos_recurrentes_pendientes,
                'subobjetivos_completados': subobjetivos_completados
            })
            
    except Exception as e:
        logger.error(f"Error en objetivos_detalle_dia: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/objetivos/calendario', methods=['GET'])
@login_required
def objetivos_calendario():
    """
    Calendario mensual de objetivos creados y completados (MEJORADO).
    Ahora incluye:
    - Objetivos recurrentes completados (desde objetivos_completados_log)
    - Objetivos no completados por día
    
    Parámetros:
      - mes: 0-11 (0=Enero)
      - anio: año numérico (ej. 2025)
    Respuesta:
      {
        status: 'success',
        data: {
          anio: 2025,
          mes: 0,
          dias_en_mes: 31,
          creados_por_dia: { '1': 2, '5': 1, ... },
          completados_por_dia: { '2': 3, '10': 5, ... },  # Incluye recurrentes
          pendientes_por_dia: { '1': 1, '3': 2, ... },  # Total disponibles - completados
          total_creados: 10,
          total_completados: 12,  # Incluye recurrentes
          total_pendientes: 5
        }
      }
    """
    try:
        ahora = datetime.now()
        mes = request.args.get('mes', default=ahora.month - 1, type=int)
        anio = request.args.get('anio', default=ahora.year, type=int)
        
        logger.info(f"Solicitando calendario para usuario {current_user.id}, mes {mes}, año {anio}")

        # Normalizar rango del mes (0-11)
        if mes < 0 or mes > 11:
            logger.warning(f"Parámetro mes inválido: {mes}")
            return jsonify({'status': 'error', 'message': 'Parámetro mes inválido'}), 400

        inicio = datetime(anio, mes + 1, 1)
        # Fin = primer día del siguiente mes
        if mes == 11:
            fin = datetime(anio + 1, 1, 1)
        else:
            fin = datetime(anio, mes + 2, 1)

        # Cantidad de días del mes
        dias_en_mes = (fin - inicio).days
        
        logger.info(f"Período de consulta: {inicio} a {fin}, días en mes: {dias_en_mes}")

        creados = {}
        completados = {}
        pendientes = {}

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Creados por día (solo objetivos normales)
            logger.info("Ejecutando consulta de objetivos creados")
            cursor.execute(
                """
                SELECT DAY(fecha_creacion) AS dia, COUNT(*)
                FROM objetivos
                WHERE user_id = ?
                  AND fecha_creacion >= ? AND fecha_creacion < ?
                GROUP BY DAY(fecha_creacion)
                """,
                (current_user.id, inicio, fin)
            )
            creados_rows = cursor.fetchall()
            logger.info(f"Encontrados {len(creados_rows)} días con objetivos creados")
            
            for row in creados_rows:
                creados[str(int(row[0]))] = int(row[1])

            # 2. Completados por día (objetivos normales + recurrentes)
            logger.info("Ejecutando consulta de objetivos completados (normales)")
            
            # 2a. Objetivos normales completados
            cursor.execute(
                """
                SELECT DAY(fecha_completado) AS dia, COUNT(*)
                FROM objetivos
                WHERE user_id = ?
                  AND completado = 1
                  AND fecha_completado >= ? AND fecha_completado < ?
                  AND (recurrente = 0 OR recurrente IS NULL)
                GROUP BY DAY(fecha_completado)
                """,
                (current_user.id, inicio, fin)
            )
            completados_normales = cursor.fetchall()
            logger.info(f"Encontrados {len(completados_normales)} días con objetivos normales completados")
            
            for row in completados_normales:
                dia = str(int(row[0]))
                count = int(row[1])
                completados[dia] = completados.get(dia, 0) + count

            # 2b. Objetivos recurrentes completados (desde log)
            logger.info("Ejecutando consulta de objetivos recurrentes completados")
            cursor.execute(
                """
                SELECT DAY(ocl.fecha_completado) AS dia, COUNT(*)
                FROM objetivos_completados_log ocl
                JOIN objetivos o ON ocl.objetivo_id = o.id
                WHERE ocl.user_id = ?
                  AND ocl.fecha_completado >= ? AND ocl.fecha_completado < ?
                GROUP BY DAY(ocl.fecha_completado)
                """,
                (current_user.id, inicio, fin)
            )
            completados_recurrentes = cursor.fetchall()
            logger.info(f"Encontrados {len(completados_recurrentes)} días con objetivos recurrentes completados")
            
            for row in completados_recurrentes:
                dia = str(int(row[0]))
                count = int(row[1])
                completados[dia] = completados.get(dia, 0) + count

# 3. Pendientes por día (recurrentes no completados ese día + objetivos creados ese día no completados)
            logger.info("Calculando objetivos pendientes por día")

            # Para cada día del mes, calcular pendientes
            dia_actual_loop = inicio.date()
            while dia_actual_loop < fin.date():
                fecha_dia = dia_actual_loop
                dia_str = str(fecha_dia.day)
                
                # Solo calcular para días pasados o hoy
                if fecha_dia <= datetime.now().date():
                    # 3a. Objetivos recurrentes no completados ese día (basado en el log)
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM objetivos o
                        LEFT JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id 
                            AND ocl.user_id = o.user_id 
                            AND CONVERT(date, ocl.fecha_completado) = ?
                        WHERE o.user_id = ?
                          AND o.recurrente = 1
                          AND (o.estado != 'histórico' OR o.estado IS NULL)
                          AND LOWER(COALESCE(o.categoria, '')) = 'diario'
                          AND ocl.id IS NULL
                          AND CAST(o.fecha_creacion AS DATE) <= ?
                        """,
                        (fecha_dia, current_user.id, fecha_dia)
                    )
                    recurrentes_pendientes = cursor.fetchone()[0]

                    # 3b. Objetivos normales creados ese día no completados
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM objetivos
                        WHERE user_id = ?
                          AND CAST(fecha_creacion AS DATE) = ?
                          AND (recurrente = 0 OR recurrente IS NULL)
                          AND completado = 0
                        """,
                        (current_user.id, fecha_dia)
                    )
                    normales_pendientes = cursor.fetchone()[0]

                    total_pendientes_dia = recurrentes_pendientes + normales_pendientes
                    if total_pendientes_dia > 0:
                        pendientes[dia_str] = total_pendientes_dia
                
                dia_actual_loop += timedelta(days=1)

            logger.info(f"Calculados pendientes para {len(pendientes)} días")

        total_creados = sum(creados.values())
        total_completados = sum(completados.values())
        total_pendientes = sum(pendientes.values())
        
        logger.info(f"Totales - Creados: {total_creados}, Completados: {total_completados}, Pendientes: {total_pendientes}")

        response_data = {
            'status': 'success',
            'data': {
                'anio': anio,
                'mes': mes,
                'dias_en_mes': dias_en_mes,
                'creados_por_dia': creados,
                'completados_por_dia': completados,
                'pendientes_por_dia': pendientes,
                'total_creados': total_creados,
                'total_completados': total_completados,
                'total_pendientes': total_pendientes
            }
        }
        
        logger.info(f"Enviando respuesta del calendario con {len(completados)} días con completados")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error en objetivos_calendario: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error', 
            'message': 'No se pudo generar el calendario de objetivos',
            'error': str(e) if app.debug else None
        }), 500

@app.route('/api/objetivos/dia', methods=['GET'])
@login_required
def objetivos_dia():
    """
    Obtiene todos los objetivos de un día específico con detalles completos.
    Parámetros:
      - dia: día del mes (1-31)
      - mes: mes (0-11, donde 0=Enero)
      - anio: año numérico (ej. 2025)
    Respuesta:
      {
        status: 'success',
        data: {
          fecha: '2025-01-15',
          objetivos: [
            {
              id: 1,
              titulo: 'Hacer ejercicio',
              descripcion: 'Correr 30 minutos',
              completado: true,
              fecha_creacion: '2025-01-15 08:00:00',
              fecha_completado: '2025-01-15 19:30:00',
              categoria: 'Salud'
            },
            ...
          ]
        }
      }
    """
    try:
        dia = request.args.get('dia', type=int)
        mes = request.args.get('mes', type=int)
        anio = request.args.get('anio', type=int)
        
        if not all([dia, mes is not None, anio]):
            return jsonify({'status': 'error', 'message': 'Parámetros día, mes y año son requeridos'}), 400
            
        if mes < 0 or mes > 11 or dia < 1 or dia > 31:
            return jsonify({'status': 'error', 'message': 'Parámetros inválidos'}), 400
        
        # Crear fecha específica
        try:
            fecha_objetivo = datetime(anio, mes + 1, dia)
            fecha_siguiente = fecha_objetivo + timedelta(days=1)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Fecha inválida'}), 400
        
        # Listas para la respuesta
        objetivos_creados = []
        objetivos_completados = []
        objetivos_recurrentes_pendientes = []
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Objetivos Creados en este día
            cursor.execute(
                """
                SELECT o.id, o.titulo, o.descripcion, o.completado, 
                       o.fecha_creacion, o.fecha_completado, o.categoria, o.prioridad, o.parte_dia,
                       o.recurrente, o.tipo
                FROM objetivos o
                WHERE o.user_id = ?
                  AND o.fecha_creacion >= ? AND o.fecha_creacion < ?
                ORDER BY o.fecha_creacion DESC
                """,
                (current_user.id, fecha_objetivo, fecha_siguiente)
            )
            
            for row in cursor.fetchall():
                obj = {
                    'id': row[0],
                    'titulo': row[1],
                    'descripcion': row[2] or '',
                    'completado': bool(row[3]),
                    'fecha_creacion': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else '',
                    'fecha_completado': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else '',
                    'categoria': row[6] or 'Sin categoría',
                    'prioridad': row[7] or 'media',
                    'parte_dia': row[8] or '',
                    'recurrente': bool(row[9]) if row[9] is not None else False,
                    'tipo': row[10] or 'normal'
                }
                objetivos_creados.append(obj)

            # 2. Objetivos Completados en este día (Normales y Recurrentes)
            # 2a. Normales completados hoy (que no fueron creados hoy, para no duplicar en lógica de frontend, 
            # pero el frontend usa 'some' así que está bien tenerlos todos)
            cursor.execute(
                """
                SELECT o.id, o.titulo, o.descripcion, 1 as completado, 
                       o.fecha_creacion, o.fecha_completado, o.categoria, o.prioridad, o.parte_dia,
                       o.recurrente, o.tipo
                FROM objetivos o
                WHERE o.user_id = ?
                  AND o.completado = 1
                  AND o.fecha_completado >= ? AND o.fecha_completado < ?
                """,
                (current_user.id, fecha_objetivo, fecha_siguiente)
            )
            for row in cursor.fetchall():
                obj = {
                    'id': row[0],
                    'titulo': row[1],
                    'descripcion': row[2] or '',
                    'completado': True,
                    'fecha_creacion': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else '',
                    'fecha_completado': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else '',
                    'categoria': row[6] or 'Sin categoría',
                    'prioridad': row[7] or 'media',
                    'parte_dia': row[8] or '',
                    'recurrente': bool(row[9]) if row[9] is not None else False,
                    'tipo': row[10] or 'normal'
                }
                objetivos_completados.append(obj)

            # 2b. Recurrentes completados hoy (desde log)
            cursor.execute(
                """
                SELECT o.id, o.titulo, o.descripcion, 1 as completado, 
                       o.fecha_creacion, log.fecha_completado, o.categoria, o.prioridad, o.parte_dia,
                       o.recurrente, o.tipo
                FROM objetivos_completados_log log
                JOIN objetivos o ON log.objetivo_id = o.id
                WHERE log.user_id = ?
                  AND log.fecha_completado >= ? AND log.fecha_completado < ?
                """,
                (current_user.id, fecha_objetivo, fecha_siguiente)
            )
            for row in cursor.fetchall():
                # Evitar duplicados si ya está (aunque query anterior era tabla objetivos, esta es log)
                if not any(o['id'] == row[0] for o in objetivos_completados):
                    obj = {
                        'id': row[0],
                        'titulo': row[1],
                        'descripcion': row[2] or '',
                        'completado': True,
                        'fecha_creacion': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else '',
                        'fecha_completado': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else '',
                        'categoria': row[6] or 'Sin categoría',
                        'prioridad': row[7] or 'media',
                        'parte_dia': row[8] or '',
                        'recurrente': True,
                        'tipo': row[10] or 'recurrente'
                    }
                    objetivos_completados.append(obj)

            # 3. Objetivos Recurrentes Pendientes
            # Solo si el día es hoy o pasado
            if fecha_objetivo.date() <= datetime.now().date():
                cursor.execute(
                    """
                    SELECT o.id, o.titulo, o.descripcion, 0 as completado, 
                           o.fecha_creacion, NULL as fecha_completado, o.categoria, o.prioridad, o.parte_dia,
                           o.recurrente, o.tipo
                    FROM objetivos o
                    LEFT JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id 
                        AND ocl.user_id = o.user_id 
                        AND ocl.fecha_completado >= ? AND ocl.fecha_completado < ?
                    WHERE o.user_id = ?
                      AND o.recurrente = 1
                      AND (o.estado != 'histórico' OR o.estado IS NULL)
                      AND LOWER(COALESCE(o.categoria, '')) = 'diario'
                      AND ocl.id IS NULL
                      AND CAST(o.fecha_creacion AS DATE) <= ?
                    """,
                    (fecha_objetivo, fecha_siguiente, current_user.id, fecha_objetivo)
                )
                for row in cursor.fetchall():
                    obj = {
                        'id': row[0],
                        'titulo': row[1],
                        'descripcion': row[2] or '',
                        'completado': False,
                        'fecha_creacion': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else '',
                        'fecha_completado': None,
                        'categoria': row[6] or 'Sin categoría',
                        'prioridad': row[7] or 'media',
                        'parte_dia': row[8] or '',
                        'recurrente': True,
                        'tipo': row[10] or 'recurrente'
                    }
                    objetivos_recurrentes_pendientes.append(obj)
        
        return jsonify({
            'status': 'success',
            'data': {
                'fecha': fecha_objetivo.strftime('%Y-%m-%d'),
                'dia': dia,
                'mes': mes,
                'anio': anio,
                'objetivos_creados': objetivos_creados,
                'objetivos_completados': objetivos_completados,
                'objetivos_recurrentes_pendientes': objetivos_recurrentes_pendientes
            }
        })
        
    except Exception as e:
        logger.error(f"Error en objetivos_dia: {str(e)}")
        return jsonify({'status': 'error', 'message': 'No se pudieron obtener los objetivos del día'}), 500

@app.route('/api/objetivos/mes-detallado', methods=['GET'])
@login_required
def objetivos_mes_detallado():
    """
    Obtiene todos los objetivos de un mes específico con detalles completos.
    Parámetros:
      - mes: mes (0-11, donde 0=Enero)
      - anio: año numérico (ej. 2025)
    Respuesta:
      {
        status: 'success',
        data: {
          mes: 0,
          anio: 2025,
          objetivos: [
            {
              id: 1,
              titulo: 'Hacer ejercicio',
              descripcion: 'Correr 30 minutos',
              completado: true,
              fecha_creacion: '2025-01-15',
              fecha_completado: '2025-01-15',
              categoria: 'Salud',
              prioridad: 'alta'
            },
            ...
          ]
        }
      }
    """
    try:
        ahora = datetime.now()
        mes = request.args.get('mes', default=ahora.month - 1, type=int)
        anio = request.args.get('anio', default=ahora.year, type=int)
        
        logger.info(f"Solicitando objetivos detallados para usuario {current_user.id}, mes {mes}, año {anio}")

        # Normalizar rango del mes (0-11)
        if mes < 0 or mes > 11:
            logger.warning(f"Parámetro mes inválido: {mes}")
            return jsonify({'status': 'error', 'message': 'Parámetro mes inválido'}), 400

        inicio = datetime(anio, mes + 1, 1)
        # Fin = primer día del siguiente mes
        if mes == 11:
            fin = datetime(anio + 1, 1, 1)
        else:
            fin = datetime(anio, mes + 2, 1)

        objetivos = []
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Buscar objetivos que deberían aparecer en este mes:
            # 1. Objetivos creados en este mes
            # 2. Objetivos completados en este mes  
            # 3. Objetivos activos que por su frecuencia deberían estar disponibles en este mes
            # INCLUIMOS objetivos históricos para mostrar todo lo que pasó en el mes
            cursor.execute(
                """
                SELECT DISTINCT o.id, o.titulo, o.descripcion, o.completado, 
                       o.fecha_creacion, o.fecha_completado, o.categoria, o.prioridad,
                       o.recurrente, o.frecuencia, o.estado,
                       (SELECT COUNT(*) FROM objetivos_saltados os 
                        WHERE os.objetivo_id = o.id AND os.user_id = o.user_id) as veces_saltado
                FROM objetivos o
                WHERE o.user_id = ?
                  AND (
                    -- Objetivos creados en este mes
                    (o.fecha_creacion >= ? AND o.fecha_creacion < ?) OR
                    -- Objetivos completados en este mes
                    (o.completado = 1 AND o.fecha_completado >= ? AND o.fecha_completado < ?) OR
                    -- Objetivos activos por frecuencia que deberían estar disponibles
                    (o.estado != 'histórico' AND o.fecha_creacion < ? AND (
                        -- Objetivos diarios: siempre activos si fueron creados antes del mes
                        (o.categoria = 'diario' OR o.categoria IS NULL) OR
                        -- Objetivos semanales: activos si fueron creados antes del mes
                        o.categoria = 'semanal' OR
                        -- Objetivos mensuales: activos si fueron creados antes del mes
                        o.categoria = 'mensual' OR
                        -- Objetivos anuales: activos si fueron creados antes del mes
                        o.categoria = 'anual' OR
                        -- Objetivos generales: siempre activos
                        o.categoria = 'general'
                    ))
                  )
                ORDER BY o.fecha_creacion DESC, o.fecha_completado DESC
                """,
                (current_user.id, inicio, fin, inicio, fin, fin)
            )
            
            for row in cursor.fetchall():
                objetivo = {
                    'id': row[0],
                    'titulo': row[1],
                    'descripcion': row[2] or '',
                    'completado': bool(row[3]),
                    'fecha_creacion': row[4].strftime('%Y-%m-%d') if row[4] else '',
                    'fecha_completado': row[5].strftime('%Y-%m-%d') if row[5] else '',
                    'categoria': row[6] or 'Sin categoría',
                    'prioridad': row[7] or 'media',
                    'recurrente': bool(row[8]) if len(row) > 8 else False,
                    'frecuencia': row[9] if len(row) > 9 else None,
                    'estado': row[10] if len(row) > 10 else None,
                    'veces_saltado': int(row[11]) if len(row) > 11 and row[11] is not None else 0
                }
                objetivos.append(objetivo)
        
        logger.info(f"Encontrados {len(objetivos)} objetivos para el mes {mes+1}/{anio}")
        
        # Debug: mostrar algunos objetivos encontrados
        if objetivos:
            logger.info(f"Primeros 3 objetivos encontrados:")
            for i, obj in enumerate(objetivos[:3]):
                logger.info(f"  {i+1}. {obj['titulo']} - Estado: {obj['estado']} - Completado: {obj['completado']} - Saltado: {obj['veces_saltado']} veces")
            
            # Estadísticas de saltos
            total_saltos = sum(obj['veces_saltado'] for obj in objetivos)
            objetivos_saltados = len([obj for obj in objetivos if obj['veces_saltado'] > 0])
            if total_saltos > 0:
                logger.info(f"Estadísticas de saltos: {objetivos_saltados} objetivos saltados un total de {total_saltos} veces")
        else:
            logger.warning(f"No se encontraron objetivos para el período {inicio} - {fin}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'mes': mes,
                'anio': anio,
                'objetivos': objetivos,
                'total': len(objetivos)
            }
        })
        
    except Exception as e:
        logger.error(f"Error en objetivos_mes_detallado: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error', 
            'message': 'No se pudieron obtener los objetivos del mes',
            'error': str(e) if app.debug else None
        }), 500

# Modelos
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    @classmethod
    def get(cls, user_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password FROM [user] WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if user:
                return cls(user[0], user[1], user[2])
        return None

    @classmethod
    def get_by_username(cls, username):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password FROM [user] WHERE username = ?', (username,))
            user_data = cursor.fetchone()
            if user_data:
                return cls(user_data[0], user_data[1], user_data[2])
        return None

class Question:
    def __init__(self, id, text, type, options, active, created_at, assigned_user_id=None, descripcion=None, is_required=0, categoria='General', frecuencia='diaria'):
        self.id = id
        self.text = text
        self.type = type
        self.options = options
        self.active = active
        self.created_at = created_at
        self.assigned_user_id = assigned_user_id
        self.descripcion = descripcion
        self.is_required = is_required
        self.categoria = categoria
        self.frecuencia = frecuencia

    @classmethod
    def get_all(cls):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, text, type, options, active, created_at, assigned_user_id, descripcion, is_required, categoria, frecuencia FROM question')
            questions = [cls(*row) for row in cursor.fetchall()]
            return questions

    @classmethod
    def get_by_user(cls, user_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, text, type, options, active, created_at, assigned_user_id, descripcion, is_required, categoria, frecuencia '
                'FROM question WHERE assigned_user_id = ? AND active = 1',
                (user_id,)
            )
            rows = cursor.fetchall()
            questions = [cls(*row) for row in rows]
            return questions

    @classmethod
    def get_by_user_and_frequency(cls, user_id, frecuencia):
        try:
            logger.info(f"[DEBUG] Buscando preguntas para usuario {user_id} con frecuencia '{frecuencia}'")
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, text, type, options, active, created_at, assigned_user_id, descripcion, is_required, categoria, frecuencia '
                    'FROM question WHERE assigned_user_id = ? AND active = 1 AND frecuencia = ?',
                    (user_id, frecuencia)
                )
                rows = cursor.fetchall()
                logger.info(f"[DEBUG] Consulta SQL ejecutada, encontradas {len(rows)} filas")
                questions = [cls(*row) for row in rows]
                logger.info(f"[DEBUG] Creados {len(questions)} objetos Question")
                return questions
        except Exception as e:
            logger.error(f"[ERROR] Error en get_by_user_and_frequency: {str(e)}", exc_info=True)
            raise

    @classmethod
    def create(cls, text, type, options=None, assigned_user_id=None, descripcion=None, is_required=0, categoria='General', frecuencia='diaria', active=1):
        try:
            logger.info(f"[DEBUG] Ejecutando INSERT: text={text}, type={type}, options={options}, assigned_user_id={assigned_user_id}, descripcion={descripcion}, is_required={is_required}, categoria={categoria}, frecuencia={frecuencia}, active={active}")
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO question (text, type, options, assigned_user_id, descripcion, is_required, categoria, frecuencia, active, created_at) OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())',
                    (text, type, options, assigned_user_id, descripcion, is_required, categoria, frecuencia, active)
                )
                question_id = cursor.fetchone()[0]
                conn.commit()
                logger.info(f"[DEBUG] Pregunta creada con ID: {question_id}")
                return question_id
        except Exception as e:
            logger.error(f"[DEBUG] Error al crear pregunta: {str(e)}")
            raise

class Response:
    def __init__(self, id, question_id, response, date, created_at):
        self.id = id
        self.question_id = question_id
        self.response = response
        self.date = date
        self.created_at = created_at

    @classmethod
    def create(cls, question_id, response, date):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO response (question_id, response, date) VALUES (?, ?, ?)',
                (question_id, response, date)
            )
            conn.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

# Rutas
@app.route('/')
@login_required
def index():
    try:
        logger.info(f"[DEBUG] Accediendo a preguntas diarias para usuario {current_user.id}")
        questions_objects = Question.get_by_user_and_frequency(current_user.id, 'diaria')
        logger.info(f"[DEBUG] Encontradas {len(questions_objects)} preguntas diarias")
        
        # Convertir objetos Question a diccionarios para que sean JSON serializables
        questions = []
        for q in questions_objects:
            questions.append({
                'id': q.id,
                'text': q.text,
                'type': q.type,
                'options': q.options,
                'active': q.active,
                'created_at': q.created_at,
                'assigned_user_id': q.assigned_user_id,
                'descripcion': q.descripcion,
                'is_required': q.is_required,
                'categoria': q.categoria,
                'frecuencia': q.frecuencia
            })
        
        return render_template('index.html', questions=questions, date=datetime.now(), tipo_pregunta='diaria')
    except Exception as e:
        logger.error(f"[ERROR] Error en index: {str(e)}", exc_info=True)
        flash(f'Error al cargar preguntas diarias: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/preguntas-semanales')
@login_required
def preguntas_semanales():
    try:
        logger.info(f"[DEBUG] Accediendo a preguntas semanales para usuario {current_user.id}")
        questions_objects = Question.get_by_user_and_frequency(current_user.id, 'semanal')
        logger.info(f"[DEBUG] Encontradas {len(questions_objects)} preguntas semanales")
        
        # Convertir objetos Question a diccionarios para que sean JSON serializables
        questions = []
        for q in questions_objects:
            questions.append({
                'id': q.id,
                'text': q.text,
                'type': q.type,
                'options': q.options,
                'active': q.active,
                'created_at': q.created_at,
                'assigned_user_id': q.assigned_user_id,
                'descripcion': q.descripcion,
                'is_required': q.is_required,
                'categoria': q.categoria,
                'frecuencia': q.frecuencia
            })
        
        return render_template('preguntas_semanales.html', questions=questions, date=datetime.now(), tipo_pregunta='semanal')
    except Exception as e:
        logger.error(f"[ERROR] Error en preguntas_semanales: {str(e)}", exc_info=True)
        flash(f'Error al cargar preguntas semanales: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/preguntas-mensuales')
@login_required
def preguntas_mensuales():
    try:
        logger.info(f"[DEBUG] Accediendo a preguntas mensuales para usuario {current_user.id}")
        questions_objects = Question.get_by_user_and_frequency(current_user.id, 'mensual')
        logger.info(f"[DEBUG] Encontradas {len(questions_objects)} preguntas mensuales")
        
        # Convertir objetos Question a diccionarios para que sean JSON serializables
        questions = []
        for q in questions_objects:
            questions.append({
                'id': q.id,
                'text': q.text,
                'type': q.type,
                'options': q.options,
                'active': q.active,
                'created_at': q.created_at,
                'assigned_user_id': q.assigned_user_id,
                'descripcion': q.descripcion,
                'is_required': q.is_required,
                'categoria': q.categoria,
                'frecuencia': q.frecuencia
            })
        
        return render_template('preguntas_mensuales.html', questions=questions, date=datetime.now(), tipo_pregunta='mensual')
    except Exception as e:
        logger.error(f"[ERROR] Error en preguntas_mensuales: {str(e)}", exc_info=True)
        flash(f'Error al cargar preguntas mensuales: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya está autenticado, redirigir a la página principal
    if current_user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'redirect': url_for('index')})
        return redirect(url_for('index'))
    
    # Obtener la URL de redirección de los parámetros de la solicitud o de la sesión
    next_url = request.args.get('next') or session.pop('next_url', None)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Por favor ingrese usuario y contraseña'}), 400
            flash('Por favor ingrese usuario y contraseña')
            return render_template('login.html', next=next_url)
            
        print(f"Intento de inicio de sesión para el usuario: {username}")
        
        try:
            # Obtener el usuario
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, username, password FROM [user] WHERE username = ?', (username,))
                db_user = cursor.fetchone()
            
            if db_user:
                user_id, db_username, db_password = db_user
                print(f"Usuario encontrado en DB - ID: {user_id}, Username: {db_username}")
                
                # Verificar la contraseña
                if check_password_hash(db_password, password):
                    user = User(user_id, db_username, db_password)
                    login_user(user)
                    print("Inicio de sesión exitoso")
                    
                    # Redirigir a la URL guardada o al índice
                    next_page = next_url or url_for('index')
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'redirect': next_page})
                    # Validar que la URL de redirección sea relativa al host actual
                    if next_page and not next_page.startswith(('http://', 'https://')):
                        return redirect(next_page)
                    return redirect(url_for('index'))
                
            # Si llegamos aquí, las credenciales son inválidas
            error_msg = 'Usuario o contraseña inválidos'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 401
            flash(error_msg)
            
        except Exception as e:
            print(f"Error durante el inicio de sesión: {str(e)}")
            error_msg = 'Error al procesar la solicitud de inicio de sesión'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 500
            flash(error_msg)
    
    # Para solicitudes GET o si hay un error, mostrar el formulario de login
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Método no permitido'}), 405
    return render_template('login.html', next=next_url)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si el usuario ya existe
                cursor.execute('SELECT id FROM [user] WHERE username = ?', (username,))
                if cursor.fetchone():
                    flash('El nombre de usuario ya existe')
                    return redirect(url_for('register'))
                
                # Crear nuevo usuario
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    'INSERT INTO [user] (username, password) VALUES (?, ?)',
                    (username, hashed_password)
                )
                conn.commit()
            
            flash('¡Registro exitoso! Por favor inicia sesión.')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Error durante el registro: {str(e)}")
            flash('Error al procesar el registro. Por favor intente de nuevo.')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    # Inicializar estadísticas con valores por defecto
    stats = {
        'total_preguntas': 0,
        'preguntas_activas': 0,
        'respuestas_hoy': 0
    }
    
    questions = []
    users = []
    
    try:
        connection_context = get_db_connection()
        
        with connection_context as conn:
            cursor = conn.cursor()
            
            # Verificar si el usuario existe
            try:
                user_query = 'SELECT id, username FROM [user] WHERE id = ?'
                cursor.execute(user_query, (current_user.id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    logger.error(f"Usuario {current_user.id} no encontrado en la base de datos")
                    flash('Error: Usuario no encontrado', 'error')
                    return redirect(url_for('index'))
                    
                user_id, username = user_data
                    
            except Exception as e:
                logger.error(f"Error en verificación de usuario: {str(e)}", exc_info=True)
                flash('Error al verificar permisos de usuario', 'error')
                return redirect(url_for('index'))
            
            # Verificar si hay datos en la tabla
            try:
                cursor.execute("SELECT COUNT(*) FROM question")
                count_result = cursor.fetchone()
                record_count = count_result[0] if count_result else 0
                
                if record_count > 0:
                    # Consulta completa para obtener preguntas (activas primero, luego por fecha)
                    basic_query = """
                        SELECT 
                            [id], 
                            [text], 
                            [type], 
                            [options], 
                            [active], 
                            [created_at],
                            [assigned_user_id],
                            [descripcion],
                            [is_required],
                            [categoria],
                            [frecuencia]
                        FROM [question] q
                        WHERE q.[assigned_user_id] = ? 
                        ORDER BY q.[active] DESC, q.[created_at] DESC
                    """
                        
                    # Ejecutar la consulta básica solo para el usuario actual
                    cursor.execute(basic_query, (current_user.id,))
                    
                    # Procesar resultados
                    questions_data = cursor.fetchall()
                    print(f"[DEBUG] Preguntas encontradas para usuario {current_user.id}: {[row[0] for row in questions_data]}")
                    
                    # Mapear los resultados a objetos Question
                    questions = []
                    for row in questions_data:
                        try:
                            # Procesar opciones
                            options = row[3]  # Índice 3 es donde está options en la consulta
                            if options and isinstance(options, str):
                                # Si las opciones están en formato de lista de Python, limpiarlas
                                if options.startswith('[') and options.endswith(']'):
                                    try:
                                        # Intentar evaluar como lista de Python
                                        options_list = eval(options)
                                        if isinstance(options_list, list):
                                            options = [str(opt).strip() for opt in options_list if opt]
                                        else:
                                            options = []
                                    except:
                                        # Si falla, tratar como cadena simple
                                        options = [opt.strip() for opt in options.split(',') if opt.strip()]
                                else:
                                    # Si es una cadena simple, dividir por comas
                                    options = [opt.strip() for opt in options.split(',') if opt.strip()]
                            else:
                                options = []
                            
                            question = Question(
                                id=row[0],
                                text=row[1],
                                type=row[2],
                                options=options,  # Ahora es una lista limpia
                                active=row[4],
                                created_at=row[5],
                                assigned_user_id=row[6],
                                descripcion=row[7],
                                is_required=row[8] if len(row) > 8 else 0,
                                categoria=row[9] if len(row) > 9 else 'General',
                                frecuencia=row[10] if len(row) > 10 and row[10] else 'diaria'
                            )
                            questions.append(question)
                        except Exception as e:
                            logger.error(f"Error al procesar pregunta {row[0] if row else 'N/A'}: {str(e)}", exc_info=True)
                            continue
                    
                    # Actualizar estadísticas
                    stats['total_preguntas'] = len(questions)
                    stats['preguntas_activas'] = sum(1 for q in questions if q.active)
                    
            except Exception as e:
                logger.error(f"Error al ejecutar consulta básica: {str(e)}", exc_info=True)
                # Si falla, intentar con una consulta más simple
                try:
                    cursor.execute("SELECT id, text, active FROM question")
                    simple_questions = cursor.fetchall()
                    questions = []
                    for q in simple_questions:
                        questions.append({
                            'id': q[0],
                            'text': q[1],
                            'active': q[2]
                        })
                    stats['total_preguntas'] = len(questions)
                    stats['preguntas_activas'] = sum(1 for q in questions if q['active'])
                except Exception as simple_e:
                    logger.error(f"Error en consulta simple: {str(simple_e)}")
                    questions = []
                    stats['total_preguntas'] = 0
                    stats['preguntas_activas'] = 0
                    questions = [] # Asegurarse de que questions esté definido en caso de error
                    
            # 4. Obtener lista de usuarios
            logger.info("=== OBTENIENDO LISTA DE USUARIOS ===")
            try:
                cursor.execute('SELECT id, username FROM [user] ORDER BY username')
                users = [{'id': row[0], 'username': row[1]} for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"Error obteniendo usuarios: {str(e)}")
                users = []

            # 5. Obtener lista de categorías únicas
            logger.info("=== OBTENIENDO LISTA DE CATEGORIAS ===")
            try:
                # Usar parámetros para evitar problemas de inyección SQL
                cursor.execute("SELECT DISTINCT categoria FROM question WHERE categoria IS NOT NULL AND categoria <> '' ORDER BY categoria")
                categories_from_db = [row[0] for row in cursor.fetchall() if row[0]]  # Filtrar valores None o vacíos
                
                # Depuración
                logger.info(f"Categorías encontradas en BD: {categories_from_db}")
                
                # Asegurarse de que 'General' esté siempre si no hay otras y ordenarlas
                categories = [cat for cat in categories_from_db if cat and cat != 'Todas' and cat != 'General']
                categories = list(set(categories))  # Eliminar duplicados por si acaso
                categories.sort()  # Ordenar alfabéticamente las categorías
                
                # Asegurarse de que 'General' esté presente
                if 'General' in categories_from_db or not categories:
                    if 'General' not in categories:
                        categories.insert(0, 'General')
                
                # Asegurarse de que 'Todas' esté al inicio
                if 'Todas' not in categories:
                    categories.insert(0, 'Todas')
                
                logger.info(f"Categorías finales: {categories}")
                
            except Exception as e:
                logger.error(f"Error obteniendo categorías: {str(e)}", exc_info=True)
                categories = ['Todas', 'General']  # Default en caso de error o tabla vacía

            # 6. Contar respuestas de hoy (simplificado)
            logger.info("=== CONTEO DE RESPUESTAS HOY ===")
            try:
                today_str = datetime.now().strftime('%Y-%m-%d')
                
                cursor.execute('SELECT COUNT(*) FROM response WHERE CONVERT(date, date) = ?', (today_str,))
                count_result = cursor.fetchone()
                
                if count_result and count_result[0] is not None:
                    stats['respuestas_hoy'] = int(count_result[0])
                else:
                    stats['respuestas_hoy'] = 0
                                    
            except Exception as e:
                logger.error(f"Error en conteo de respuestas: {str(e)}")
                stats['respuestas_hoy'] = 0
            
            
            return render_template('admin.html', 
                                stats=stats, 
                                questions=questions,
                                users=users,
                                categories=categories) # Pasar la lista de categorías
            
    except Exception as e:
        logger.error("\n=== ERROR GENERAL EN LA RUTA ADMIN ===")
        logger.error(f"Tipo de error: {type(e)}")
        logger.error(f"Error: {str(e)}")
        logger.error("Traceback completo:", exc_info=True)
        
        # Intentar obtener más información sobre el error
        error_details = {
            'type': str(type(e).__name__),
            'message': str(e),
            'traceback': str(traceback.format_exc())
        }
        
        # Registrar información adicional del estado actual
        logger.error(f"Estado actual - Preguntas: {len(questions)}, Usuarios: {len(users)}")
        
        # Mostrar un mensaje de error más descriptivo
        error_msg = f"Error al cargar el panel de administración: {str(e)}"
        if 'categorías' in str(e).lower():
            error_msg = "Error al cargar las categorías. Por favor, verifica la base de datos."
        elif 'preguntas' in str(e).lower():
            error_msg = "Error al cargar las preguntas. Por favor, verifica la base de datos."
            
        flash(error_msg, 'error')
        
        # Si es un error de base de datos, intentar una recuperación básica
        if 'pyodbc' in str(type(e).__module__):
            logger.error("Error de base de datos detectado, intentando recuperación...")
            try:
                # Intentar devolver una versión simplificada de la página
                return render_template('admin.html', 
                                    stats=stats, 
                                    questions=[],
                                    users=[],
                                    categories=['Todas', 'General'])
            except Exception as recovery_error:
                logger.error(f"Error en la recuperación: {str(recovery_error)}")
        
        return redirect(url_for('index'))
    finally:
        logger.info("=== FIN DE LA RUTA ADMIN ===\n")

@app.route('/add_question', methods=['POST'])
@login_required
def add_question():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    try:
        if request.is_json or is_ajax:
            try:
                data = request.get_json()
                text = data.get('text', '').strip()
                type = data.get('type', 'text')
                options = data.get('options', '').strip()
                descripcion = data.get('descripcion', '').strip()
                is_required = 1 if data.get('is_required') else 0
                active = 1 if data.get('active', True) else 0
                frecuencia = data.get('frecuencia', 'diaria').strip()
                categoria = data.get('categoria_existente', '').strip()
                nueva_categoria = data.get('nueva_categoria', '').strip()
                if nueva_categoria:
                    categoria = nueva_categoria
                    logger.info(f"Usando nueva categoría: {categoria}")
                elif not categoria:
                    categoria = 'Sin Categoría'
                    logger.info("No se seleccionó categoría, usando 'Sin Categoría'")
                else:
                    logger.info(f"Usando categoría existente: {categoria}")
            except Exception as e:
                logger.error(f"Error al procesar JSON: {str(e)}")
                if is_ajax:
                    return jsonify({'status': 'error', 'message': f'Error en el formato de los datos: {str(e)}'}), 400
                flash(f'Error en el formato de los datos: {str(e)}', 'danger')
                return redirect(url_for('admin'))
        else:
            # Debug: mostrar todos los datos del formulario
            logger.info(f"[DEBUG] Datos del formulario recibidos: {dict(request.form)}")
            
            text = request.form.get('text', '').strip()
            type = request.form.get('type', 'text')
            options = request.form.get('options', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            is_required = 1 if request.form.get('is_required') == 'on' else 0
            active = 1 if request.form.get('active') == 'on' else 0
            frecuencia = request.form.get('frecuencia', 'diaria').strip()
            categoria = request.form.get('categoria_existente', '').strip()
            nueva_categoria = request.form.get('nueva_categoria', '').strip()
            
            logger.info(f"[DEBUG] Frecuencia extraída del formulario: '{frecuencia}'")
            if nueva_categoria:
                categoria = nueva_categoria
                logger.info(f"[Form] Usando nueva categoría: {categoria}")
            elif not categoria:
                categoria = 'Sin Categoría'
                logger.info("[Form] No se seleccionó categoría, usando 'Sin Categoría'")
            else:
                logger.info(f"[Form] Usando categoría existente: {categoria}")
        assigned_user_id = int(current_user.id)
        # Validar campos requeridos
        if not text:
            logger.error('El texto de la pregunta es requerido')
            if is_ajax:
                return jsonify({'status': 'error', 'message': 'El texto de la pregunta es requerido'}), 400
            flash('El texto de la pregunta es requerido', 'error')
            return redirect(url_for('admin'))
        if type in ['checkbox', 'radio'] and not options:
            logger.error('Debes proporcionar al menos una opción para este tipo de pregunta')
            if is_ajax:
                return jsonify({'status': 'error', 'message': 'Debes proporcionar al menos una opción para este tipo de pregunta'}), 400
            flash('Debes proporcionar al menos una opción para este tipo de pregunta', 'error')
            return redirect(url_for('admin'))
        print(f"Tipo de pregunta: {type}")
        print(f"Opciones recibidas: {options}")
        print(f"Texto de la pregunta: {text}")
        print(f"Descripción: {descripcion}")
        print(f"Es requerida: {is_required}")
        print(f"Activa: {active}")
        if type not in ['text', 'select', 'checkbox', 'radio']:
            logger.error('Tipo de pregunta no válido')
            if is_ajax:
                return jsonify({'status': 'error', 'message': 'Tipo de pregunta no válido'}), 400
            flash('Tipo de pregunta no válido', 'error')
            return redirect(url_for('admin'))
        processed_options = None
        try:
            if type in ['checkbox', 'radio', 'multiple_choice'] and options:
                logger.info(f"Procesando opciones: {options}")
                options_list = []
                for opt in options.split('\n'):
                    opt = opt.strip()
                    if opt:
                        if opt.startswith('-'):
                            opt = opt[1:].strip()
                        options_list.append(opt)
                logger.info(f"Opciones después de procesar: {options_list}")
                processed_options = ','.join(options_list)
                logger.info(f"Opciones procesadas: {processed_options}")
                if not options_list and type != 'text':
                    type = 'text'
                    logger.warning('No se proporcionaron opciones válidas. Convirtiendo a tipo texto.')
            else:
                logger.info(f"No se requiere procesar opciones para el tipo: {type}")
        except Exception as e:
            logger.error(f"Error al procesar opciones: {str(e)}")
            if is_ajax:
                return jsonify({'status': 'error', 'message': f'Error al procesar las opciones: {str(e)}'}), 400
            flash(f'Error al procesar las opciones: {str(e)}', 'danger')
            return redirect(url_for('admin'))
        print(f"[DEBUG] Valores a insertar: text={text}, type={type}, options={processed_options}, assigned_user_id={assigned_user_id}, descripcion={descripcion}, is_required={is_required}, categoria={categoria}, active={active}")
        logger.info(f"[DEBUG] Valores a insertar: text={text}, type={type}, options={processed_options}, assigned_user_id={assigned_user_id}, descripcion={descripcion}, is_required={is_required}, categoria={categoria}, frecuencia={frecuencia}, active={active}")
        try:
            question_id = Question.create(
                text=text,
                type=type,
                options=processed_options,
                assigned_user_id=assigned_user_id,
                descripcion=descripcion,
                is_required=is_required,
                categoria=categoria,
                frecuencia=frecuencia,
                active=active
            )
            logger.info(f"[DEBUG] ID de pregunta insertada: {question_id} | Usuario: {assigned_user_id} | Texto: {text} | Activa: {active} | Categoria: {categoria}")
            print(f"[DEBUG] ID de pregunta insertada: {question_id} | Usuario: {assigned_user_id} | Texto: {text} | Activa: {active} | Categoria: {categoria}")
            if is_ajax:
                return jsonify({
                    'status': 'success',
                    'message': 'Pregunta creada exitosamente',
                    'question_id': question_id,
                    'redirect': url_for('admin')
                }), 200
            else:
                flash('Pregunta creada exitosamente', 'success')
                return redirect(url_for('admin'))
        except Exception as e:
            logger.error(f"Error al guardar en la base de datos: {str(e)}")
            if is_ajax:
                return jsonify({
                    'status': 'error',
                    'message': f'Error al guardar la pregunta en la base de datos: {str(e)}'
                }), 500
            flash(f'Error al guardar la pregunta: {str(e)}', 'danger')
            return redirect(url_for('admin'))
    except Exception as e:
        print(f"Error al agregar pregunta: {str(e)}")
        logger.error(f"Error inesperado en add_question: {str(e)}")
        if is_ajax:
            return jsonify({
                'status': 'error',
                'message': f'Error inesperado al agregar la pregunta: {str(e)}'
            }), 500
        flash(f'Error inesperado al agregar la pregunta: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route('/submit_responses', methods=['POST'])
@login_required
def submit_responses():
    try:
        data = request.get_json()
        print("Datos recibidos en submit_responses:", data)  # <-- DEPURACIÓN
        if not data or 'date' not in data or 'responses' not in data:
            return jsonify({'status': 'error', 'message': 'Datos de solicitud inválidos'}), 400
            
        # Convertir la fecha al formato correcto para SQL Server
        date_str = data['date']
        from datetime import datetime
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        now = datetime.now()
        date_with_time = now.replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
        responses = data['responses']
        
        print(f"Recibiendo respuestas para la fecha: {date_obj}")
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Primero eliminamos cualquier respuesta existente para este día
                try:
                    # Primero obtenemos los IDs de las preguntas asignadas al usuario
                    cursor.execute(
                        'SELECT id FROM question WHERE assigned_user_id = ?',
                        (current_user.id,)
                    )
                    question_ids = [row[0] for row in cursor.fetchall()]  # Mantener como enteros
                    
                    if question_ids:  # Solo si hay preguntas asignadas
                        # Convertir la fecha a string en formato YYYY-MM-DD
                        date_str = date_obj.strftime('%Y-%m-%d')
                        
                        # Crear una lista de cadenas con los IDs de pregunta
                        question_ids_str = [str(qid) for qid in question_ids]
                        
                        # Construir la consulta SQL directamente (sin usar parámetros para la lista IN)
                        delete_sql = """
                            DELETE r
                            FROM response r
                            INNER JOIN question q ON r.question_id = q.id
                            WHERE CONVERT(DATE, r.date) = ?
                            AND q.assigned_user_id = ?
                        """
                        
                        cursor.execute(delete_sql, (date_str, current_user.id))
                        print(f"Respuestas anteriores eliminadas para el usuario {current_user.id} en la fecha {date_str}")
                    else:
                        print("No hay preguntas asignadas a este usuario")
                except Exception as e:
                    print(f"Error al eliminar respuestas anteriores: {str(e)}")
                    conn.rollback()
                    return jsonify({
                        'status': 'error', 
                        'message': f'Error al limpiar respuestas anteriores: {str(e)}'
                    }), 500
                
                # Luego insertamos las nuevas respuestas
                for question_id_str, response_data in responses.items():
                    try:
                        question_id = int(question_id_str)  # Asegurar que el ID sea entero
                        
                        # Manejar tanto el formato antiguo (solo texto) como el nuevo (objeto con tiempo)
                        if isinstance(response_data, dict):
                            response_text = str(response_data.get('answer', '')) if response_data.get('answer') is not None else ""
                            start_time_str = response_data.get('start_time')
                            response_time = response_data.get('response_time')
                        else:
                            response_text = str(response_data) if response_data is not None else ""
                            start_time_str = None
                            response_time = None
                        
                        print(f"Procesando pregunta {question_id}: {response_text[:50]}...")
                        
                        # Verificar si la pregunta está asignada al usuario
                        if question_id not in question_ids:
                            print(f"Advertencia: La pregunta {question_id} no está asignada al usuario {current_user.id}")
                            continue
                        
                        # Convertir start_time si está presente
                        start_time = None
                        if start_time_str:
                            try:
                                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                            except:
                                start_time = None
                        
                        # Insertar la respuesta con los nuevos campos de tiempo
                        cursor.execute(
                            """
                            INSERT INTO response (question_id, response, date, user_id, start_time, response_time)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (question_id, response_text, date_with_time, current_user.id, start_time, response_time)
                        )
                    except ValueError as ve:
                        conn.rollback()
                        return jsonify({
                            'status': 'error',
                            'message': f'ID de pregunta inválido: {question_id}'
                        }), 400
                        
                    except Exception as e:
                        conn.rollback()
                        return jsonify({
                            'status': 'error',
                            'message': f'Error al guardar la respuesta: {str(e)}',
                            'question_id': question_id
                        }), 500
                
                # Si todo salió bien, hacemos commit
                conn.commit()
                return jsonify({
                    'status': 'success',
                    'message': 'Respuestas guardadas correctamente'
                })
                
    except ValueError as ve:
        return jsonify({
            'status': 'error',
            'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
        }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': f'Error en el servidor: {str(e)}'
        }), 500

def get_stats_by_frequency(user_id, frecuencia):
    """Obtiene estadísticas específicas para una frecuencia de preguntas"""
    try:
        hoy = datetime.now()
        today = hoy.strftime('%Y-%m-%d')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total preguntas activas de esta frecuencia
            cursor.execute(
                'SELECT COUNT(*) FROM question WHERE assigned_user_id = ? AND active = 1 AND frecuencia = ?', 
                (user_id, frecuencia)
            )
            total_preguntas = cursor.fetchone()[0] or 0
            
            # Respuestas de hoy para esta frecuencia
            cursor.execute('''
                SELECT COUNT(DISTINCT r.question_id) FROM response r
                JOIN question q ON r.question_id = q.id
                WHERE q.assigned_user_id = ? AND q.active = 1 AND q.frecuencia = ?
                AND CONVERT(DATE, r.date) = ?
                AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
            ''', (user_id, frecuencia, today))
            respondidas_hoy = cursor.fetchone()[0] or 0
            
            # Calcular completitud
            completitud = int((respondidas_hoy / total_preguntas) * 100) if total_preguntas > 0 else 0
            pendientes = total_preguntas - respondidas_hoy
            
            return {
                'total_preguntas': total_preguntas,
                'respondidas_hoy': respondidas_hoy,
                'pendientes_hoy': pendientes,
                'completitud': completitud
            }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas para frecuencia {frecuencia}: {str(e)}")
        return {
            'total_preguntas': 0,
            'respondidas_hoy': 0,
            'pendientes_hoy': 0,
            'completitud': 0
        }

@app.route('/stats')
@login_required
def stats():
    try:
        print('Fecha actual del backend:', datetime.now())
        hoy = datetime.now()
        inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        fin_semana = inicio_semana + timedelta(days=6, hours=23, minutes=59, seconds=59)
        inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if hoy.month == 12:
            fin_mes = hoy.replace(year=hoy.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
        else:
            fin_mes = hoy.replace(month=hoy.month+1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
        today = datetime.now().strftime('%Y-%m-%d')
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Total preguntas activas asignadas actualmente
                cursor.execute('SELECT COUNT(*) FROM question WHERE assigned_user_id = ? AND active = 1', (current_user.id,))
                total_asignadas = cursor.fetchone()[0] or 0

                # Respondidas semana (solo preguntas activas)
                cursor.execute('''
                    SELECT COUNT(*) FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    AND r.date >= ? AND r.date <= ?
                    AND q.active = 1
                    AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
                ''', (current_user.id, inicio_semana, fin_semana))
                respondidas_semana = cursor.fetchone()[0] or 0
                eficiencia_semanal = int((respondidas_semana / (total_asignadas * 7)) * 100) if total_asignadas > 0 else 0

                # Respondidas mes (solo preguntas activas)
                cursor.execute('''
                    SELECT COUNT(*) FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    AND r.date >= ? AND r.date <= ?
                    AND q.active = 1
                    AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
                ''', (current_user.id, inicio_mes, fin_mes))
                respondidas_mes = cursor.fetchone()[0] or 0
                eficiencia_mensual = int((respondidas_mes / (total_asignadas * (fin_mes.date() - inicio_mes.date()).days + 1)) * 100) if total_asignadas > 0 else 0

                # Respuestas de hoy (solo las que no están vacías y de preguntas activas)
                cursor.execute('''
                    SELECT COUNT(DISTINCT r.question_id) FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ? AND q.active = 1
                    AND CONVERT(DATE, r.date) = ?
                    AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
                ''', (current_user.id, today))
                respondidas_hoy = cursor.fetchone()[0] or 0

                # Última respuesta
                cursor.execute('''
                    SELECT TOP 1 r.date FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    ORDER BY r.date DESC
                ''', (current_user.id,))
                row = cursor.fetchone()
                if row and row[0]:
                    ultima_fecha = row[0]
                    if hasattr(ultima_fecha, 'strftime'):
                        # Si es date, convertir a datetime
                        if type(ultima_fecha).__name__ == 'date':
                            ultima_fecha = datetime.combine(ultima_fecha, datetime.min.time())
                        meses_es = {
                            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
                            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
                            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
                        }
                        dia = ultima_fecha.day
                        mes = meses_es[ultima_fecha.month]
                        año = ultima_fecha.year
                        hora = ultima_fecha.strftime('%H:%M')
                        ultima_fecha_str = f"{dia} de {mes} de {año}, {hora}"
                        # Calcular tiempo relativo real
                        ahora = datetime.now()
                        diff = ahora - ultima_fecha
                        if diff.days > 0:
                            relativo = f"hace {diff.days} día{'s' if diff.days > 1 else ''}"
                        elif diff.seconds >= 3600:
                            horas = diff.seconds // 3600
                            relativo = f"hace {horas} hora{'s' if horas > 1 else ''}"
                        elif diff.seconds >= 60:
                            minutos = diff.seconds // 60
                            relativo = f"hace {minutos} minuto{'s' if minutos > 1 else ''}"
                        else:
                            relativo = "hace unos segundos"
                    else:
                        ultima_fecha_str = str(ultima_fecha)
                        relativo = ''
                else:
                    ultima_fecha_str = '-'
                    relativo = ''

                # Preguntas pendientes hoy
                pendientes_hoy = total_asignadas - respondidas_hoy
                completitud_diaria = int((respondidas_hoy / total_asignadas) * 100) if total_asignadas > 0 else 0

                resumen_diario = {
                    'respondidas_hoy': respondidas_hoy,
                    'pendientes_hoy': pendientes_hoy,
                    'completitud_diaria': completitud_diaria,
                    'ultima_respuesta': {
                        'fecha': ultima_fecha_str,
                        'relativo': relativo
                    }
                }

                # Días consecutivos y días activos
                cursor.execute('''
                    SELECT CONVERT(DATE, r.date) as dia
                    FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    GROUP BY CONVERT(DATE, r.date)
                    ORDER BY dia DESC
                ''', (current_user.id,))
                dias = [row[0] for row in cursor.fetchall()]
                total_dias_activos = len(dias)
                dias_consecutivos = 0
                if dias:
                    hoy = datetime.now().date()
                    for i, d in enumerate(dias):
                        if (hoy - d).days == i:
                            dias_consecutivos += 1
                        else:
                            break

                resumen_general = {
                    'total_asignadas': total_asignadas,
                    'dias_consecutivos': dias_consecutivos,
                    'total_dias_activos': total_dias_activos
                }

                # Indicadores de rendimiento
                eficiencia = completitud_diaria
                promedio_diario = respondidas_hoy  # Puedes calcular un promedio real si lo deseas
                indicadores = {
                    'eficiencia': eficiencia,
                    'promedio_diario': promedio_diario
                }

                # === Productividad por Día (Lunes a Domingo) ===
                dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                productividad_dias = []
                mejor_dia = {'nombre': '', 'porcentaje': 0}
                for i, nombre_dia in enumerate(dias_semana):
                    dia_fecha = (inicio_semana + timedelta(days=i)).date()
                    # Preguntas asignadas activas ese día
                    cursor.execute('''
                        SELECT COUNT(*) FROM question
                        WHERE assigned_user_id = ? AND active = 1
                    ''', (current_user.id,))
                    asignadas = cursor.fetchone()[0] or 0
                    # Respuestas dadas ese día (no vacías y solo de preguntas activas)
                    cursor.execute('''
                        SELECT COUNT(DISTINCT r.question_id) FROM response r
                        JOIN question q ON r.question_id = q.id
                        WHERE q.assigned_user_id = ?
                        AND q.active = 1
                        AND CONVERT(DATE, r.date) = ?
                        AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
                    ''', (current_user.id, dia_fecha))
                    respuestas = cursor.fetchone()[0] or 0
                    porcentaje = int((respuestas / asignadas) * 100) if asignadas > 0 else 0
                    productividad_dias.append({
                        'nombre': nombre_dia,
                        'respuestas': respuestas,
                        'asignadas': asignadas,
                        'porcentaje': porcentaje
                    })
                    if porcentaje > mejor_dia['porcentaje']:
                        mejor_dia = {'nombre': nombre_dia, 'porcentaje': porcentaje}

                # === Racha de Días Consecutivos ===
                cursor.execute('''
                    SELECT CONVERT(DATE, r.date) as dia
                    FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    GROUP BY CONVERT(DATE, r.date)
                    ORDER BY dia ASC
                ''', (current_user.id,))
                dias_respondidos = [row[0] for row in cursor.fetchall()]
                dias_respondidos_set = set(dias_respondidos)
                total_dias = len(dias_respondidos_set)
                # Mejor racha histórica
                mejor_racha = 0
                racha_actual = 0
                racha_temp = 0
                prev = None
                for d in dias_respondidos:
                    if prev is not None and (d - prev).days == 1:
                        racha_temp += 1
                    else:
                        racha_temp = 1
                    if racha_temp > mejor_racha:
                        mejor_racha = racha_temp
                    prev = d
                # Racha actual (solo si hoy respondió)
                hoy = datetime.now().date()
                if hoy in dias_respondidos_set:
                    racha_actual = 1
                    prev = hoy
                    while True:
                        prev = prev - timedelta(days=1)
                        if prev in dias_respondidos_set:
                            racha_actual += 1
                        else:
                            break
                else:
                    racha_actual = 0
                # Visualización últimos 7 días corridos
                ultimos7 = []
                dias_letras = ['L','M','MI','J','V','S','D']
                for i in range(6, -1, -1):
                    dia = hoy - timedelta(days=i)
                    ultimos7.append(1 if dia in dias_respondidos_set else 0)
                racha_zip = list(zip(ultimos7, [dias_letras[(hoy - timedelta(days=i)).weekday()] for i in range(6, -1, -1)]))

                # === Tiempo de Respuesta ===
                # Calcular tiempo promedio de respuesta
                cursor.execute('''
                    SELECT AVG(CAST(r.response_time AS FLOAT)) as tiempo_promedio
                    FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    AND r.response_time IS NOT NULL
                    AND r.response_time > 0
                ''', (current_user.id,))
                tiempo_promedio_row = cursor.fetchone()
                tiempo_respuesta_promedio = round(tiempo_promedio_row[0] / 60, 1) if tiempo_promedio_row[0] else 0.0

                # Calcular tiempo más rápido y más lento
                cursor.execute('''
                    SELECT 
                        MIN(CAST(r.response_time AS FLOAT)) as tiempo_minimo,
                        MAX(CAST(r.response_time AS FLOAT)) as tiempo_maximo,
                        COUNT(r.response_time) as total_con_tiempo
                    FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    AND r.response_time IS NOT NULL
                    AND r.response_time > 0
                ''', (current_user.id,))
                tiempo_stats = cursor.fetchone()
                
                tiempo_respuesta_rapido = round(tiempo_stats[0] / 60, 1) if tiempo_stats[0] else 0.0
                tiempo_respuesta_lento = round(tiempo_stats[1] / 60, 1) if tiempo_stats[1] else 0.0
                total_respuestas_tiempo = tiempo_stats[2] if tiempo_stats[2] else 0

                # Obtener preguntas que requieren más reflexión (top 3 con mayor tiempo)
                cursor.execute('''
                    SELECT TOP 3 
                        q.text,
                        AVG(CAST(r.response_time AS FLOAT)) as tiempo_promedio
                    FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                    AND r.response_time IS NOT NULL
                    AND r.response_time > 0
                    GROUP BY q.id, q.text
                    ORDER BY tiempo_promedio DESC
                ''', (current_user.id,))
                
                preguntas_reflexion = []
                for row in cursor.fetchall():
                    tiempo_minutos = round(row[1] / 60, 1) if row[1] else 0.0
                    preguntas_reflexion.append({
                        'texto': row[0][:50] + '...' if len(row[0]) > 50 else row[0],
                        'tiempo': tiempo_minutos
                    })

                # Si no hay datos de tiempo, usar valores por defecto
                if not preguntas_reflexion:
                    preguntas_reflexion = [
                        {'texto': 'No hay datos suficientes', 'tiempo': 0.0},
                    ]

                # === Cumplimientos por pregunta (semana y mes) ===
                # Obtener todas las preguntas activas asignadas al usuario
                cursor.execute('''
                    SELECT id, text, categoria
                    FROM question
                    WHERE assigned_user_id = ? AND active = 1
                ''', (current_user.id,))
                preguntas = cursor.fetchall()

                # Fechas del periodo
                dias_semana = [(inicio_semana + timedelta(days=i)).date() for i in range(7)]
                dias_mes = [(inicio_mes + timedelta(days=i)).date() for i in range((fin_mes.date() - inicio_mes.date()).days + 1)]

                habitos_semanal = []
                habitos_mensual = []

                for pregunta in preguntas:
                    pregunta_id, texto, categoria = pregunta
                    # --- SEMANAL ---
                    cumplidos = 0
                    omitidos = 0
                    frecuencia_semanal = []
                    for dia in dias_semana:
                        cursor.execute('''
                            SELECT r.response FROM response r
                            WHERE r.question_id = ? AND CONVERT(DATE, r.date) = ?
                            AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
                        ''', (pregunta_id, dia))
                        if cursor.fetchone():
                            cumplidos += 1
                            frecuencia_semanal.append(True)
                        else:
                            omitidos += 1
                            frecuencia_semanal.append(False)
                    porcentaje = int((cumplidos / len(dias_semana)) * 100) if len(dias_semana) > 0 else 0
                    habitos_semanal.append({
                        'pregunta': texto,
                        'categoria': categoria or 'General',
                        'icono': '✅',  # Puedes personalizar esto luego
                        'cumplimiento': porcentaje,
                        'cumplidos': cumplidos,
                        'omitidos': omitidos,
                        'color': 'success' if porcentaje >= 80 else 'warning' if porcentaje >= 60 else 'danger',
                        'frecuencia_semanal': frecuencia_semanal,
                    })
                    # --- MENSUAL ---
                    cumplidos_m = 0
                    omitidos_m = 0
                    for dia in dias_mes:
                        cursor.execute('''
                            SELECT r.response FROM response r
                            WHERE r.question_id = ? AND CONVERT(DATE, r.date) = ?
                            AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
                        ''', (pregunta_id, dia))
                        if cursor.fetchone():
                            cumplidos_m += 1
                        else:
                            omitidos_m += 1
                    porcentaje_m = int((cumplidos_m / len(dias_mes)) * 100) if len(dias_mes) > 0 else 0
                    habitos_mensual.append({
                        'pregunta': texto,
                        'categoria': categoria or 'General',
                        'icono': '✅',
                        'cumplimiento': porcentaje_m,
                        'cumplidos': cumplidos_m,
                        'omitidos': omitidos_m,
                        'color': 'success' if porcentaje_m >= 80 else 'warning' if porcentaje_m >= 60 else 'danger',
                    })

                # Obtener preguntas para el selector de Frecuencia de Respuesta
                cursor.execute('''
                    SELECT id, text, type
                    FROM question
                    WHERE assigned_user_id = ? AND active = 1
                ''', (current_user.id,))
                preguntas = [
                    {'id': row[0], 'texto': row[1], 'tipo': row[2]}
                    for row in cursor.fetchall()
                ]

                # Obtener estadísticas por frecuencia
                stats_diarias = get_stats_by_frequency(current_user.id, 'diaria')
                stats_semanales = get_stats_by_frequency(current_user.id, 'semanal')
                stats_mensuales = get_stats_by_frequency(current_user.id, 'mensual')

                return render_template(
                    'stats.html',
                    resumen_diario=resumen_diario,
                    resumen_general=resumen_general,
                    indicadores=indicadores,
                    eficiencia_semanal=eficiencia_semanal,
                    eficiencia_mensual=eficiencia_mensual,
                    comparacion_porcentaje=7,
                    eficiencia_actual=89,
                    eficiencia_anterior=82,
                    productividad_dias=productividad_dias,
                    mejor_dia=mejor_dia,
                    tiempo_respuesta_promedio=tiempo_respuesta_promedio,
                    tiempo_respuesta_rapido=tiempo_respuesta_rapido,
                    tiempo_respuesta_lento=tiempo_respuesta_lento,
                    total_respuestas_tiempo=total_respuestas_tiempo,
                    preguntas_reflexion=preguntas_reflexion,
                    racha_actual=racha_actual,
                    mejor_racha=mejor_racha,
                    total_dias=total_dias,
                    racha_ultimos7=ultimos7,
                    racha_zip=racha_zip,
                    habitos_semanal=habitos_semanal,
                    habitos_mensual=habitos_mensual,
                    preguntas=preguntas,
                    stats_diarias=stats_diarias,
                    stats_semanales=stats_semanales,
                    stats_mensuales=stats_mensuales
                )
    except Exception as e:
        logger.error(f"Error al cargar las estadísticas: {str(e)}")
        flash('Error al cargar las estadísticas', 'error')
        return redirect(url_for('index'))

@app.route('/api/stats/weekly_responses')
@login_required
def get_weekly_responses():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener los últimos 7 días
        today = datetime.now()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        
        # Formatear fechas para la consulta SQL
        start_date = days[0].strftime('%Y-%m-%d')
        end_date = days[-1].strftime('%Y-%m-%d')
        
        # Obtener todas las respuestas de la semana
        cursor.execute('''
            SELECT q.id, q.text, q.type, r.response, r.date
            FROM question q
            LEFT JOIN response r ON q.id = r.question_id 
                AND CONVERT(date, r.date) BETWEEN ? AND ?
            WHERE q.assigned_user_id = ?
            ORDER BY q.id, r.date
        ''', (start_date, end_date, current_user.id))
        
        responses = []
        for row in cursor.fetchall():
            try:
                # Manejo seguro de la fecha
                date_value = row[4] if len(row) > 4 else None
                if date_value:
                    if hasattr(date_value, 'strftime'):
                        date_str = date_value.strftime('%Y-%m-%d')
                    else:
                        try:
                            date_obj = datetime.strptime(str(date_value), '%Y-%m-%d')
                            date_str = date_obj.strftime('%Y-%m-%d')
                        except (ValueError, TypeError):
                            date_str = str(date_value)
                else:
                    date_str = None
                
                responses.append({
                    'question_id': row[0],
                    'text': row[1],
                    'type': row[2],
                    'response': row[3],
                    'date': date_str
                })
                
            except Exception as e:
                continue
        
        return jsonify(responses)
        
    except Exception as e:
        return jsonify({'error': 'Error al obtener las respuestas semanales'}), 500
        
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@app.route('/api/stats')
@login_required
def get_stats():
    try:
        # Obtener la fecha actual en formato YYYY-MM-DD
        today = datetime.now().strftime('%Y-%m-%d')
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Obtener las respuestas del día actual para el usuario
                cursor.execute('''
                    SELECT q.text as pregunta, r.response as respuesta, r.date
                    FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE CONVERT(DATE, r.date) = ?
                    AND q.assigned_user_id = ?
                    ORDER BY q.id
                ''', (today, current_user.id))
                
                respuestas = []
                for row in cursor.fetchall():
                    # Verificar si la fecha es un objeto datetime antes de formatear
                    date_value = row.date
                    date_str = date_value.strftime('%Y-%m-%d') if hasattr(date_value, 'strftime') else date_value
                    
                    respuestas.append({
                        'pregunta': row.pregunta,
                        'respuesta': row.respuesta,
                        'fecha': date_str
                    })
                
                # Obtener estadísticas generales
                cursor.execute('''
                    SELECT 
                        COUNT(DISTINCT CONVERT(DATE, r.date)) as dias_respondidos,
                        COUNT(r.id) as total_respuestas
                    FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ?
                ''', (current_user.id,))
                
                stats = cursor.fetchone()
                
                return jsonify({
                    'status': 'success',
                    'fecha': today,
                    'respuestas': respuestas,
                    'estadisticas': {
                        'dias_respondidos': stats.dias_respondidos if stats else 0,
                        'total_respuestas': stats.total_respuestas if stats else 0
                    }
                })
                
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener estadísticas'
        }), 500

@app.route('/question/<int:question_id>', methods=['PUT', 'POST'])
@login_required
def update_question(question_id):
    data = request.get_json() if request.is_json else request.form
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Verificar que la pregunta exista y pertenezca al usuario actual o sea global
            cursor.execute('SELECT assigned_user_id FROM question WHERE id = ?', (question_id,))
            question = cursor.fetchone()
            if not question or (question[0] not in (None, 0, current_user.id)):
                return jsonify({'status': 'error', 'message': 'No autorizado'}), 403
            
            # Procesar opciones si es necesario
            options = None
            if data.get('type') in ['checkbox', 'radio'] and 'options' in data:
                # Procesar las opciones del formulario
                options_text = data['options'].strip()
                if options_text:
                    # Dividir por líneas, limpiar y eliminar guiones iniciales
                    options_list = []
                    for opt in options_text.split('\n'):
                        opt = opt.strip()
                        if opt.startswith('-'):
                            opt = opt[1:].strip()
                        if opt:  # Solo agregar si no está vacío
                            options_list.append(opt)
                    
                    # Unir las opciones con comas para almacenar en la base de datos
                    options = ','.join(options_list)
            
            # Procesar categoría para edición
            categoria = data.get('categoria_existente', '').strip() if 'categoria_existente' in data else data.get('categoria', '').strip()
            nueva_categoria = data.get('nueva_categoria', '').strip() if 'nueva_categoria' in data else ''
            if nueva_categoria:
                categoria = nueva_categoria
            elif not categoria:
                categoria = 'Sin Categoría'
            
            # Actualizar campos (sin modificar 'active')
            cursor.execute(
                'UPDATE question SET text = ?, descripcion = ?, type = ?, categoria = ?, frecuencia = ?, is_required = ?' + 
                (', options = ?' if options is not None else '') + ' WHERE id = ?',
                (
                    data.get('text', ''),
                    data.get('descripcion', ''),
                    data.get('type', 'text'),
                    categoria,
                    data.get('frecuencia', 'diaria'),
                    1 if data.get('is_required') in ['on', '1', 1, True, 'true'] else 0,
                    *([options] if options is not None else []),  # Agregar options solo si existe
                    question_id
                )
            )
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error al actualizar pregunta: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/question/<int:question_id>/toggle', methods=['POST'])
@login_required
def toggle_question_status(question_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la pregunta pertenezca al usuario actual
            cursor.execute('SELECT active FROM question WHERE id = ? AND assigned_user_id = ?', 
                         (question_id, current_user.id))
            question = cursor.fetchone()
            
            if not question:
                return jsonify({'status': 'error', 'message': 'Pregunta no encontrada o no autorizada'}), 404
            
            # Alternar el estado
            new_status = 0 if question[0] else 1
            cursor.execute('UPDATE question SET active = ? WHERE id = ? AND assigned_user_id = ?',
                         (new_status, question_id, current_user.id))
            
            return jsonify({'status': 'success', 'active': bool(new_status)})
            
    except Exception as e:
        print(f"Error al alternar estado de la pregunta: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/question/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Verificar que la pregunta exista y pertenezca al usuario actual o sea global
            cursor.execute('SELECT assigned_user_id FROM question WHERE id = ?', (question_id,))
            question = cursor.fetchone()
            if not question or (question[0] not in (None, 0, current_user.id)):
                response = jsonify({'status': 'error', 'message': 'No autorizado'})
                response.status_code = 403
                return response
            # Eliminar primero las respuestas asociadas
            cursor.execute('DELETE FROM response WHERE question_id = ?', (question_id,))
            # Luego eliminar la pregunta
            cursor.execute('DELETE FROM question WHERE id = ?', (question_id,))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error al eliminar pregunta: {str(e)}")
        response = jsonify({'status': 'error', 'message': str(e)})
        response.status_code = 500
        return response

@app.route('/api/question/<int:question_id>/start', methods=['POST'])
@login_required
def start_question_timer(question_id):
    """Registra el tiempo de inicio para una pregunta específica"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Verificar que la pregunta esté asignada al usuario
                cursor.execute(
                    'SELECT id FROM question WHERE id = ? AND assigned_user_id = ?',
                    (question_id, current_user.id)
                )
                if not cursor.fetchone():
                    return jsonify({
                        'status': 'error',
                        'message': 'Pregunta no encontrada o no asignada al usuario'
                    }), 404
                
                # Registrar el tiempo de inicio
                start_time = datetime.now()
                
                return jsonify({
                    'status': 'success',
                    'start_time': start_time.isoformat(),
                    'question_id': question_id
                })
                
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error al registrar tiempo de inicio: {str(e)}'
        }), 500

@app.route('/stats/intermedias')
@login_required
def stats_intermedias():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT id, text, type
                FROM question
                WHERE assigned_user_id = ? AND active = 1
            ''', (current_user.id,))
            preguntas = [
                {'id': row[0], 'texto': row[1], 'tipo': row[2]}
                for row in cursor.fetchall()
            ]
    habitos = []  # Puedes poner aquí la lógica real si la necesitas
    return render_template('intermedias.html', preguntas=preguntas, habitos=habitos)

@app.route('/api/stats/frequency/<int:question_id>')
@login_required
def get_question_frequency(question_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, text, type, options
                FROM question
                WHERE id = ? AND assigned_user_id = ?
            ''', (question_id, current_user.id))
            question = cursor.fetchone()
            if not question:
                return jsonify({'error': 'Pregunta no encontrada'}), 404
            question_id, question_text, question_type, options = question
            
            if question_type in ['texto', 'text', 'open']:
                return jsonify({
                    'error': 'Las preguntas de texto abierto no pueden analizarse cuantitativamente',
                    'excluded': True
                }), 400
            periodo = request.args.get('periodo', '7dias')
            hoy = datetime.now()
            
            if periodo == '7dias':
                inicio = hoy - timedelta(days=7)
                fin = hoy
            elif periodo == 'mes':
                # Obtener mes y año específicos de los parámetros
                mes = int(request.args.get('mes', hoy.month - 1))  # JavaScript envía 0-11
                anio = int(request.args.get('anio', hoy.year))
                
                # Convertir mes de JavaScript (0-11) a Python (1-12)
                mes_python = mes + 1
                
                # Primer y último día del mes
                inicio = datetime(anio, mes_python, 1)
                if mes_python == 12:
                    fin = datetime(anio + 1, 1, 1) - timedelta(seconds=1)
                else:
                    fin = datetime(anio, mes_python + 1, 1) - timedelta(seconds=1)
            elif periodo == 'custom':
                # Período personalizado con fechas específicas
                fecha_desde_str = request.args.get('fecha_desde')
                fecha_hasta_str = request.args.get('fecha_hasta')
                
                if not fecha_desde_str or not fecha_hasta_str:
                    return jsonify({'error': 'Se requieren fecha_desde y fecha_hasta para período personalizado'}), 400
                
                try:
                    # Parsear las fechas (formato YYYY-MM-DD)
                    inicio = datetime.strptime(fecha_desde_str, '%Y-%m-%d')
                    fin = datetime.strptime(fecha_hasta_str, '%Y-%m-%d')
                    # Agregar 23:59:59 a la fecha final para incluir todo el día
                    fin = fin.replace(hour=23, minute=59, second=59)
                    
                    # Validar que la fecha desde sea anterior a la fecha hasta
                    if inicio > fin:
                        return jsonify({'error': 'La fecha desde debe ser anterior a la fecha hasta'}), 400
                        
                except ValueError:
                    return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
            else:
                # Fallback para compatibilidad
                inicio = hoy - timedelta(days=7)
                fin = hoy
            cursor.execute('''
                SELECT r.response, r.date
                FROM response r
                WHERE r.question_id = ?
                AND r.date >= ?
                AND r.date <= ?
                AND (r.response IS NOT NULL AND LTRIM(RTRIM(r.response)) <> '')
                ORDER BY r.date
            ''', (question_id, inicio, fin))
            responses = cursor.fetchall()
            print(f"[DEBUG] Opciones de la pregunta: {options}")
            print(f"[DEBUG] Tipo de pregunta: {question_type}")
            print(f"[DEBUG] Respuestas encontradas: {responses}")

            def es_select_si_no(tipo, opciones, respuestas):
                si_variantes = ['sí', 'si', 'yes', 'true', '1', 'verdadero']
                no_variantes = ['no', 'false', '0', 'falso']
                if tipo not in ['select', 'radio']:
                    return False
                if opciones:
                    opts = [o.strip().lower() for o in opciones.split(',') if o.strip()]
                    if len(opts) != 2:
                        return False
                    return (
                        (opts[0] in si_variantes and opts[1] in no_variantes) or
                        (opts[1] in si_variantes and opts[0] in no_variantes)
                    )
                # Si no hay opciones, revisar las respuestas
                if respuestas:
                    valores = set([r[0].strip().lower() for r in respuestas if r[0]])
                    solo_si_no = all(v in si_variantes + no_variantes for v in valores)
                    return solo_si_no and len(valores) > 0
                return False

            if question_type in ['yes_no', 'boolean'] or es_select_si_no(question_type, options, responses):
                print("[DEBUG] Entrando a if de SÍ/NO")
                # Contar totales de Sí y No en el periodo
                si_count = 0
                no_count = 0
                for response, date in responses:
                    response_lower = response.lower().strip()
                    if response_lower in ['sí', 'si', 'yes', 'true', '1', 'verdadero']:
                        si_count += 1
                    elif response_lower in ['no', 'false', '0', 'falso']:
                        no_count += 1
                print(f"[DEBUG] Total Sí: {si_count}, Total No: {no_count}")
                return jsonify({
                    'tipo': 'barras',
                    'labels': ['Sí', 'No'],
                    'datasets': [
                        {
                            'label': 'Respuestas',
                            'data': [si_count, no_count],
                            'backgroundColor': ['#10b981', '#ef4444'],
                            'borderColor': ['#059669', '#dc2626'],
                            'borderWidth': 1
                        }
                    ],
                    'question_text': question_text,
                    'question_type': question_type
                })
            elif question_type in ['radio', 'checkbox']:
                print("[DEBUG] Entrando a if de opciones múltiples")
                if options:
                    opciones_disponibles = [opt.strip() for opt in options.split(',') if opt.strip()]
                else:
                    opciones_disponibles = []
                frecuencia_opciones = {}
                for opt in opciones_disponibles:
                    frecuencia_opciones[opt] = 0
                for response, date in responses:
                    if question_type == 'radio':
                        if response in frecuencia_opciones:
                            frecuencia_opciones[response] += 1
                    else:
                        respuestas_seleccionadas = [r.strip() for r in response.split(',') if r.strip()]
                        for resp in respuestas_seleccionadas:
                            if resp in frecuencia_opciones:
                                frecuencia_opciones[resp] += 1
                labels = list(frecuencia_opciones.keys())
                data = list(frecuencia_opciones.values())
                return jsonify({
                    'tipo': 'barras',
                    'labels': labels,
                    'datasets': [{
                        'label': 'Frecuencia de selección',
                        'data': data,
                        'backgroundColor': [
                            '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
                            '#8b5cf6', '#06b6d4', '#f97316', '#84cc16'
                        ][:len(data)],
                        'borderColor': [
                            '#2563eb', '#dc2626', '#059669', '#d97706',
                            '#7c3aed', '#0891b2', '#ea580c', '#65a30d'
                        ][:len(data)],
                        'borderWidth': 1
                    }],
                    'question_text': question_text,
                    'question_type': question_type
                })
            # Detectar si es pregunta de sí/no aunque el tipo sea select o radio
            es_si_no = False
            opciones_si_no = ['sí', 'si', 'no']
            if question_type in ['yes_no', 'boolean']:
                es_si_no = True
            elif question_type in ['select', 'radio'] and options:
                opts = [o.strip().lower() for o in options.split(',') if o.strip()]
                if sorted(opts) == sorted(['sí', 'no']) or sorted(opts) == sorted(['si', 'no']):
                    es_si_no = True
            if es_si_no:
                # Agrupar por periodo
                period_labels = []
                si_counts = []
                no_counts = []
                grouped = defaultdict(lambda: {'Sí': 0, 'No': 0})
                for response, date in responses:
                    if not date:
                        continue
                    if periodo == '7dias':
                        # Para últimos 7 días, agrupar por día
                        label = date.strftime('%d/%m')
                    elif periodo == 'mes':
                        # Para mes específico, agrupar por día del mes
                        label = f"Día {date.day}"
                    else:
                        # Fallback
                        label = date.strftime('%d/%m')
                    response_lower = response.lower().strip()
                    if response_lower in ['sí', 'si', 'yes', 'true', '1', 'verdadero']:
                        grouped[label]['Sí'] += 1
                    elif response_lower in ['no', 'false', '0', 'falso']:
                        grouped[label]['No'] += 1
                sorted_labels = sorted(grouped.keys(), key=lambda x: x)
                for label in sorted_labels:
                    period_labels.append(label)
                    si_counts.append(grouped[label]['Sí'])
                    no_counts.append(grouped[label]['No'])
                return jsonify({
                    'tipo': 'barras',
                    'labels': period_labels,
                    'datasets': [
                        {
                            'label': 'Sí',
                            'data': si_counts,
                            'backgroundColor': '#10b981',
                            'borderColor': '#059669',
                            'borderWidth': 1
                        },
                        {
                            'label': 'No',
                            'data': no_counts,
                            'backgroundColor': '#ef4444',
                            'borderColor': '#dc2626',
                            'borderWidth': 1
                        }
                    ],
                    'question_text': question_text,
                    'question_type': question_type
                })
            # Si no es ninguno de los tipos contemplados, retorna vacío
            return jsonify({
                'tipo': 'barras',
                'labels': [],
                'datasets': [],
                'question_text': question_text,
                'question_type': question_type,
                'message': 'Tipo de pregunta no soportado para análisis de frecuencia.'
            })
    except Exception as e:
        logger.error(f"Error al obtener frecuencia de pregunta: {str(e)}")
        return jsonify({'error': 'Error al obtener datos de frecuencia'}), 500

@app.route('/api/stats/calendario/<int:question_id>')
@login_required
def get_question_calendar(question_id):
    """
    Obtiene los datos del calendario de cumplimiento para una pregunta específica
    """
    try:
        mes = int(request.args.get('mes', datetime.now().month - 1))  # JavaScript usa 0-11
        anio = int(request.args.get('anio', datetime.now().year))
        
        logger.info(f"Solicitud calendario - Pregunta: {question_id}, Mes: {mes}, Año: {anio}")
        
        # Convertir mes de JavaScript (0-11) a Python (1-12)
        mes_python = mes + 1
        logger.info(f"Mes convertido a Python: {mes_python}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la pregunta pertenece al usuario
            cursor.execute('''
                SELECT id, text FROM question 
                WHERE id = ? AND assigned_user_id = ?
            ''', (question_id, current_user.id))
            
            question = cursor.fetchone()
            if not question:
                return jsonify({'error': 'Pregunta no encontrada'}), 404
            
            # Consulta de prueba para ver si hay respuestas para esta pregunta
            cursor.execute('''
                SELECT COUNT(*) FROM response r
                WHERE r.question_id = ?
                AND r.response IS NOT NULL 
                AND LTRIM(RTRIM(r.response)) <> ''
            ''', (question_id,))
            total_respuestas = cursor.fetchone()[0]
            logger.info(f"Total respuestas para pregunta {question_id}: {total_respuestas}")
            
            # Obtener el primer y último día del mes
            primer_dia = datetime(anio, mes_python, 1).date()
            if mes_python == 12:
                ultimo_dia = datetime(anio + 1, 1, 1).date() - timedelta(days=1)
            else:
                ultimo_dia = datetime(anio, mes_python + 1, 1).date() - timedelta(days=1)
            
            # Primero, obtener algunas respuestas de muestra para debug
            cursor.execute('''
                SELECT TOP 5 r.date, r.response 
                FROM response r
                WHERE r.question_id = ?
                AND r.response IS NOT NULL 
                AND LTRIM(RTRIM(r.response)) <> ''
                ORDER BY r.date DESC
            ''', (question_id,))
            muestra_respuestas = cursor.fetchall()
            logger.info(f"Muestra de respuestas: {muestra_respuestas}")
            
            # Obtener todas las respuestas del mes
            logger.info(f"Buscando respuestas entre {primer_dia} y {ultimo_dia}")
            
            # Obtener respuestas del mes con el contenido de la respuesta
            # Usar una consulta más simple y robusta
            cursor.execute('''
                SELECT r.date, r.response
                FROM response r
                WHERE r.question_id = ? 
                AND r.response IS NOT NULL 
                AND LTRIM(RTRIM(r.response)) <> ''
                ORDER BY r.date DESC
            ''', (question_id,))
            
            todas_respuestas = cursor.fetchall()
            logger.info(f"Total respuestas encontradas: {len(todas_respuestas)}")
            
            # Filtrar por mes en Python para evitar problemas de SQL
            respuestas_mes = []
            for fecha, respuesta in todas_respuestas:
                if isinstance(fecha, str):
                    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S').date()
                else:
                    fecha_obj = fecha.date() if hasattr(fecha, 'date') else fecha
                
                if fecha_obj.year == anio and fecha_obj.month == mes_python:
                    respuestas_mes.append((fecha_obj, respuesta))
            
            logger.info(f"Respuestas del mes {mes_python}/{anio}: {len(respuestas_mes)}")
            respuestas_por_dia = respuestas_mes
            
            # Crear diccionario de días con respuestas
            dias_con_respuestas = {}
            for fecha_obj, respuesta in respuestas_por_dia:
                fecha_str = fecha_obj.strftime('%Y-%m-%d')
                
                # Si ya existe el día, agregar la respuesta (en caso de múltiples respuestas)
                if fecha_str in dias_con_respuestas:
                    # Si hay múltiples respuestas el mismo día, tomar la más reciente
                    dias_con_respuestas[fecha_str]['respuestas'].append(respuesta)
                    dias_con_respuestas[fecha_str]['count'] += 1
                else:
                    dias_con_respuestas[fecha_str] = {
                        'respondida': True,
                        'count': 1,
                        'respuestas': [respuesta]
                    }
                logger.info(f"Día con respuesta: {fecha_str} - Respuesta: {respuesta}")
            
            # Generar todos los días del mes y marcar su estado
            dias_mes = {}
            dia_actual = primer_dia
            respondidas = 0
            no_respondidas = 0
            
            while dia_actual <= ultimo_dia:
                fecha_str = dia_actual.strftime('%Y-%m-%d')
                if fecha_str in dias_con_respuestas:
                    dias_mes[fecha_str] = {
                        'respondida': True,
                        'count': dias_con_respuestas[fecha_str]['count'],
                        'respuestas': dias_con_respuestas[fecha_str]['respuestas']
                    }
                    respondidas += 1
                else:
                    # Solo contar como "no respondida" si es un día pasado o hoy
                    if dia_actual <= datetime.now().date():
                        dias_mes[fecha_str] = {
                            'respondida': False,
                            'count': 0
                        }
                        no_respondidas += 1
                    else:
                        # Días futuros no se cuentan
                        dias_mes[fecha_str] = {
                            'respondida': None,  # Día futuro
                            'count': 0
                        }
                
                dia_actual += timedelta(days=1)
            
            # Calcular estadísticas
            estadisticas = {
                'respondidas': respondidas,
                'no_respondidas': no_respondidas,
                'total': respondidas + no_respondidas
            }
            
            logger.info(f"Estadísticas finales: {estadisticas}")
            logger.info(f"Total días en mes: {len(dias_mes)}")
            logger.info(f"Días con datos: {len([d for d in dias_mes.values() if d['respondida'] is not None])}")
            
            resultado = {
                'dias': dias_mes,
                'estadisticas': estadisticas,
                'pregunta': question[1],
                'mes': mes,
                'anio': anio
            }
            
            return jsonify(resultado)
            
    except Exception as e:
        logger.error(f"Error al obtener datos del calendario: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Error al obtener datos del calendario', 'details': str(e)}), 500

# Manejadores de error globales
@app.errorhandler(404)
def page_not_found(e):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'error', 'message': 'Recurso no encontrado'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f'500 Error: {str(e)}')
    # Si no existe la plantilla 500.html, devolver un mensaje simple
    try:
        return render_template('500.html'), 500
    except:
        return "<h1>Error 500 - Error interno del servidor</h1><p>Ha ocurrido un error inesperado.</p>", 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f'Excepción no manejada: {str(e)}', exc_info=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'error',
            'message': 'Ha ocurrido un error inesperado',
            'error': str(e)
        }), 500
    return render_template('500.html'), 500

@app.route('/objetivos')
@login_required
def objetivos():
    return render_template('objetivos.html')

@app.route('/objetivos-programados')
@login_required
def objetivos_programados():
    return render_template('objetivos_programados.html')

@app.route('/test-calendario')
@login_required
def test_calendario():
    """Página de prueba para el calendario de objetivos"""
    return render_template('test_calendario.html')

@app.route('/test-focus')
@login_required
def test_focus():
    """Página de prueba para el focus de subobjetivos"""
    return render_template('test_focus.html')

@app.route('/api/objetivos/manana', methods=['GET'])
@login_required
def api_objetivos_manana():
    """Obtener objetivos programados para mañana"""
    try:
        # Calcular la fecha de mañana
        from datetime import datetime, timedelta
        manana = datetime.now() + timedelta(days=1)
        fecha_manana = manana.strftime('%Y-%m-%d')
        
        print(f"📅 Buscando objetivos para mañana: {fecha_manana}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Primero, una consulta más simple para verificar que funciona
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
            ''', (current_user.id, fecha_manana))
            
            rows = cursor.fetchall()
            print(f"📊 Encontrados {len(rows)} objetivos para mañana")
            
            objetivos = []
            
            for row in rows:
                try:
                    objetivo = {
                        'id': row[0],
                        'titulo': row[1] or '',
                        'descripcion': row[2] or '',
                        'prioridad': row[3] or 'media',
                        'categoria': row[4] or '',
                        'horas_estimadas': row[5] or 0,
                        'parte_dia': row[6] or '',
                        'fecha_programada': row[7].strftime('%Y-%m-%d') if row[7] else None,
                        'programado_para': row[8] or '',
                        'recurrente': bool(row[9]) if len(row) > 9 else False,
                        'fecha_manana': fecha_manana
                    }
                    
                    # Cargar subobjetivos para este objetivo
                    cursor.execute('''
                        SELECT id, titulo, completado
                        FROM subobjetivos 
                        WHERE objetivo_id = ?
                        ORDER BY orden, id
                    ''', (row[0],))
                    
                    subobjetivos_rows = cursor.fetchall()
                    subobjetivos = []
                    for sub_row in subobjetivos_rows:
                        subobjetivos.append({
                            'id': sub_row[0],
                            'titulo': sub_row[1],
                            'completado': bool(sub_row[2])
                        })
                    
                    objetivo['subobjetivos'] = subobjetivos
                    objetivo['total_subobjetivos'] = len(subobjetivos)
                    objetivo['subobjetivos_completados'] = len([s for s in subobjetivos if s['completado']])
                    
                    objetivos.append(objetivo)
                    print(f"✅ Objetivo agregado: {objetivo['titulo']} con {len(subobjetivos)} subobjetivos")
                except Exception as row_error:
                    print(f"❌ Error procesando fila: {row_error}")
                    continue
            
            result = {
                'objetivos': objetivos,
                'fecha_manana': fecha_manana,
                'total': len(objetivos)
            }
            
            print(f"📤 Enviando respuesta: {len(objetivos)} objetivos")
            return jsonify(result)
            
    except Exception as e:
        print(f"💥 Error en api_objetivos_manana: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/api/export/respuestas-excel')
@login_required
def export_respuestas_excel():
    """
    Exporta todas las respuestas del usuario en un archivo Excel con 4 hojas:
    1. Preguntas Sí/No
    2. Preguntas de Texto Libre  
    3. Preguntas de Selección Múltiple
    4. Preguntas de Opción Única
    
    Columnas según imagen de referencia:
    - Pregunta
    - Fecha Inicio Mensual
    - Porcentaje Sí
    - Porcentaje No
    - Segunda Más Elegida
    - Longitud Promedio de Respuesta
    - Tiempo Promedio
    - Resumen Previo
    """
    try:
        import pandas as pd
        from io import BytesIO
        from datetime import datetime, timedelta
        
        # Obtener fechas del filtro
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        

        
        logger.info(f"Exportando respuestas a Excel para usuario {current_user.id} desde {fecha_desde} hasta {fecha_hasta}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener todas las preguntas del usuario con sus respuestas
            # Construir consulta con filtro de fechas si están disponibles
            query = """
                SELECT DISTINCT 
                    q.id, q.text, q.type, q.options,
                    r.response, r.date, r.response_time, r.start_time
                FROM question q
                LEFT JOIN response r ON q.id = r.question_id
                WHERE q.assigned_user_id = ? AND q.active = 1
            """
            params = [current_user.id]
            
            # Agregar filtro de fechas si están disponibles
            if fecha_desde and fecha_hasta:
                # Agregar un día completo al final para incluir todo el día final
                fecha_hasta_completa = fecha_hasta + ' 23:59:59'
                query += " AND (r.date IS NULL OR (r.date >= ? AND r.date <= ?))"
                params.extend([fecha_desde, fecha_hasta_completa])
            
            query += " ORDER BY q.text, r.date"
            
            cursor.execute(query, params)
            
            data = cursor.fetchall()
            
            # Organizar datos por tipo de pregunta
            preguntas_por_tipo = {
                'si_no': [],
                'texto_libre': [],
                'seleccion_multiple': [],
                'opcion_unica': []
            }
            
            # Organizar respuestas individuales para texto libre
            respuestas_individuales_texto = []
            
            # Procesar cada pregunta
            preguntas_procesadas = {}
            
            for row in data:
                q_id, q_text, q_type, q_options, response, date, response_time, start_time = row
                
                if q_id not in preguntas_procesadas:
                    preguntas_procesadas[q_id] = {
                        'text': q_text,
                        'type': q_type,
                        'options': q_options,
                        'responses': []
                    }
                
                if response:
                    preguntas_procesadas[q_id]['responses'].append({
                        'response': response,
                        'date': date,
                        'response_time': response_time,
                        'start_time': start_time
                    })
            
            # Clasificar preguntas por tipo y calcular estadísticas
            for q_id, pregunta in preguntas_procesadas.items():
                q_type = pregunta['type']
                responses = pregunta['responses']
                
                if not responses:
                    continue
                
                # Clasificar por tipo y calcular estadísticas específicas
                if q_type in ['yes_no', 'select'] or (q_type == 'radio' and pregunta['options'] and 'sí,no' in pregunta['options'].lower()):
                    stats = calcular_estadisticas_si_no(pregunta, fecha_desde, fecha_hasta)
                    preguntas_por_tipo['si_no'].append(stats)
                elif q_type in ['text', 'textarea']:
                    stats = calcular_estadisticas_texto_libre(pregunta, fecha_desde, fecha_hasta)
                    preguntas_por_tipo['texto_libre'].append(stats)
                    # También recopilar respuestas individuales
                    respuestas_individuales = obtener_respuestas_individuales_texto_libre(pregunta, fecha_desde, fecha_hasta)
                    respuestas_individuales_texto.extend(respuestas_individuales)
                elif q_type == 'checkbox':
                    stats = calcular_estadisticas_seleccion_multiple(pregunta, fecha_desde, fecha_hasta)
                    preguntas_por_tipo['seleccion_multiple'].append(stats)
                elif q_type in ['radio', 'multiple_choice']:
                    stats = calcular_estadisticas_opcion_unica(pregunta, fecha_desde, fecha_hasta)
                    preguntas_por_tipo['opcion_unica'].append(stats)
        
        # Crear archivo Excel
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hoja 1: Preguntas Sí/No
            if preguntas_por_tipo['si_no']:
                df_si_no = pd.DataFrame(preguntas_por_tipo['si_no'])
                df_si_no.to_excel(writer, sheet_name='Si No', index=False)
            
            # Hoja 2: Texto Libre
            if preguntas_por_tipo['texto_libre']:
                df_texto = pd.DataFrame(preguntas_por_tipo['texto_libre'])
                df_texto.to_excel(writer, sheet_name='Texto Libre', index=False)
                
                # Agregar respuestas individuales debajo si existen
                if respuestas_individuales_texto:
                    # Obtener la hoja de trabajo
                    worksheet = writer.sheets['Texto Libre']
                    
                    # Calcular la fila donde empezar (después de las métricas + 2 filas de separación)
                    start_row = len(preguntas_por_tipo['texto_libre']) + 3
                    
                    # Escribir título de sección
                    worksheet.cell(row=start_row, column=1, value="RESPUESTAS INDIVIDUALES")
                    
                    # Escribir respuestas individuales
                    df_respuestas = pd.DataFrame(respuestas_individuales_texto)
                    
                    # Escribir headers
                    for col_num, column_title in enumerate(df_respuestas.columns, 1):
                        worksheet.cell(row=start_row + 1, column=col_num, value=column_title)
                    
                    # Escribir datos
                    for row_num, row_data in enumerate(df_respuestas.values, start_row + 2):
                        for col_num, cell_value in enumerate(row_data, 1):
                            worksheet.cell(row=row_num, column=col_num, value=cell_value)
            
            # Hoja 3: Selección Múltiple
            if preguntas_por_tipo['seleccion_multiple']:
                df_multiple = pd.DataFrame(preguntas_por_tipo['seleccion_multiple'])
                df_multiple.to_excel(writer, sheet_name='Seleccion Multiple', index=False)
            
            # Hoja 4: Opción Única
            if preguntas_por_tipo['opcion_unica']:
                df_unica = pd.DataFrame(preguntas_por_tipo['opcion_unica'])
                df_unica.to_excel(writer, sheet_name='Opcion Unica', index=False)
        
        output.seek(0)
        
        # Generar nombre de archivo con fechas del filtro
        if fecha_desde and fecha_hasta:
            # Convertir fechas para el nombre del archivo (formato YYYY-MM-DD a YYYYMMDD)
            fecha_desde_formato = fecha_desde.replace('-', '')
            fecha_hasta_formato = fecha_hasta.replace('-', '')
            filename = f'respuestas_analisis_{fecha_desde_formato}_a_{fecha_hasta_formato}.xlsx'
        else:
            # Fallback si no hay fechas del filtro
            fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'respuestas_analisis_{fecha_actual}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except ImportError:
        return jsonify({
            'status': 'error',
            'message': 'pandas no está instalado. Instala con: pip install pandas openpyxl'
        }), 500
    except Exception as e:
        logger.error(f"Error exportando respuestas a Excel: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error al generar el archivo Excel: {str(e)}'
        }), 500

def calcular_estadisticas_si_no(pregunta, fecha_desde=None, fecha_hasta=None):
    """Calcula estadísticas específicas para preguntas Sí/No"""
    responses = pregunta['responses']
    
    # Datos básicos para preguntas Sí/No
    stats = {
        'Pregunta': pregunta['text'],
        'Fecha Inicio Métrica': '',
        'Fecha Fin Métrica': '',
        'Porcentaje Sí': 0,
        'Veces Sí': 0,
        'Porcentaje No': 0,
        'Veces No': 0,
        'Resumen Propio': ''
    }
    
    if not responses:
        return stats
    
    # Usar fechas del filtro si están disponibles, sino usar fechas de las respuestas
    if fecha_desde and fecha_hasta:
        stats['Fecha Inicio Métrica'] = fecha_desde
        stats['Fecha Fin Métrica'] = fecha_hasta
    else:
        # Fechas de inicio y fin del rango de datos
        fechas = [r['date'] for r in responses if r['date']]
        if fechas:
            primera_fecha = min(fechas)
            ultima_fecha = max(fechas)
            stats['Fecha Inicio Métrica'] = primera_fecha.strftime('%Y-%m-%d') if hasattr(primera_fecha, 'strftime') else str(primera_fecha)
            stats['Fecha Fin Métrica'] = ultima_fecha.strftime('%Y-%m-%d') if hasattr(ultima_fecha, 'strftime') else str(ultima_fecha)
    
    # Análisis de respuestas
    respuestas_texto = [r['response'] for r in responses if r['response']]
    
    if respuestas_texto:
        # Conteos y porcentajes para preguntas Sí/No
        total_respuestas = len(respuestas_texto)
        si_count = sum(1 for r in respuestas_texto if r.lower() in ['sí', 'si', 'yes', '1', 'true'])
        no_count = sum(1 for r in respuestas_texto if r.lower() in ['no', 'false', '0'])
        
        # Guardar conteos absolutos
        stats['Veces Sí'] = si_count
        stats['Veces No'] = no_count
        
        # Calcular porcentajes
        if si_count + no_count > 0:
            stats['Porcentaje Sí'] = round((si_count / total_respuestas) * 100, 1)
            stats['Porcentaje No'] = round((no_count / total_respuestas) * 100, 1)
        
        # Resumen propio (respuesta más común)
        from collections import Counter
        contador = Counter(respuestas_texto)
        mas_comunes = contador.most_common(2)
        if mas_comunes:
            stats['Resumen Propio'] = mas_comunes[0][0]
    
    return stats

def calcular_estadisticas_texto_libre(pregunta, fecha_desde=None, fecha_hasta=None):
    """Calcula estadísticas específicas para preguntas de texto libre"""
    responses = pregunta['responses']
    
    # Datos básicos para texto libre con estructura exacta
    stats = {
        'Pregunta': pregunta['text'],
        'Fecha Inicio Métrica': '',
        'Fecha Fin Métrica': '',
        'Palabra Que Más Aparece': '',
        'Segunda Palabra Que Más Aparece': '',
        'Longitud Promedio de Respuesta': 0,
        'Tiempo Promedio': 0
    }
    
    if not responses:
        return stats
    
    # Usar fechas del filtro si están disponibles
    if fecha_desde and fecha_hasta:
        stats['Fecha Inicio Métrica'] = fecha_desde
        stats['Fecha Fin Métrica'] = fecha_hasta
    
    # Análisis de respuestas de texto
    respuestas_texto = [r['response'] for r in responses if r['response']]
    
    if respuestas_texto:
        # Análisis de palabras más frecuentes
        from collections import Counter
        import re
        
        # Extraer todas las palabras (sin palabras vacías comunes)
        palabras_vacias = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'como', 'pero', 'sus', 'me', 'ya', 'muy', 'mi', 'si', 'más', 'este', 'esta', 'todo', 'bien', 'fue', 'han', 'hay', 'donde', 'quien', 'desde', 'todos', 'durante', 'tanto', 'menos', 'puede', 'ser', 'estar', 'tener', 'hacer', 'ir', 'ver', 'dar', 'saber', 'querer', 'venir', 'poder', 'decir', 'otro', 'algún', 'qué', 'sí', 'porque', 'cuando', 'mucho', 'sin', 'sobre', 'también', 'me', 'le', 'ya', 'todo', 'esta', 'entre', 'era', 'estos', 'mucho', 'había', 'él', 'hasta', 'poder', 'dónde', 'ir', 'le', 'tiempo', 'cada', 'caso', 'esos', 'pues', 'ahora', 'donde', 'modo', 'bien', 'saber', 'qué', 'trabajo', 'vida', 'día', 'grupo', 'momento', 'primer', 'vez', 'sin', 'lugar', 'año', 'trabajo', 'hombre', 'tanto', 'gobierno', 'parte', 'niño', 'punto', 'mundo', 'venir', 'parecer', 'existir', 'creer', 'hablar', 'llevar', 'dejar', 'nada', 'cada', 'seguir', 'menos', 'nuevo'}
        
        todas_palabras = []
        for respuesta in respuestas_texto:
            # Limpiar y extraer palabras (mínimo 3 caracteres)
            palabras = re.findall(r'\b[a-záéíóúñü]{3,}\b', respuesta.lower())
            # Filtrar palabras vacías
            palabras_filtradas = [p for p in palabras if p not in palabras_vacias]
            todas_palabras.extend(palabras_filtradas)
        
        if todas_palabras:
            contador_palabras = Counter(todas_palabras)
            mas_comunes_palabras = contador_palabras.most_common(5)
            
            if len(mas_comunes_palabras) > 0:
                stats['Palabra Que Más Aparece'] = f"{mas_comunes_palabras[0][0]} ({mas_comunes_palabras[0][1]})"
            
            if len(mas_comunes_palabras) > 1:
                stats['Segunda Palabra Que Más Aparece'] = f"{mas_comunes_palabras[1][0]} ({mas_comunes_palabras[1][1]})"
        
        # Longitud promedio de respuesta
        longitudes = [len(str(r)) for r in respuestas_texto]
        stats['Longitud Promedio de Respuesta'] = round(sum(longitudes) / len(longitudes), 1)
        
        # Tiempo promedio de respuesta (en segundos)
        tiempos = [r['response_time'] for r in responses if r['response_time']]
        if tiempos:
            stats['Tiempo Promedio'] = round(sum(tiempos) / len(tiempos), 1)
    
    return stats

def obtener_respuestas_individuales_texto_libre(pregunta, fecha_desde=None, fecha_hasta=None):
    """Obtiene respuestas individuales para preguntas de texto libre"""
    responses = pregunta['responses']
    
    if not responses:
        return []
    
    # Crear una lista de respuestas individuales
    respuestas_individuales = []
    
    for response in responses:
        if response['response']:  # Solo incluir respuestas no vacías
            respuesta_individual = {
                'Pregunta': pregunta['text'],
                'Fecha Respuesta': response['date'].strftime('%Y-%m-%d') if response['date'] else '',
                'Respuesta': response['response'],
                'Longitud Respuesta': len(response['response']) if response['response'] else 0,
                'Tiempo Respuesta': response['response_time'] if response['response_time'] else 0
            }
            respuestas_individuales.append(respuesta_individual)
    
    return respuestas_individuales

def calcular_estadisticas_seleccion_multiple(pregunta, fecha_desde=None, fecha_hasta=None):
    """Calcula estadísticas específicas para preguntas de selección múltiple"""
    responses = pregunta['responses']
    
    # Datos básicos para selección múltiple con estructura exacta
    stats = {
        'Pregunta': pregunta['text'],
        'Fecha Inicio Métrica': '',
        'Fecha Fin Métrica': '',
        'Opción Más Elegida': '',
        'Segunda Más Elegida': '',
        'Tercera Más Elegida': '',
        'Cuarta Más Elegida': '',
        'Quinta Más Elegida': '',
        'Sexta Más Elegida': '',
        'Tiempo Promedio': 0
    }
    
    if not responses:
        return stats
    
    # Usar fechas del filtro si están disponibles
    if fecha_desde and fecha_hasta:
        stats['Fecha Inicio Métrica'] = fecha_desde
        stats['Fecha Fin Métrica'] = fecha_hasta
    
    # Análisis de opciones seleccionadas
    respuestas_texto = [r['response'] for r in responses if r['response']]
    
    if respuestas_texto:
        from collections import Counter
        
        # Para checkboxes, las respuestas pueden venir separadas por comas
        todas_opciones = []
        for respuesta in respuestas_texto:
            if ',' in respuesta:
                opciones = [opt.strip() for opt in respuesta.split(',')]
                todas_opciones.extend(opciones)
            else:
                todas_opciones.append(respuesta.strip())
        
        contador = Counter(todas_opciones)
        mas_comunes = contador.most_common(6)  # Obtener hasta 6 opciones
        
        if len(mas_comunes) > 0:
            stats['Opción Más Elegida'] = f"{mas_comunes[0][0]} ({mas_comunes[0][1]})"
        
        if len(mas_comunes) > 1:
            stats['Segunda Más Elegida'] = f"{mas_comunes[1][0]} ({mas_comunes[1][1]})"
            
        if len(mas_comunes) > 2:
            stats['Tercera Más Elegida'] = f"{mas_comunes[2][0]} ({mas_comunes[2][1]})"
            
        if len(mas_comunes) > 3:
            stats['Cuarta Más Elegida'] = f"{mas_comunes[3][0]} ({mas_comunes[3][1]})"
            
        if len(mas_comunes) > 4:
            stats['Quinta Más Elegida'] = f"{mas_comunes[4][0]} ({mas_comunes[4][1]})"
            
        if len(mas_comunes) > 5:
            stats['Sexta Más Elegida'] = f"{mas_comunes[5][0]} ({mas_comunes[5][1]})"
        
        # Tiempo promedio de respuesta (en segundos)
        tiempos = [r['response_time'] for r in responses if r['response_time']]
        if tiempos:
            stats['Tiempo Promedio'] = round(sum(tiempos) / len(tiempos), 1)
    
    return stats

def calcular_estadisticas_opcion_unica(pregunta, fecha_desde=None, fecha_hasta=None):
    """Calcula estadísticas específicas para preguntas de opción única"""
    responses = pregunta['responses']
    
    # Datos básicos para opción única con estructura exacta
    stats = {
        'Pregunta': pregunta['text'],
        'Fecha Inicio Métrica': '',
        'Fecha Fin Métrica': '',
        'Opción Más Elegida': '',
        'Segunda Más Elegida': '',
        'Tercera Más Elegida': '',
        'Cuarta Más Elegida': '',
        'Quinta Más Elegida': '',
        'Sexta Más Elegida': '',
        'Tiempo Promedio': 0
    }
    
    if not responses:
        return stats
    
    # Usar fechas del filtro si están disponibles
    if fecha_desde and fecha_hasta:
        stats['Fecha Inicio Métrica'] = fecha_desde
        stats['Fecha Fin Métrica'] = fecha_hasta
    
    # Análisis de opciones seleccionadas
    respuestas_texto = [r['response'] for r in responses if r['response']]
    
    if respuestas_texto:
        from collections import Counter
        
        contador = Counter(respuestas_texto)
        mas_comunes = contador.most_common(6)  # Obtener hasta 6 opciones
        total = len(respuestas_texto)
        
        if len(mas_comunes) > 0:
            porcentaje = round((mas_comunes[0][1] / total) * 100, 1)
            stats['Opción Más Elegida'] = f"{mas_comunes[0][0]} ({mas_comunes[0][1]} - {porcentaje}%)"
        
        if len(mas_comunes) > 1:
            porcentaje = round((mas_comunes[1][1] / total) * 100, 1)
            stats['Segunda Más Elegida'] = f"{mas_comunes[1][0]} ({mas_comunes[1][1]} - {porcentaje}%)"
            
        if len(mas_comunes) > 2:
            porcentaje = round((mas_comunes[2][1] / total) * 100, 1)
            stats['Tercera Más Elegida'] = f"{mas_comunes[2][0]} ({mas_comunes[2][1]} - {porcentaje}%)"
            
        if len(mas_comunes) > 3:
            porcentaje = round((mas_comunes[3][1] / total) * 100, 1)
            stats['Cuarta Más Elegida'] = f"{mas_comunes[3][0]} ({mas_comunes[3][1]} - {porcentaje}%)"
            
        if len(mas_comunes) > 4:
            porcentaje = round((mas_comunes[4][1] / total) * 100, 1)
            stats['Quinta Más Elegida'] = f"{mas_comunes[4][0]} ({mas_comunes[4][1]} - {porcentaje}%)"
            
        if len(mas_comunes) > 5:
            porcentaje = round((mas_comunes[5][1] / total) * 100, 1)
            stats['Sexta Más Elegida'] = f"{mas_comunes[5][0]} ({mas_comunes[5][1]} - {porcentaje}%)"
        
        # Distribución general
        distribuciones = [f"{opcion}: {count}" for opcion, count in mas_comunes[:3]]
        stats['Distribución'] = " | ".join(distribuciones)
        
        # Tiempo promedio de respuesta (en segundos)
        tiempos = [r['response_time'] for r in responses if r['response_time']]
        if tiempos:
            stats['Tiempo Promedio'] = round(sum(tiempos) / len(tiempos), 1)
    
    return stats

@app.route('/debug-preguntas-mensuales')
@login_required
def debug_preguntas_mensuales():
    """Debug endpoint para preguntas mensuales"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar todas las preguntas del usuario
            cursor.execute(
                'SELECT id, text, frecuencia, active FROM question WHERE assigned_user_id = ?',
                (current_user.id,)
            )
            todas_preguntas = cursor.fetchall()
            
            # Verificar preguntas mensuales específicamente
            cursor.execute(
                'SELECT id, text, type, options, active, created_at, assigned_user_id, descripcion, is_required, categoria, frecuencia '
                'FROM question WHERE assigned_user_id = ? AND active = 1 AND frecuencia = ?',
                (current_user.id, 'mensual')
            )
            preguntas_mensuales = cursor.fetchall()
            
            return jsonify({
                'status': 'success',
                'user_id': current_user.id,
                'todas_preguntas': [
                    {'id': p[0], 'text': p[1], 'frecuencia': p[2], 'active': p[3]} 
                    for p in todas_preguntas
                ],
                'preguntas_mensuales': [
                    {'id': p[0], 'text': p[1], 'frecuencia': p[10]} 
                    for p in preguntas_mensuales
                ],
                'total_preguntas': len(todas_preguntas),
                'total_mensuales': len(preguntas_mensuales)
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/objetivos', methods=['GET'])
@login_required
def api_list_objetivos():
    from datetime import datetime, timedelta
    hoy = datetime.now().date()
    dia_semana = hoy.weekday()  # 0=lunes
    primer_dia_semana = hoy - timedelta(days=dia_semana)
    primer_dia_mes = hoy.replace(day=1)
    primer_dia_anio = hoy.replace(month=1, day=1)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Consulta con ordenamiento que pone solo los completados al final
        hoy = datetime.now().date()
        cursor.execute('''
            SELECT o.id, o.titulo, o.descripcion, o.prioridad, o.categoria, o.completado, o.fecha_creacion, o.fecha_completado, 
                   o.objetivo_padre_id, o.es_padre, o.estado, o.fecha_inicio, o.fecha_fin, 
                   o.horas_estimadas, o.recompensa, o.recurrente, o.frecuencia, o.orden, o.parte_dia,
                   CASE WHEN os.objetivo_id IS NOT NULL THEN 1 ELSE 0 END as saltado_hoy,
                   o.fecha_programada, o.programado_para, o.tiempo_focus
            FROM objetivos o
            LEFT JOIN objetivos_saltados os ON o.id = os.objetivo_id AND os.user_id = o.user_id AND os.fecha_saltada = ?
            WHERE o.user_id = ? 
            AND (
                (o.fecha_programada IS NULL AND o.programado_para IS NULL) OR
                (o.fecha_programada IS NOT NULL AND o.fecha_programada <= ?) OR
                (o.recurrente = 1 AND o.programado_para = 'diario')
            )
            ORDER BY 
                CASE 
                    WHEN o.completado = 1 THEN 2
                    WHEN os.objetivo_id IS NOT NULL THEN 1
                    ELSE 0
                END ASC,
                CASE 
                    WHEN o.parte_dia = 'mañana' THEN 1
                    WHEN o.parte_dia = 'tarde' THEN 2
                    WHEN o.parte_dia = 'noche' THEN 3
                    ELSE 4
                END ASC,
                o.orden ASC, 
                o.fecha_creacion DESC
        ''', (hoy, current_user.id, hoy))
        rows = cursor.fetchall()
        objetivos = []
        
        for row in rows:
            obj = {
                'id': row[0],
                'titulo': row[1],
                'descripcion': row[2],
                'prioridad': row[3],
                'categoria': row[4],
                'completado': bool(row[5]),
                'fecha_creacion': row[6].strftime('%Y-%m-%d') if row[6] else None,
                'fecha_completado': row[7].strftime('%Y-%m-%d') if row[7] else None,
                'objetivo_padre_id': row[8],
                'es_padre': bool(row[9]),
                'estado': row[10],
                'fecha_inicio': row[11].strftime('%Y-%m-%d') if row[11] else None,
                'fecha_fin': row[12].strftime('%Y-%m-%d') if row[12] else None,
                'horas_estimadas': row[13],
                'recompensa': row[14],
                'recurrente': bool(row[15]) if len(row) > 15 else False,
                'frecuencia': row[16] if len(row) > 16 else None,
                'orden': row[17] if len(row) > 17 else 0,
                'parte_dia': row[18] if len(row) > 18 else None,
                'saltado_hoy': bool(row[19]) if len(row) > 19 else False,
                'fecha_programada': row[20].strftime('%Y-%m-%d') if len(row) > 20 and row[20] else None,
                'programado_para': row[21] if len(row) > 21 else None,
                'tiempo_focus': row[22] if len(row) > 22 else None
            }
            # Verificar si el objetivo está vencido
            vencido = es_objetivo_vencido(obj, hoy)
            

            
            if vencido:
                # Mover a históricos si no está ya en histórico
                if obj['estado'] != 'histórico':
                    with get_db_connection() as conn_update:
                        cursor_update = conn_update.cursor()
                        cursor_update.execute('''UPDATE objetivos SET estado = 'histórico' WHERE id = ? AND user_id = ? AND estado != 'histórico' ''', (obj['id'], current_user.id))
                        conn_update.commit()
                        obj['estado'] = 'histórico'
            # Solo mostrar como activo si NO está vencido, aunque esté completado manualmente
            if not vencido:
                objetivos.append(obj)
        

        
        return jsonify(objetivos)

def parse_fecha(fecha_str):
    if not fecha_str:
        return None
    try:
        return datetime.strptime(fecha_str, '%Y-%m-%d')
    except ValueError:
        return None

def calcular_fecha_vencimiento(fecha_inicio, frecuencia):
    """
    Calcula la fecha de vencimiento automática basada en la frecuencia.
    """
    if not fecha_inicio:
        return None
    
    fecha_inicio = fecha_inicio.date() if hasattr(fecha_inicio, 'date') else fecha_inicio
    
    if frecuencia == 'diario':
        return fecha_inicio + timedelta(days=1)
    elif frecuencia == 'semanal':
        return fecha_inicio + timedelta(days=7)
    elif frecuencia == 'mensual':
        # Aproximadamente 30 días para mensual
        return fecha_inicio + timedelta(days=30)
    elif frecuencia == 'anual':
        # Aproximadamente 365 días para anual
        return fecha_inicio + timedelta(days=365)
    else:
        return None

def es_objetivo_vencido(objetivo, hoy):
    """
    Determina si un objetivo está vencido basado en su fecha de vencimiento calculada.
    """
    # EXCEPCIÓN: Los objetivos programados para hoy NUNCA están vencidos
    if objetivo.get('fecha_programada'):
        try:
            fecha_prog = datetime.strptime(objetivo['fecha_programada'], '%Y-%m-%d').date()
            if fecha_prog == hoy:
                print(f"DEBUG - Objetivo programado para HOY: {objetivo['titulo']} - NO VENCIDO")
                return False
        except (ValueError, TypeError):
            pass
    # Comentamos esta línea para que también se muevan los objetivos completados
    # if objetivo['completado']:
    #     print(f"DEBUG - Objetivo completado: {objetivo['titulo']} - NO VENCIDO (ya está completado)")
    #     return False
    
    # Si tiene fecha_fin explícita, usar esa
    if objetivo['fecha_fin']:
        try:
            fecha_vencimiento = datetime.strptime(objetivo['fecha_fin'], '%Y-%m-%d').date()
            return hoy > fecha_vencimiento
        except (ValueError, TypeError):
            return False
    
    # Si es recurrente, NO se considera vencido (permanece activo)
    if objetivo['recurrente']:
        print(f"DEBUG - Objetivo recurrente: {objetivo['titulo']} - NO VENCIDO (es recurrente)")
        return False
    
    # Objetivos NO recurrentes: vencimiento automático según categoría y fecha_creacion
    if objetivo['categoria'] and objetivo['fecha_creacion']:
        try:
            fecha_creacion = datetime.strptime(objetivo['fecha_creacion'], '%Y-%m-%d').date()
            categoria_lower = objetivo['categoria'].lower()
            
            # Debug: imprimir información del objetivo
            # print(f"DEBUG - Objetivo: {objetivo['titulo']}")
            # print(f"  Categoría: '{objetivo['categoria']}' -> '{categoria_lower}'")
            # print(f"  Fecha creación: {objetivo['fecha_creacion']} -> {fecha_creacion}")
            # print(f"  Hoy: {hoy}")
            # print(f"  Es diario: {categoria_lower == 'diario'}")
            # print(f"  Hoy > fecha_creacion: {hoy > fecha_creacion}")
            # print(f"  RESULTADO: VENCIDO")
            # print(f"  RESULTADO: VENCIDO (semanal)")
            # print(f"  RESULTADO: VENCIDO (mensual)")
            # print(f"  RESULTADO: VENCIDO (anual)")
            # print(f"ERROR parsing fecha: {e}")
            # print(f"DEBUG - Objetivo recurrente: {objetivo['titulo']} - NO VENCIDO (es recurrente)")
            
            if categoria_lower == 'diario' and hoy > fecha_creacion:
                print(f"  RESULTADO: VENCIDO")
                return True
            if categoria_lower == 'semanal' and hoy > (fecha_creacion + timedelta(days=7)):
                print(f"  RESULTADO: VENCIDO (semanal)")
                return True
            # Para objetivos mensuales: vencen después de 30 días
            if categoria_lower == 'mensual' and hoy > (fecha_creacion + timedelta(days=30)):
                print(f"  RESULTADO: VENCIDO (mensual)")
                return True
            # Para objetivos anuales: vencen después de 365 días
            if categoria_lower == 'anual' and hoy > (fecha_creacion + timedelta(days=365)):
                print(f"  RESULTADO: VENCIDO (anual)")
                return True
            # Para objetivos generales: NO deben vencerse automáticamente
            # if categoria_lower == 'general' and hoy > fecha_creacion:
            #     print(f"  RESULTADO: VENCIDO (general)")
            #     return True
        except (ValueError, TypeError) as e:
            print(f"ERROR parsing fecha: {e}")
            return False
    
    return False

def enviar_notificacion_proyeccion_comienzo(objetivo, usuario_email):
    """
    Envía una notificación por correo cuando llega la fecha de proyección de comienzo.
    """
    try:
        subject = f"¡Es hora de comenzar tu objetivo: {objetivo['titulo']}!"
        
        html_body = f"""
        <html>
        <body>
            <h2>¡Hola! 👋</h2>
            <p>Hoy es la fecha que proyectaste para comenzar tu objetivo:</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #007bff; margin-top: 0;">{objetivo['titulo']}</h3>
                <p><strong>Descripción:</strong> {objetivo.get('descripcion', 'Sin descripción')}</p>
                <p><strong>Categoría:</strong> {objetivo.get('categoria', 'Sin categoría')}</p>
                <p><strong>Prioridad:</strong> {objetivo.get('prioridad', 'Media')}</p>
                <p><strong>Dificultad:</strong> {objetivo.get('dificultad', 'No especificada')}</p>
            </div>
            
            <p>¡Es el momento perfecto para dar el primer paso hacia tu meta!</p>
            
            <div style="margin: 30px 0;">
                <a href="http://localhost:5000/objetivos" 
                   style="background-color: #007bff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Ver mis objetivos
                </a>
            </div>
            
            <p style="color: #6c757d; font-size: 14px;">
                Este correo fue enviado automáticamente por Daily Questions App.
            </p>
        </body>
        </html>
        """
        
        msg = Message(
            subject=subject,
            recipients=[usuario_email],
            html=html_body
        )
        
        mail.send(msg)
        logger.info(f"Notificación enviada exitosamente a {usuario_email} para el objetivo: {objetivo['titulo']}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación de proyección: {str(e)}")
        return False

def verificar_proyecciones_comienzo():
    """
    Verifica los objetivos que tienen fecha de proyección de comienzo para hoy
    y envía notificaciones por correo.
    """
    try:
        hoy = datetime.now().date()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Buscar objetivos con fecha de proyección de comienzo para hoy
            cursor.execute("""
                SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad, o.dificultad,
                       u.username, u.password
                FROM objetivos o
                JOIN [user] u ON o.user_id = u.id
                WHERE o.fecha_inicio = ?
                AND o.completado = 0
            """, (hoy,))
            
            objetivos_hoy = cursor.fetchall()
            
            for objetivo_data in objetivos_hoy:
                objetivo = {
                    'id': objetivo_data[0],
                    'titulo': objetivo_data[1],
                    'descripcion': objetivo_data[2],
                    'categoria': objetivo_data[3],
                    'prioridad': objetivo_data[4],
                    'dificultad': objetivo_data[5]
                }
                
                # Por ahora usamos el username como email (en producción deberías tener un campo email)
                usuario_email = f"{objetivo_data[6]}@example.com"  # Placeholder
                
                # Enviar notificación
                enviar_notificacion_proyeccion_comienzo(objetivo, usuario_email)
                
        logger.info(f"Verificación de proyecciones completada. {len(objetivos_hoy)} objetivos encontrados para hoy.")
        
    except Exception as e:
        logger.error(f"Error verificando proyecciones de comienzo: {str(e)}")

@app.route('/api/verificar-proyecciones', methods=['POST'])
@login_required
def api_verificar_proyecciones():
    """
    Endpoint para verificar proyecciones de comienzo (puede ser llamado por un cron job)
    """
    try:
        verificar_proyecciones_comienzo()
        return jsonify({'status': 'success', 'message': 'Verificación de proyecciones completada'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/reset-objetivos-diarios', methods=['POST'])
@login_required
def api_reset_objetivos_diarios():
    """
    Endpoint para ejecutar manualmente el reset de objetivos diarios recurrentes
    """
    try:
        reset_objetivos_diarios_recurrentes()
        return jsonify({'status': 'success', 'message': 'Reset de objetivos diarios completado'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/test-orden', methods=['GET'])
@login_required
def api_test_orden():
    """
    Endpoint de prueba para verificar el orden de objetivos
    """
    try:
        from datetime import datetime
        hoy = datetime.now().date()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.id, o.titulo, o.completado, o.orden,
                       CASE WHEN os.objetivo_id IS NOT NULL THEN 1 ELSE 0 END as saltado_hoy
                FROM objetivos o
                LEFT JOIN objetivos_saltados os ON o.id = os.objetivo_id AND os.user_id = o.user_id AND os.fecha_saltada = ?
                WHERE o.user_id = ? 
                ORDER BY 
                    o.completado ASC,
                    o.orden ASC, 
                    o.fecha_creacion DESC
            ''', (hoy, current_user.id))
            
            objetivos = cursor.fetchall()
            
            # Convertir a formato JSON
            result = []
            for obj in objetivos:
                result.append({
                    'id': obj[0],
                    'titulo': obj[1][:50] + '...' if len(obj[1]) > 50 else obj[1],
                    'completado': bool(obj[2]),
                    'orden': obj[3],
                    'saltado_hoy': bool(obj[4])
                })
            
            return jsonify({
                'status': 'success',
                'total': len(result),
                'primeros_10': result[:10],
                'ultimos_10': result[-10:],
                'completados_total': sum(1 for obj in objetivos if obj[2]),
                'mensaje': 'Si ves completados en primeros_10, hay un problema. Si están en ultimos_10, está funcionando.'
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/objetivos', methods=['POST'])
@login_required
def api_create_objetivo():
    data = request.get_json()
    titulo = data.get('titulo', '').strip()
    descripcion = data.get('descripcion', '').strip()
    prioridad = data.get('prioridad', 'media')
    categoria = data.get('categoria', '').strip().lower()
    es_padre = int(bool(data.get('es_padre', False)))
    objetivo_padre_id = data.get('objetivo_padre_id')
    estado = data.get('estado')
    fecha_inicio = parse_fecha(data.get('fecha_inicio'))
    fecha_fin = parse_fecha(data.get('fecha_fin'))
    horas_estimadas = data.get('horas_estimadas')
    recompensa = data.get('recompensa')
    parte_dia = data.get('parte_dia')
    recurrente = int(bool(data.get('recurrente', False)))
    frecuencia = data.get('frecuencia') if recurrente else None
    if not titulo:
        return jsonify({'error': 'El título es obligatorio'}), 400
    
    # Obtener la fecha actual para la creación
    fecha_creacion = datetime.now()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Obtener el mayor valor de orden actual para la categoría
        cursor.execute('''SELECT COALESCE(MAX(orden), 0) FROM objetivos WHERE user_id = ? AND categoria = ?''', (current_user.id, categoria))
        max_orden = cursor.fetchone()[0]
        nuevo_orden = max_orden + 1
        
        cursor.execute('''INSERT INTO objetivos (user_id, titulo, descripcion, prioridad, categoria, completado, fecha_creacion, objetivo_padre_id, es_padre, estado, fecha_inicio, fecha_fin, horas_estimadas, recompensa, parte_dia, recurrente, frecuencia, orden)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (current_user.id, titulo, descripcion, prioridad, categoria, fecha_creacion, objetivo_padre_id, es_padre, estado, fecha_inicio, fecha_fin, horas_estimadas, recompensa, parte_dia, recurrente, frecuencia, nuevo_orden))
        objetivo_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'status': 'success', 'id': objetivo_id})

@app.route('/api/objetivos/<int:objetivo_id>', methods=['GET'])
@login_required
def api_get_objetivo(objetivo_id):
    """Obtener un objetivo específico por ID"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.id, o.titulo, o.descripcion, o.prioridad, o.categoria, o.completado, 
                       o.fecha_creacion, o.fecha_completado, o.objetivo_padre_id, o.es_padre, 
                       o.estado, o.fecha_inicio, o.fecha_fin, o.horas_estimadas, o.recompensa, 
                       o.parte_dia, o.recurrente, o.frecuencia, o.orden, o.fecha_programada, o.programado_para, o.tiempo_focus, o.notas_adicionales
                FROM objetivos o
                WHERE o.id = ? AND o.user_id = ?
            ''', (objetivo_id, current_user.id))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': 'Objetivo no encontrado'}), 404
            
            objetivo = {
                'id': row[0],
                'titulo': row[1],
                'descripcion': row[2],
                'prioridad': row[3],
                'categoria': row[4],
                'completado': bool(row[5]),
                'fecha_creacion': row[6].strftime('%Y-%m-%d') if row[6] else None,
                'fecha_completado': row[7].strftime('%Y-%m-%d') if row[7] else None,
                'objetivo_padre_id': row[8],
                'es_padre': bool(row[9]),
                'estado': row[10],
                'fecha_inicio': row[11].strftime('%Y-%m-%d') if row[11] else None,
                'fecha_fin': row[12].strftime('%Y-%m-%d') if row[12] else None,
                'horas_estimadas': row[13],
                'recompensa': row[14],
                'parte_dia': row[15],
                'recurrente': bool(row[16]),
                'frecuencia': row[17],
                'orden': row[18],
                'fecha_programada': row[19].strftime('%Y-%m-%d') if row[19] else None,
                'programado_para': row[20],
                'tiempo_focus': row[21] if row[21] else 0,
                'notas_adicionales': row[22] if row[22] else ''
            }
            
            return jsonify(objetivo)
            
    except Exception as e:
        logger.error(f"Error al obtener objetivo {objetivo_id}: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/objetivos/<int:objetivo_id>', methods=['PATCH'])
@login_required
def api_update_objetivo(objetivo_id):
    data = request.get_json()
    

    
    # Si se está marcando como recurrente Y viene del histórico (solo restaurar si cambia de False a True)
    # Esta lógica debería ejecutarse solo cuando se restaura desde histórico, no en ediciones normales
    # Por ahora la comentamos para permitir ediciones normales de objetivos recurrentes
    # if 'recurrente' in data and data['recurrente'] == True:
    #     return restaurar_objetivo_completo(objetivo_id)
    
    campos = {}
    for campo in ['titulo', 'descripcion', 'prioridad', 'categoria', 'objetivo_padre_id', 'es_padre', 'estado', 'fecha_inicio', 'fecha_fin', 'horas_estimadas', 'recompensa', 'parte_dia', 'recurrente', 'frecuencia', 'tiempo_focus', 'programado_para', 'fecha_programada', 'notas_adicionales']:
        if campo in data:
            if campo in ['fecha_inicio', 'fecha_fin', 'fecha_programada']:
                campos[campo] = parse_fecha(data[campo])
            elif campo == 'categoria':
                campos[campo] = data[campo].strip().lower()
            elif campo == 'tiempo_focus':
                # Validar que sea un número entero positivo
                try:
                    tiempo = int(data[campo])
                    if tiempo >= 0:
                        campos[campo] = tiempo
                    else:
                        logger.warning(f"Tiempo focus negativo ignorado: {tiempo}")
                except (ValueError, TypeError):
                    logger.warning(f"Tiempo focus inválido ignorado: {data[campo]}")
            elif campo == 'notas_adicionales':
                # Limpiar y validar notas
                notas = data[campo].strip() if data[campo] else ''
                campos[campo] = notas
                print(f"📝 OBJ: Actualizando notas_adicionales: {len(notas)} caracteres")
            else:
                campos[campo] = data[campo]
    if 'completado' in data:
        campos['completado'] = int(bool(data['completado']))
        if data['completado']:
            campos['fecha_completado'] = 'GETDATE()'
        else:
            campos['fecha_completado'] = 'NULL'
    if not campos:
        return jsonify({'error': 'No hay campos para actualizar'}), 400
    set_clause = []
    values = []
    for k, v in campos.items():
        if k == 'fecha_completado' and v == 'GETDATE()':
            set_clause.append(f"{k} = GETDATE()")
        elif k == 'fecha_completado' and v == 'NULL':
            set_clause.append(f"{k} = NULL")
        else:
            set_clause.append(f"{k} = ?")
            values.append(v)
    values.extend([objetivo_id, current_user.id])
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Primero verificar si el objetivo es recurrente
        cursor.execute("SELECT recurrente FROM objetivos WHERE id = ? AND user_id = ?", (objetivo_id, current_user.id))
        objetivo_info = cursor.fetchone()
        
        if not objetivo_info:
            return jsonify({'error': 'Objetivo no encontrado'}), 404
        
        es_recurrente = objetivo_info.recurrente
        
        # Actualizar el objetivo
        query = f"UPDATE objetivos SET {', '.join(set_clause)} WHERE id = ? AND user_id = ?"
        cursor.execute(query, tuple(values))
        
        # Si es un objetivo recurrente y se está marcando como completado, registrar en el log
        if 'completado' in data and data['completado'] and es_recurrente:
            # Verificar si ya existe un registro para hoy
            hoy = datetime.now().date()
            cursor.execute("""
                SELECT COUNT(*) FROM objetivos_completados_log 
                WHERE objetivo_id = ? AND user_id = ? AND CAST(fecha_completado AS DATE) = ?
            """, (objetivo_id, current_user.id, hoy))
            
            existe_hoy = cursor.fetchone()[0] > 0
            
            if not existe_hoy:
                # Registrar en el log de completados
                cursor.execute("""
                    INSERT INTO objetivos_completados_log (objetivo_id, user_id, fecha_completado)
                    VALUES (?, ?, GETDATE())
                """, (objetivo_id, current_user.id))
                logger.info(f"Objetivo recurrente {objetivo_id} registrado en log de completados para hoy")
        
        # Si es un objetivo recurrente y se está desmarcando, eliminar del log de hoy
        elif 'completado' in data and not data['completado'] and es_recurrente:
            hoy = datetime.now().date()
            cursor.execute("""
                DELETE FROM objetivos_completados_log 
                WHERE objetivo_id = ? AND user_id = ? AND CAST(fecha_completado AS DATE) = ?
            """, (objetivo_id, current_user.id, hoy))
            logger.info(f"Objetivo recurrente {objetivo_id} eliminado del log de completados para hoy")
        
        conn.commit()
        return jsonify({'status': 'success'})

def restaurar_objetivo_completo(objetivo_id):
    """Restaura un objetivo del histórico incluyendo sus subobjetivos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Marcar el objetivo como recurrente y no completado
            cursor.execute("""
                UPDATE objetivos 
                SET recurrente = 1, completado = 0, fecha_completado = NULL
                WHERE id = ? AND user_id = ?
            """, (objetivo_id, current_user.id))
            
            # 2. Restaurar todos los subobjetivos asociados
            # Primero verificamos si existen subobjetivos para este objetivo
            cursor.execute("""
                SELECT COUNT(*) FROM subobjetivos 
                WHERE objetivo_id = ?
            """, (objetivo_id,))
            
            count_subobjetivos = cursor.fetchone()[0]
            
            if count_subobjetivos > 0:
                # Si existen subobjetivos, los restauramos (marcar como no completados)
                cursor.execute("""
                    UPDATE subobjetivos 
                    SET completado = 0
                    WHERE objetivo_id = ?
                """, (objetivo_id,))
                
                logger.info(f"Restaurados {count_subobjetivos} subobjetivos para el objetivo {objetivo_id}")
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Objetivo restaurado con {count_subobjetivos} subobjetivos'
            })
            
    except Exception as e:
        logger.error(f"Error restaurando objetivo completo {objetivo_id}: {str(e)}")
        return jsonify({'error': 'Error al restaurar el objetivo'}), 500

@app.route('/api/objetivos/<int:objetivo_id>', methods=['DELETE'])
@login_required
def api_delete_objetivo(objetivo_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Eliminar registros relacionados en objetivos_saltados y subobjetivos
        cursor.execute('''DELETE FROM objetivos_saltados WHERE objetivo_id = ?''', (objetivo_id,))
        cursor.execute('''DELETE FROM subobjetivos WHERE objetivo_id = ?''', (objetivo_id,))
        # Ahora sí eliminar el objetivo
        cursor.execute('''DELETE FROM objetivos WHERE id = ? AND user_id = ?''', (objetivo_id, current_user.id))
        conn.commit()
        return jsonify({'status': 'success'})

@app.route('/api/objetivos/reordenar', methods=['POST'])
@login_required
def api_reordenar_objetivos():
    data = request.get_json()
    ids = data.get('ids', [])
    categoria = data.get('categoria', '')
    
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return jsonify({'error': 'Formato de datos inválido'}), 400
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for orden, obj_id in enumerate(ids):
            cursor.execute('''UPDATE objetivos SET orden = ? WHERE id = ? AND user_id = ? AND categoria = ?''', 
                         (orden + 1, obj_id, current_user.id, categoria))
        conn.commit()
    return jsonify({'status': 'success'})

@app.route('/api/objetivos_padre', methods=['GET'])
@login_required
def api_list_objetivos_padre():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT id, titulo FROM objetivos WHERE user_id = ? AND es_padre = 1 ORDER BY titulo ASC''', (current_user.id,))
        rows = cursor.fetchall()
        objetivos = [
            {
                'id': row[0],
                'titulo': row[1]
            }
            for row in rows
        ]
        return jsonify(objetivos)

@app.route('/api/objetivos_historico', methods=['GET'])
@login_required
def api_objetivos_historico():
    try:
        from datetime import datetime, timedelta
        tipo = request.args.get('tipo')
        estado = request.args.get('estado')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        q = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))

        filtros = ["user_id = ?"]
        valores = [current_user.id]

        hoy = datetime.now().date()
        
        # Lógica completa del histórico
        filtros_hist = []
        
        # 1. Objetivos completados
        filtros_hist.append("completado = 1")
        
        # 2. Objetivos vencidos (con fecha_fin pasada y no completados)
        filtros_hist.append("(completado = 0 AND fecha_fin IS NOT NULL AND fecha_fin < ?)")
        valores.append(hoy)
        
        # 3. Objetivos diarios de ayer y anteriores (no completados)
        filtros_hist.append("(completado = 0 AND categoria = 'diario' AND CAST(fecha_creacion AS DATE) < ?)")
        valores.append(hoy)
        
        # 4. Objetivos semanales vencidos (más de 7 días)
        filtros_hist.append("(completado = 0 AND categoria = 'semanal' AND fecha_creacion <= ?)")
        valores.append(hoy - timedelta(days=7))
        
        # 5. Objetivos mensuales vencidos (más de 30 días)
        filtros_hist.append("(completado = 0 AND categoria = 'mensual' AND fecha_creacion <= ?)")
        valores.append(hoy - timedelta(days=30))
        
        # 6. Objetivos anuales vencidos (más de 365 días)
        filtros_hist.append("(completado = 0 AND categoria = 'anual' AND fecha_creacion <= ?)")
        valores.append(hoy - timedelta(days=365))
        
        # Combinar todos los filtros del histórico
        filtros.append(f"({' OR '.join(filtros_hist)})")

        if tipo:
            filtros.append("categoria = ?")
            valores.append(tipo)
        if estado == 'completado':
            filtros.append("completado = 1")
        elif estado == 'vencido':
            filtros.append("completado = 0 AND fecha_fin IS NOT NULL AND fecha_fin < ?")
            valores.append(hoy)
        if fecha_inicio:
            filtros.append("fecha_creacion >= ?")
            valores.append(fecha_inicio)
        if fecha_fin:
            filtros.append("fecha_creacion <= ?")
            valores.append(fecha_fin)
        if q:
            filtros.append("(titulo LIKE ? OR descripcion LIKE ? OR etiquetas LIKE ?)")
            valores.extend([f'%{q}%', f'%{q}%', f'%{q}%'])

        where_clause = ' AND '.join(filtros)
        sql = f'''
            SELECT id, titulo, descripcion, prioridad, categoria, completado, fecha_creacion, fecha_completado, objetivo_padre_id, es_padre, estado, fecha_inicio, fecha_fin, horas_estimadas, recompensa, recurrente
            FROM objetivos
            WHERE {where_clause}
            ORDER BY fecha_creacion DESC
        '''
        # Log de depuración para ver la consulta y los valores
        print('SQL HISTORICOS:', sql)
        print('VALORES HISTORICOS:', valores)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(valores))
            rows = cursor.fetchall()
            objetivos = [
            {
                'id': row[0],
                'titulo': row[1],
                'descripcion': row[2],
                'prioridad': row[3],
                'categoria': row[4],
                'completado': bool(row[5]),
                'fecha_creacion': row[6].strftime('%Y-%m-%d') if row[6] else None,
                'fecha_completado': row[7].strftime('%Y-%m-%d') if row[7] else None,
                'objetivo_padre_id': row[8],
                'es_padre': bool(row[9]),
                'estado': row[10],
                'fecha_inicio': row[11].strftime('%Y-%m-%d') if row[11] else None,
                'fecha_fin': row[12].strftime('%Y-%m-%d') if row[12] else None,
                'horas_estimadas': row[13],
                'recompensa': row[14],
                'recurrente': bool(row[15])
            }
            for row in rows
        ]
        paginados = objetivos[offset:offset+limit]
        return jsonify(paginados)
    except Exception as e:
        logger.error(f"Error en objetivos_historico: {str(e)}")
        return jsonify({'error': 'Error al obtener histórico de objetivos'}), 500

def reset_objetivos_diarios_recurrentes():
    """
    Desmarca automáticamente todos los objetivos diarios recurrentes al inicio de cada día.
    Esta función se ejecuta automáticamente a medianoche.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Desmarcar todos los objetivos diarios recurrentes que estén completados
            cursor.execute("""
                UPDATE objetivos 
                SET completado = 0, fecha_completado = NULL
                WHERE LOWER(COALESCE(categoria,'')) = 'diario'
                AND COALESCE(recurrente, 0) = 1
                AND completado = 1
                AND COALESCE(estado,'') <> 'histórico'
            """)
            
            objetivos_desmarcados = cursor.rowcount
            conn.commit()
            
            logger.info(f"Reset automático completado: {objetivos_desmarcados} objetivos diarios recurrentes desmarcados.")
            
    except Exception as e:
        logger.error(f"Error en reset automático de objetivos diarios: {str(e)}")

# --- Scheduler para notificaciones automáticas ---
def start_scheduler():
    from datetime import datetime
    scheduler = BackgroundScheduler(timezone="America/Bogota")
    
    # Ejecutar reset de objetivos diarios a las 00:00 todos los días
    scheduler.add_job(reset_objetivos_diarios_recurrentes, 'cron', hour=0, minute=0, id='reset_objetivos_diarios')
    
    # Ejecutar verificación de proyecciones a las 00:00 y 12:00 todos los días
    scheduler.add_job(verificar_proyecciones_comienzo, 'cron', hour=0, minute=1, id='notificacion_medianoche')
    scheduler.add_job(verificar_proyecciones_comienzo, 'cron', hour=12, minute=0, id='notificacion_mediodia')
    
    scheduler.start()
    print("[Scheduler] Tareas programadas:")
    print("  - Reset objetivos diarios recurrentes: 00:00 todos los días")
    print("  - Notificaciones de proyecciones: 00:01 y 12:00 todos los días")

@app.route('/api/objetivos/<int:objetivo_id>/saltar', methods=['POST'])
@login_required
def api_saltar_objetivo(objetivo_id):
    from datetime import datetime
    hoy = datetime.now().date()
    user_id = current_user.id
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Verificar si ya existe un salto para este objetivo y fecha
        cursor.execute('''SELECT id FROM objetivos_saltados WHERE objetivo_id = ? AND user_id = ? AND fecha_saltada = ?''', (objetivo_id, user_id, hoy))
        if cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Ya saltaste este objetivo hoy'}), 400
        # Insertar el salto
        cursor.execute('''INSERT INTO objetivos_saltados (objetivo_id, user_id, fecha_saltada) VALUES (?, ?, ?)''', (objetivo_id, user_id, hoy))
        conn.commit()
    return jsonify({'status': 'success', 'message': 'Objetivo saltado para hoy'})

@app.route('/api/objetivos/<int:objetivo_id>/reactivar_hoy', methods=['POST'])
@login_required
def api_reactivar_objetivo_hoy(objetivo_id):
    from datetime import datetime
    hoy = datetime.now().date()
    user_id = current_user.id
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM objetivos_saltados WHERE objetivo_id = ? AND user_id = ? AND fecha_saltada = ?''', (objetivo_id, user_id, hoy))
        conn.commit()
    return jsonify({'status': 'success', 'message': 'Objetivo reactivado para hoy'})

@app.route('/api/objetivos/<int:objetivo_id>/subobjetivos', methods=['GET'])
@login_required
def api_list_subobjetivos(objetivo_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT id, titulo, completado, fecha_creacion, orden, tiempo_focus, notas FROM subobjetivos WHERE objetivo_id = ? ORDER BY orden ASC, id ASC''', (objetivo_id,))
        rows = cursor.fetchall()
        subobjetivos = [
            {
                'id': row[0],
                'titulo': row[1],
                'completado': bool(row[2]),
                'fecha_creacion': row[3].strftime('%Y-%m-%d %H:%M') if row[3] else None,
                'orden': row[4],
                'tiempo_focus': row[5] if row[5] else 0,
                'notas': row[6] if row[6] else ''
            }
            for row in rows
        ]
        return jsonify(subobjetivos)

@app.route('/api/objetivos/<int:objetivo_id>/subobjetivos', methods=['POST'])
@login_required
def api_create_subobjetivo(objetivo_id):
    data = request.get_json()
    titulo = data.get('titulo', '').strip()
    if not titulo:
        return jsonify({'error': 'El título es obligatorio'}), 400
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Validar que no exista un subobjetivo con el mismo título para este objetivo
        cursor.execute('''SELECT id FROM subobjetivos WHERE objetivo_id = ? AND LOWER(titulo) = LOWER(?)''', (objetivo_id, titulo))
        if cursor.fetchone():
            return jsonify({'error': 'Ya existe un subobjetivo con ese título'}), 400
        # Obtener el mayor valor de orden actual
        cursor.execute('''SELECT COALESCE(MAX(orden), 0) FROM subobjetivos WHERE objetivo_id = ?''', (objetivo_id,))
        max_orden = cursor.fetchone()[0]
        nuevo_orden = max_orden + 1
        cursor.execute('''INSERT INTO subobjetivos (objetivo_id, titulo, completado, orden) VALUES (?, ?, 0, ?)''', (objetivo_id, titulo, nuevo_orden))
        conn.commit()
        return jsonify({'status': 'success'})

@app.route('/api/objetivos/<int:objetivo_id>/subobjetivos/reordenar', methods=['POST'])
@login_required
def api_reordenar_subobjetivos(objetivo_id):
    data = request.get_json()
    ids = data.get('ids', [])
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return jsonify({'error': 'Formato de datos inválido'}), 400
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for orden, sub_id in enumerate(ids):
            cursor.execute('''UPDATE subobjetivos SET orden = ? WHERE id = ? AND objetivo_id = ?''', (orden + 1, sub_id, objetivo_id))
        conn.commit()
    return jsonify({'status': 'success'})

@app.route('/api/subobjetivos/<int:subobjetivo_id>', methods=['PATCH'])
@login_required
def api_update_subobjetivo(subobjetivo_id):
    data = request.get_json()
    print(f"🔍 PATCH subobjetivo {subobjetivo_id} - Data recibida: {data}")
    
    campos = []
    valores = []
    completado_changed = False
    nuevo_completado = None
    
    if 'titulo' in data:
        campos.append('titulo = ?')
        valores.append(data['titulo'].strip())
    if 'completado' in data:
        campos.append('completado = ?')
        nuevo_completado = int(bool(data['completado']))
        valores.append(nuevo_completado)
        completado_changed = True
    if 'tiempo_focus' in data:
        campos.append('tiempo_focus = ?')
        valores.append(int(data['tiempo_focus']))
        print(f"💾 Actualizando tiempo_focus a: {data['tiempo_focus']} segundos")
    if 'notas' in data:
        campos.append('notas = ?')
        valores.append(data['notas'].strip() if data['notas'] else '')
        print(f"📝 Actualizando notas: {len(data['notas'])} caracteres")
    
    if not campos:
        return jsonify({'error': 'Nada para actualizar'}), 400
    
    valores.append(subobjetivo_id)
    print(f"🔧 Query: UPDATE subobjetivos SET {', '.join(campos)} WHERE id = ?")
    print(f"🔧 Valores: {tuple(valores)}")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Obtener información del subobjetivo antes de actualizar
        cursor.execute('SELECT objetivo_id, completado FROM subobjetivos WHERE id = ?', (subobjetivo_id,))
        subobj_info = cursor.fetchone()
        if not subobj_info:
            return jsonify({'error': 'Subobjetivo no encontrado'}), 404
        
        objetivo_id, completado_actual = subobj_info
        
        # Actualizar el subobjetivo
        cursor.execute(f'''UPDATE subobjetivos SET {', '.join(campos)} WHERE id = ?''', tuple(valores))
        
        # Si cambió el estado de completado, registrar en el log
        if completado_changed:
            fecha_hoy = datetime.now().date()
            
            if nuevo_completado == 1 and completado_actual == 0:
                # Se completó el subobjetivo - agregar al log
                try:
                    cursor.execute('''
                        INSERT INTO subobjetivos_completados_log 
                        (subobjetivo_id, objetivo_id, user_id, fecha_completado)
                        VALUES (?, ?, ?, ?)
                    ''', (subobjetivo_id, objetivo_id, current_user.id, fecha_hoy))
                    print(f"📝 Subobjetivo {subobjetivo_id} registrado como completado en {fecha_hoy}")
                except Exception as e:
                    # Si ya existe el registro para hoy, no es un error crítico
                    if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e).lower():
                        print(f"ℹ️ Subobjetivo {subobjetivo_id} ya estaba registrado como completado hoy")
                    else:
                        print(f"⚠️ Error registrando completado: {e}")
                        
            elif nuevo_completado == 0 and completado_actual == 1:
                # Se descompletó el subobjetivo - remover del log de hoy
                cursor.execute('''
                    DELETE FROM subobjetivos_completados_log 
                    WHERE subobjetivo_id = ? AND user_id = ? AND fecha_completado = ?
                ''', (subobjetivo_id, current_user.id, fecha_hoy))
                print(f"🗑️ Registro de completado removido para subobjetivo {subobjetivo_id} en {fecha_hoy}")
        
        conn.commit()
        print(f"✅ Subobjetivo {subobjetivo_id} actualizado exitosamente")
        return jsonify({'status': 'success'})

@app.route('/api/subobjetivos/completados/<fecha>', methods=['GET'])
@login_required
def api_subobjetivos_completados_fecha(fecha):
    """Obtiene los subobjetivos completados en una fecha específica"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener subobjetivos completados en la fecha específica
            query = """
                SELECT s.id, s.titulo, s.objetivo_id, o.titulo as objetivo_titulo,
                       scl.fecha_completado, scl.fecha_creacion as hora_completado
                FROM subobjetivos s
                INNER JOIN subobjetivos_completados_log scl ON s.id = scl.subobjetivo_id
                INNER JOIN objetivos o ON s.objetivo_id = o.id
                WHERE scl.user_id = ? 
                  AND CAST(scl.fecha_completado AS DATE) = ?
                ORDER BY scl.fecha_creacion ASC
            """
            
            cursor.execute(query, (current_user.id, fecha))
            subobjetivos_completados = []
            
            for row in cursor.fetchall():
                subobjetivos_completados.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'objetivo_id': row.objetivo_id,
                    'objetivo_titulo': row.objetivo_titulo,
                    'fecha_completado': row.fecha_completado.strftime('%Y-%m-%d') if row.fecha_completado else None,
                    'hora_completado': row.hora_completado.strftime('%H:%M:%S') if row.hora_completado else None
                })
            
            return jsonify({
                'status': 'success',
                'fecha': fecha,
                'subobjetivos_completados': subobjetivos_completados,
                'total': len(subobjetivos_completados)
            })
            
    except Exception as e:
        logger.error(f"Error obteniendo subobjetivos completados para {fecha}: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/subobjetivos/<int:subobjetivo_id>', methods=['DELETE'])
@login_required
def api_delete_subobjetivo(subobjetivo_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM subobjetivos WHERE id = ?''', (subobjetivo_id,))
        conn.commit()
        return jsonify({'status': 'success'})

# =============================
# Endpoints para Objetivos Programados
# =============================

@app.route('/api/objetivos/programados/mañana', methods=['GET'])
@login_required
def api_objetivos_programados_mañana():
    """Obtener objetivos programados para mañana"""
    try:
        from datetime import datetime, timedelta
        mañana = (datetime.now() + timedelta(days=1)).date()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, titulo, descripcion, categoria, prioridad, parte_dia, 
                       horas_estimadas, fecha_programada, programado_para,
                       CONVERT(varchar, fecha_creacion, 120) as fecha_creacion
                FROM objetivos 
                WHERE user_id = ? 
                AND (fecha_programada = ? OR programado_para = 'mañana')
                AND completado = 0
                ORDER BY 
                    CASE prioridad 
                        WHEN 'alta' THEN 1 
                        WHEN 'media' THEN 2 
                        WHEN 'baja' THEN 3 
                        ELSE 4 
                    END,
                    fecha_creacion DESC
            """, (current_user.id, mañana))
            
            objetivos = []
            for row in cursor.fetchall():
                objetivos.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'categoria': row.categoria,
                    'prioridad': row.prioridad,
                    'parte_dia': row.parte_dia,
                    'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                    'fecha_programada': row.fecha_programada.isoformat() if row.fecha_programada else None,
                    'programado_para': row.programado_para,
                    'fecha_creacion': row.fecha_creacion
                })
            
            return jsonify({
                'status': 'success',
                'objetivos': objetivos,
                'fecha_mañana': mañana.isoformat(),
                'total': len(objetivos)
            })
            
    except Exception as e:
        logger.error(f"Error al obtener objetivos programados para mañana: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/objetivos/programados/todos', methods=['GET'])
@login_required
def api_objetivos_programados_todos():
    """Obtener todos los objetivos programados"""
    try:
        from datetime import datetime
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, titulo, descripcion, categoria, prioridad, parte_dia, 
                       horas_estimadas, fecha_programada, programado_para,
                       CONVERT(varchar, fecha_creacion, 120) as fecha_creacion
                FROM objetivos 
                WHERE user_id = ? 
                AND (fecha_programada IS NOT NULL OR programado_para IS NOT NULL)
                AND completado = 0
                ORDER BY 
                    fecha_programada ASC,
                    CASE prioridad 
                        WHEN 'alta' THEN 1 
                        WHEN 'media' THEN 2 
                        WHEN 'baja' THEN 3 
                        ELSE 4 
                    END,
                    fecha_creacion DESC
            """, (current_user.id,))
            
            objetivos = []
            for row in cursor.fetchall():
                objetivos.append({
                    'id': row.id,
                    'titulo': row.titulo,
                    'descripcion': row.descripcion,
                    'categoria': row.categoria,
                    'prioridad': row.prioridad,
                    'parte_dia': row.parte_dia,
                    'horas_estimadas': float(row.horas_estimadas) if row.horas_estimadas else None,
                    'fecha_programada': row.fecha_programada.isoformat() if row.fecha_programada else None,
                    'programado_para': row.programado_para,
                    'fecha_creacion': row.fecha_creacion
                })
            
            return jsonify({
                'status': 'success',
                'objetivos': objetivos,
                'total': len(objetivos)
            })
            
    except Exception as e:
        logger.error(f"Error al obtener objetivos programados: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/objetivos/<int:objetivo_id>/programar', methods=['POST'])
@login_required
def api_programar_objetivo(objetivo_id):
    """Programar un objetivo para mañana"""
    try:
        data = request.get_json()
        programar_para = data.get('programar_para', 'mañana')  # 'mañana' o 'fecha_especifica'
        fecha_especifica = data.get('fecha_especifica')  # Solo si programar_para es 'fecha_especifica'
        
        print(f"🚀 INICIO - Programando objetivo {objetivo_id} para {programar_para}")
        logger.info(f"📅 Programando objetivo {objetivo_id} para {programar_para}")
        
        from datetime import datetime, timedelta
        
        # Determinar la fecha programada
        if programar_para == 'mañana':
            fecha_programada = (datetime.now() + timedelta(days=1)).date()
        elif programar_para == 'fecha_especifica' and fecha_especifica:
            try:
                fecha_programada = datetime.strptime(fecha_especifica, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Formato de fecha inválido'}), 400
        else:
            return jsonify({'status': 'error', 'message': 'Parámetros de programación inválidos'}), 400
        
        print(f"📅 FECHA CALCULADA: {fecha_programada}")
        logger.info(f"📅 Fecha programada calculada: {fecha_programada}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que el objetivo existe y pertenece al usuario
            cursor.execute("""
                SELECT id, titulo FROM objetivos 
                WHERE id = ? AND user_id = ?
            """, (objetivo_id, current_user.id))
            
            objetivo = cursor.fetchone()
            if not objetivo:
                logger.warning(f"❌ Objetivo {objetivo_id} no encontrado para usuario {current_user.id}")
                return jsonify({'status': 'error', 'message': 'Objetivo no encontrado'}), 404
            
            logger.info(f"✅ Objetivo encontrado: {objetivo.titulo}")
            
            # Actualizar el objetivo con la programación
            cursor.execute("""
                UPDATE objetivos 
                SET fecha_programada = ?, programado_para = ?
                WHERE id = ? AND user_id = ?
            """, (fecha_programada, programar_para, objetivo_id, current_user.id))
            
            rows_affected = cursor.rowcount
            print(f"📝 FILAS ACTUALIZADAS: {rows_affected}")
            logger.info(f"📝 Filas actualizadas: {rows_affected}")
            
            conn.commit()
            
            # Verificar que se actualizó correctamente
            cursor.execute("""
                SELECT fecha_programada, programado_para FROM objetivos 
                WHERE id = ? AND user_id = ?
            """, (objetivo_id, current_user.id))
            
            verificacion = cursor.fetchone()
            logger.info(f"🔍 Verificación - Fecha: {verificacion.fecha_programada}, Programado para: {verificacion.programado_para}")
            
            return jsonify({
                'status': 'success',
                'message': f'Objetivo "{objetivo.titulo}" programado para {fecha_programada.isoformat()}',
                'fecha_programada': fecha_programada.isoformat(),
                'programado_para': programar_para
            })
            
    except Exception as e:
        logger.error(f"❌ Error al programar objetivo: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/objetivos/<int:objetivo_id>/desprogramar', methods=['POST'])
@login_required
def api_desprogramar_objetivo(objetivo_id):
    """Quitar la programación de un objetivo (volver a hoy)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que el objetivo existe y pertenece al usuario
            cursor.execute("""
                SELECT id, titulo FROM objetivos 
                WHERE id = ? AND user_id = ?
            """, (objetivo_id, current_user.id))
            
            objetivo = cursor.fetchone()
            if not objetivo:
                return jsonify({'status': 'error', 'message': 'Objetivo no encontrado'}), 404
            
            # Quitar la programación
            cursor.execute("""
                UPDATE objetivos 
                SET fecha_programada = NULL, programado_para = NULL
                WHERE id = ? AND user_id = ?
            """, (objetivo_id, current_user.id))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Objetivo "{objetivo.titulo}" desprogramado (vuelve a hoy)'
            })
            
    except Exception as e:
        logger.error(f"Error al desprogramar objetivo: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Configuración de la aplicación
# === RUTA PARA GESTIÓN DE CATEGORÍAS ===

@app.route('/gestion-categorias')
@login_required
def gestion_categorias():
    """Página de gestión de categorías y subcategorías"""
    return render_template('gestion_categorias.html')

# ===========================================
# API PARA GESTIÓN DE CATEGORÍAS
# ===========================================

@app.route('/api/categorias', methods=['GET'])
@login_required
def api_list_categorias():
    """Obtener todas las categorías del usuario"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si la tabla de categorías existe
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'categorias'
            """)
            
            if cursor.fetchone().count == 0:
                # Si la tabla no existe, devolver lista vacía
                return jsonify({
                    'status': 'success',
                    'data': {
                        'categorias': [],
                        'subcategorias': []
                    }
                })
            
            # Obtener categorías activas del usuario
            cursor.execute('''
                SELECT id, nombre, fecha_creacion 
                FROM categorias 
                WHERE user_id = ? AND activa = 1
                ORDER BY nombre
            ''', (current_user.id,))
            
            categorias = [{
                'id': row[0],
                'nombre': row[1],
                'fecha_creacion': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else None
            } for row in cursor.fetchall()]
            
            # Obtener todas las subcategorías activas del usuario (de categorías activas)
            cursor.execute('''
                SELECT s.id, s.nombre, s.categoria_id, s.fecha_creacion 
                FROM subcategorias s
                INNER JOIN categorias c ON s.categoria_id = c.id
                WHERE c.user_id = ? AND c.activa = 1 AND s.activa = 1
                ORDER BY s.nombre
            ''', (current_user.id,))
            
            subcategorias = [{
                'id': row[0],
                'nombre': row[1],
                'categoria_id': row[2],
                'fecha_creacion': row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None
            } for row in cursor.fetchall()]
            
            return jsonify({
                'status': 'success',
                'data': {
                    'categorias': categorias,
                    'subcategorias': subcategorias
                }
            })
            
    except Exception as e:
        logger.error(f"Error al obtener categorías: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener las categorías',
            'error': str(e)
        }), 500

@app.route('/api/categorias/gestion', methods=['GET'])
@login_required
def api_list_categorias_gestion():
    """Obtener todas las categorías del usuario para gestión (incluye activas e inactivas)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener categorías del usuario con estado activo
            cursor.execute('''
                SELECT id, nombre, activa, fecha_creacion 
                FROM categorias 
                WHERE user_id = ?
                ORDER BY nombre
            ''', (current_user.id,))
            
            categorias = [{
                'id': row[0],
                'nombre': row[1],
                'activa': bool(row[2]),
                'fecha_creacion': row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None
            } for row in cursor.fetchall()]
            
            # Obtener todas las subcategorías del usuario con estado activo
            cursor.execute('''
                SELECT s.id, s.nombre, s.categoria_id, s.activa, s.fecha_creacion, c.nombre as categoria_nombre
                FROM subcategorias s
                INNER JOIN categorias c ON s.categoria_id = c.id
                WHERE c.user_id = ?
                ORDER BY c.nombre, s.nombre
            ''', (current_user.id,))
            
            subcategorias = [{
                'id': row[0],
                'nombre': row[1],
                'categoria_id': row[2],
                'activa': bool(row[3]),
                'fecha_creacion': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None,
                'categoria_nombre': row[5]
            } for row in cursor.fetchall()]
            
            return jsonify({
                'status': 'success',
                'data': {
                    'categorias': categorias,
                    'subcategorias': subcategorias
                }
            })
            
    except Exception as e:
        logger.error(f"Error al obtener categorías para gestión: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener las categorías',
            'error': str(e)
        }), 500

@app.route('/api/categorias', methods=['POST'])
@login_required
def api_create_categoria():
    """Crear una nueva categoría"""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        
        if not nombre:
            return jsonify({'error': 'El nombre de la categoría es obligatorio'}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si ya existe una categoría con el mismo nombre para este usuario
            cursor.execute('''
                SELECT id FROM categorias 
                WHERE user_id = ? AND LOWER(nombre) = LOWER(?)
            ''', (current_user.id, nombre))
            
            if cursor.fetchone() is not None:
                return jsonify({'error': 'Ya existe una categoría con este nombre'}), 400
            
            # Crear la nueva categoría
            cursor.execute('''
                INSERT INTO categorias (user_id, nombre, fecha_creacion)
                OUTPUT INSERTED.id, INSERTED.nombre, INSERTED.fecha_creacion
                VALUES (?, ?, GETDATE())
            ''', (current_user.id, nombre))
            
            row = cursor.fetchone()
            conn.commit()
            
            categoria = {
                'id': row[0],
                'nombre': row[1],
                'fecha_creacion': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else None,
                'subcategorias': []
            }

            return jsonify({'status': 'success', 'data': categoria}), 201
            
    except Exception as e:
        logger.error(f"Error al crear categoría: {str(e)}")
        return jsonify({'error': 'Error al crear categoría'}), 500


@app.route('/api/categorias/estadisticas', methods=['GET'])
@login_required
def api_categorias_estadisticas():
    """Devuelve estadísticas agregadas por categoría: total_frases y total_repasos ordenadas de mayor a menor"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT c.id, c.nombre,
                       COUNT(f.id) AS total_frases,
                       SUM(COALESCE(f.total_repasos, 0)) AS total_repasos
                FROM categorias c
                LEFT JOIN frases f ON f.categoria_id = c.id AND f.user_id = ?
                WHERE c.user_id = ?
                GROUP BY c.id, c.nombre
                ORDER BY SUM(COALESCE(f.total_repasos, 0)) DESC
            ''', (current_user.id, current_user.id))

            estadisticas = []
            for row in cursor.fetchall():
                estadisticas.append({
                    'id': row[0],
                    'nombre': row[1],
                    'total_frases': int(row[2]) if row[2] is not None else 0,
                    'total_repasos': int(row[3]) if row[3] is not None else 0
                })

            # Obtener estadísticas por subcategoría también
            cursor.execute('''
                SELECT s.id, s.nombre, s.categoria_id,
                       COUNT(f.id) AS total_frases,
                       SUM(COALESCE(f.total_repasos, 0)) AS total_repasos
                FROM subcategorias s
                LEFT JOIN frases f ON f.subcategoria_id = s.id AND f.user_id = ?
                WHERE s.user_id = ?
                GROUP BY s.id, s.nombre, s.categoria_id
                ORDER BY SUM(COALESCE(f.total_repasos, 0)) DESC
            ''', (current_user.id, current_user.id))

            sub_estadisticas = []
            for row in cursor.fetchall():
                sub_estadisticas.append({
                    'id': row[0],
                    'nombre': row[1],
                    'categoria_id': row[2],
                    'total_frases': int(row[3]) if row[3] is not None else 0,
                    'total_repasos': int(row[4]) if row[4] is not None else 0
                })

            return jsonify({'status': 'success', 'data': {'estadisticas': estadisticas, 'subcategorias': sub_estadisticas}})
    except Exception as e:
        logger.error(f"Error al obtener estadísticas de categorías: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error al obtener estadísticas'}), 500

@app.route('/api/categorias/<int:categoria_id>', methods=['PUT'])
@login_required
def api_update_categoria(categoria_id):
    """Actualizar una categoría existente"""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        
        if not nombre:
            return jsonify({'error': 'El nombre de la categoría es obligatorio'}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la categoría existe y pertenece al usuario
            cursor.execute('''
                SELECT id FROM categorias 
                WHERE id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))
            
            if cursor.fetchone() is None:
                return jsonify({'error': 'Categoría no encontrada'}), 404
            
            # Verificar si ya existe otra categoría con el mismo nombre
            cursor.execute('''
                SELECT id FROM categorias 
                WHERE user_id = ? AND LOWER(nombre) = LOWER(?) AND id != ?
            ''', (current_user.id, nombre, categoria_id))
            
            if cursor.fetchone() is not None:
                return jsonify({'error': 'Ya existe otra categoría con este nombre'}), 400
            
            # Actualizar la categoría
            cursor.execute('''
                UPDATE categorias 
                SET nombre = ?
                WHERE id = ? AND user_id = ?
            ''', (nombre, categoria_id, current_user.id))

            # Sincronizar el campo 'categoria' en frases
            cursor.execute('''
                UPDATE frases
                SET categoria = ?
                WHERE categoria_id = ? AND user_id = ?
            ''', (nombre, categoria_id, current_user.id))

            conn.commit()
            
            return jsonify({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error al actualizar categoría: {str(e)}")
        return jsonify({'error': 'Error al actualizar categoría'}), 500

@app.route('/api/categorias/<int:categoria_id>/toggle', methods=['POST'])
@login_required
def api_toggle_categoria(categoria_id):
    """Activar/desactivar una categoría"""
    try:
        logger.info(f"Toggle categoría {categoria_id} para usuario {current_user.id}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la categoría pertenece al usuario
            cursor.execute('''
                SELECT activa FROM categorias 
                WHERE id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"Categoría {categoria_id} no encontrada para usuario {current_user.id}")
                return jsonify({'error': 'Categoría no encontrada'}), 404
            
            # Cambiar estado
            nueva_activa = not result[0]
            logger.info(f"Cambiando categoría {categoria_id} de {result[0]} a {nueva_activa}")
            
            cursor.execute('''
                UPDATE categorias 
                SET activa = ? 
                WHERE id = ? AND user_id = ?
            ''', (nueva_activa, categoria_id, current_user.id))
            
            # Si se desactiva la categoría, también desactivar sus subcategorías
            if not nueva_activa:
                cursor.execute('''
                    UPDATE subcategorias 
                    SET activa = 0 
                    WHERE categoria_id = ? AND user_id = ?
                ''', (categoria_id, current_user.id))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'activa': nueva_activa,
                'message': f'Categoría {"activada" if nueva_activa else "desactivada"} exitosamente'
            })
            
    except Exception as e:
        logger.error(f"Error al cambiar estado de categoría {categoria_id}: {str(e)}")
        return jsonify({'error': 'Error al cambiar estado de categoría'}), 500

@app.route('/api/categorias/<int:categoria_id>', methods=['DELETE'])
@login_required
def api_delete_categoria(categoria_id):
    """Eliminar una categoría y sus subcategorías asociadas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la categoría existe y pertenece al usuario
            cursor.execute('''
                SELECT id FROM categorias 
                WHERE id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))
            
            if cursor.fetchone() is None:
                return jsonify({'error': 'Categoría no encontrada'}), 404
            
            # Verificar si la categoría tiene subcategorías
            cursor.execute('''
                SELECT COUNT(*)
                FROM subcategorias
                WHERE categoria_id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))

            if cursor.fetchone()[0] > 0:
                return jsonify({
                    'error': 'No se puede eliminar la categoría porque tiene subcategorías asociadas',
                    'code': 'CATEGORY_HAS_SUBCATEGORIES'
                }), 400
            
            # Eliminar subcategorías primero
            cursor.execute('''
                DELETE FROM subcategorias 
                WHERE categoria_id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))
            
            # Eliminar la categoría
            cursor.execute('''
                DELETE FROM categorias 
                WHERE id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))
            
            conn.commit()
            
            return jsonify({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error al eliminar categoría: {str(e)}")
        return jsonify({'error': 'Error al eliminar categoría'}), 500

# ===========================================
# API PARA GESTIÓN DE SUBCATEGORÍAS
# ===========================================

@app.route('/api/subcategorias', methods=['POST'])
@login_required
def api_create_subcategoria():
    """Crear una nueva subcategoría"""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        categoria_id = data.get('categoria_id')
        
        if not nombre:
            return jsonify({'error': 'El nombre de la subcategoría es obligatorio'}), 400
            
        if not categoria_id:
            return jsonify({'error': 'El ID de la categoría es obligatorio'}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la categoría existe y pertenece al usuario
            cursor.execute('''
                SELECT id FROM categorias 
                WHERE id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))
            
            if cursor.fetchone() is None:
                return jsonify({'error': 'Categoría no encontrada'}), 404
            
            # Verificar si ya existe una subcategoría con el mismo nombre en esta categoría
            cursor.execute('''
                SELECT id FROM subcategorias 
                WHERE user_id = ? AND categoria_id = ? AND LOWER(nombre) = LOWER(?)
            ''', (current_user.id, categoria_id, nombre))
            
            if cursor.fetchone() is not None:
                return jsonify({'error': 'Ya existe una subcategoría con este nombre en la categoría seleccionada'}), 400
            
            # Crear la nueva subcategoría
            cursor.execute('''
                INSERT INTO subcategorias (user_id, categoria_id, nombre, fecha_creacion)
                OUTPUT INSERTED.id, INSERTED.nombre, INSERTED.fecha_creacion
                VALUES (?, ?, ?, GETDATE())
            ''', (current_user.id, categoria_id, nombre))
            
            row = cursor.fetchone()
            conn.commit()
            
            subcategoria = {
                'id': row[0],
                'nombre': row[1],
                'fecha_creacion': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else None,
                'categoria_id': categoria_id
            }

            return jsonify({'status': 'success', 'data': subcategoria}), 201
            
    except Exception as e:
        logger.error(f"Error al crear subcategoría: {str(e)}")
        return jsonify({'error': 'Error al crear subcategoría'}), 500

@app.route('/api/subcategorias/<int:subcategoria_id>', methods=['PUT'])
@login_required
def api_update_subcategoria(subcategoria_id):
    """Actualizar una subcategoría existente"""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        categoria_id = data.get('categoria_id')
        
        if not nombre:
            return jsonify({'error': 'El nombre de la subcategoría es obligatorio'}), 400
            
        if not categoria_id:
            return jsonify({'error': 'El ID de la categoría es obligatorio'}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la subcategoría existe y pertenece al usuario
            cursor.execute('''
                SELECT id, categoria_id 
                FROM subcategorias 
                WHERE id = ? AND user_id = ?
            ''', (subcategoria_id, current_user.id))
            
            subcategoria = cursor.fetchone()
            if subcategoria is None:
                return jsonify({'error': 'Subcategoría no encontrada'}), 404
            
            # Verificar que la categoría existe y pertenece al usuario
            cursor.execute('''
                SELECT id FROM categorias 
                WHERE id = ? AND user_id = ?
            ''', (categoria_id, current_user.id))
            
            if cursor.fetchone() is None:
                return jsonify({'error': 'Categoría no encontrada'}), 404
            
            # Verificar si ya existe otra subcategoría con el mismo nombre en la misma categoría
            cursor.execute('''
                SELECT id FROM subcategorias 
                WHERE user_id = ? AND categoria_id = ? AND LOWER(nombre) = LOWER(?) AND id != ?
            ''', (current_user.id, categoria_id, nombre, subcategoria_id))
            
            if cursor.fetchone() is not None:
                return jsonify({'error': 'Ya existe otra subcategoría con este nombre en la categoría seleccionada'}), 400
            
            # Actualizar la subcategoría
            cursor.execute('''
                UPDATE subcategorias 
                SET nombre = ?, categoria_id = ?
                WHERE id = ? AND user_id = ?
            ''', (nombre, categoria_id, subcategoria_id, current_user.id))

            # Sincronizar el campo 'subcategoria' en frases
            cursor.execute('''
                UPDATE frases
                SET subcategoria = ?
                WHERE subcategoria_id = ? AND user_id = ?
            ''', (nombre, subcategoria_id, current_user.id))

            conn.commit()
            
            return jsonify({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error al actualizar subcategoría: {str(e)}")
        return jsonify({'error': 'Error al actualizar subcategoría'}), 500

@app.route('/api/subcategorias/<int:subcategoria_id>/toggle', methods=['POST'])
@login_required
def api_toggle_subcategoria(subcategoria_id):
    """Activar/desactivar una subcategoría"""
    try:
        logger.info(f"Toggle subcategoría {subcategoria_id} para usuario {current_user.id}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la subcategoría pertenece al usuario y obtener info de la categoría
            cursor.execute('''
                SELECT s.activa, c.activa as categoria_activa
                FROM subcategorias s
                INNER JOIN categorias c ON s.categoria_id = c.id
                WHERE s.id = ? AND s.user_id = ?
            ''', (subcategoria_id, current_user.id))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Subcategoría no encontrada'}), 404
            
            subcategoria_activa, categoria_activa = result
            
            # No permitir activar subcategoría si la categoría está desactivada
            if not categoria_activa and not subcategoria_activa:
                return jsonify({'error': 'No se puede activar la subcategoría porque su categoría está desactivada'}), 400
            
            # Cambiar estado
            nueva_activa = not subcategoria_activa
            cursor.execute('''
                UPDATE subcategorias 
                SET activa = ? 
                WHERE id = ? AND user_id = ?
            ''', (nueva_activa, subcategoria_id, current_user.id))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'activa': nueva_activa,
                'message': f'Subcategoría {"activada" if nueva_activa else "desactivada"} exitosamente'
            })
            
    except Exception as e:
        logger.error(f"Error al cambiar estado de subcategoría {subcategoria_id}: {str(e)}")
        return jsonify({'error': 'Error al cambiar estado de subcategoría'}), 500

@app.route('/api/subcategorias/<int:subcategoria_id>', methods=['DELETE'])
@login_required
def api_delete_subcategoria(subcategoria_id):
    """Eliminar una subcategoría"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la subcategoría existe y pertenece al usuario
            cursor.execute('''
                SELECT id FROM subcategorias 
                WHERE id = ? AND user_id = ?
            ''', (subcategoria_id, current_user.id))
            
            if cursor.fetchone() is None:
                return jsonify({'error': 'Subcategoría no encontrada'}), 404
            
            # Nota: Se permite eliminar subcategorías incluso si tienen frases asociadas
            # Las frases seguirán existiendo con la subcategoría como texto
            
            # Eliminar la subcategoría
            cursor.execute('''
                DELETE FROM subcategorias 
                WHERE id = ? AND user_id = ?
            ''', (subcategoria_id, current_user.id))
            
            conn.commit()
            
            return jsonify({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error al eliminar subcategoría: {str(e)}")
        return jsonify({'error': 'Error al eliminar subcategoría'}), 500

# === RUTAS PARA FRASES INSPIRACIONALES ===

@app.route('/api/frases', methods=['GET'])
@login_required
def api_list_frases():
    """Obtener todas las frases del usuario con filtros opcionales"""
    try:
        categoria = request.args.get('categoria')
        subcategoria = request.args.get('subcategoria')
        solo_activas = request.args.get('solo_activas', '1') == '1'

        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT f.id, f.texto, f.autor, c.nombre as categoria, s.nombre as subcategoria,
                       f.notas, f.total_repasos, f.ultima_vez, f.fecha_creacion, f.activa
                FROM frases f
                LEFT JOIN categorias c ON f.categoria_id = c.id AND f.user_id = c.user_id
                LEFT JOIN subcategorias s ON f.subcategoria_id = s.id AND f.user_id = s.user_id
                WHERE f.user_id = ?
            '''
            params = [current_user.id]
            if solo_activas:
                query += ' AND f.activa = 1'
            if categoria:
                query += ' AND LOWER(c.nombre) = LOWER(?)'
                params.append(categoria)
            if subcategoria:
                query += ' AND LOWER(s.nombre) = LOWER(?)'
                params.append(subcategoria)
            query += ' ORDER BY f.fecha_creacion DESC'
            cursor.execute(query, params)
            frases = []
            for row in cursor.fetchall():
                categoria_nombre = row[3] if row[3] else row[2] if row[2] else 'Sin categoría'
                frases.append({
                    'id': row[0],
                    'texto': row[1],
                    'autor': row[2],
                    'categoria': categoria_nombre,
                    'subcategoria': row[4],
                    'notas': row[5],
                    'total_repasos': row[6] or 0,
                    'ultima_vez': row[7].isoformat() if row[7] else None,
                    'fecha_creacion': row[8].isoformat() if row[8] else None,
                    'activa': row[9] if len(row) > 9 else 1
                })
            return jsonify(frases)
    except Exception as e:
        logger.error(f"Error al obtener frases: {str(e)}")
        return jsonify({'error': 'Error al obtener frases'}), 500

@app.route('/api/frases', methods=['POST'])
@login_required
def api_create_frase():
    """Crear una nueva frase"""
    try:
        data = request.get_json()

        # Resolver o crear categoría
        categoria_text = data.get('categoria') or ''
        categoria_id = None
        if categoria_text:
            # Buscar categoría existente
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM categorias
                    WHERE user_id = ? AND LOWER(nombre) = LOWER(?)
                ''', (current_user.id, categoria_text))
                row = cursor.fetchone()
                if row:
                    categoria_id = row[0]
                else:
                    # Crear categoría nueva
                    cursor.execute('''
                        INSERT INTO categorias (user_id, nombre, fecha_creacion)
                        OUTPUT INSERTED.id
                        VALUES (?, ?, GETDATE())
                    ''', (current_user.id, categoria_text))
                    row = cursor.fetchone()
                    categoria_id = row[0] if row else None

        # Resolver o crear subcategoría (requiere categoria_id)
        subcategoria_id = None
        sub_text = data.get('subcategoria') or ''
        if sub_text:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM subcategorias
                    WHERE user_id = ? AND LOWER(nombre) = LOWER(?)
                ''', (current_user.id, sub_text))
                sub_row = cursor.fetchone()
                if sub_row:
                    subcategoria_id = sub_row[0]
                else:
                    # Sólo crear subcategoría si tenemos categoria_id
                    if categoria_id:
                        cursor.execute('''
                            INSERT INTO subcategorias (user_id, categoria_id, nombre, fecha_creacion)
                            OUTPUT INSERTED.id
                            VALUES (?, ?, ?, GETDATE())
                        ''', (current_user.id, categoria_id, sub_text))
                        row = cursor.fetchone()
                        subcategoria_id = row[0] if row else None

        # Asegurar que el texto de categoría no sea NULL (la columna no admite NULL)
        categoria_text = categoria_text or ''

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO frases (user_id, texto, autor, categoria, categoria_id, subcategoria_id, notas, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_user.id,
                data['texto'],
                data.get('autor'),
                categoria_text,
                categoria_id,
                subcategoria_id,
                data.get('notas'),
                datetime.now()
            ))
            conn.commit()

        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error al crear frase: {str(e)}")
        return jsonify({'error': 'Error al crear frase'}), 500

@app.route('/api/frases/<int:frase_id>', methods=['PUT'])
@login_required
def api_update_frase(frase_id):
    """Actualizar una frase"""
    try:
        data = request.get_json()

        # Resolver o crear categoría
        categoria_text = data.get('categoria') or ''
        categoria_id = None
        if categoria_text:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM categorias
                    WHERE user_id = ? AND LOWER(nombre) = LOWER(?)
                ''', (current_user.id, categoria_text))
                row = cursor.fetchone()
                if row:
                    categoria_id = row[0]
                else:
                    cursor.execute('''
                        INSERT INTO categorias (user_id, nombre, fecha_creacion)
                        OUTPUT INSERTED.id
                        VALUES (?, ?, GETDATE())
                    ''', (current_user.id, categoria_text))
                    row = cursor.fetchone()
                    categoria_id = row[0] if row else None

        # Resolver o crear subcategoría
        subcategoria_id = None
        sub_text = data.get('subcategoria') or ''
        if sub_text:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM subcategorias
                    WHERE user_id = ? AND LOWER(nombre) = LOWER(?)
                ''', (current_user.id, sub_text))
                sub_row = cursor.fetchone()
                if sub_row:
                    subcategoria_id = sub_row[0]
                else:
                    if categoria_id:
                        cursor.execute('''
                            INSERT INTO subcategorias (user_id, categoria_id, nombre, fecha_creacion)
                            OUTPUT INSERTED.id
                            VALUES (?, ?, ?, GETDATE())
                        ''', (current_user.id, categoria_id, sub_text))
                        row = cursor.fetchone()
                        subcategoria_id = row[0] if row else None

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Verificar que la frase pertenece al usuario
            cursor.execute('SELECT user_id FROM frases WHERE id = ?', (frase_id,))
            frase = cursor.fetchone()
            if not frase or frase[0] != current_user.id:
                return jsonify({'error': 'Frase no encontrada'}), 404

            # Asegurar texto de categoría no nulo
            categoria_text = categoria_text or ''
            cursor.execute('''
                UPDATE frases
                SET texto = ?, autor = ?, categoria = ?, categoria_id = ?, subcategoria_id = ?, notas = ?
                WHERE id = ? AND user_id = ?
            ''', (
                data['texto'],
                data.get('autor'),
                categoria_text,
                categoria_id,
                subcategoria_id,
                data.get('notas'),
                frase_id,
                current_user.id
            ))
            conn.commit()

        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error al actualizar frase: {str(e)}")
        return jsonify({'error': 'Error al actualizar frase'}), 500

@app.route('/api/frases/<int:frase_id>', methods=['DELETE'])
@login_required
def api_delete_frase(frase_id):
    """Eliminar una frase"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la frase pertenece al usuario
            cursor.execute('SELECT user_id FROM frases WHERE id = ?', (frase_id,))
            frase = cursor.fetchone()
            if not frase or frase[0] != current_user.id:
                return jsonify({'error': 'Frase no encontrada'}), 404
            
            cursor.execute('DELETE FROM frases WHERE id = ? AND user_id = ?', (frase_id, current_user.id))
            conn.commit()
            
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error al eliminar frase: {str(e)}")
        return jsonify({'error': 'Error al eliminar frase'}), 500

@app.route('/api/frases/<int:frase_id>/repasar', methods=['POST'])
@login_required
def api_repasar_frase(frase_id):
    """Marcar una frase como repasada"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la frase pertenece al usuario
            cursor.execute('SELECT user_id FROM frases WHERE id = ?', (frase_id,))
            frase = cursor.fetchone()
            if not frase or frase[0] != current_user.id:
                return jsonify({'error': 'Frase no encontrada'}), 404
            
            # Actualizar contador y fecha de último repaso
            cursor.execute('''
                UPDATE frases 
                SET total_repasos = COALESCE(total_repasos, 0) + 1,
                    ultima_vez = ?
                WHERE id = ? AND user_id = ?
            ''', (datetime.now(), frase_id, current_user.id))
            conn.commit()
            
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error al repasar frase: {str(e)}")
        return jsonify({'error': 'Error al repasar frase'}), 500


@app.route('/api/frases/<int:frase_id>/toggle', methods=['POST'])
@login_required
def api_toggle_frase(frase_id):
    """Activar / Desactivar una frase (campo activa)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Verificar que la frase pertenece al usuario
            cursor.execute('SELECT user_id, activa FROM frases WHERE id = ?', (frase_id,))
            row = cursor.fetchone()
            if not row or row[0] != current_user.id:
                return jsonify({'error': 'Frase no encontrada'}), 404

            current_activa = row[1] if len(row) > 1 else 1
            nueva_activa = 0 if current_activa else 1

            cursor.execute('''
                UPDATE frases
                SET activa = ?
                WHERE id = ? AND user_id = ?
            ''', (nueva_activa, frase_id, current_user.id))
            conn.commit()

        return jsonify({'status': 'success', 'activa': bool(nueva_activa)})
    except Exception as e:
        logger.error(f"Error al alternar activa de frase: {str(e)}")
        return jsonify({'error': 'Error al alternar estado de la frase'}), 500

@app.route('/api/frases/repasar-todas', methods=['POST'])
@login_required
def api_repasar_todas_frases():
    """Marcar todas las frases como repasadas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Actualizar todas las frases del usuario
            cursor.execute('''
                UPDATE frases 
                SET total_repasos = COALESCE(total_repasos, 0) + 1,
                    ultima_vez = ?
                WHERE user_id = ?
            ''', (datetime.now(), current_user.id))
            
            # Obtener el número de frases actualizadas
            cursor.execute('SELECT COUNT(*) FROM frases WHERE user_id = ?', (current_user.id,))
            count = cursor.fetchone()[0]
            
            conn.commit()
            
        return jsonify({'status': 'success', 'count': count})
    except Exception as e:
        logger.error(f"Error al repasar todas las frases: {str(e)}")
        return jsonify({'error': 'Error al repasar frases'}), 500

@app.route('/api/frases/categorias', methods=['GET'])
@login_required
def api_list_categorias_frases():
    """Obtener categorías y subcategorías del usuario para filtros de frases.
    Query params opcionales: categoria (para listar subcategorías específicas)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Categorías principales activas (de la tabla categorias para obtener las categorías reales)
            cursor.execute('''
                SELECT id, nombre
                FROM categorias
                WHERE user_id = ? AND activa = 1
                ORDER BY nombre
            ''', (current_user.id,))
            categorias_data = cursor.fetchall()
            cats = [row[1] for row in categorias_data]  # Obtener nombres de categorías reales

            # Subcategorías (opcionalmente filtradas por categoria)
            categoria_filter = request.args.get('categoria')
            if categoria_filter:
                # Obtener el ID de la categoría seleccionada
                cursor.execute('''
                    SELECT id FROM categorias
                    WHERE user_id = ? AND LOWER(nombre) = LOWER(?)
                ''', (current_user.id, categoria_filter))
                categoria_row = cursor.fetchone()

                if categoria_row:
                    categoria_id = categoria_row[0]
                    cursor.execute('''
                        SELECT DISTINCT COALESCE(s.nombre,'') AS sub
                        FROM subcategorias s
                        WHERE s.user_id = ? AND s.categoria_id = ? AND s.activa = 1
                    ''', (current_user.id, categoria_id))
                    subs = [row[0] for row in cursor.fetchall() if (row[0] or '').strip() != '']
                else:
                    subs = []
                subs.sort()
            else:
                # Todas las subcategorías activas del usuario
                cursor.execute('''
                    SELECT DISTINCT COALESCE(s.nombre,'') AS sub
                    FROM subcategorias s
                    INNER JOIN categorias c ON s.categoria_id = c.id
                    WHERE s.user_id = ? AND s.activa = 1 AND c.activa = 1
                ''', (current_user.id,))
                subs = [row[0] for row in cursor.fetchall() if (row[0] or '').strip() != '']
                subs.sort()

            return jsonify({'categorias': cats, 'subcategorias': subs})
    except Exception as e:
        logger.error(f"Error al obtener categorías: {str(e)}")
        return jsonify({'error': 'Error al obtener categorías'}), 500

@app.route('/api/frases/repasar_filtradas', methods=['POST'])
@login_required
def api_repasar_frases_filtradas():
    """Repasar frases filtradas por categoría y/o subcategoría"""
    try:
        data = request.get_json()
        categoria = data.get('categoria')
        subcategoria = data.get('subcategoria')

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Construir query con filtros usando nombres reales de categorías
            query = '''
                SELECT f.id FROM frases f
                LEFT JOIN categorias c ON f.categoria_id = c.id AND f.user_id = c.user_id
                LEFT JOIN subcategorias s ON f.subcategoria_id = s.id AND f.user_id = s.user_id
                WHERE f.user_id = ?
            '''
            params = [current_user.id]

            if categoria:
                query += ' AND LOWER(c.nombre) = LOWER(?)'
                params.append(categoria)

            if subcategoria:
                query += ' AND LOWER(s.nombre) = LOWER(?)'
                params.append(subcategoria)

            cursor.execute(query, params)
            frases_ids = [row[0] for row in cursor.fetchall()]

            if not frases_ids:
                return jsonify({'repasadas': 0, 'mensaje': 'No hay frases que coincidan con los filtros'})

            # Actualizar última vez y contador de repasos
            repasadas = 0
            for frase_id in frases_ids:
                cursor.execute('''
                    UPDATE frases
                    SET ultima_vez = GETDATE(),
                        total_repasos = ISNULL(total_repasos, 0) + 1
                    WHERE id = ? AND user_id = ?
                ''', (frase_id, current_user.id))
                repasadas += 1

            conn.commit()

        return jsonify({'repasadas': repasadas})

    except Exception as e:
        logger.error(f"Error al repasar frases filtradas: {str(e)}")
        return jsonify({'error': 'Error al repasar frases'}), 500


@app.route('/api/reports/frecuencia_uso', methods=['GET'])
@login_required
def api_reports_frecuencia_uso():
    """Report: frases más/menos usadas y tendencia de uso por día.
    Query params: categoria, subcategoria, days (default 30), top_n (default 10)
    """
    try:
        categoria = request.args.get('categoria')
        subcategoria = request.args.get('subcategoria')
        days = int(request.args.get('days') or 30)
        top_n = int(request.args.get('top_n') or 10)
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        include_inactivos = str(request.args.get('include_inactivos') or '').lower() in ('1','true','yes')

        where_clauses = ['f.user_id = ?']
        params = [current_user.id]
        if not include_inactivos:
            where_clauses.append('ISNULL(f.activa,1) = 1')
        if categoria:
            where_clauses.append('LOWER(f.categoria) = LOWER(?)')
            params.append(categoria)
        if subcategoria:
            where_clauses.append('LOWER(f.subcategoria) = LOWER(?)')
            params.append(subcategoria)

        where_sql = ' AND '.join(where_clauses)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Top más usadas por total_repasos (aplicar rango de fechas a ultima_vez si se especifica)
            params_top = params.copy()
            where_top = where_sql
            if desde and hasta:
                where_top = where_top + ' AND CAST(ultima_vez AS DATE) BETWEEN ? AND ?'
                params_top = params_top + [desde, hasta]

            cursor.execute(f'''
                SELECT TOP ({top_n}) f.id, f.texto, f.autor, ISNULL(f.total_repasos,0) as total_repasos
                FROM frases f
                WHERE {where_top}
                ORDER BY ISNULL(f.total_repasos,0) DESC, f.fecha_creacion DESC
            ''', params_top)
            top_mas = [{'id': r[0], 'texto': r[1], 'autor': r[2], 'total_repasos': int(r[3])} for r in cursor.fetchall()]

            # Top menos usadas
            params_top2 = params.copy()
            where_top2 = where_sql
            if desde and hasta:
                where_top2 = where_top2 + ' AND CAST(ultima_vez AS DATE) BETWEEN ? AND ?'
                params_top2 = params_top2 + [desde, hasta]
            cursor.execute(f'''
                SELECT TOP ({top_n}) f.id, f.texto, f.autor, ISNULL(f.total_repasos,0) as total_repasos
                FROM frases f
                WHERE {where_top2}
                ORDER BY ISNULL(f.total_repasos,0) ASC, f.fecha_creacion ASC
            ''', params_top2)
            top_menos = [{'id': r[0], 'texto': r[1], 'autor': r[2], 'total_repasos': int(r[3])} for r in cursor.fetchall()]

            # Tendencia de uso: contar frases cuya ultima_vez cae dentro del rango si se especifica, o últimos N días
            if desde and hasta:
                cursor.execute(f'''
                    SELECT CAST(ultima_vez AS DATE) AS dia, COUNT(*) as cnt
                    FROM frases f
                    WHERE {where_sql} AND ultima_vez IS NOT NULL AND CAST(ultima_vez AS DATE) BETWEEN ? AND ?
                    GROUP BY CAST(ultima_vez AS DATE)
                    ORDER BY dia ASC
                ''', params + [desde, hasta])
            else:
                cursor.execute(f'''
                    SELECT CAST(ultima_vez AS DATE) AS dia, COUNT(*) as cnt
                    FROM frases f
                    WHERE {where_sql} AND ultima_vez IS NOT NULL AND ultima_vez >= DATEADD(day, -?, GETDATE())
                    GROUP BY CAST(ultima_vez AS DATE)
                    ORDER BY dia ASC
                ''', params + [days])
            trend_rows = cursor.fetchall()
            tendencia = [{'dia': str(r[0]), 'count': int(r[1])} for r in trend_rows]

        return jsonify({'top_mas': top_mas, 'top_menos': top_menos, 'tendencia': tendencia})
    except Exception as e:
        logger.error(f"Error en reporte frecuencia_uso: {str(e)}")
        return jsonify({'error': 'Error al obtener reporte'}), 500


@app.route('/api/reports/tendencias', methods=['GET'])
@login_required
def api_reports_tendencias():
    """Report: frases en tendencia (actividad reciente) y en declive.
    Heurística usada por limitación de esquema: se usa 'ultima_vez' y 'total_repasos'.
    Query params: days_recent (default 7), days_decline (default 30), top_n
    """
    try:
        days_recent = int(request.args.get('days_recent') or 7)
        days_decline = int(request.args.get('days_decline') or 30)
        top_n = int(request.args.get('top_n') or 20)
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        include_inactivos = str(request.args.get('include_inactivos') or '').lower() in ('1','true','yes')

        where_base = 'user_id = ?'
        params_base = [current_user.id]
        if not include_inactivos:
            where_base = where_base + ' AND ISNULL(activa,1) = 1'

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Frases en tendencia: tuvieron su ultima_vez en los últimos days_recent días o dentro de rango
            if desde and hasta:
                cursor.execute('''
                    SELECT TOP (?) id, texto, autor, ISNULL(total_repasos,0) as total_repasos, ultima_vez
                    FROM frases
                    WHERE %s AND ultima_vez IS NOT NULL AND CAST(ultima_vez AS DATE) BETWEEN ? AND ?
                    ORDER BY ISNULL(total_repasos,0) DESC, ultima_vez DESC
                ''' % where_base, (top_n, current_user.id, desde, hasta))
            else:
                cursor.execute('''
                    SELECT TOP (?) id, texto, autor, ISNULL(total_repasos,0) as total_repasos, ultima_vez
                    FROM frases
                    WHERE %s AND ultima_vez IS NOT NULL AND ultima_vez >= DATEADD(day, -?, GETDATE())
                    ORDER BY ISNULL(total_repasos,0) DESC, ultima_vez DESC
                ''' % where_base, (top_n, current_user.id, days_recent))
            en_tendencia = [{'id': r[0], 'texto': r[1], 'autor': r[2], 'total_repasos': int(r[3]), 'ultima_vez': r[4].isoformat() if r[4] else None} for r in cursor.fetchall()]

            # Frases en declive: no han sido repasadas en los últimos days_decline días o fuera del rango
            if desde and hasta:
                cursor.execute('''
                    SELECT TOP (?) id, texto, autor, ISNULL(total_repasos,0) as total_repasos, ultima_vez
                    FROM frases
                    WHERE %s AND (ultima_vez IS NULL OR CAST(ultima_vez AS DATE) < ?)
                    ORDER BY COALESCE(ultima_vez, '1900-01-01') ASC
                ''' % where_base, (top_n, current_user.id, desde))
            else:
                cursor.execute('''
                    SELECT TOP (?) id, texto, autor, ISNULL(total_repasos,0) as total_repasos, ultima_vez
                    FROM frases
                    WHERE %s AND (ultima_vez IS NULL OR ultima_vez < DATEADD(day, -?, GETDATE()))
                    ORDER BY COALESCE(ultima_vez, '1900-01-01') ASC
                ''' % where_base, (top_n, current_user.id, days_decline))
            en_declive = [{'id': r[0], 'texto': r[1], 'autor': r[2], 'total_repasos': int(r[3]), 'ultima_vez': r[4].isoformat() if r[4] else None} for r in cursor.fetchall()]

            # Patrones por día de la semana (basado en ultima_vez)
            cursor.execute(f'''
                SELECT DATEPART(weekday, ultima_vez) as weekday, COUNT(*) as cnt
                FROM frases
                WHERE {where_base} AND ultima_vez IS NOT NULL
                GROUP BY DATEPART(weekday, ultima_vez)
                ORDER BY weekday
            ''', tuple(params_base))
            rows = cursor.fetchall()
            patrones = [{'weekday': int(r[0]), 'count': int(r[1])} for r in rows]

        return jsonify({'en_tendencia': en_tendencia, 'en_declive': en_declive, 'patrones': patrones})
    except Exception as e:
        logger.error(f"Error en reporte tendencias: {str(e)}")
        return jsonify({'error': 'Error al obtener reporte'}), 500

def _ensure_subcategoria_schema(cursor):
    """Asegura que exista la columna subcategoria en la tabla frases y migra datos iniciales.
    - Añade columna [subcategoria] NVARCHAR(255) NULL si no existe.
    - Migra: si subcategoria es NULL y categoria tiene valor, copia categoria a subcategoria.
    - Crea índices simples para mejorar filtros por categoria/subcategoria.
    """
    # Crear columna si no existe
    cursor.execute('''
        IF NOT EXISTS (
            SELECT 1 FROM sys.columns 
            WHERE Name = N'subcategoria' AND Object_ID = Object_ID(N'frases')
        )
        BEGIN
            ALTER TABLE frases ADD subcategoria NVARCHAR(255) NULL;
        END
    ''')
    # Migrar valores existentes (una sola vez)
    cursor.execute('''
        UPDATE frases
        SET subcategoria = categoria
        WHERE subcategoria IS NULL AND categoria IS NOT NULL
    ''')
    # Índices para filtros
    cursor.execute('''
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes WHERE name = 'IX_frases_user_categoria' AND object_id = OBJECT_ID('frases')
        )
        BEGIN
            CREATE INDEX IX_frases_user_categoria ON frases(user_id, categoria);
        END
    ''')
    cursor.execute('''
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes WHERE name = 'IX_frases_user_subcategoria' AND object_id = OBJECT_ID('frases')
        )
        BEGIN
            CREATE INDEX IX_frases_user_subcategoria ON frases(user_id, subcategoria);
        END
    ''')

# ==================== RUTAS DE AUDIOS ====================

@app.route('/api/audios', methods=['GET'])
@login_required
def api_get_audios():
    """Obtener audios del usuario con filtros opcionales"""
    try:
        categoria = request.args.get('categoria', '')
        subcategoria = request.args.get('subcategoria', '')
        solo_activas = request.args.get('solo_activas', '1') == '1'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Construir query con filtros
            query = '''
                SELECT id, titulo, descripcion, archivo_nombre, archivo_url, 
                       duracion_segundos, categoria, subcategoria, notas, 
                       total_reproducciones, ultima_reproduccion, activa, fecha_creacion
                FROM audios 
                WHERE user_id = ?
            '''
            params = [current_user.id]
            
            if categoria:
                query += ' AND categoria = ?'
                params.append(categoria)
                
            if subcategoria:
                query += ' AND subcategoria = ?'
                params.append(subcategoria)
                
            if solo_activas:
                query += ' AND activa = 1'
            
            query += ' ORDER BY fecha_creacion DESC'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            audios = []
            for row in rows:
                audios.append({
                    'id': row[0],
                    'titulo': row[1],
                    'descripcion': row[2],
                    'archivo_nombre': row[3],
                    'archivo_url': f'/api/audios/{row[0]}/stream',  # Nueva URL de streaming desde BD
                    'duracion_segundos': row[5],
                    'categoria': row[6],
                    'subcategoria': row[7],
                    'notas': row[8],
                    'total_reproducciones': row[9],
                    'ultima_reproduccion': row[10].isoformat() if row[10] else None,
                    'activa': bool(row[11]),
                    'fecha_creacion': row[12].isoformat() if row[12] else None
                })
            
            return jsonify(audios)
            
    except Exception as e:
        logger.error(f"Error al obtener audios: {str(e)}")
        return jsonify({'error': 'Error al obtener audios'}), 500

@app.route('/api/audios', methods=['POST'])
@login_required
def api_create_audio():
    """Crear un nuevo audio"""
    try:
        # Verificar si se subió un archivo
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No se proporcionó archivo de audio'}), 400
        
        file = request.files['audio_file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        # Validar tipo de archivo
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.ogg'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Formato de audio no permitido. Use: MP3, WAV, M4A, OGG'}), 400
        
        # Obtener datos del formulario
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria = request.form.get('categoria', '').strip()
        subcategoria = request.form.get('subcategoria', '').strip()
        notas = request.form.get('notas', '').strip()
        
        if not titulo:
            return jsonify({'error': 'El título es requerido'}), 400
        
        # Leer el contenido binario del archivo
        file.seek(0)  # Asegurar que estamos al inicio del archivo
        contenido_binario = file.read()
        
        # Determinar tipo MIME
        tipo_mime_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg'
        }
        tipo_mime = tipo_mime_map.get(file_ext, 'audio/mpeg')
        
        # Generar ID único para el audio
        import uuid
        audio_uuid = uuid.uuid4().hex
        
        # Guardar en base de datos con contenido binario
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audios (user_id, titulo, descripcion, archivo_nombre, 
                                  categoria, subcategoria, notas, contenido_binario, tipo_mime)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (current_user.id, titulo, descripcion, file.filename, 
                  categoria, subcategoria, notas, contenido_binario, tipo_mime))
            
            audio_id = cursor.fetchone()[0]
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Audio creado exitosamente',
                'audio_id': audio_id
            })
            
    except Exception as e:
        logger.error(f"Error al crear audio: {str(e)}")
        return jsonify({'error': 'Error al crear audio'}), 500

@app.route('/api/audios/<int:audio_id>', methods=['PUT'])
@login_required
def api_update_audio(audio_id):
    """Actualizar un audio existente"""
    try:
        data = request.get_json()
        
        titulo = data.get('titulo', '').strip()
        descripcion = data.get('descripcion', '').strip()
        categoria = data.get('categoria', '').strip()
        subcategoria = data.get('subcategoria', '').strip()
        notas = data.get('notas', '').strip()
        
        if not titulo:
            return jsonify({'error': 'El título es requerido'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE audios 
                SET titulo = ?, descripcion = ?, categoria = ?, subcategoria = ?, notas = ?
                WHERE id = ? AND user_id = ?
            ''', (titulo, descripcion, categoria, subcategoria, notas, audio_id, current_user.id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Audio no encontrado'}), 404
            
            conn.commit()
            return jsonify({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error al actualizar audio: {str(e)}")
        return jsonify({'error': 'Error al actualizar audio'}), 500

@app.route('/api/audios/<int:audio_id>', methods=['DELETE'])
@login_required
def api_delete_audio(audio_id):
    """Eliminar un audio"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener información del archivo antes de eliminar
            cursor.execute('''
                SELECT archivo_url FROM audios 
                WHERE id = ? AND user_id = ?
            ''', (audio_id, current_user.id))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Audio no encontrado'}), 404
            
            archivo_url = result[0]
            
            # Eliminar de la base de datos
            cursor.execute('''
                DELETE FROM audios 
                WHERE id = ? AND user_id = ?
            ''', (audio_id, current_user.id))
            
            conn.commit()
            
            # Intentar eliminar el archivo físico
            try:
                file_path = os.path.join('daily_questions_app', archivo_url.lstrip('/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo físico: {str(e)}")
            
            return jsonify({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error al eliminar audio: {str(e)}")
        return jsonify({'error': 'Error al eliminar audio'}), 500

@app.route('/api/audios/<int:audio_id>/toggle', methods=['POST'])
@login_required
def api_toggle_audio_activa(audio_id):
    """Alternar estado activa de un audio"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener estado actual
            cursor.execute('''
                SELECT activa FROM audios 
                WHERE id = ? AND user_id = ?
            ''', (audio_id, current_user.id))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Audio no encontrado'}), 404
            
            # Alternar estado
            nueva_activa = not result[0]
            
            cursor.execute('''
                UPDATE audios 
                SET activa = ?
                WHERE id = ? AND user_id = ?
            ''', (nueva_activa, audio_id, current_user.id))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'activa': nueva_activa
            })
            
    except Exception as e:
        logger.error(f"Error al alternar estado de audio {audio_id}: {str(e)}")
        return jsonify({'error': 'Error al cambiar estado del audio'}), 500

@app.route('/api/audios/<int:audio_id>/reproducir', methods=['POST'])
@login_required
def api_reproducir_audio(audio_id):
    """Registrar reproducción de un audio"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE audios 
                SET total_reproducciones = total_reproducciones + 1,
                    ultima_reproduccion = GETDATE()
                WHERE id = ? AND user_id = ?
            ''', (audio_id, current_user.id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Audio no encontrado'}), 404
            
            conn.commit()
            return jsonify({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error al registrar reproducción: {str(e)}")
        return jsonify({'error': 'Error al registrar reproducción'}), 500

@app.route('/api/audios/<int:audio_id>/stream', methods=['GET'])
@login_required
def api_stream_audio(audio_id):
    """Servir archivo de audio desde la base de datos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT contenido_binario, tipo_mime, archivo_nombre
                FROM audios 
                WHERE id = ? AND user_id = ?
            ''', (audio_id, current_user.id))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Audio no encontrado'}), 404
            
            contenido_binario, tipo_mime, archivo_nombre = result
            
            if not contenido_binario:
                return jsonify({'error': 'Contenido de audio no disponible'}), 404
            
            # Crear respuesta con el contenido binario
            from flask import Response
            response = Response(
                contenido_binario,
                mimetype=tipo_mime or 'audio/mpeg',
                headers={
                    'Content-Disposition': f'inline; filename="{archivo_nombre}"',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(len(contenido_binario))
                }
            )
            
            return response
            
    except Exception as e:
        logger.error(f"Error al servir audio {audio_id}: {str(e)}")
        return jsonify({'error': 'Error al servir audio'}), 500

@app.route('/api/audios/categorias', methods=['GET'])
@login_required
def api_get_categorias_audios():
    """Obtener categorías y subcategorías que tienen audios asociados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener categorías que tienen audios
            cursor.execute('''
                SELECT DISTINCT categoria 
                FROM audios 
                WHERE user_id = ? AND categoria IS NOT NULL AND categoria != ''
                ORDER BY categoria
            ''', (current_user.id,))
            
            categorias = [row[0] for row in cursor.fetchall()]
            
            # Obtener subcategorías que tienen audios
            cursor.execute('''
                SELECT DISTINCT subcategoria 
                FROM audios 
                WHERE user_id = ? AND subcategoria IS NOT NULL AND subcategoria != ''
                ORDER BY subcategoria
            ''', (current_user.id,))
            
            subcategorias = [row[0] for row in cursor.fetchall()]
            
            return jsonify({
                'categorias': categorias,
                'subcategorias': subcategorias
            })
            
    except Exception as e:
        logger.error(f"Error al obtener categorías de audios: {str(e)}")
        return jsonify({'error': 'Error al obtener categorías'}), 500

@app.route('/api/audios/subcategorias', methods=['GET'])
@login_required
def api_get_subcategorias_audios():
    """Obtener subcategorías que tienen audios asociados para una categoría específica"""
    try:
        categoria = request.args.get('categoria', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if categoria:
                # Obtener subcategorías para una categoría específica que tienen audios
                cursor.execute('''
                    SELECT DISTINCT subcategoria 
                    FROM audios 
                    WHERE user_id = ? AND categoria = ? AND subcategoria IS NOT NULL AND subcategoria != ''
                    ORDER BY subcategoria
                ''', (current_user.id, categoria))
            else:
                # Obtener todas las subcategorías que tienen audios
                cursor.execute('''
                    SELECT DISTINCT subcategoria 
                    FROM audios 
                    WHERE user_id = ? AND subcategoria IS NOT NULL AND subcategoria != ''
                    ORDER BY subcategoria
                ''', (current_user.id,))
            
            subcategorias = [row[0] for row in cursor.fetchall()]
            
            return jsonify({
                'subcategorias': subcategorias
            })
            
    except Exception as e:
        logger.error(f"Error al obtener subcategorías de audios: {str(e)}")
        return jsonify({'error': 'Error al obtener subcategorías'}), 500

if __name__ == '__main__':
    start_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=True)
