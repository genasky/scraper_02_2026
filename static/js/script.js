// Global variables
let currentResults = [];

// DOM elements
const searchForm = document.getElementById('searchForm');
const resultsSection = document.getElementById('resultsSection');
const loading = document.getElementById('loading');
const resultsContainer = document.getElementById('resultsContainer');
const resultsCount = document.querySelector('.results-count');
const toast = document.getElementById('toast');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    searchForm.addEventListener('submit', handleSearch);
});

// Handle search form submission
async function handleSearch(e) {
    e.preventDefault();
    
    const formData = new FormData(searchForm);
    const query = formData.get('query').trim();
    
    if (!query) {
        showToast('Введите поисковый запрос', 'error');
        return;
    }
    
    // Get selected engines
    const engines = [];
    const engineCheckboxes = document.querySelectorAll('input[name="engines"]:checked');
    engineCheckboxes.forEach(checkbox => {
        engines.push(checkbox.value);
    });
    
    if (engines.length === 0) {
        showToast('Выберите хотя бы одну поисковую систему', 'error');
        return;
    }
    
    // Build proxy URL from advanced settings
    const proxyType = formData.get('proxy_type');
    const proxyHost = formData.get('proxy_host');
    const proxyPort = formData.get('proxy_port');
    const proxyUsername = formData.get('proxy_username');
    const proxyPassword = formData.get('proxy_password');
    
    let proxy = '';
    if (proxyType && proxyHost && proxyPort) {
        proxy = `${proxyType}://`;
        if (proxyUsername && proxyPassword) {
            proxy += `${encodeURIComponent(proxyUsername)}:${encodeURIComponent(proxyPassword)}@`;
        }
        proxy += `${proxyHost}:${proxyPort}`;
    }
    
    // Prepare search data
    const searchData = {
        query: query,
        engines: engines,
        pages: parseInt(formData.get('pages')),
        proxy: proxy,
        ignore_duplicates: formData.has('ignore_duplicates'),
        filter: formData.get('filter') || '',
        language: formData.get('language') || 'ru',
        country: formData.get('country') || '',
        safe_search: formData.get('safe_search') || 'moderate',
        result_type: formData.get('result_type') || 'all',
        use_tor: formData.has('use_tor'),
        proxy_verify_ssl: formData.has('proxy_verify_ssl')
    };
    
    // Show loading
    showLoading(true);
    resultsSection.style.display = 'block';
    
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(searchData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentResults = data.results;
            displayResults(data.results, data.query, data.engines);
            showToast(`Найдено ${data.total} результатов`, 'success');
        } else {
            showToast(data.error || 'Произошла ошибка при поиске', 'error');
            showLoading(false);
        }
    } catch (error) {
        console.error('Search error:', error);
        showToast('Ошибка соединения с сервером', 'error');
        showLoading(false);
    }
}

// Display search results
function displayResults(results, query, engines) {
    showLoading(false);
    
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="no-results">
                <p>По запросу "${query}" ничего не найдено</p>
                <p>Попробуйте изменить запрос или выбрать другие поисковые системы</p>
            </div>
        `;
        resultsCount.textContent = '0 результатов';
        return;
    }
    
    // Update results count
    resultsCount.textContent = `${results.length} результатов`;
    
    // Generate results HTML
    const resultsHTML = results.map((result, index) => `
        <div class="result-item">
            <a href="${result.link}" target="_blank" class="result-title">
                ${escapeHtml(result.title)}
            </a>
            <div class="result-url">${escapeHtml(result.link)}</div>
            <div class="result-snippet">${escapeHtml(result.snippet)}</div>
            <span class="result-engine">${result.engine}</span>
        </div>
    `).join('');
    
    resultsContainer.innerHTML = resultsHTML;
}

// Show/hide loading state
function showLoading(show) {
    if (show) {
        loading.style.display = 'block';
        resultsContainer.style.display = 'none';
    } else {
        loading.style.display = 'none';
        resultsContainer.style.display = 'grid';
    }
}

// Export results
async function exportResults(format) {
    if (currentResults.length === 0) {
        showToast('Нет результатов для экспорта', 'error');
        return;
    }
    
    try {
        const response = await fetch('/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                results: currentResults,
                format: format
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Trigger download
            const link = document.createElement('a');
            link.href = data.download_url;
            link.download = data.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showToast(`Результаты экспортированы в ${format.toUpperCase()}`, 'success');
        } else {
            showToast(data.error || 'Ошибка экспорта', 'error');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Ошибка экспорта', 'error');
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    // Show toast
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-resize textarea if needed
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to submit search
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const activeElement = document.activeElement;
        if (activeElement && activeElement.id === 'query') {
            searchForm.dispatchEvent(new Event('submit'));
        }
    }
    
    // Escape to clear results
    if (e.key === 'Escape') {
        if (resultsSection.style.display === 'block') {
            resultsSection.style.display = 'none';
            currentResults = [];
        }
    }
});

// Smooth scroll to results when search is performed
function scrollToResults() {
    if (resultsSection.style.display === 'block') {
        resultsSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Add smooth scroll after search results are displayed
const originalDisplayResults = displayResults;
displayResults = function(results, query, engines) {
    originalDisplayResults(results, query, engines);
    setTimeout(scrollToResults, 100);
};

// Form validation
function validateForm() {
    const query = document.getElementById('query').value.trim();
    const engineCheckboxes = document.querySelectorAll('input[name="engines"]:checked');
    
    if (!query) {
        showToast('Введите поисковый запрос', 'error');
        return false;
    }
    
    if (engineCheckboxes.length === 0) {
        showToast('Выберите хотя бы одну поисковую систему', 'error');
        return false;
    }
    
    return true;
}

// Progressive enhancement - check if browser supports required features
if (!window.fetch || !window.Promise) {
    showToast('Ваш браузер не поддерживает необходимые функции. Пожалуйста, обновите браузер.', 'error');
    // Disable form
    searchForm.style.opacity = '0.5';
    searchForm.style.pointerEvents = 'none';
}

// Service Worker registration for offline support (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('SW registered: ', registration);
            })
            .catch(function(registrationError) {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Toggle all search engines
function toggleAllEngines(selectAllCheckbox) {
    const engineCheckboxes = document.querySelectorAll('input[name="engines"]');
    engineCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}

// Toggle advanced settings
function toggleAdvancedSettings() {
    const advancedContent = document.getElementById('advancedContent');
    const toggleButton = document.querySelector('.advanced-toggle');
    
    if (advancedContent.style.display === 'none') {
        advancedContent.style.display = 'block';
        toggleButton.innerHTML = '<i class="fas fa-chevron-up"></i> Скрыть расширенные настройки';
    } else {
        advancedContent.style.display = 'none';
        toggleButton.innerHTML = '<i class="fas fa-cog"></i> Расширенные настройки';
    }
}

// Update proxy placeholder based on proxy type
function updateProxyPlaceholder() {
    const proxyType = document.getElementById('proxy_type').value;
    const proxyHost = document.getElementById('proxy_host');
    const proxyPort = document.getElementById('proxy_port');
    
    // Set default ports based on proxy type
    switch (proxyType) {
        case 'http':
            proxyPort.placeholder = '8080';
            proxyHost.placeholder = '127.0.0.1';
            break;
        case 'https':
            proxyPort.placeholder = '443';
            proxyHost.placeholder = '127.0.0.1';
            break;
        case 'socks4':
        case 'socks5':
            proxyPort.placeholder = '1080';
            proxyHost.placeholder = '127.0.0.1';
            break;
        default:
            proxyPort.placeholder = '8080';
            proxyHost.placeholder = '127.0.0.1';
    }
}
