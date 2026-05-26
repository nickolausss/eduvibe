from django import forms
from .models import Scenario


class ScenarioCreateForm(forms.ModelForm):
    """Форма-конструктор по ТЗ. Собирает все параметры для генерации."""

    # Дополнительные поля, которых нет в модели
    subjects = forms.CharField(
        label='Предметная область (интеграция)',
        help_text='Например: История + Литература, Биология + Экология',
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'История + Обществознание'})
    )

    relevance = forms.CharField(
        label='Актуальность',
        help_text='Почему это важно именно сейчас?',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Низкая мотивация к чтению, необходимость сплотить класс...'})
    )

    problem = forms.CharField(
        label='Решаемая проблема',
        help_text='Какую проблему решает мероприятие?',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Отсутствие навыков командной работы...'})
    )

    goal = forms.CharField(
        label='Воспитательная цель',
        help_text='Какое качество личности формируем?',
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Чувство патриотизма, экологическая ответственность...'})
    )

    SOFT_SKILLS_CHOICES = [
        ('communication', 'Коммуникация'),
        ('critical_thinking', 'Критическое мышление'),
        ('creativity', 'Креативность'),
        ('collaboration', 'Коллаборация (работа в команде)'),
        ('leadership', 'Лидерство'),
        ('emotional_intelligence', 'Эмоциональный интеллект'),
        ('public_speaking', 'Публичные выступления'),
        ('time_management', 'Тайм-менеджмент'),
        ('problem_solving', 'Решение проблем'),
        ('media_literacy', 'Медиаграмотность'),
    ]

    soft_skills = forms.MultipleChoiceField(
        label='Развиваемые Soft Skills',
        choices=SOFT_SKILLS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    need_legend = forms.BooleanField(
        label='Добавить легенду (крючок вовлечения)',
        help_text='Сюжетная линия, которая превращает обычный урок в приключение',
        required=False,
        initial=True
    )

    MECHANICS_CHOICES = [
        ('gamification', 'Геймификация (баллы, уровни, награды)'),
        ('station_rotation', 'Смена рабочих зон / Вертушка'),
        ('challenge', 'Челленджи и испытания'),
        ('quest', 'Квест (цепочка заданий)'),
        ('role_play', 'Ролевая игра'),
        ('project_work', 'Проектная работа'),
        ('case_method', 'Кейс-метод (разбор ситуаций)'),
    ]

    mechanics = forms.MultipleChoiceField(
        label='Игровые механики',
        choices=MECHANICS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    EQUIPMENT_CHOICES = [
        ('projector', 'Проектор'),
        ('speakers', 'Колонки / Аудиосистема'),
        ('computers', 'Компьютеры / Ноутбуки'),
        ('tablets', 'Планшеты'),
        ('interactive_board', 'Интерактивная доска'),
        ('none', 'Ничего, только раздаточные материалы'),
    ]

    equipment = forms.MultipleChoiceField(
        label='Доступное оборудование',
        choices=EQUIPMENT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    CLASSROOM_LEVEL_CHOICES = [
        ('minimal', 'Минимальное (доска и мел)'),
        ('standard', 'Стандартное (проектор + экран)'),
        ('advanced', 'Продвинутое (интерактивная доска, планшеты)'),
        ('full', 'Полное (компьютерный класс, 3D-принтер, лаборатория)'),
    ]

    classroom_level = forms.ChoiceField(
        label='Уровень оснащения кабинета',
        choices=CLASSROOM_LEVEL_CHOICES,
        initial='standard',
        widget=forms.RadioSelect
    )

    class_features = forms.CharField(
        label='Особенности класса',
        help_text='Есть ли дети с ОВЗ, отстающие, конфликты, низкая мотивация?',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'В классе есть слабослышащий ученик / низкая дисциплина / есть явные лидеры и аутсайдеры...'})
    )

    extra_notes = forms.CharField(
        label='Дополнительные пожелания',
        help_text='Что ещё важно учесть при генерации?',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Нужна патриотическая песня в финале / обязательно групповую работу...'})
    )

    class Meta:
        model = Scenario
        fields = [
            'direction',
            'grade',
            'theme',
            'duration',
            'format_type',
            'title',
        ]
        widgets = {
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'grade': forms.NumberInput(attrs={'min': 1, 'max': 11}),
            'duration': forms.NumberInput(attrs={'min': 20, 'max': 90, 'value': 40}),
            'format_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_grade(self):
        grade = self.cleaned_data['grade']
        if grade < 1 or grade > 11:
            raise forms.ValidationError('Класс должен быть от 1 до 11')
        return grade

    def clean_duration(self):
        duration = self.cleaned_data['duration']
        if duration < 15 or duration > 120:
            raise forms.ValidationError('Длительность должна быть от 15 до 120 минут')
        return duration

    def get_age_from_grade(self, grade):
        """Примерный возраст по классу."""
        return grade + 6

    def build_params_for_prompt(self) -> dict:
        """Собирает все данные формы в словарь для промпта."""
        data = self.cleaned_data
        grade = data['grade']

        return {
            'format_type_label': dict(Scenario.FORMAT_CHOICES).get(data['format_type'], ''),
            'grade': grade,
            'age': grade + 6,
            'duration': data['duration'],
            'direction_label': dict(Scenario.DIRECTION_CHOICES).get(data['direction'], ''),
            'theme': data['theme'],
            'subjects': data.get('subjects', ''),
            'relevance': data.get('relevance', ''),
            'problem': data.get('problem', ''),
            'goal': data.get('goal', ''),
            'soft_skills': ', '.join(data.get('soft_skills', [])),
            'need_legend': data.get('need_legend', True),
            'mechanics': ', '.join(data.get('mechanics', [])),
            'equipment': ', '.join(data.get('equipment', [])),
            'classroom_level': data.get('classroom_level', 'standard'),
            'class_features': data.get('class_features', ''),
            'extra_notes': data.get('extra_notes', ''),
        }