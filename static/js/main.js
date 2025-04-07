document.addEventListener('DOMContentLoaded', function() {
    // Minimizar/restaurar ventanas
    document.querySelectorAll('.toggle-window').forEach(button => {
        button.addEventListener('click', function() {
            const card = this.closest('.window-card');
            card.classList.toggle('collapsed');
            this.textContent = card.classList.contains('collapsed') ? '+' : '−';
        });
    });
    
    // Opcional: Hacer las ventanas arrastrables
    // (Implementación básica - podrías usar una librería como interact.js para mejor funcionalidad)
    const cards = document.querySelectorAll('.window-card');
    
    cards.forEach(card => {
        const header = card.querySelector('.card-header');
        let isDragging = false;
        let offsetX, offsetY;
        
        header.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('toggle-window')) return;
            
            isDragging = true;
            offsetX = e.clientX - card.getBoundingClientRect().left;
            offsetY = e.clientY - card.getBoundingClientRect().top;
            card.style.position = 'absolute';
            card.style.zIndex = '1000';
            card.style.cursor = 'grabbing';
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            card.style.left = (e.clientX - offsetX) + 'px';
            card.style.top = (e.clientY - offsetY) + 'px';
        });
        
        document.addEventListener('mouseup', () => {
            isDragging = false;
            card.style.cursor = 'grab';
        });
    });
});