import calendar
from datetime import date
from django.shortcuts import render
from scenarios.models import Scenario, ScheduledTheme
from django.http import JsonResponse
from django.utils.html import escape

# Константы на уровне модуля
MONTH_NAMES = [
    '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]

DAYS_OF_WEEK = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']


def _get_or_create_session(request):
    """Хелпер: получает или создаёт session_key."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def index(request):
    return render(request, 'core/index.html')


def about(request):
    return render(request, 'core/about.html')


def calendar_view(request):
    """Календарная сетка сценариев на месяц + автоопределение ближайшей темы."""
    today = date.today()

    # Безопасное получение года и месяца
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    # Нормализация месяца
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    # Границы для навигации
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    session_key = _get_or_create_session(request)

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    all_events = Scenario.objects.filter(
        session_key=session_key,
        scheduled_date__gte=first_day,
        scheduled_date__lte=last_day
    )

    planned_themes = ScheduledTheme.objects.filter(
        session_key=session_key,
        date__gte=first_day,
        date__lte=last_day
    )

    # Ближайшая незакрытая тема
    next_theme = ScheduledTheme.objects.filter(
        session_key=session_key,
        date__gte=today,
        scenario__isnull=True
    ).order_by('date').first()

    cal = calendar.monthcalendar(year, month)

    # Безопасный set_scenario
    set_scenario = request.GET.get('set_scenario', '')
    if set_scenario and not set_scenario.isdigit():
        set_scenario = ''

    context = {
        'year': year,
        'month': month,
        'month_name': MONTH_NAMES[month],
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today_year': today.year,
        'today_month': today.month,
        'calendar': cal,
        'all_events': all_events,
        'planned_themes': planned_themes,
        'today': today.day if today.month == month and today.year == year else None,
        'days_of_week': DAYS_OF_WEEK,
        'total_events': all_events.count(),
        'set_scenario': escape(set_scenario),
        'next_theme': next_theme,
    }

    return render(request, 'core/calendar.html', context)


def my_scenarios(request, session_key):
    """
    Персональная страница со всеми сценариями по session_key из URL.
    Доступ только для просмотра, без редактирования.
    """
    # Валидация: session_key должен быть буквенно-цифровым
    if not session_key or not session_key.isalnum():
        return render(request, 'core/access_denied.html', status=400)

    scenarios = Scenario.objects.filter(session_key=session_key)
    planned_themes = ScheduledTheme.objects.filter(session_key=session_key)

    return render(request, 'core/my_scenarios.html', {
        'scenarios': scenarios,
        'planned_themes': planned_themes,
        'session_key': session_key,
        'total_count': scenarios.count(),
        'themes_count': planned_themes.count(),
    })


def get_session_key_api(request):
    """Возвращает session_key текущего пользователя."""
    session_key = _get_or_create_session(request)
    return JsonResponse({'session_key': session_key})


def get_my_link(request):
    """Возвращает персональную ссылку пользователя."""
    session_key = _get_or_create_session(request)
    return JsonResponse({'session_key': session_key})