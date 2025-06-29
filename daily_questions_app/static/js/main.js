// Variables globales
let currentQuestionIndex = 0;
let questions = [];
let responses = {};

// Integración de SweetAlert2 para alertas globales
// Asegúrate de incluir el script de SweetAlert2 en tu HTML

// Alerta de éxito
function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: 'Éxito',
        text: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 2500,
        timerProgressBar: true
    });
}

// Alerta de error
function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 4000,
        timerProgressBar: true
    });
}

// Alerta de información
function showInfo(message) {
    Swal.fire({
        icon: 'info',
        title: 'Información',
        text: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 2500,
        timerProgressBar: true
    });
}

// Confirmación (retorna una promesa)
function showConfirm(message) {
    return Swal.fire({
        title: '¿Estás seguro?',
        text: message,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí, continuar',
        cancelButtonText: 'Cancelar',
        width: '23rem',
        customClass: {
            title: 'swal2-custom-title',
            htmlContainer: 'swal2-custom-text'
        }
    });
}

// Exportar funciones globalmente
window.showSuccess = showSuccess;
window.showError = showError;
window.showInfo = showInfo;
window.showConfirm = showConfirm;

// Función para mostrar notificaciones
function showNotification(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.main-container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Función para manejar errores de fetch
function handleFetchError(error) {
    console.error('Error:', error);
    showNotification('Ha ocurrido un error. Por favor, intenta nuevamente.', 'danger');
}

// Función para mostrar la pregunta actual
function showQuestion(index) {
    // Ocultar todas las preguntas
    document.querySelectorAll('.question-card').forEach((card, i) => {
        if (i === index) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
    
    // Actualizar la barra de progreso
    const progress = ((index + 1) / questions.length) * 100;
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text span:last-child');
    
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', index + 1);
    progressText.textContent = `${index + 1} de ${questions.length}`;
    
    // Actualizar botones de navegación
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const submitBtn = document.getElementById('submit-btn');
    
    prevBtn.disabled = index === 0;
    
    if (index === questions.length - 1) {
        nextBtn.style.display = 'none';
        submitBtn.style.display = 'inline-block';
    } else {
        nextBtn.style.display = 'inline-block';
        submitBtn.style.display = 'none';
    }
    
    // Restaurar respuesta guardada si existe
    const questionId = questions[index].id;
    if (responses[questionId]) {
        const optionBtns = document.querySelectorAll(`.question-card[style*='display: block'] .option-btn`);
        optionBtns.forEach(btn => {
            if (btn.dataset.option === responses[questionId]) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });
    }
}

// Función para guardar la respuesta actual
function saveCurrentResponse() {
    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return;
    const card = currentQuestion.element;
    let value = null;

    // 1. Botones personalizados (option-btn)
    const selectedBtn = card.querySelector('.option-btn.selected');
    if (selectedBtn) {
        value = selectedBtn.dataset.option;
    }

    // 2. Checkbox (varias opciones)
    const checkboxes = card.querySelectorAll('input[type="checkbox"]');
    if (checkboxes.length > 0) {
        const checked = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
        if (checked.length > 0) {
            value = checked.join(',');
        }
    }

    // 3. Radio (una opción)
    const radios = card.querySelectorAll('input[type="radio"]');
    if (radios.length > 0) {
        const checkedRadio = Array.from(radios).find(r => r.checked);
        if (checkedRadio) {
            value = checkedRadio.value;
        }
    }

    // 4. Textarea (texto libre)
    const textarea = card.querySelector('textarea');
    if (textarea) {
        if (textarea.value.trim() !== '') {
            value = textarea.value.trim();
        }
    }

    // Guardar siempre la respuesta (vacía o no) para preguntas no obligatorias
    const isRequired = card.getAttribute('data-is-required') == '1' || card.getAttribute('data-is-required') == 'true';
    if (isRequired) {
        if (value !== null && value !== undefined && value !== '') {
            responses[currentQuestion.id] = value;
        } else {
            delete responses[currentQuestion.id];
        }
    } else {
        // No obligatoria: guardar aunque esté vacía
        responses[currentQuestion.id] = value !== null && value !== undefined ? value : '';
    }
}

// Función para enviar las respuestas al servidor
async function submitResponses() {
    try {
        console.log('Respuestas que se enviarán:', responses);
        const response = await fetch('/submit_responses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: new Date().toISOString().split('T')[0],
                responses: responses
            })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showNotification('¡Tus respuestas han sido guardadas exitosamente!', 'success');
            // Redirigir a la página de estadísticas o dashboard
            setTimeout(() => {
                window.location.href = '/stats';
            }, 1500);
        } else {
            throw new Error(result.message || 'Error al guardar las respuestas');
        }
    } catch (error) {
        console.error('Error al enviar respuestas:', error);
        showNotification('Error al enviar las respuestas. Por favor, inténtalo de nuevo.', 'danger');
    }
}

// Event listeners globales
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar variables
    questions = Array.from(document.querySelectorAll('.question-card')).map((card) => ({
        id: card.getAttribute('data-question-id'),
        element: card
    }));
    
    // Mostrar la primera pregunta
    if (questions.length > 0) {
        showQuestion(0);
    }
    
    // Manejar clic en opciones de respuesta
    document.addEventListener('click', function(e) {
        if (e.target.closest('.option-btn')) {
            const optionBtn = e.target.closest('.option-btn');
            const questionCard = optionBtn.closest('.question-card');
            
            // Deseleccionar otras opciones
            questionCard.querySelectorAll('.option-btn').forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Seleccionar la opción actual
            optionBtn.classList.add('selected');
        }
    });
    
    // Manejar botón Anterior
    const prevBtn = document.getElementById('prev-btn');
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (currentQuestionIndex > 0) {
                saveCurrentResponse();
                currentQuestionIndex--;
                showQuestion(currentQuestionIndex);
            }
        });
    }
    
    // Manejar botón Siguiente
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            saveCurrentResponse();
            currentQuestionIndex++;
            showQuestion(currentQuestionIndex);
        });
    }
    
    // Manejar botón Enviar
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            saveCurrentResponse();
            // Validar preguntas obligatorias antes de enviar
            const obligatoriasSinResponder = questions.filter(q => {
                const card = q.element;
                const isRequired = card.getAttribute('data-is-required') == '1' || card.getAttribute('data-is-required') == 'true';
                return isRequired && !(q.id in responses) && !card.querySelector('.option-btn.selected') && !card.querySelector('input[type="checkbox"]:checked') && !card.querySelector('input[type="radio"]:checked') && (!card.querySelector('textarea') || card.querySelector('textarea').value.trim() === '');
            });
            if (obligatoriasSinResponder.length > 0) {
                showError('Debes responder todas las preguntas obligatorias antes de enviar.');
                return;
            }
            showConfirm('¿Estás seguro de que deseas enviar tus respuestas?').then((result) => {
                if (result.isConfirmed) {
                    submitResponses();
                }
            });
        });
    }

    // Validación del submit solo del campo visible
    const form = document.getElementById('add-question-form');
    // Definir las variables necesarias para el handler
    const bloqueCatExistenteNueva = document.getElementById('bloque-categoria-existente-nueva');
    const bloqueNuevaCatNueva = document.getElementById('bloque-nueva-categoria-nueva');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Submit capturado'); // Para depuración
            // Validar existencia de los bloques
            if (!bloqueCatExistenteNueva || !bloqueNuevaCatNueva) {
                console.error('No se encontraron los bloques de categoría.');
                return;
            }
            const submitBtn = document.getElementById('submit-question');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Guardando...';
            const formData = new FormData(form);
            let categoriaExistente = '';
            let nuevaCategoria = '';
            if (bloqueCatExistenteNueva && bloqueCatExistenteNueva.style.display !== 'none') {
                categoriaExistente = formData.get('categoria_existente') || '';
            }
            if (bloqueNuevaCatNueva && bloqueNuevaCatNueva.style.display !== 'none') {
                nuevaCategoria = formData.get('nueva_categoria') || '';
            }
            if (categoriaExistente && nuevaCategoria) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Crear Pregunta';
                showError('No puedes seleccionar una categoría existente y escribir una nueva al mismo tiempo.');
                return false;
            }
            // Construir el objeto de datos para enviar
            const data = {
                text: formData.get('text') || '',
                type: formData.get('type') || 'text',
                options: formData.get('options') || '',
                descripcion: formData.get('descripcion') || '',
                is_required: document.getElementById('is_required').checked ? 1 : 0,
                categoria_existente: categoriaExistente,
                nueva_categoria: nuevaCategoria
            };
            try {
                const response = await fetch('/add_question', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                if (result.status === 'success') {
                    showSuccess('Pregunta creada exitosamente');
                    setTimeout(() => {
                        window.location.href = window.location.href.split('?')[0];
                    }, 1200);
                } else {
                    showError(result.message || 'Error al crear la pregunta');
                }
            } catch (err) {
                showError('Error al crear la pregunta: ' + (err.message || err));
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Crear Pregunta';
            }
        });
    }
});

// Inicializa los eventos de administración de preguntas (editar, eliminar, switches, etc)
function initAdminEvents() {
    // Re-inicializar eventos de editar, eliminar, switches, etc.
    // Eliminar pregunta
    document.querySelectorAll('.delete-question').forEach(btn => {
        btn.onclick = function(e) {
            e.preventDefault();
            const id = this.dataset.id;
            showConfirm('¿Estás seguro de que deseas eliminar esta pregunta? Se eliminarán también todas las respuestas asociadas. Esta acción no se puede deshacer.').then((result) => {
                if (result.isConfirmed) {
                    fetch(`/question/${id}`, {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
                    })
                    .then(res => res.json())
                    .then(res => {
                        if (res.status === 'success') {
                            this.closest('.pregunta-item').remove();
                            showSuccess('Pregunta eliminada correctamente.');
                        } else {
                            showError('Error al eliminar: ' + (res.message || ''));
                        }
                    })
                    .catch(err => showError('Error al eliminar: ' + err));
                }
            });
        };
    });
    // Puedes agregar aquí la reinicialización de otros eventos (editar, switches, etc.)
}
