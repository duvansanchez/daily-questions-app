import pyodbc

conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-32COF63;"
    "DATABASE=DailyQuestions;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Eliminar tablas en orden inverso a las dependencias
    cursor.execute("""
        IF EXISTS (SELECT * FROM sys.tables WHERE name = 'response')
            DROP TABLE response;
        IF EXISTS (SELECT * FROM sys.tables WHERE name = 'question')
            DROP TABLE question;
        IF EXISTS (SELECT * FROM sys.tables WHERE name = 'user')
            DROP TABLE [user];
    """)
    
    # Crear tabla de usuarios
    cursor.execute("""
        CREATE TABLE [user] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(80) UNIQUE NOT NULL,
            password NVARCHAR(120) NOT NULL
        )
    """)
    
    # Crear tabla de preguntas
    cursor.execute("""
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
    """)
    
    # Crear tabla de respuestas
    cursor.execute("""
        CREATE TABLE response (
            id INT IDENTITY(1,1) PRIMARY KEY,
            question_id INT NOT NULL,
            response NVARCHAR(500) NOT NULL,
            date DATE NOT NULL,
            FOREIGN KEY (question_id) REFERENCES question (id)
        )
    """)
    
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
