document.addEventListener('DOMContentLoaded', function() {
    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Trigger initial resize
        textarea.dispatchEvent(new Event('input'));
    });

    // Flash messages auto-hide
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s ease';
            setTimeout(() => message.remove(), 500);
        }, 5000);
    });

    // Tag input helper
    const newTagsInput = document.getElementById('new_tags');
    if (newTagsInput) {
        newTagsInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                // You could add functionality to create tags on Enter if needed
            }
        });
    }

    // Confirm before destructive actions
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
});



// View toggle functionality
function initViewToggle() {
    const blockViewBtn = document.getElementById('blockView');
    const tableViewBtn = document.getElementById('tableView');
    const blockViewContainer = document.getElementById('blockViewContainer');
    const tableViewContainer = document.getElementById('tableViewContainer');
    
    // Load saved view preference
    const savedView = localStorage.getItem('problemsView') || 'block';
    
    function setActiveView(view) {
        // Update buttons
        blockViewBtn.classList.toggle('active', view === 'block');
        tableViewBtn.classList.toggle('active', view === 'table');
        
        // Update containers
        blockViewContainer.style.display = view === 'block' ? 'flex' : 'none';
        tableViewContainer.style.display = view === 'table' ? 'block' : 'none';
        
        // Save preference
        localStorage.setItem('problemsView', view);
    }
    
    // Set initial view
    setActiveView(savedView);
    
    // Add event listeners
    blockViewBtn.addEventListener('click', () => setActiveView('block'));
    tableViewBtn.addEventListener('click', () => setActiveView('table'));
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // ... existing code ...
    
    // Initialize view toggle
    initViewToggle();
});