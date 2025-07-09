import pyodbc

# Primero conectarse a la base de datos master para crear DailyQuestions si no existe
master_conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-PIDFCJG;"
    "DATABASE=master;"
    "Trusted_Connection=yes;"
)

try:
    # Conectar a master y crear la base de datos si no existe
    master_conn = pyodbc.connect(master_conn_str, autocommit=True)
    master_cursor = master_conn.cursor()
    
    # Crear la base de datos DailyQuestions si no existe
    master_cursor.execute("""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'DailyQuestions')
        BEGIN
            CREATE DATABASE DailyQuestions;
        END
    """)
    master_conn.close()
    print("Base de datos DailyQuestions creada/verificada exitosamente!")
    
except Exception as e:
    print(f"Error creando la base de datos: {str(e)}")
    exit(1)

# Ahora conectarse a DailyQuestions para crear las tablas
conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-PIDFCJG;"
    "DATABASE=DailyQuestions;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Crear tabla de usuarios
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user')
        BEGIN
            CREATE TABLE [user] (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(80) UNIQUE NOT NULL,
                password NVARCHAR(120) NOT NULL
            )
        END
    """)
    
    # Crear tabla de preguntas
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'question')
        BEGIN
            CREATE TABLE question (
                id INT IDENTITY(1,1) PRIMARY KEY,
                text NVARCHAR(500) NOT NULL,
                type NVARCHAR(50) NOT NULL,
                options NVARCHAR(500) NULL,
                active BIT DEFAULT 1,
                created_at DATETIME DEFAULT GETDATE(),
                assigned_user_id INT,
                FOREIGN KEY (assigned_user_id) REFERENCES [user](id)
            )
        END
    """)
    
    # Crear tabla de respuestas
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'response')
        BEGIN
            CREATE TABLE response (
                id INT IDENTITY(1,1) PRIMARY KEY,
                question_id INT NOT NULL,
                response NVARCHAR(500) NOT NULL,
                date DATE NOT NULL,
                FOREIGN KEY (question_id) REFERENCES question (id)
            )
        END
    """)
    
    # Crear tabla de objetivos (SQL Server compatible)
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'objetivos')
        BEGIN
            CREATE TABLE objetivos (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT NOT NULL,
                titulo NVARCHAR(255) NOT NULL,
                descripcion NVARCHAR(1000),
                prioridad NVARCHAR(20) DEFAULT 'media',
                categoria NVARCHAR(100),
                completado BIT DEFAULT 0,
                fecha_creacion DATETIME DEFAULT GETDATE(),
                fecha_completado DATETIME,
                objetivo_padre_id INT,
                es_padre BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES [user](id),
                FOREIGN KEY (objetivo_padre_id) REFERENCES objetivos(id)
            )
        END
    ''')
    
    # Crear tabla subobjetivos si no existe
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='subobjetivos' AND xtype='U')
            CREATE TABLE subobjetivos (
                id INT IDENTITY(1,1) PRIMARY KEY,
                objetivo_id INT NOT NULL,
                titulo NVARCHAR(255) NOT NULL,
                completado BIT NOT NULL DEFAULT 0,
                fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
                orden INT NOT NULL DEFAULT 0,
                FOREIGN KEY (objetivo_id) REFERENCES objetivos(id) ON DELETE CASCADE
            )
        ''')
        # Agregar columna 'orden' si no existe (para migraciones en bases ya creadas)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM syscolumns WHERE id=OBJECT_ID('subobjetivos') AND name='orden')
            ALTER TABLE subobjetivos ADD orden INT NOT NULL DEFAULT 0;
        """)
        conn.commit()
    
    # Tabla para registrar los saltos de objetivos recurrentes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objetivos_saltados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            objetivo_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            fecha_saltada DATE NOT NULL,
            FOREIGN KEY (objetivo_id) REFERENCES objetivos(id),
            FOREIGN KEY (user_id) REFERENCES [user](id)
        )
    ''')
    
    conn.commit()
    print("Base de datos inicializada exitosamente!")
    
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    try:
        conn.close()
    except:
        pass
    print('Database initialized successfully!')
