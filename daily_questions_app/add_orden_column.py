import pyodbc

# Configuración de conexión
conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-PIDFCJG;"
    "DATABASE=DailyQuestions;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Verificar si la columna orden existe
    cursor.execute("""
        SELECT COUNT(*) 
        FROM sys.columns 
        WHERE object_id = OBJECT_ID('objetivos') 
        AND name = 'orden'
    """)
    
    column_exists = cursor.fetchone()[0] > 0
    
    if not column_exists:
        print("Agregando columna 'orden' a la tabla objetivos...")
        
        # Agregar la columna orden
        cursor.execute("""
            ALTER TABLE objetivos 
            ADD orden INT NOT NULL DEFAULT 0
        """)
        
        # Actualizar los registros existentes con valores de orden basados en fecha_creacion
        cursor.execute("""
            WITH RankedObjetivos AS (
                SELECT id, 
                       ROW_NUMBER() OVER (PARTITION BY categoria ORDER BY fecha_creacion ASC) as rn
                FROM objetivos
            )
            UPDATE o 
            SET orden = r.rn
            FROM objetivos o
            INNER JOIN RankedObjetivos r ON o.id = r.id
        """)
        
        conn.commit()
        print("Columna 'orden' agregada exitosamente y valores inicializados.")
    else:
        print("La columna 'orden' ya existe en la tabla objetivos.")
    
    conn.close()
    print("Proceso completado exitosamente!")
    
except Exception as e:
    print(f"Error: {str(e)}")
    try:
        conn.close()
    except:
        pass 