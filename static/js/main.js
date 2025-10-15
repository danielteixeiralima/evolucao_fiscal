// Main JavaScript file for Financial Data Management System
// Enhanced functionality for better user experience

$(document).ready(function() {
    // Initialize all components
    initializeComponents();
    initializeDataTables();
    initializeFormValidation();
    initializeTooltips();
    initializeFileUpload();
    initializeSearchEnhancements();
});

// Initialize main components
function initializeComponents() {
    // Add fade-in animation to cards
    $('.card').addClass('fade-in');
    
    // Enhanced dropdown behaviors
    $('.dropdown-toggle').on('click', function(e) {
        e.stopPropagation();
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
    
    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        const target = $($(this).attr('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 70
            }, 500);
        }
    });
}

// Initialize DataTables with enhanced features
function initializeDataTables() {
    // Common DataTable configuration
    const commonConfig = {
        responsive: true,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        language: {
            search: "Search records:",
            lengthMenu: "Show _MENU_ records per page",
            info: "Showing _START_ to _END_ of _TOTAL_ records",
            infoEmpty: "No records available",
            infoFiltered: "(filtered from _MAX_ total records)",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        initComplete: function() {
            // Add Bootstrap styling to DataTables elements
            $('.dataTables_length select').addClass('form-select form-select-sm');
            $('.dataTables_filter input').addClass('form-control form-control-sm');
        }
    };
    
    // Initialize specific tables
    if ($('#movementsTable').length) {
        $('#movementsTable').DataTable({
            ...commonConfig,
            order: [[7, "desc"]], // Sort by uploaded date
            columnDefs: [
                { targets: [-1], orderable: false }, // Disable sorting on actions column
                { targets: [4], type: 'currency' }, // Currency sorting for net value
            ]
        });
    }
    
    if ($('#usersTable').length) {
        $('#usersTable').DataTable({
            ...commonConfig,
            order: [[3, "desc"]], // Sort by created date
            columnDefs: [
                { targets: [-1], orderable: false }, // Disable sorting on actions column
            ]
        });
    }
    
    if ($('#uploadsTable').length) {
        $('#uploadsTable').DataTable({
            ...commonConfig,
            order: [[5, "desc"]], // Sort by upload date
            columnDefs: [
                { targets: [-1], orderable: false }, // Disable sorting on actions column
            ]
        });
    }
}

// Initialize form validation
function initializeFormValidation() {
    // Real-time validation for forms
    $('form').on('submit', function(e) {
        const form = $(this);
        let isValid = true;
        
        // Check required fields
        form.find('[required]').each(function() {
            const field = $(this);
            if (!field.val().trim()) {
                field.addClass('is-invalid');
                isValid = false;
            } else {
                field.removeClass('is-invalid');
            }
        });
        
        // Email validation
        form.find('input[type="email"]').each(function() {
            const email = $(this);
            const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (email.val() && !emailPattern.test(email.val())) {
                email.addClass('is-invalid');
                isValid = false;
            }
        });
        
        // Password confirmation
        const password = form.find('input[name="password"]');
        const password2 = form.find('input[name="password2"]');
        if (password.length && password2.length) {
            if (password.val() !== password2.val()) {
                password2.addClass('is-invalid');
                isValid = false;
            }
        }
        
        if (!isValid) {
            e.preventDefault();
            showNotification('Please correct the highlighted fields', 'error');
        }
    });
    
    // Remove validation classes on input
    $('input, select, textarea').on('input change', function() {
        $(this).removeClass('is-invalid');
    });
}

// Initialize tooltips
function initializeTooltips() {
    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add tooltips to truncated text
    $('.text-truncate, .text-truncate-2').each(function() {
        const element = $(this);
        if (element[0].scrollWidth > element[0].clientWidth) {
            element.attr('data-bs-toggle', 'tooltip');
            element.attr('title', element.text());
            new bootstrap.Tooltip(element[0]);
        }
    });
}

// Initialize file upload enhancements
function initializeFileUpload() {
    $('input[type="file"]').on('change', function() {
        const file = this.files[0];
        const fileInfo = $(this).siblings('.file-info');
        
        if (file) {
            const size = (file.size / (1024 * 1024)).toFixed(2);
            const info = `Selected: ${file.name} (${size} MB)`;
            
            if (fileInfo.length) {
                fileInfo.text(info);
            } else {
                $(this).after(`<div class="file-info text-muted mt-1">${info}</div>`);
            }
            
            // Validate file size (50MB limit)
            if (file.size > 50 * 1024 * 1024) {
                showNotification('File size exceeds 50MB limit', 'error');
                $(this).val('');
                $(this).siblings('.file-info').remove();
            }
        } else {
            fileInfo.remove();
        }
    });
    
    // Drag and drop enhancement
    $('.form-control[type="file"]').each(function() {
        const fileInput = $(this);
        const dropZone = $('<div class="drop-zone border-2 border-dashed p-4 text-center rounded mt-2">' +
                          '<i class="fas fa-cloud-upload-alt fa-2x text-muted"></i><br>' +
                          '<span class="text-muted">Drag and drop files here or click to browse</span>' +
                          '</div>');
        
        fileInput.after(dropZone);
        fileInput.hide();
        
        dropZone.on('click', function() {
            fileInput.click();
        });
        
        dropZone.on('dragover', function(e) {
            e.preventDefault();
            $(this).addClass('border-primary bg-primary bg-opacity-10');
        });
        
        dropZone.on('dragleave', function() {
            $(this).removeClass('border-primary bg-primary bg-opacity-10');
        });
        
        dropZone.on('drop', function(e) {
            e.preventDefault();
            $(this).removeClass('border-primary bg-primary bg-opacity-10');
            
            const files = e.originalEvent.dataTransfer.files;
            if (files.length > 0) {
                fileInput[0].files = files;
                fileInput.trigger('change');
            }
        });
    });
}

// Initialize search enhancements
function initializeSearchEnhancements() {
    // Auto-complete for search fields
    $('input[name="search"]').on('input', function() {
        const query = $(this).val();
        if (query.length >= 2) {
            // Debounce search suggestions
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                // You can implement search suggestions here
                console.log('Search suggestions for:', query);
            }, 300);
        }
    });
    
    // Advanced search toggle
    $('.advanced-search-toggle').on('click', function() {
        $('.advanced-search-panel').slideToggle();
    });
    
    // Search history (localStorage)
    const searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    
    $('form').on('submit', function() {
        const searchInput = $(this).find('input[name="search"]');
        if (searchInput.length && searchInput.val().trim()) {
            const query = searchInput.val().trim();
            if (!searchHistory.includes(query)) {
                searchHistory.unshift(query);
                searchHistory.splice(10); // Keep only last 10 searches
                localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
            }
        }
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    const alertClass = type === 'error' ? 'alert-danger' : `alert-${type}`;
    const icon = type === 'error' ? 'fas fa-exclamation-triangle' : 
                 type === 'success' ? 'fas fa-check-circle' : 'fas fa-info-circle';
    
    const alert = $(`
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `);
    
    // Insert at top of main container
    $('main.container').prepend(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.alert('close');
    }, 5000);
}

function formatCurrency(amount, currency = 'R$') {
    return `${currency} ${parseFloat(amount).toFixed(2)}`;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR');
}

// Export functionality
function exportTableToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tr'));
    const csv = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('td, th'));
        return cells.slice(0, -1).map(cell => { // Exclude actions column
            let text = cell.textContent.trim();
            // Handle commas and quotes in CSV
            if (text.includes(',') || text.includes('"')) {
                text = '"' + text.replace(/"/g, '""') + '"';
            }
            return text;
        }).join(',');
    }).join('\n');
    
    // Download CSV
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// JSON data formatting for display
function formatJSONField(data, fieldName) {
    if (!data || data.length === 0) {
        return '<span class="text-muted">No data</span>';
    }
    
    if (Array.isArray(data)) {
        return `<span class="badge bg-info">${data.length} items</span>`;
    }
    
    return '<span class="badge bg-secondary">Object</span>';
}

// Performance monitoring
function measurePerformance(name, fn) {
    const start = performance.now();
    const result = fn();
    const end = performance.now();
    console.log(`${name} took ${end - start} milliseconds`);
    return result;
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    showNotification('An unexpected error occurred. Please refresh the page.', 'error');
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+/ or Cmd+/ for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        const searchInput = document.querySelector('input[name="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.querySelector('input[name="search"]:focus');
        if (searchInput) {
            searchInput.value = '';
            searchInput.blur();
        }
    }
});

// Mobile enhancements
if (window.innerWidth <= 768) {
    // Mobile-specific enhancements
    $(document).ready(function() {
        // Collapse long text on mobile
        $('.table td').each(function() {
            const text = $(this).text();
            if (text.length > 30) {
                $(this).attr('title', text);
                $(this).text(text.substring(0, 30) + '...');
            }
        });
        
        // Mobile navigation improvements
        $('.navbar-toggler').on('click', function() {
            $('body').toggleClass('nav-open');
        });
    });
}

// Progressive Web App features
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Service worker registration would go here
        console.log('Service Worker support detected');
    });
}
