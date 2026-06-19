// -----------------------------------------------------------------------------
// Unified theme-management script.
// This file controls the light/dark theme preference across pages and keeps
// the user interface appearance consistent after refreshes and navigation.
// -----------------------------------------------------------------------------

function applyTheme(mode) {
    const isDarkMode = mode === 'dark';

    document.documentElement.classList.toggle('dark-mode', isDarkMode);
    document.documentElement.style.colorScheme = isDarkMode ? 'dark' : 'light';

    if (document.body) {
        document.body.classList.toggle('dark-mode', isDarkMode);
        document.body.style.colorScheme = isDarkMode ? 'dark' : 'light';
    }
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDarkMode = savedTheme ? savedTheme === 'dark' : prefersDark;

    applyTheme(isDarkMode ? 'dark' : 'light');
    updateThemeIcon();
}

function updateThemeIcon() {
    const themeBtn = document.getElementById('themeToggle');
    if (!themeBtn) {
        return;
    }

    const isDarkMode = document.documentElement.classList.contains('dark-mode') ||
        document.body?.classList.contains('dark-mode');
    themeBtn.textContent = isDarkMode ? '☀️' : '🌙';
    themeBtn.title = isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode';
}

function toggleTheme() {
    const isDarkMode = !document.documentElement.classList.contains('dark-mode');
    const nextTheme = isDarkMode ? 'dark' : 'light';

    applyTheme(nextTheme);
    localStorage.setItem('theme', nextTheme);
    updateThemeIcon();

    // Notify other tabs/windows of the same theme change.
    window.dispatchEvent(new StorageEvent('storage', {
        key: 'theme',
        newValue: nextTheme,
        storageArea: localStorage,
    }));
}

window.addEventListener('storage', (event) => {
    if (event.key === 'theme') {
        applyTheme(event.newValue === 'dark' ? 'dark' : 'light');
        updateThemeIcon();
    }
});

window.addEventListener('pageshow', () => {
    initializeTheme();
});

window.addEventListener('focus', () => {
    initializeTheme();
});

// Attach event listener to toggle button with fallback
function attachThemeListener() {
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        themeBtn.removeEventListener('click', toggleTheme); // Remove any existing listener
        themeBtn.addEventListener('click', toggleTheme);
        console.log('Theme toggle button listener attached');
    } else {
        console.warn('Theme toggle button element not found in DOM');
    }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeTheme();
        attachThemeListener();
    });
} else {
    initializeTheme();
    attachThemeListener();
}

// Re-attach listener after a short delay to ensure DOM is fully ready
setTimeout(() => {
    attachThemeListener();
}, 100);
