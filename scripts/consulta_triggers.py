import pyodbc
import getpass
import os

# Solicitar datos de conexión
usuario = input('Usuario SQL Server: ')
contraseña = getpass.getpass('Contraseña: ')
servidor = input('Servidor/Instancia (ejemplo: localhost o localhost\\SQLEXPRESS): ')

# Conexión a la instancia (a la base master para listar bases de datos)
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={servidor};DATABASE=master;UID={usuario};PWD={contraseña}'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Obtener todas las bases de datos (excepto las del sistema)
cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4")
bases = [row[0] for row in cursor.fetchall()]

consulta_triggers = '''
SELECT 
    name AS trigger_name,
    parent_class_desc,
    OBJECT_NAME(parent_id) AS table_name,
    type_desc,
    is_disabled,
    create_date,
    modify_date
FROM sys.triggers
WHERE OBJECT_NAME(parent_id) = 'factura01'
'''

for base in bases:
    print(f'\nBuscando triggers en la base: {base}')
    try:
        conn_db = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={servidor};DATABASE={base};UID={usuario};PWD={contraseña}')
        cursor_db = conn_db.cursor()
        cursor_db.execute(consulta_triggers)
        triggers = cursor_db.fetchall()
        if triggers:
            # Crear carpeta si no existe
            if not os.path.exists(base):
                os.makedirs(base)
            for trigger in triggers:
                trigger_name = trigger.trigger_name
                # Obtener el código del trigger
                cursor_db.execute(f"SELECT OBJECT_DEFINITION(OBJECT_ID('{trigger_name}'))")
                trigger_code = cursor_db.fetchone()[0]
                # Guardar en archivo
                with open(os.path.join(base, f'{trigger_name}.sql'), 'w', encoding='utf-8') as f:
                    f.write(f'-- Trigger: {trigger_name}\n')
                    f.write(trigger_code or '-- No se pudo obtener el código')
                print(f'Trigger guardado: {trigger_name}')
        else:
            print('No se encontraron triggers en factura01.')
        conn_db.close()
    except Exception as e:
        print(f'Error en la base {base}: {e}')

conn.close()
print('\nProceso finalizado.') 