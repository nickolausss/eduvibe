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

// === 3. Кнопка «Наверх» ===
const scrollBtn = document.createElement('button');
scrollBtn.className = 'scroll-top-btn';
scrollBtn.title = 'Наверх';
const img = document.createElement('img');
img.src = '/static/images/arrow-up.png';
img.alt = '↑';
scrollBtn.appendChild(img);
document.body.appendChild(scrollBtn);

scrollBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

window.addEventListener('scroll', () => {
    if (window.scrollY > 400) {
        scrollBtn.style.opacity = '1';
        scrollBtn.style.pointerEvents = 'auto';
    } else {
        scrollBtn.style.opacity = '0';
        scrollBtn.style.pointerEvents = 'none';
    }
});

// === 4. Копирование всего сценария ===
function copyFullScenario() {
    const container = document.querySelector('section .container');
    if (!container) return;

    const clone = container.cloneNode(true);
    
    clone.querySelectorAll('.btn, button, .actions').forEach(el => el.remove());

    clone.querySelectorAll('details').forEach(d => {
        d.setAttribute('open', '');
    });

    clone.querySelectorAll('details ul li, ul li').forEach(li => {
        li.textContent = '• ' + li.textContent.replace(/^[•\-]\s*/, '');
    });

    const html = clone.innerHTML.trim();
    const text = clone.innerText.trim()
        .replace(/\n{3,}/g, '\n\n')
        .replace(/^\s+/gm, '');

    const blob = new Blob([html], { type: 'text/html' });
    const clipboardItem = new ClipboardItem({
        'text/html': blob,
        'text/plain': new Blob([text], { type: 'text/plain' })
    });

    navigator.clipboard.write([clipboardItem]).then(() => {
        showToast('✅ Сценарий скопирован в буфер обмена');
    }).catch(() => {
        showToast('❌ Не удалось скопировать');
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

async function shareScenario(pk) {
    try {
        const response = await fetch(`/scenarios/${pk}/share/`, { 
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() }
        });
        const data = await response.json();
        if (data.status === 'success') {
            navigator.clipboard.writeText(data.url).then(() => {
                showToast('✅ Ссылка скопирована! Только тот, у кого есть ссылка, увидит сценарий.');
                // Меняем кнопку без перезагрузки
                const btns = document.querySelectorAll('.actions button, .actions a');
                btns.forEach(b => {
                    if (b.textContent.includes('Поделиться')) {
                        b.outerHTML = `<button onclick="unshareScenario(${pk})" class="btn btn-outline">🔗 Удалить ссылку</button>`;
                    }
                });
            });
        }
    } catch (e) {
        showToast('❌ Ошибка');
    }
}

async function shareScenario(pk) {
    try {
        const response = await fetch(`/scenarios/${pk}/share/`, { 
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() }
        });
        const data = await response.json();
        if (data.status === 'success') {
            navigator.clipboard.writeText(data.url).then(() => {
                showToast('✅ Ссылка скопирована!');
            });
            // Меняем кнопку
            const btn = document.querySelector('button[onclick*="shareScenario"]');
            if (btn) {
                btn.textContent = '🔗 Удалить ссылку';
                btn.setAttribute('onclick', `unshareScenario(${pk})`);
            }
        }
    } catch (e) {
        showToast('❌ Ошибка');
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
            showToast('🔒 Ссылка удалена.');
            // Меняем кнопку обратно
            const btn = document.querySelector('button[onclick*="unshareScenario"]');
            if (btn) {
                btn.textContent = '📋 Поделиться';
                btn.setAttribute('onclick', `shareScenario(${pk})`);
            }
        }
    } catch (e) {
        showToast('❌ Ошибка');
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

// Получение CSRF-токена
function getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

// === Полноэкранный режим ===
function toggleFullscreen() {
    const header = document.querySelector('.navbar');
    const footer = document.querySelector('.footer');
    const btn = document.getElementById('fullscreen-btn');
    
    const isFullscreen = document.body.classList.toggle('fullscreen-mode');
    
    if (isFullscreen) {
        header.style.display = 'none';
        footer.style.display = 'none';
        btn.textContent = '✕ Выйти';
    } else {
        header.style.display = '';
        footer.style.display = '';
        btn.textContent = '📺 На весь экран';
    }
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && document.body.classList.contains('fullscreen-mode')) {
        toggleFullscreen();
    }
});

function getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

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
            showToast('✅ Сценарий добавлен в календарь');
            setTimeout(() => { window.location.href = '/calendar/'; }, 800);
        } else {
            showToast('❌ Ошибка');
        }
    });
}