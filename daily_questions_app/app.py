from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
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
                    conn_str = (
                        f"DRIVER={{{driver}}};"
                        "SERVER=localhost;"
                        "DATABASE=DailyQuestions;"
                        "Trusted_Connection=yes;"
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
    def __init__(self, id, text, type, options, active, created_at, assigned_user_id=None, descripcion=None, is_required=0, categoria='General'):
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

    @classmethod
    def get_all(cls):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, text, type, options, active, created_at, assigned_user_id, descripcion, is_required, categoria FROM question')
            questions = [cls(*row) for row in cursor.fetchall()]
            return questions

    @classmethod
    def get_by_user(cls, user_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, text, type, options, active, created_at, assigned_user_id, descripcion, is_required, categoria '
                'FROM question WHERE assigned_user_id = ? AND active = 1',
                (user_id,)
            )
            rows = cursor.fetchall()
            questions = [cls(*row) for row in rows]
            return questions

    @classmethod
    def create(cls, text, type, options=None, assigned_user_id=None, descripcion=None, is_required=0, categoria='General', active=1):
        try:
            logger.info(f"[DEBUG] Ejecutando INSERT: text={text}, type={type}, options={options}, assigned_user_id={assigned_user_id}, descripcion={descripcion}, is_required={is_required}, categoria={categoria}, active={active}")
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO question (text, type, options, assigned_user_id, descripcion, is_required, categoria, active, created_at) OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE())',
                    (text, type, options, assigned_user_id, descripcion, is_required, categoria, active)
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
    questions = Question.get_by_user(current_user.id)
    return render_template('index.html', questions=questions, date=datetime.now())

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
                    # Consulta completa para obtener preguntas
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
                            [categoria]
                        FROM [question] q
                        WHERE q.[assigned_user_id] = ? 
                        ORDER BY q.[created_at] DESC
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
                                categoria=row[9] if len(row) > 9 else 'General'
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
            text = request.form.get('text', '').strip()
            type = request.form.get('type', 'text')
            options = request.form.get('options', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            is_required = 1 if request.form.get('is_required') == 'on' else 0
            active = 1 if request.form.get('active') == 'on' else 0
            categoria = request.form.get('categoria_existente', '').strip()
            nueva_categoria = request.form.get('nueva_categoria', '').strip()
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
        logger.info(f"[DEBUG] Valores a insertar: text={text}, type={type}, options={processed_options}, assigned_user_id={assigned_user_id}, descripcion={descripcion}, is_required={is_required}, categoria={categoria}, active={active}")
        try:
            question_id = Question.create(
                text=text,
                type=type,
                options=processed_options,
                assigned_user_id=assigned_user_id,
                descripcion=descripcion,
                is_required=is_required,
                categoria=categoria,
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
                    preguntas=preguntas
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
                'UPDATE question SET text = ?, descripcion = ?, type = ?, categoria = ?, is_required = ?' + 
                (', options = ?' if options is not None else '') + ' WHERE id = ?',
                (
                    data.get('text', ''),
                    data.get('descripcion', ''),
                    data.get('type', 'text'),
                    categoria,
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
        cursor.execute('''SELECT id, titulo, descripcion, prioridad, categoria, completado, fecha_creacion, fecha_completado, objetivo_padre_id, es_padre, estado, fecha_inicio, fecha_fin, fecha_proyeccion_comienzo, horas_estimadas, dificultad, etiquetas, recompensa, notas_adicionales, recurrente, frecuencia, orden FROM objetivos WHERE user_id = ? ORDER BY orden ASC, fecha_creacion DESC''', (current_user.id,))
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
                'fecha_proyeccion_comienzo': row[13].strftime('%Y-%m-%d') if row[13] else None,
                'horas_estimadas': row[14],
                'dificultad': row[15],
                'etiquetas': row[16],
                'recompensa': row[17],
                'notas_adicionales': row[18],
                'recurrente': bool(row[19]) if len(row) > 19 else False,
                'frecuencia': row[20] if len(row) > 20 else None,
                'orden': row[21] if len(row) > 21 else 0
            }
            # Marcar si el objetivo recurrente fue saltado hoy
            if obj['recurrente']:
                cursor.execute('''SELECT 1 FROM objetivos_saltados WHERE objetivo_id = ? AND user_id = ? AND fecha_saltada = ?''', (obj['id'], current_user.id, hoy))
                obj['saltado_hoy'] = bool(cursor.fetchone())
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
                WHERE o.fecha_proyeccion_comienzo = ?
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
    fecha_proyeccion_comienzo = parse_fecha(data.get('fecha_proyeccion_comienzo'))
    horas_estimadas = data.get('horas_estimadas')
    dificultad = data.get('dificultad')
    etiquetas = data.get('etiquetas')
    recompensa = data.get('recompensa')
    notas_adicionales = data.get('notas_adicionales')
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
        
        cursor.execute('''INSERT INTO objetivos (user_id, titulo, descripcion, prioridad, categoria, completado, fecha_creacion, objetivo_padre_id, es_padre, estado, fecha_inicio, fecha_fin, fecha_proyeccion_comienzo, horas_estimadas, dificultad, etiquetas, recompensa, notas_adicionales, recurrente, frecuencia, orden)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (current_user.id, titulo, descripcion, prioridad, categoria, fecha_creacion, objetivo_padre_id, es_padre, estado, fecha_inicio, fecha_fin, fecha_proyeccion_comienzo, horas_estimadas, dificultad, etiquetas, recompensa, notas_adicionales, recurrente, frecuencia, nuevo_orden))
        objetivo_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'status': 'success', 'id': objetivo_id})

@app.route('/api/objetivos/<int:objetivo_id>', methods=['PATCH'])
@login_required
def api_update_objetivo(objetivo_id):
    data = request.get_json()
    
    # Si se está marcando como recurrente (restaurando del histórico)
    if 'recurrente' in data and data['recurrente'] == True:
        return restaurar_objetivo_completo(objetivo_id)
    
    campos = {}
    for campo in ['titulo', 'descripcion', 'prioridad', 'categoria', 'objetivo_padre_id', 'es_padre', 'estado', 'fecha_inicio', 'fecha_fin', 'fecha_proyeccion_comienzo', 'horas_estimadas', 'dificultad', 'etiquetas', 'recompensa', 'notas_adicionales', 'recurrente', 'frecuencia']:
        if campo in data:
            if campo in ['fecha_inicio', 'fecha_fin', 'fecha_proyeccion_comienzo']:
                campos[campo] = parse_fecha(data[campo])
            elif campo == 'categoria':
                campos[campo] = data[campo].strip().lower()
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
        cursor.execute(f"""
            UPDATE objetivos SET {', '.join(set_clause)} WHERE id = ? AND user_id = ?
        """, tuple(values))
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
            SELECT id, titulo, descripcion, prioridad, categoria, completado, fecha_creacion, fecha_completado, objetivo_padre_id, es_padre, estado, fecha_inicio, fecha_fin, fecha_proyeccion_comienzo, horas_estimadas, dificultad, etiquetas, recompensa, notas_adicionales, recurrente
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
                'fecha_proyeccion_comienzo': row[13].strftime('%Y-%m-%d') if row[13] else None,
                'horas_estimadas': row[14],
                'dificultad': row[15],
                'etiquetas': row[16],
                'recompensa': row[17],
                'notas_adicionales': row[18],
                'recurrente': bool(row[19])
            }
            for row in rows
        ]
        paginados = objetivos[offset:offset+limit]
        return jsonify(paginados)
    except Exception as e:
        logger.error(f"Error en objetivos_historico: {str(e)}")
        return jsonify({'error': 'Error al obtener histórico de objetivos'}), 500

# --- Scheduler para notificaciones automáticas ---
def start_scheduler():
    from datetime import datetime
    scheduler = BackgroundScheduler(timezone="America/Bogota")
    # Ejecutar a las 00:00 y 12:00 todos los días
    scheduler.add_job(verificar_proyecciones_comienzo, 'cron', hour=0, minute=0, id='notificacion_medianoche')
    scheduler.add_job(verificar_proyecciones_comienzo, 'cron', hour=12, minute=0, id='notificacion_mediodia')
    scheduler.start()
    print("[Scheduler] Notificaciones programadas a las 00:00 y 12:00 todos los días.")

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
        cursor.execute('''SELECT id, titulo, completado, fecha_creacion, orden FROM subobjetivos WHERE objetivo_id = ? ORDER BY orden ASC, id ASC''', (objetivo_id,))
        rows = cursor.fetchall()
        subobjetivos = [
            {
                'id': row[0],
                'titulo': row[1],
                'completado': bool(row[2]),
                'fecha_creacion': row[3].strftime('%Y-%m-%d %H:%M') if row[3] else None,
                'orden': row[4]
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
    campos = []
    valores = []
    if 'titulo' in data:
        campos.append('titulo = ?')
        valores.append(data['titulo'].strip())
    if 'completado' in data:
        campos.append('completado = ?')
        valores.append(int(bool(data['completado'])))
    if not campos:
        return jsonify({'error': 'Nada para actualizar'}), 400
    valores.append(subobjetivo_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''UPDATE subobjetivos SET {', '.join(campos)} WHERE id = ?''', tuple(valores))
        conn.commit()
        return jsonify({'status': 'success'})

@app.route('/api/subobjetivos/<int:subobjetivo_id>', methods=['DELETE'])
@login_required
def api_delete_subobjetivo(subobjetivo_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM subobjetivos WHERE id = ?''', (subobjetivo_id,))
        conn.commit()
        return jsonify({'status': 'success'})

# Configuración de la aplicación
# === RUTAS PARA FRASES INSPIRACIONALES ===

@app.route('/api/frases', methods=['GET'])
@login_required
def api_list_frases():
    """Obtener todas las frases del usuario"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, texto, autor, categoria, notas, total_repasos, ultima_vez, fecha_creacion
                FROM frases
                WHERE user_id = ?
                ORDER BY fecha_creacion DESC
            ''', (current_user.id,))
            
            frases = []
            for row in cursor.fetchall():
                frases.append({
                    'id': row[0],
                    'texto': row[1],
                    'autor': row[2],
                    'categoria': row[3],
                    'notas': row[4],
                    'total_repasos': row[5] or 0,
                    'ultima_vez': row[6].isoformat() if row[6] else None,
                    'fecha_creacion': row[7].isoformat() if row[7] else None
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
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO frases (user_id, texto, autor, categoria, notas, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                current_user.id,
                data['texto'],
                data.get('autor'),
                data['categoria'],
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
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la frase pertenece al usuario
            cursor.execute('SELECT user_id FROM frases WHERE id = ?', (frase_id,))
            frase = cursor.fetchone()
            if not frase or frase[0] != current_user.id:
                return jsonify({'error': 'Frase no encontrada'}), 404
            
            cursor.execute('''
                UPDATE frases 
                SET texto = ?, autor = ?, categoria = ?, notas = ?
                WHERE id = ? AND user_id = ?
            ''', (
                data['texto'],
                data.get('autor'),
                data['categoria'],
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
    """Obtener todas las categorías de frases del usuario"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT categoria
                FROM frases
                WHERE user_id = ?
                ORDER BY categoria
            ''', (current_user.id,))
            
            categorias = [row[0] for row in cursor.fetchall()]
            
            # Agregar categorías predeterminadas si no existen
            categorias_predeterminadas = [
                'motivacion', 'exito', 'perseverancia', 'sabiduria', 
                'crecimiento', 'liderazgo', 'felicidad', 'personal'
            ]
            
            # Combinar y eliminar duplicados
            todas_categorias = list(set(categorias + categorias_predeterminadas))
            todas_categorias.sort()
            
            return jsonify(todas_categorias)
    except Exception as e:
        logger.error(f"Error al obtener categorías: {str(e)}")
        return jsonify({'error': 'Error al obtener categorías'}), 500

if __name__ == '__main__':
    start_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=True)
