@app.route('/admin')
@login_required
def admin():
    # Obtener preguntas del usuario actual
    questions = Question.get_by_user(current_user.id)
    
    # Obtener categorías únicas de las preguntas del usuario actual
    categories = list(set(q.categoria for q in questions if q.categoria))
    
    return render_template('admin.html', questions=questions, categories=categories)

@app.route('/add_question', methods=['POST'])
@login_required
def add_question():
    try:
        # Obtener datos del formulario
        text = request.form.get('text', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        type = request.form.get('type', 'text')
        
        # Manejar categoría: priorizar nueva categoría si se proporciona
        nueva_categoria = request.form.get('nueva_categoria', '').strip()
        categoria_existente = request.form.get('categoria_existente', '').strip()
        categoria = nueva_categoria if nueva_categoria else categoria_existente
        
        options = request.form.get('options', '').strip() if 'options' in request.form else None
        # Switches
        is_required = 1 if request.form.get('is_required') == 'on' else 0
        active = 1 if request.form.get('active') == 'on' else 0
        assigned_user_id = request.form.get('assigned_user_id')
        if not assigned_user_id or not assigned_user_id.isdigit():
            assigned_user_id = current_user.id
        
        # Validar campos requeridos
        if not text:
            flash('El texto de la pregunta es requerido', 'error')
            return redirect(url_for('admin'))
        if type not in ['text', 'select', 'checkbox', 'radio']:
            flash('Tipo de pregunta no válido', 'error')
            return redirect(url_for('admin'))
        
        # Insertar la pregunta
        Question.create(
            text=text,
            type=type,
            options=options,
            assigned_user_id=assigned_user_id,
            descripcion=descripcion,
            is_required=is_required,
            categoria=categoria,
            active=active
        )
        flash('Pregunta agregada exitosamente', 'success')
        return redirect(url_for('admin'))
    except Exception as e:
        print(f"Error al agregar pregunta: {str(e)}")
        flash('Error al agregar la pregunta. Por favor, intente de nuevo.', 'error')
        return redirect(url_for('admin')) 