// Variables globales
let currentQuestionIndex = 0;
let questions = [];
let responses = {};

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
    
    const selectedOption = document.querySelector(`.question-card[style*='display: block'] .option-btn.selected`);
    if (selectedOption) {
        responses[currentQuestion.id] = selectedOption.dataset.option;
    }
}

// Función para enviar las respuestas al servidor
async function submitResponses() {
    try {
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
    questions = Array.from(document.querySelectorAll('.question-card')).map((card, index) => ({
        id: card.querySelector('.option-btn')?.dataset.questionId || index,
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
            if (confirm('¿Estás seguro de que deseas enviar tus respuestas?')) {
                submitResponses();
            }
        });
    }
});
