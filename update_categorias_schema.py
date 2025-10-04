import os
import sys
import pyodbc
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la conexión a la base de datos
DB_SERVER = os.getenv('DB_SERVER', 'localhost')
DB_DATABASE = os.getenv('DB_DATABASE', 'DailyQuestions')
DB_USERNAME = os.getenv('DB_USERNAME', 'sa')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'yourStrong(!)Password')

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD}"
    return pyodbc.connect(connection_string)

def crear_tablas():
    """Crea las tablas necesarias para categorías y subcategorías"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Crear tabla de categorías si no existe
            cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'categorias')
            BEGIN
                CREATE TABLE categorias (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NOT NULL,
                    nombre NVARCHAR(100) NOT NULL,
                    fecha_creacion DATETIME DEFAULT GETDATE(),
                    CONSTRAINT FK_categorias_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                
                -- Índice para búsquedas por usuario
                CREATE INDEX IX_categorias_user_id ON categorias(user_id);
                
                -- Índice para búsqueda por nombre
                CREATE INDEX IX_categorias_nombre ON categorias(nombre);
                
                PRINT 'Tabla categorías creada correctamente.'
            END
            ELSE
            BEGIN
                PRINT 'La tabla categorías ya existe.'
            END
            ''')
            
            # Crear tabla de subcategorías si no existe
            cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'subcategorias')
            BEGIN
                CREATE TABLE subcategorias (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NOT NULL,
                    categoria_id INT NOT NULL,
                    nombre NVARCHAR(100) NOT NULL,
                    fecha_creacion DATETIME DEFAULT GETDATE(),
                    CONSTRAINT FK_subcategorias_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT FK_subcategorias_categorias FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
                )
                
                -- Índice para búsquedas por usuario
                CREATE INDEX IX_subcategorias_user_id ON subcategorias(user_id);
                
                -- Índice para búsqueda por categoría
                CREATE INDEX IX_subcategorias_categoria_id ON subcategorias(categoria_id);
                
                -- Índice para búsqueda por nombre
                CREATE INDEX IX_subcategorias_nombre ON subcategorias(nombre);
                
                PRINT 'Tabla subcategorías creada correctamente.'
            END
            ELSE
            BEGIN
                PRINT 'La tabla subcategorías ya existe.'
            END
            ''')
            
            # Actualizar tabla frases para usar las nuevas tablas de categorías
            cursor.execute('''
            -- Primero, verificar si existen las columnas antiguas
            IF EXISTS (SELECT 1 FROM sys.columns WHERE Name = 'categoria' AND Object_ID = Object_ID('frases'))
            BEGIN
                -- 1. Crear columnas para las nuevas claves foráneas si no existen
                IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE Name = 'categoria_id' AND Object_ID = Object_ID('frases'))
                BEGIN
                    -- Agregar columna categoria_id
                    ALTER TABLE frases ADD categoria_id INT NULL;
                    
                    -- Agregar columna subcategoria_id
                    ALTER TABLE frases ADD subcategoria_id INT NULL;
                    
                    -- Agregar restricciones de clave foránea
                    ALTER TABLE frases 
                    ADD CONSTRAINT FK_frases_categorias FOREIGN KEY (categoria_id) 
                    REFERENCES categorias(id) ON DELETE SET NULL;
                    
                    ALTER TABLE frases 
                    ADD CONSTRAINT FK_frases_subcategorias FOREIGN KEY (subcategoria_id) 
                    REFERENCES subcategorias(id) ON DELETE SET NULL;
                    
                    PRINT 'Columnas de categorías actualizadas en la tabla frases.';
                END
                
                -- 2. Migrar datos existentes (esto se hará en un paso posterior)
                -- Primero necesitamos crear las categorías y subcategorías
            END
            ELSE
            BEGIN
                PRINT 'La tabla frases no tiene las columnas antiguas de categoría.';
            END
            ''')
            
            conn.commit()
            print("Esquema de base de datos actualizado correctamente.")
            
    except Exception as e:
        print(f"Error al actualizar el esquema de la base de datos: {str(e)}")
        sys.exit(1)

def migrar_datos():
    """Migra los datos de las categorías y subcategorías existentes"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Obtener todos los usuarios
            cursor.execute('SELECT id FROM users')
            users = cursor.fetchall()
            
            for user in users:
                user_id = user[0]
                print(f"Procesando usuario ID: {user_id}")
                
                # 2. Obtener todas las categorías únicas del usuario
                cursor.execute('''
                    SELECT DISTINCT LTRIM(RTRIM(categoria)) as categoria
                    FROM frases 
                    WHERE user_id = ? AND categoria IS NOT NULL AND LTRIM(RTRIM(categoria)) != ''
                ''', (user_id,))
                
                categorias = [row[0] for row in cursor.fetchall()]
                print(f"  Encontradas {len(categorias)} categorías")
                
                # 3. Insertar categorías en la nueva tabla
                for categoria_nombre in categorias:
                    # Verificar si la categoría ya existe
                    cursor.execute('''
                        SELECT id FROM categorias 
                        WHERE user_id = ? AND nombre = ?
                    ''', (user_id, categoria_nombre))
                    
                    if cursor.fetchone() is None:
                        # Insertar nueva categoría
                        cursor.execute('''
                            INSERT INTO categorias (user_id, nombre)
                            OUTPUT INSERTED.id
                            VALUES (?, ?)
                        ''', (user_id, categoria_nombre))
                        
                        categoria_id = cursor.fetchone()[0]
                        print(f"  Categoría creada: {categoria_nombre} (ID: {categoria_id})")
                    else:
                        # La categoría ya existe, obtener su ID
                        cursor.execute('''
                            SELECT id FROM categorias 
                            WHERE user_id = ? AND nombre = ?
                        ''', (user_id, categoria_nombre))
                        categoria_id = cursor.fetchone()[0]
                    
                    # 4. Obtener subcategorías para esta categoría
                    cursor.execute('''
                        SELECT DISTINCT LTRIM(RTRIM(subcategoria)) as subcategoria
                        FROM frases 
                        WHERE user_id = ? AND categoria = ? 
                            AND subcategoria IS NOT NULL 
                            AND LTRIM(RTRIM(subcategoria)) != ''
                    ''', (user_id, categoria_nombre))
                    
                    subcategorias = [row[0] for row in cursor.fetchall()]
                    print(f"    Encontradas {len(subcategorias)} subcategorías para {categoria_nombre}")
                    
                    # 5. Insertar subcategorías
                    for subcategoria_nombre in subcategorias:
                        # Verificar si la subcategoría ya existe
                        cursor.execute('''
                            SELECT s.id 
                            FROM subcategorias s
                            JOIN categorias c ON s.categoria_id = c.id
                            WHERE s.user_id = ? AND s.nombre = ? AND c.id = ?
                        ''', (user_id, subcategoria_nombre, categoria_id))
                        
                        if cursor.fetchone() is None:
                            # Insertar nueva subcategoría
                            cursor.execute('''
                                INSERT INTO subcategorias (user_id, categoria_id, nombre)
                                VALUES (?, ?, ?)
                            ''', (user_id, categoria_id, subcategoria_nombre))
                            print(f"    Subcategoría creada: {subcategoria_nombre}")
                
                # 6. Actualizar referencias en la tabla frases
                print("  Actualizando referencias en la tabla frases...")
                
                # Actualizar categoria_id
                cursor.execute('''
                    UPDATE f
                    SET f.categoria_id = c.id
                    FROM frases f
                    JOIN categorias c ON f.user_id = c.user_id AND LTRIM(RTRIM(f.categoria)) = c.nombre
                    WHERE f.user_id = ? AND f.categoria_id IS NULL AND f.categoria IS NOT NULL
                ''', (user_id,))
                
                # Actualizar subcategoria_id
                cursor.execute('''
                    UPDATE f
                    SET f.subcategoria_id = s.id
                    FROM frases f
                    JOIN subcategorias s ON f.user_id = s.user_id AND LTRIM(RTRIM(f.subcategoria)) = s.nombre
                    WHERE f.user_id = ? AND f.subcategoria_id IS NULL AND f.subcategoria IS NOT NULL
                ''', (user_id,))
                
                conn.commit()
                print(f"  Datos migrados correctamente para el usuario ID: {user_id}")
            
            print("Migración de datos completada exitosamente.")
            
    except Exception as e:
        print(f"Error durante la migración de datos: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    print("=== Actualización del esquema de la base de datos ===")
    print("1. Creando tablas de categorías y subcategorías...")
    crear_tablas()
    
    print("\n2. Migrando datos existentes...")
    migrar_datos()
    
    print("\n¡Proceso completado exitosamente!")
