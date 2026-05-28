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
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// === Шеринг сценария ===
async function shareScenario(pk) {
    try {
        const response = await fetch(`/scenarios/${pk}/share/`, { 
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() }
        });
        const data = await response.json();
        if (data.status === 'success') {
            navigator.clipboard.writeText(data.url).then(() => {
                showToast('Ссылка скопирована');
            });
        }
    } catch (e) {
        showToast('Ошибка');
    }
}

async function unshareScenario(pk) {
    try {
        const response = await fetch(`/scenarios/${pk}/unshare/`, { 
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() }
        });
        const data = await response.json();
        if (data.status === 'success') {
            showToast('Ссылка удалена');
        }
    } catch (e) {
        showToast('Ошибка');
    }
}

// === Тёмная тема ===
function toggleTheme() {
    const html = document.documentElement;
    const btn = document.getElementById('theme-btn');
    html.classList.toggle('dark');
    const isDark = html.classList.contains('dark');
    btn.style.transform = isDark ? 'rotate(180deg)' : 'rotate(0deg)';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// === CSRF-токен ===
function getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

// === Полноэкранный режим ===
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

// === Привязка к дате ===
function bindScenarioToDate(pk, dateStr) {
    fetch(`/scenarios/${pk}/set-date/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCSRFToken()
        },
        body: `date=${dateStr}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('Сценарий добавлен в календарь');
            setTimeout(() => { window.location.href = '/calendar/'; }, 800);
        }
    });
}