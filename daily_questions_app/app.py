from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from flask_session import Session
import pyodbc
from dotenv import load_dotenv
import logging
import sys
import traceback

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
    def create(cls, question_id, response_text, date):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO response (question_id, response, date) VALUES (?, ?, ?)',
                (question_id, response_text, date)
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
        return redirect(url_for('index'))
    
    # Obtener la URL de redirección de los parámetros de la solicitud o de la sesión
    next_url = request.args.get('next') or session.pop('next_url', None)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
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
                    # Validar que la URL de redirección sea relativa al host actual
                    if next_page and not next_page.startswith(('http://', 'https://')):
                        return redirect(next_page)
                    return redirect(url_for('index'))
                
            # Si llegamos aquí, las credenciales son inválidas
            flash('Usuario o contraseña inválidos')
            
        except Exception as e:
            print(f"Error durante el inicio de sesión: {str(e)}")
            flash('Error al procesar la solicitud de inicio de sesión')
    
    # Para solicitudes GET o si hay un error, mostrar el formulario de login
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
                for question_id_str, response_text in responses.items():
                    try:
                        question_id = int(question_id_str)  # Asegurar que el ID sea entero
                        response_text = str(response_text) if response_text is not None else ""
                        
                        print(f"Procesando pregunta {question_id}: {response_text[:50]}...")
                        
                        # Verificar si la pregunta está asignada al usuario
                        if question_id not in question_ids:
                            print(f"Advertencia: La pregunta {question_id} no está asignada al usuario {current_user.id}")
                            continue
                        
                        # Insertar la respuesta con parámetros explícitos
                        cursor.execute(
                            """
                            INSERT INTO response (question_id, response, date)
                            VALUES (?, ?, ?)
                            """,
                            (question_id, response_text, date_with_time)
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
        today = datetime.now().strftime('%Y-%m-%d')
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Preguntas asignadas al usuario (solo activas)
                cursor.execute('SELECT COUNT(*) FROM question WHERE assigned_user_id = ? AND active = 1', (current_user.id,))
                total_asignadas = cursor.fetchone()[0] or 0

                # Respuestas de hoy (solo las que no están vacías)
                cursor.execute('''
                    SELECT COUNT(*) FROM response r
                    JOIN question q ON r.question_id = q.id
                    WHERE q.assigned_user_id = ? AND CONVERT(DATE, r.date) = ?
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
                    from datetime import timedelta
                    dias_ordenados = sorted([d if isinstance(d, datetime) else datetime.strptime(str(d), '%Y-%m-%d') for d in dias], reverse=True)
                    hoy = datetime.now().date()
                    for i, d in enumerate(dias_ordenados):
                        if (hoy - d.date()).days == i:
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

                return render_template(
                    'stats.html',
                    resumen_diario=resumen_diario,
                    resumen_general=resumen_general,
                    indicadores=indicadores
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
            cursor.execute('DELETE FROM question WHERE id = ?', (question_id,))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error al eliminar pregunta: {str(e)}")
        response = jsonify({'status': 'error', 'message': str(e)})
        response.status_code = 500
        return response

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

# Configuración de la aplicación
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
