// Main JavaScript for Zerox Network

// Smooth animations on page load
document.addEventListener('DOMContentLoaded', () => {
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('animate-fade-in');
        }, index * 100);
    });
});

// File upload drag and drop
function initializeFileUpload() {
    const uploadArea = document.querySelector('.upload-area');
    if (!uploadArea) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('dragover');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('dragover');
        }, false);
    });
    
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.files = files;
            updateFileInfo(files[0]);
        }
    }
}

// Update file info display
function updateFileInfo(file) {
    const fileInfoDiv = document.getElementById('file-info');
    if (fileInfoDiv && file) {
        fileInfoDiv.innerHTML = `
            <p><strong>File:</strong> ${file.name}</p>
            <p><strong>Size:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
        `;
    }
}

// Price calculation
function calculatePrice() {
    const pages = parseInt(document.getElementById('pages')?.value) || 0;
    const paperSize = document.querySelector('input[name="paper_size"]:checked')?.value;
    const colorType = document.querySelector('input[name="color_type"]:checked')?.value;
    const printSide = document.querySelector('input[name="print_side"]:checked')?.value;
    
    const priceElement = document.getElementById('total-price');
    if (!priceElement) return;
    
    // Get prices from data attributes (set by Django)
    const pricePerPage = parseFloat(priceElement.dataset[`${paperSize}_${colorType}`]) || 0;
    
    let effectivePages = pages;
    if (printSide === 'DOUBLE') {
        effectivePages = Math.ceil(pages / 2);
    }
    
    const total = pricePerPage * effectivePages;
    priceElement.textContent = `₹${total.toFixed(2)}`;
}

// Initialize
initializeFileUpload();
