// Test script to run in browser console
// Go to http://localhost:5000/objetivos and paste this in the console

console.log('🧪 Testing Prefix Functionality...');

// Test 1: Check if functions are loaded
console.log('📋 Function availability:');
console.log('- procesarTituloConPrefijos:', typeof procesarTituloConPrefijos);
console.log('- aplicarPrefijosSubobjetivos:', typeof aplicarPrefijosSubobjetivos);
console.log('- window.procesarTituloConPrefijos:', typeof window.procesarTituloConPrefijos);
console.log('- window.aplicarPrefijosSubobjetivos:', typeof window.aplicarPrefijosSubobjetivos);

// Test 2: Test prefix processing function
if (typeof procesarTituloConPrefijos === 'function') {
    console.log('🎨 Testing prefix processing:');
    const testCases = [
        'feat: Nueva funcionalidad',
        'fix: Corregir error',
        'refactor: Limpiar código',
        'docs: Actualizar documentación',
        'style: Mejorar diseño',
        'investigate: Analizar problema',
        'config: Configurar servidor',
        'Sin prefijo'
    ];
    
    testCases.forEach(test => {
        const result = procesarTituloConPrefijos(test);
        console.log(`Input: "${test}" -> Output: ${result}`);
    });
} else {
    console.log('❌ procesarTituloConPrefijos function not available');
}

// Test 3: Check if CSS classes are loaded
console.log('🎨 CSS classes test:');
const testElement = document.createElement('span');
testElement.className = 'subobjetivo-prefix prefix-feat';
testElement.textContent = 'feat:';
document.body.appendChild(testElement);

const styles = window.getComputedStyle(testElement);
console.log('- prefix-feat background-color:', styles.backgroundColor);
console.log('- prefix-feat color:', styles.color);

// Clean up
document.body.removeChild(testElement);

// Test 4: Check tooltip element
const tooltipElement = document.querySelector('[data-bs-toggle="tooltip"]');
console.log('📋 Tooltip element found:', !!tooltipElement);
if (tooltipElement) {
    console.log('- Tooltip title:', tooltipElement.getAttribute('data-bs-title'));
}

console.log('✅ Prefix functionality test completed!');