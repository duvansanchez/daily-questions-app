import re

# Archivos HTML a procesar
files = [
    'daily_questions_app/templates/objetivos.html',
]

# Emojis de debug que queremos comentar
debug_emojis = ['🚀', '✅', '📅', '🔧', '📡', '📊', '🔍', '💾', '⏱️', '📝', '⏸️', '🔄', '👁️', '✏️', '🎨', '🧹', '📤', '📥', '💡', '📋', '🎯']

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        modified_lines = []
        
        for line in lines:
            # Si la línea contiene console.log con alguno de los emojis de debug
            if 'console.log(' in line and any(emoji in line for emoji in debug_emojis):
                # Comentar la línea si no está ya comentada
                if not line.strip().startswith('//'):
                    # Mantener la indentación original
                    indent = len(line) - len(line.lstrip())
                    modified_lines.append(' ' * indent + '// ' + line.lstrip())
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)
        
        # Escribir el archivo modificado
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(modified_lines))
        
        print(f'✅ Procesado: {file_path}')
    
    except FileNotFoundError:
        print(f'⚠️  Archivo no encontrado: {file_path}')
    except Exception as e:
        print(f'❌ Error procesando {file_path}: {e}')

print('\n✅ Proceso completado')
