// === CSRF-токен (единая версия для всего проекта) ===
function getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

// === 1. Плавное появление секций при скролле ===
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.card, .stage, .feature-card, .hero-content, .hero-image').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'all 0.5s ease';
    observer.observe(el);
});

// === 2. Подсветка активного пункта навигации ===
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href && (currentPath === href || (href !== '/' && currentPath.startsWith(href)))) {
        link.style.color = 'hsl(var(--primary))';
        link.style.fontWeight = '600';
    }
});

// === 3. Копирование всего сценария ===
function copyFullScenario() {
    const container = document.querySelector('section .container');
    if (!container) return;

    const clone = container.cloneNode(true);
    clone.querySelectorAll('.btn, button, .actions').forEach(el => el.remove());
    clone.querySelectorAll('details').forEach(d => d.setAttribute('open', ''));
    clone.querySelectorAll('details ul li, ul li').forEach(li => {
        li.textContent = '• ' + li.textContent.replace(/^[•\-]\s*/, '');
    });

    const text = clone.innerText.trim().replace(/\n{3,}/g, '\n\n').replace(/^\s+/gm, '');
    navigator.clipboard.writeText(text).then(() => {
        showToast('Сценарий скопирован');
    }).catch(() => {
        showToast('Не удалось скопировать');
    });
}

// === Toast-уведомление ===
function showToast(message) {
    const existingToast = document.querySelector('.toast');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// === Тёмная тема ===
function toggleTheme() {
    const html = document.documentElement;
    const btn = document.getElementById('theme-btn');
    html.classList.toggle('dark');
    const isDark = html.classList.contains('dark');
    if (btn) {
        btn.style.transform = isDark ? 'rotate(180deg)' : 'rotate(0deg)';
    }
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// === Полноэкранный режим ===
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
        const navbar = document.querySelector('.navbar');
        if (navbar) navbar.style.display = 'none';
    } else {
        document.exitFullscreen();
        const navbar = document.querySelector('.navbar');
        if (navbar) navbar.style.display = '';
    }
}

document.addEventListener('fullscreenchange', function() {
    if (!document.fullscreenElement) {
        const navbar = document.querySelector('.navbar');
        if (navbar) navbar.style.display = '';
    }
});