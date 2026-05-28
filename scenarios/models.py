from django.db import models


class Scenario(models.Model):
    DIRECTION_CHOICES = [
        ('civil', 'Гражданское'),
        ('patriotic', 'Патриотическое'),
        ('spiritual', 'Духовно-нравственное'),
        ('aesthetic', 'Эстетическое'),
        ('physical', 'Физическое'),
        ('labor', 'Трудовое'),
        ('ecological', 'Экологическое'),
        ('scientific', 'Ценности научного познания'),
    ]

    FORMAT_CHOICES = [
        ('class_hour', 'Классный час'),
        ('quiz', 'Квиз'),
        ('discussion', 'Беседа'),
        ('game', 'Игра'),
        ('workshop', 'Мастерская'),
        ('movie_club', 'Киноклуб'),
        ('debate', 'Дебаты'),
        ('project', 'Проектная сессия'),
    ]

    session_key = models.CharField('Сессия', max_length=40, db_index=True)
    share_key = models.CharField('Ключ доступа', max_length=64, blank=True, null=True)
    title = models.CharField('Название', max_length=500, blank=True)
    direction = models.CharField('Направление воспитания', max_length=20, choices=DIRECTION_CHOICES)
    grade = models.IntegerField('Класс (1-11)')
    theme = models.CharField('Тема занятия', max_length=500)
    duration = models.IntegerField('Продолжительность (минут)')
    format_type = models.CharField('Формат занятия', max_length=20, choices=FORMAT_CHOICES)

    goals = models.TextField('Цели и результаты', blank=True)
    stages = models.TextField('Этапы занятия', blank=True)
    materials = models.TextField('Материалы и ресурсы', blank=True)
    adaptation = models.TextField('Адаптация для возрастов', blank=True)

    legend = models.TextField('Легенда', blank=True)
    reflection = models.TextField('Рефлексия', blank=True)
    risks = models.TextField('Риски', blank=True)
    assessment = models.TextField('Критерии оценки', blank=True)
    teacher_tips = models.TextField('Советы учителю', blank=True)

    host_script = models.TextField('Сценарий для ведущего', blank=True)
    checklist = models.TextField('Чек-лист подготовки', blank=True)
    homework = models.TextField('Домашнее задание', blank=True)

    scheduled_date = models.DateField('Дата проведения', null=True, blank=True, db_index=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сценарий'
        verbose_name_plural = 'Сценарии'
        indexes = [
            models.Index(fields=['session_key', 'scheduled_date']),
            models.Index(fields=['session_key', '-created_at']),
        ]

    def __str__(self):
        return self.title or f'{self.get_direction_display()} - {self.theme}'

    @property
    def has_scheduled_date(self):
        return self.scheduled_date is not None

    @property
    def stage_count(self):
        import json
        try:
            stages = json.loads(self.stages) if self.stages else []
            return len(stages) if isinstance(stages, list) else 0
        except (json.JSONDecodeError, TypeError):
            return 0

    @property
    def total_duration_minutes(self):
        import json
        try:
            stages = json.loads(self.stages) if self.stages else []
            if not isinstance(stages, list):
                return 0
            return sum(
                stage.get('duration_minutes', 0)
                for stage in stages
                if isinstance(stage, dict)
            )
        except (json.JSONDecodeError, TypeError):
            return 0


class ScenarioVersion(models.Model):
    """
    История версий сценария.
    Сохраняет полный снимок сценария при каждом сохранении.
    Позволяет восстановить любую предыдущую версию.
    """
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.IntegerField('Номер версии')

    # Полный снимок всех полей сценария
    title = models.CharField('Название', max_length=500, blank=True)
    legend = models.TextField('Легенда', blank=True)
    goals = models.TextField('Цели и результаты', blank=True)
    stages = models.TextField('Этапы занятия', blank=True)
    materials = models.TextField('Материалы и ресурсы', blank=True)
    adaptation = models.TextField('Адаптация для возрастов', blank=True)
    reflection = models.TextField('Рефлексия', blank=True)
    risks = models.TextField('Риски', blank=True)
    assessment = models.TextField('Критерии оценки', blank=True)
    teacher_tips = models.TextField('Советы учителю', blank=True)
    host_script = models.TextField('Сценарий для ведущего', blank=True)
    checklist = models.TextField('Чек-лист подготовки', blank=True)
    homework = models.TextField('Домашнее задание', blank=True)

    # Мета-информация о версии
    change_description = models.CharField(
        'Описание изменений',
        max_length=500,
        blank=True,
        help_text='Что изменилось в этой версии'
    )
    created_by = models.CharField(
        'Кто создал',
        max_length=40,
        blank=True,
        help_text='session_key пользователя'
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        verbose_name = 'Версия сценария'
        verbose_name_plural = 'Версии сценариев'
        unique_together = [['scenario', 'version_number']]
        indexes = [
            models.Index(fields=['scenario', '-version_number']),
        ]

    def __str__(self):
        return f'{self.scenario} — версия {self.version_number}'

    @property
    def preview(self):
        if self.change_description:
            return self.change_description
        return f'Версия {self.version_number} от {self.created_at:%d.%m.%Y %H:%M}'

    @property
    def total_duration(self):
        import json
        try:
            stages = json.loads(self.stages) if self.stages else []
            if not isinstance(stages, list):
                return 0
            return sum(s.get('duration_minutes', 0) for s in stages if isinstance(s, dict))
        except (json.JSONDecodeError, TypeError):
            return 0


class LLMRequestLog(models.Model):
    session_key = models.CharField('Сессия', max_length=40, db_index=True)
    client_identifier = models.CharField(
        'Идентификатор клиента',
        max_length=512,
        db_index=True,
        default='',
        help_text='IP|UserAgent — не сбрасывается при очистке кук'
    )
    request_type = models.CharField('Тип запроса', max_length=50)
    tokens_used = models.IntegerField('Потрачено токенов', default=0)
    success = models.BooleanField('Успешно', default=True)
    error_message = models.TextField('Ошибка', blank=True)
    created_at = models.DateTimeField('Время запроса', auto_now_add=True)

    class Meta:
        verbose_name = 'Лог запроса к LLM'
        verbose_name_plural = 'Логи запросов к LLM'
        indexes = [
            models.Index(fields=['client_identifier', '-created_at']),
            models.Index(fields=['session_key', '-created_at']),
        ]

    def __str__(self):
        return f'{self.client_identifier[:20]}... - {self.request_type} ({self.created_at:%d.%m.%Y %H:%M})'


class ScheduledTheme(models.Model):
    """Тема из загруженного плана воспитательной работы."""
    session_key = models.CharField('Сессия', max_length=40, db_index=True)
    theme = models.CharField('Тема', max_length=500)
    grade = models.IntegerField('Класс', null=True, blank=True)
    date = models.DateField('Дата проведения', db_index=True)
    is_completed = models.BooleanField('Готово', default=False)
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_themes'
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        ordering = ['date']
        verbose_name = 'Тема из плана'
        verbose_name_plural = 'Темы из плана'
        indexes = [
            models.Index(fields=['session_key', 'date']),
        ]

    def __str__(self):
        return f'{self.date} - {self.theme}'