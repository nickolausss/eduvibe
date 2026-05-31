"""
Сервис для работы с эмбеддингами сценариев.
Использует комбинацию хеш-векторов (надёжно) и YandexGPT API (опционально).
"""
import json
import hashlib
import logging
import time
import re
from openai import OpenAI
from django.conf import settings
from .models import Scenario, ScenarioEmbedding

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Генерирует и хранит эмбеддинги сценариев."""

    VECTOR_SIZE = 256  # Размерность вектора

    def __init__(self):
        api_key = settings.YANDEX_API_KEY
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://ai.api.cloud.yandex.net/v1",
        )
        self.project_id = settings.YANDEX_PROJECT_ID

    def build_search_text(self, scenario):
        """Строит текстовое представление сценария для эмбеддинга."""
        parts = []
        if scenario.title:
            parts.append(f"Название: {scenario.title}")
        if scenario.theme:
            parts.append(f"Тема: {scenario.theme}")
        if scenario.direction:
            parts.append(f"Направление: {scenario.get_direction_display()}")
        if scenario.format_type:
            parts.append(f"Формат: {scenario.get_format_type_display()}")
        if scenario.grade:
            parts.append(f"Класс: {scenario.grade}")
        if scenario.goals:
            try:
                goals = json.loads(scenario.goals)
                if isinstance(goals, dict):
                    if goals.get('educational'):
                        parts.append(f"Цель: {goals['educational'][:100]}")
                    if goals.get('practical'):
                        parts.append(f"Результат: {goals['practical'][:100]}")
            except (json.JSONDecodeError, TypeError):
                pass

        return ' | '.join(parts)

    def get_embedding(self, text: str) -> list:
        """
        Получает эмбеддинг для текста.
        Стратегия:
        1. Пробуем YandexGPT API (text-to-vector)
        2. При ошибке — используем хеш-вектор
        """
        # Способ 1: YandexGPT API
        try:
            return self._get_embedding_from_api(text)
        except Exception as e:
            logger.warning(f"API-эмбеддинг не сработал: {e}")

        # Способ 2: Хеш-вектор (всегда работает)
        logger.info("Использую хеш-вектор как фолбэк")
        return self._get_hash_embedding(text)

    def _get_embedding_from_api(self, text: str) -> list:
        """Получает эмбеддинг через YandexGPT API (текстовая модель)."""
        system_prompt = """Ты — система векторизации образовательного контента. Представь текст в виде числового вектора.

## ПРАВИЛА
1. Проанализируй текст: выдели направление воспитания, формат, возраст, тему, цели.
2. Создай вектор из ровно 256 чисел от -1 до 1.
3. Каждое число отражает выраженность определённого признака.
4. Верни СТРОГО ТОЛЬКО JSON-массив чисел. Никаких пояснений, никаких маркдаун-блоков.

## ПРИМЕР ОТВЕТА
[0.92, -0.34, 0.67, 0.12, -0.88, 0.45, ...]"""

        user_prompt = f"""Текст для векторизации:

{text[:2000]}

Верни ТОЛЬКО JSON-массив из 256 чисел."""

        response = self.client.chat.completions.create(
            model="gpt://b1g2jhvu89pmefv3qk8v/yandexgpt-5.1/latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=3000,
            timeout=30,
            extra_headers={"X-Yandex-Project-ID": self.project_id}
        )

        content = response.choices[0].message.content
        logger.info(f"Ответ API (первые 200 символов): {content[:200]}")

        # Парсим JSON из ответа (устойчиво к markdown-блокам)
        return self._parse_vector_response(content)

    def _parse_vector_response(self, content: str) -> list:
        """Извлекает числовой вектор из ответа модели."""
        # Убираем markdown-блоки
        content = content.strip()
        content = re.sub(r'```(?:json)?\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()

        # Ищем JSON-массив
        match = re.search(r'\[([^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]', content, re.DOTALL)
        if match:
            numbers_str = match.group(0)  # Берём весь массив с скобками
            try:
                numbers = json.loads(numbers_str)
                if isinstance(numbers, list) and len(numbers) > 0:
                    # Нормализуем до нужного размера
                    return self._normalize_vector(numbers)
            except json.JSONDecodeError:
                pass

        # Пробуем извлечь все числа из текста
        numbers = re.findall(r'-?\d+\.?\d*', content)
        if numbers:
            floats = [float(n) for n in numbers]
            return self._normalize_vector(floats)

        raise ValueError(f"Не удалось извлечь вектор из ответа: {content[:200]}")

    def _normalize_vector(self, numbers: list, target_size: int = 256) -> list:
        """Приводит вектор к нужному размеру."""
        if len(numbers) >= target_size:
            return numbers[:target_size]

        # Дополняем нулями или повторяем
        result = []
        while len(result) < target_size:
            for n in numbers:
                result.append(n)
                if len(result) >= target_size:
                    break
        return result

    def _get_hash_embedding(self, text: str) -> list:
        """
        Создаёт эмбеддинг на основе хеша текста.
        Не требует API, всегда работает, детерминирован.
        """
        # Нормализуем текст
        text = text.lower().strip()

        # Создаём вектор из хеша
        vector = []
        for i in range(self.VECTOR_SIZE):
            # Разные хеши для разных позиций вектора
            seed = f"{text}_{i}_edu_vibe_salt"
            hash_bytes = hashlib.sha256(seed.encode('utf-8')).digest()
            # Преобразуем первые 4 байта в число от -1 до 1
            val = int.from_bytes(hash_bytes[:4], 'big') / (2**31)
            val = max(-1.0, min(1.0, val - 1.0))
            vector.append(round(val, 6))

        return vector

    def embed_scenario(self, scenario):
        """Создаёт или обновляет эмбеддинг для сценария."""
        search_text = self.build_search_text(scenario)

        if not search_text.strip():
            logger.warning(f"Пустой search_text для сценария {scenario.pk}")
            return None

        try:
            vector = self.get_embedding(search_text)

            embedding, created = ScenarioEmbedding.objects.update_or_create(
                scenario=scenario,
                defaults={
                    'embedding_json': json.dumps(vector),
                    'search_text': search_text,
                }
            )

            logger.info(
                f"Эмбеддинг {'создан' if created else 'обновлён'} "
                f"для сценария {scenario.pk} (размерность: {len(vector)}, "
                f"первые 3 значения: {vector[:3]})"
            )
            return embedding

        except Exception as e:
            logger.error(f"Не удалось создать эмбеддинг для сценария {scenario.pk}: {e}")
            return None

    def embed_all_scenarios(self, batch_size=50, delay_between=1):
        """Пакетное создание эмбеддингов для всех сценариев без эмбеддинга."""
        scenarios_without = Scenario.objects.filter(embedding__isnull=True)
        total = scenarios_without.count()

        if total == 0:
            logger.info("Все сценарии уже имеют эмбеддинги")
            return 0

        logger.info(f"Сценариев без эмбеддинга: {total}")

        processed = 0
        for i in range(0, total, batch_size):
            batch = scenarios_without[i:i + batch_size]
            for scenario in batch:
                try:
                    result = self.embed_scenario(scenario)
                    if result:
                        processed += 1
                    time.sleep(delay_between)
                except Exception as e:
                    logger.error(f"Пропущен сценарий {scenario.pk}: {e}")

        logger.info(f"Пакетное создание завершено. Создано эмбеддингов: {processed}")
        return processed