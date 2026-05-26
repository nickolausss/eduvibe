"""
Конвертирует JSON-поля всех сценариев в HTML.
Запуск: python manage.py convert_json_to_html
"""
import json
from django.core.management.base import BaseCommand
from scenarios.models import Scenario


class Command(BaseCommand):
    help = 'Конвертирует JSON-поля сценариев в HTML для WYSIWYG-редактора'

    def handle(self, *args, **options):
        scenarios = Scenario.objects.all()
        converted = 0

        for scenario in scenarios:
            changed = False

            # Цели
            if scenario.goals and self._looks_like_json(scenario.goals):
                data = json.loads(scenario.goals)
                scenario.goals = self._goals_to_html(data)
                changed = True

            # Этапы
            if scenario.stages and self._looks_like_json(scenario.stages):
                data = json.loads(scenario.stages)
                scenario.stages = self._stages_to_html(data)
                changed = True

            # Материалы
            if scenario.materials and self._looks_like_json(scenario.materials):
                data = json.loads(scenario.materials)
                scenario.materials = self._materials_to_html(data)
                changed = True

            # Адаптация
            if scenario.adaptation and self._looks_like_json(scenario.adaptation):
                data = json.loads(scenario.adaptation)
                scenario.adaptation = self._adaptation_to_html(data)
                changed = True

            # Рефлексия
            if scenario.reflection and self._looks_like_json(scenario.reflection):
                data = json.loads(scenario.reflection)
                scenario.reflection = self._reflection_to_html(data)
                changed = True

            # Риски
            if scenario.risks and self._looks_like_json(scenario.risks):
                data = json.loads(scenario.risks)
                scenario.risks = self._risks_to_html(data)
                changed = True

            # Оценка
            if scenario.assessment and self._looks_like_json(scenario.assessment):
                data = json.loads(scenario.assessment)
                scenario.assessment = self._assessment_to_html(data)
                changed = True

            # Советы учителю
            if scenario.teacher_tips and self._looks_like_json(scenario.teacher_tips):
                data = json.loads(scenario.teacher_tips)
                scenario.teacher_tips = self._tips_to_html(data)
                changed = True

            # Чек-лист
            if scenario.checklist and self._looks_like_json(scenario.checklist):
                data = json.loads(scenario.checklist)
                scenario.checklist = self._checklist_to_html(data)
                changed = True

            # Домашнее задание
            if scenario.homework and self._looks_like_json(scenario.homework):
                data = json.loads(scenario.homework)
                scenario.homework = self._homework_to_html(data)
                changed = True

            if changed:
                scenario.save()
                converted += 1
                self.stdout.write(f'✅ Сценарий {scenario.pk}: "{scenario.title or scenario.theme}"')

        self.stdout.write(self.style.SUCCESS(f'\nГотово! Конвертировано сценариев: {converted}'))

    def _looks_like_json(self, text):
        """Проверяет, похожа ли строка на JSON."""
        if not text or not text.strip():
            return False
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))

    def _goals_to_html(self, data):
        html = '<h2>Цели</h2>'
        if data.get('educational'):
            html += f'<p><strong>Воспитательная:</strong> {data["educational"]}</p>'
        if data.get('practical'):
            html += f'<p><strong>Практическая:</strong> {data["practical"]}</p>'
        if data.get('soft_skills'):
            html += f'<p><strong>Soft Skills:</strong> {data["soft_skills"]}</p>'
        return html

    def _stages_to_html(self, stages):
        if not stages:
            return ''
        html = '<h2>Этапы занятия</h2>'
        for i, stage in enumerate(stages, 1):
            name = stage.get('name', f'Этап {i}')
            duration = stage.get('duration_minutes', '')
            stype = stage.get('type', '')
            html += f'<h3>{i}. {name} ({duration} мин, {stype})</h3>'
            if stage.get('description'):
                html += f'<p>{stage["description"]}</p>'
            if stage.get('teacher_actions'):
                html += '<p><strong>Действия учителя:</strong></p><ul>'
                for action in stage['teacher_actions']:
                    html += f'<li>{action}</li>'
                html += '</ul>'
            if stage.get('student_actions'):
                html += '<p><strong>Действия учеников:</strong></p><ul>'
                for action in stage['student_actions']:
                    html += f'<li>{action}</li>'
                html += '</ul>'
            if stage.get('questions'):
                html += '<p><strong>Вопросы и ответы:</strong></p><ul>'
                for q in stage['questions']:
                    html += f'<li>{q}</li>'
                html += '</ul>'
            if stage.get('materials'):
                html += f'<p><strong>Материалы:</strong> {", ".join(stage["materials"])}</p>'
            if stage.get('mechanics'):
                html += f'<p><strong>Механика:</strong> {stage["mechanics"]}</p>'
            html += '<hr>'
        return html

    def _materials_to_html(self, data):
        html = '<h2>Материалы и ресурсы</h2>'
        labels = {'equipment': 'Оборудование', 'stationery': 'Канцелярия', 'digital': 'Цифровые', 'props': 'Реквизит'}
        for key, label in labels.items():
            if data.get(key):
                html += f'<p><strong>{label}:</strong></p><ul>'
                for item in data[key]:
                    html += f'<li>{item}</li>'
                html += '</ul>'
        return html

    def _adaptation_to_html(self, data):
        html = '<h2>Адаптация</h2>'
        if data.get('for_juniors'):
            html += f'<p><strong>Для 5-6 классов:</strong> {data["for_juniors"]}</p>'
        if data.get('for_seniors'):
            html += f'<p><strong>Для 10-11 классов:</strong> {data["for_seniors"]}</p>'
        if data.get('for_ovz'):
            html += f'<p><strong>Для детей с ОВЗ:</strong> {data["for_ovz"]}</p>'
        return html

    def _reflection_to_html(self, data):
        html = '<h2>Рефлексия</h2>'
        if data.get('method'):
            html += f'<p><strong>Метод:</strong> {data["method"]}</p>'
        if data.get('questions'):
            html += '<p><strong>Вопросы:</strong></p><ul>'
            for q in data['questions']:
                html += f'<li>{q}</li>'
            html += '</ul>'
        if data.get('teacher_script'):
            html += f'<p><strong>Слова учителя:</strong> {data["teacher_script"]}</p>'
        return html

    def _risks_to_html(self, data):
        html = '<h2>Риски</h2>'
        labels = {'technical': 'Технический', 'methodical': 'Методический', 'dynamic': 'Динамический', 'conflict': 'Конфликтный'}
        for key, label in labels.items():
            if data.get(key):
                html += f'<p><strong>{label}:</strong> {data[key]}</p>'
        return html

    def _assessment_to_html(self, data):
        html = '<h2>Оценка эффективности</h2>'
        if data.get('quantitative'):
            html += f'<p><strong>Количественная:</strong> {data["quantitative"]}</p>'
        if data.get('qualitative'):
            html += f'<p><strong>Качественная:</strong> {data["qualitative"]}</p>'
        return html

    def _tips_to_html(self, data):
        if isinstance(data, list):
            html = '<h2>Советы учителю</h2><ol>'
            for tip in data:
                html += f'<li>{tip}</li>'
            html += '</ol>'
            return html
        return str(data)

    def _checklist_to_html(self, data):
        html = '<h2>Чек-лист подготовки</h2>'
        labels = {'week_before': 'За неделю', 'day_before': 'За день', 'hour_before': 'За час', 'five_minutes': 'За 5 минут'}
        for key, label in labels.items():
            if data.get(key):
                html += f'<h3>{label}</h3><ul>'
                for item in data[key]:
                    html += f'<li>{item}</li>'
                html += '</ul>'
        return html

    def _homework_to_html(self, data):
        if not data.get('variants'):
            return ''
        html = '<h2>Домашнее задание</h2>'
        for variant in data['variants']:
            html += f'<h3>{variant.get("title", "")}</h3>'
            if variant.get('description'):
                html += f'<p>{variant["description"]}</p>'
            if variant.get('materials'):
                html += f'<p><em>Понадобится: {variant["materials"]}</em></p>'
            if variant.get('deadline'):
                html += f'<p><em>Срок: {variant["deadline"]}</em></p>'
        return html