import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings
from .models import Scenario, ScenarioVersion, ScheduledTheme
from .prompts import (
    build_structure_prompt,
    build_all_stages_prompt,
    build_reflection_prompt,
    build_materials_adaptation_prompt,
    build_risks_assessment_tips_prompt,
    build_host_script_checklist_homework_prompt,
    build_regenerate_block_prompt,
)

logger = logging.getLogger(__name__)


class DeepSeekClientPool:
    """Пул клиентов для параллельных запросов."""

    def __init__(self, api_keys, project_id):
        from openai import OpenAI
        self.clients = []
        for key in api_keys:
            if key.strip():
                self.clients.append({
                    'client': OpenAI(
                        api_key=key.strip(),
                        base_url="https://ai.api.cloud.yandex.net/v1",
                    ),
                    'key': key.strip()[:10] + '...'
                })
        self.project_id = project_id
        self.index = 0
        logger.info(f"Пул клиентов создан: {len(self.clients)} ключей")

    def get_client(self):
        if not self.clients:
            from openai import OpenAI
            api_key = settings.YANDEX_API_KEY
            return OpenAI(
                api_key=api_key,
                base_url="https://ai.api.cloud.yandex.net/v1",
            )
        client_info = self.clients[self.index]
        self.index = (self.index + 1) % len(self.clients)
        return client_info['client']


class DeepSeekClient:
    """Клиент для YandexGPT 5.1 Pro."""

    def __init__(self, pool=None):
        self.pool = pool
        self.project_id = settings.YANDEX_PROJECT_ID
        if not pool:
            from openai import OpenAI
            api_key = settings.YANDEX_API_KEY
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://ai.api.cloud.yandex.net/v1",
            )

    def _get_client(self):
        if self.pool:
            return self.pool.get_client()
        return self.client

    def generate(self, system_prompt: str, user_input: str, temperature: float = 0.4, max_tokens: int = 7000, max_retries: int = 10) -> dict:
        """Отправляет запрос. При плохом JSON — переотправляет."""
        last_error = None

        for attempt in range(1, max_retries + 1):
            logger.info(f"Попытка {attempt}/{max_retries}")
            start_time = time.time()

            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model="gpt://b1g2jhvu89pmefv3qk8v/yandexgpt-5.1/latest",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=120,
                    extra_headers={"X-Yandex-Project-ID": self.project_id}
                )

                elapsed = time.time() - start_time
                logger.info(f"✅ Ответ за {elapsed:.1f} сек")

                if not response.choices:
                    raise ValueError("Нет choices")

                choice = response.choices[0]

                if not choice.message or not choice.message.content:
                    finish = choice.finish_reason if hasattr(choice, 'finish_reason') else 'неизвестно'
                    logger.warning(f"❌ Пустой контент. Причина: {finish}")
                    if attempt < max_retries:
                        time.sleep(5)
                        continue
                    raise ValueError(f"Пустой контент после {max_retries} попыток")

                output_text = choice.message.content
                logger.info(f"📝 {len(output_text)} символов")

                output_text = self._clean_json_response(output_text)
                result = self._safe_parse_json(output_text)

                logger.info(f"✅ JSON распарсен (попытка {attempt})")
                return result

            except ValueError as e:
                if "Не удалось распарсить JSON" in str(e):
                    logger.warning(f"⚠️ Плохой JSON, пробуем снова...")
                    if attempt < max_retries:
                        time.sleep(5)
                        continue
                raise

            except Exception as e:
                logger.error(f"❌ Ошибка: {type(e).__name__}: {e}")
                if attempt < max_retries:
                    time.sleep(7)
                    continue
                raise

        raise last_error if last_error else Exception("Не удалось")

    def validate_scenario(self, scenario_json: str, max_retries: int = 3) -> dict:
        """Отправляет сценарий на проверку модератору. При ошибках возвращает исходный JSON."""
        system_prompt = """Ты — модератор образовательного контента. Проверь сценарий внеурочного занятия.

## ЧТО ПРОВЕРИТЬ
1. Безопасность: нет ли запрещённых тем, вредных советов, политики, нецензурной лексики?
2. Структура: все ли разделы заполнены? Нет ли пустых полей?
3. JSON: нет ли синтаксических ошибок (запятые, кавычки, скобки)?

## ЧТО ДЕЛАТЬ
- Если всё правильно — верни JSON как есть
- Если есть вредный контент — ЗАМЕНИ его на безопасный
- Если есть пустые поля — ЗАПОЛНИ их
- Если есть ошибки JSON — ИСПРАВЬ их

## ФОРМАТ ОТВЕТА
Верни ТОЛЬКО исправленный JSON, без маркдаун-блоков, без пояснений."""

        user_prompt = f"""Проверь этот сценарий и исправь ошибки:

{scenario_json}"""

        for attempt in range(1, max_retries + 1):
            logger.info(f"🔍 Валидация: попытка {attempt}/{max_retries}")

            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model="gpt://b1g2jhvu89pmefv3qk8v/yandexgpt-5.1/latest",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=8000,
                    timeout=60,
                    extra_headers={"X-Yandex-Project-ID": self.project_id}
                )

                if not response.choices or not response.choices[0].message.content:
                    logger.warning(f"⚠️ Валидатор вернул пустой ответ")
                    if attempt < max_retries:
                        time.sleep(3)
                        continue
                    return json.loads(scenario_json)

                output_text = response.choices[0].message.content
                output_text = self._clean_json_response(output_text)

                try:
                    result = self._safe_parse_json(output_text)
                    logger.info(f"✅ Валидация успешна")
                    return result
                except ValueError:
                    logger.warning(f"⚠️ Валидатор вернул битый JSON")
                    if attempt < max_retries:
                        time.sleep(3)
                        continue
                    return json.loads(scenario_json)

            except Exception as e:
                logger.warning(f"⚠️ Валидация прервана: {type(e).__name__}")
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                return json.loads(scenario_json)

        logger.warning("⚠️ Все попытки валидации провалились, использую исходный сценарий")
        return json.loads(scenario_json)

    def _clean_json_response(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _safe_parse_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            fixed = re.sub(r',\s*}', '}', text)
            fixed = re.sub(r',\s*]', ']', fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        try:
            fixed = re.sub(r'"\s*\n\s*"', '",\n"', text)
            fixed = re.sub(r'\}\s*\n\s*"', '},\n"', fixed)
            fixed = re.sub(r'\]\s*\n\s*"', '],\n"', fixed)
            fixed = re.sub(r'"\s*\n\s*\{', '",\n{', fixed)
            fixed = re.sub(r'\}\s*\n\s*\{', '},\n{', fixed)
            fixed = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', fixed)
            fixed = re.sub(r'"\s*\n\s*\[', '",\n[', fixed)
            fixed = re.sub(r'\]\s*\n\s*\{', '],\n{', fixed)
            fixed = re.sub(r'(\d)\s*\n\s*\{', r'\1,\n{', fixed)
            fixed = re.sub(r',\s*,', ',', fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        try:
            fixed = text.rstrip()
            open_braces = fixed.count('{') - fixed.count('}')
            open_brackets = fixed.count('[') - fixed.count(']')
            if ',"' in fixed[-100:]:
                fixed = fixed[:fixed.rfind(',"')]
            fixed += '}' * open_braces
            fixed += ']' * open_brackets
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise ValueError(f"Не удалось распарсить JSON: {e}")


class ScenarioGeneratorService:
    """Сервис генерации сценариев. 6 запросов + 1 валидация."""

    SYSTEM_PROMPT = """Ты — агент-методист EduVibe, опытный педагог с 20-летним стажем, эксперт по внеурочной деятельности и воспитательной работе согласно ФГОС.

## Твои компетенции
- Все 8 направлений воспитательной работы: гражданское, патриотическое, духовно-нравственное, эстетическое, физическое, трудовое, экологическое, ценности научного познания
- Все форматы: классный час, квиз, беседа, игра, мастерская, киноклуб, дебаты, проектная сессия
- Возрастная психология: особенности 1-4, 5-8, 9-11 классов
- Методика: проблемное обучение, геймификация, проектный подход, развитие Soft Skills

## Требования ФГОС
1. Формирование личностных результатов: осознание российской гражданской идентичности, готовность к саморазвитию, мотивация к социально значимой деятельности
2. Формирование метапредметных результатов: умение работать в команде, критическое мышление, коммуникативные навыки, умение планировать и оценивать результаты
3. Соответствие целевым ориентирам воспитания:
   - НОО (1-4 кл): знающий и любящий свою малую родину, доброжелательный, проявляющий сопереживание
   - ООО (5-9 кл): сознающий принадлежность к народу России, уважающий духовно-нравственную культуру, проявляющий интерес к познанию
   - СОО (10-11 кл): осознанно выражающий гражданскую принадлежность, демонстрирующий навыки рефлексии, ориентированный на осознанный выбор профессии
4. Учёт примерной рабочей программы воспитания: 11 модулей воспитательной работы, календарный план с памятными датами
5. Соблюдение СанПиН 2.4.3648-20:
   - Хронометраж не более 45 минут (40 минут для 1 класса)
   - Обязательные физкультминутки и гимнастика для глаз
   - Напоминание о проветривании помещения
   - Учёт норм использования электронных средств обучения по возрастам

## Правила работы
1. Всегда отвечай на русском языке.
2. Учитывай возраст детей: для 1-4 классов — простые инструкции, игра, движение; для 5-8 — соревнования, групповая работа; для 9-11 — дискуссии, аргументация, проект.
3. Все слова учителя давай ПРЯМОЙ РЕЧЬЮ в кавычках. Не «учитель объясняет», а «Учитель говорит: "Ребята, сегодня мы..."». Распиши дословно, с интонациями.
4. К каждому вопросу добавляй 2-3 ПРЕДПОЛАГАЕМЫХ ОТВЕТА детей и реакцию учителя на них.
5. Хронометраж этапов должен строго суммироваться в указанную длительность. Проверь сумму минут!
6. Придумывай яркие, нешаблонные названия (не "Классный час на тему...", не "Беседа о...").
7. В рисках указывай КОНКРЕТНЫЕ запасные варианты с примерами прямой речи учителя, а не общие фразы.
8. Для детей с ОВЗ давай конкретные адаптации с примерами формулировок.
9. Описывай КОНКРЕТНЫЕ действия. Не «провести обсуждение», а «учитель задаёт вопрос, дети обсуждают в парах 30 секунд, затем 3 человека озвучивают ответы».
10. Для каждого этапа указывай КОНКРЕТНЫЕ материалы с количеством.

## Формат ответа
Всегда возвращай только JSON, без маркдаун-блоков (```), без пояснений до или после."""

    def __init__(self):
        pool = DeepSeekClientPool(settings.YANDEX_API_KEYS, settings.YANDEX_PROJECT_ID)
        self.client = DeepSeekClient(pool=pool)

    def generate_scenario(self, params: dict, session_key: str = None) -> dict:
        """Генерирует полный сценарий + валидация."""
        total_start = time.time()
        logger.info("🚀 ГЕНЕРАЦИЯ (6 запросов + валидация)")

        # Запрос 1
        logger.info("=== ЗАПРОС 1/6: Структура ===")
        prompt1 = build_structure_prompt(params)
        structure = self.client.generate(self.SYSTEM_PROMPT, prompt1, temperature=0.4, max_tokens=7000)
        stages_list = structure.get('stages', [])
        logger.info(f"✅ Структура: {structure.get('title', 'НЕТ')}, этапов: {len(stages_list)}")

        # Запросы 2-6 — параллельно
        logger.info("=== ЗАПРОСЫ 2-6/6: ПАРАЛЛЕЛЬНО ===")
        prompt2 = build_all_stages_prompt(stages_list, params, structure)
        prompt3 = build_reflection_prompt(structure, [], params)
        prompt4 = build_materials_adaptation_prompt(structure, [], params)
        prompt5 = build_risks_assessment_tips_prompt(structure, [], {}, params)
        prompt6 = build_host_script_checklist_homework_prompt(structure, [], {}, params)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.client.generate, self.SYSTEM_PROMPT, prompt2, 0.4, 7000, 10): 'stages',
                executor.submit(self.client.generate, self.SYSTEM_PROMPT, prompt3, 0.4, 7000, 10): 'reflection',
                executor.submit(self.client.generate, self.SYSTEM_PROMPT, prompt4, 0.4, 7000, 10): 'materials',
                executor.submit(self.client.generate, self.SYSTEM_PROMPT, prompt5, 0.4, 7000, 10): 'risks',
                executor.submit(self.client.generate, self.SYSTEM_PROMPT, prompt6, 0.4, 7000, 10): 'host',
            }

            results = {}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                    logger.info(f"✅ {key} готов")
                except Exception as e:
                    logger.error(f"❌ {key} провален: {e}")
                    raise

        detailed_stages = results['stages'].get('stages', [])
        reflection = results['reflection']
        mat_adapt = results['materials']
        risks_assessment = results['risks']
        host_result = results['host']

        full_result = {
            "title": structure.get('title', ''),
            "legend": structure.get('legend', ''),
            "goals": structure.get('goals', {}),
            "stages": detailed_stages,
            "reflection": reflection,
            "materials_full": mat_adapt.get('materials_full', {}),
            "adaptation": mat_adapt.get('adaptation', {}),
            "risks": risks_assessment.get('risks', {}),
            "assessment": risks_assessment.get('assessment', {}),
            "teacher_tips": risks_assessment.get('teacher_tips', []),
            "host_script": host_result.get('host_script', ''),
            "checklist": host_result.get('checklist', {}),
            "homework": host_result.get('homework', {}),
        }

        # Валидация
        logger.info("=== ВАЛИДАЦИЯ СЦЕНАРИЯ ===")
        try:
            scenario_json = json.dumps(full_result, ensure_ascii=False)
            validated = self.client.validate_scenario(scenario_json, max_retries=3)
            full_result = validated
            logger.info("✅ Сценарий проверен модератором")
        except Exception as e:
            logger.warning(f"⚠️ Валидация не удалась: {e}. Использую исходный сценарий.")

        logger.info(f"🎉 ГОТОВО ЗА {time.time() - total_start:.1f} сек")
        return full_result

    def regenerate_block(self, block_type: str, current_block: dict, full_context: dict) -> dict:
        user_prompt = build_regenerate_block_prompt(block_type, current_block, full_context)
        return self.client.generate(self.SYSTEM_PROMPT, user_prompt, temperature=0.4, max_tokens=7000)

    def adapt_scenario(self, original_scenario: dict, target_grade: int) -> dict:
        return original_scenario


class ScenarioVersionService:
    """
    Сервис для работы с историей версий сценария.
    
    Отвечает за:
    - Создание новой версии при сохранении
    - Восстановление предыдущей версии
    - Сравнение версий
    - Очистку старых версий
    """
    
    MAX_VERSIONS = 50
    
    def __init__(self, scenario):
        self.scenario = scenario
    
    def create_version(self, change_description='', created_by=''):
        last_version = (
            ScenarioVersion.objects
            .filter(scenario=self.scenario)
            .order_by('-version_number')
            .first()
        )
        next_number = (last_version.version_number + 1) if last_version else 1
        
        version = ScenarioVersion.objects.create(
            scenario=self.scenario,
            version_number=next_number,
            title=self.scenario.title,
            legend=self.scenario.legend,
            goals=self.scenario.goals,
            stages=self.scenario.stages,
            materials=self.scenario.materials,
            adaptation=self.scenario.adaptation,
            reflection=self.scenario.reflection,
            risks=self.scenario.risks,
            assessment=self.scenario.assessment,
            teacher_tips=self.scenario.teacher_tips,
            host_script=self.scenario.host_script,
            checklist=self.scenario.checklist,
            homework=self.scenario.homework,
            change_description=change_description,
            created_by=created_by,
        )
        
        logger.info(f'Создана версия {next_number} для сценария {self.scenario.pk}')
        self._cleanup_old_versions()
        
        return version
    
    def restore_version(self, version_number):
        try:
            target_version = ScenarioVersion.objects.get(
                scenario=self.scenario,
                version_number=version_number
            )
        except ScenarioVersion.DoesNotExist:
            raise ValueError(f'Версия {version_number} не найдена')
        
        self.create_version(
            change_description=f'Автосохранение перед восстановлением версии {version_number}',
            created_by='system'
        )
        
        self.scenario.title = target_version.title
        self.scenario.legend = target_version.legend
        self.scenario.goals = target_version.goals
        self.scenario.stages = target_version.stages
        self.scenario.materials = target_version.materials
        self.scenario.adaptation = target_version.adaptation
        self.scenario.reflection = target_version.reflection
        self.scenario.risks = target_version.risks
        self.scenario.assessment = target_version.assessment
        self.scenario.teacher_tips = target_version.teacher_tips
        self.scenario.host_script = target_version.host_script
        self.scenario.checklist = target_version.checklist
        self.scenario.homework = target_version.homework
        self.scenario.save()
        
        self.create_version(
            change_description=f'Восстановлена версия {version_number}',
            created_by=target_version.created_by
        )
        
        logger.info(f'Сценарий {self.scenario.pk} восстановлен до версии {version_number}')
        return self.scenario
    
    def get_versions(self):
        return (
            ScenarioVersion.objects
            .filter(scenario=self.scenario)
            .order_by('-version_number')
            .only('id', 'version_number', 'change_description', 'created_by', 'created_at')
        )
    
    def get_version(self, version_number):
        try:
            return ScenarioVersion.objects.get(
                scenario=self.scenario,
                version_number=version_number
            )
        except ScenarioVersion.DoesNotExist:
            return None
    
    def get_latest_version(self):
        return (
            ScenarioVersion.objects
            .filter(scenario=self.scenario)
            .order_by('-version_number')
            .first()
        )
    
    def compare_versions(self, version_number_1, version_number_2):
        v1 = self.get_version(version_number_1)
        v2 = self.get_version(version_number_2)
        
        if not v1 or not v2:
            raise ValueError('Одна из версий не найдена')
        
        differences = {}
        fields_to_compare = [
            'title', 'legend', 'goals', 'stages', 'materials',
            'adaptation', 'reflection', 'risks', 'assessment',
            'teacher_tips', 'host_script', 'checklist', 'homework'
        ]
        
        for field in fields_to_compare:
            val1 = getattr(v1, field)
            val2 = getattr(v2, field)
            
            if field == 'stages':
                try:
                    stages1 = json.loads(val1) if val1 else []
                    stages2 = json.loads(val2) if val2 else []
                except (json.JSONDecodeError, TypeError):
                    stages1 = val1 or ''
                    stages2 = val2 or ''
                
                if isinstance(stages1, list) and isinstance(stages2, list):
                    if len(stages1) != len(stages2):
                        differences[f'{field}_count'] = {'old': len(stages1), 'new': len(stages2)}
                    names1 = [s.get('name', '') for s in stages1 if isinstance(s, dict)]
                    names2 = [s.get('name', '') for s in stages2 if isinstance(s, dict)]
                    if names1 != names2:
                        differences[field] = {'old': names1, 'new': names2}
            elif str(val1) != str(val2):
                if isinstance(val1, str):
                    differences[field] = {'old_length': len(val1), 'new_length': len(val2)}
                else:
                    differences[field] = {'old': str(val1)[:200], 'new': str(val2)[:200]}
        
        return {
            'version_1': {'number': v1.version_number, 'created_at': v1.created_at.isoformat(), 'description': v1.change_description},
            'version_2': {'number': v2.version_number, 'created_at': v2.created_at.isoformat(), 'description': v2.change_description},
            'differences': differences,
            'has_changes': len(differences) > 0
        }
    
    def delete_version(self, version_number):
        try:
            version = ScenarioVersion.objects.get(
                scenario=self.scenario,
                version_number=version_number
            )
        except ScenarioVersion.DoesNotExist:
            return {'status': 'error', 'message': f'Версия {version_number} не найдена'}
        
        total_versions = ScenarioVersion.objects.filter(scenario=self.scenario).count()
        
        if total_versions <= 1:
            scenario_title = self.scenario.title or self.scenario.theme
            scenario_pk = self.scenario.pk
            self.scenario.delete()
            logger.info(f'Сценарий "{scenario_title}" (pk={scenario_pk}) удалён вместе с последней версией {version_number}')
            return {'status': 'scenario_deleted', 'message': f'Сценарий «{scenario_title}» полностью удалён вместе с последней версией'}
        
        version.delete()
        logger.info(f'Удалена версия {version_number} сценария {self.scenario.pk}. Осталось версий: {total_versions - 1}')
        return {'status': 'deleted', 'message': f'Версия {version_number} удалена. Осталось версий: {total_versions - 1}'}
    
    def _cleanup_old_versions(self):
        total = ScenarioVersion.objects.filter(scenario=self.scenario).count()
        
        if total > self.MAX_VERSIONS:
            versions_to_keep = (
                ScenarioVersion.objects
                .filter(scenario=self.scenario)
                .order_by('-version_number')
                .values_list('id', flat=True)[:self.MAX_VERSIONS]
            )
            
            deleted_count, _ = (
                ScenarioVersion.objects
                .filter(scenario=self.scenario)
                .exclude(id__in=versions_to_keep)
                .delete()
            )
            
            logger.info(f'Очищено {deleted_count} старых версий сценария {self.scenario.pk}')