"""
Сервис поиска похожих сценариев через косинусное сходство.
Использует NumPy для быстрого вычисления.
"""
import json
import logging
import numpy as np
from .models import ScenarioEmbedding

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Ищет похожие сценарии по эмбеддингам."""

    def __init__(self, embedding_service):
        self.embedding_service = embedding_service

    def cosine_similarity(self, vec1, vec2):
        """Косинусное сходство между двумя векторами."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    def search_similar(self, query_text: str, top_k: int = 3, min_similarity: float = 0.3) -> list:
        """
        Ищет top_k похожих сценариев.

        Returns:
            list[dict]: [
                {
                    'scenario_id': int,
                    'title': str,
                    'theme': str,
                    'similarity': float,
                    'search_text': str
                },
                ...
            ]
        """
        try:
            query_vector = self.embedding_service.get_embedding(query_text)
        except Exception as e:
            logger.error(f"Не удалось получить эмбеддинг запроса: {e}")
            return []

        all_embeddings = ScenarioEmbedding.objects.select_related('scenario').all()

        if not all_embeddings:
            logger.info("Нет эмбеддингов для поиска")
            return []

        results = []
        for emb in all_embeddings:
            try:
                doc_vector = json.loads(emb.embedding_json)
                similarity = self.cosine_similarity(query_vector, doc_vector)

                if similarity >= min_similarity:
                    results.append({
                        'scenario_id': emb.scenario.pk,
                        'title': emb.scenario.title or emb.scenario.theme,
                        'theme': emb.scenario.theme,
                        'direction': emb.scenario.get_direction_display(),
                        'format_type': emb.scenario.get_format_type_display(),
                        'grade': emb.scenario.grade,
                        'similarity': round(similarity, 4),
                        'search_text': emb.search_text,
                        'stages_preview': self._get_stages_preview(emb.scenario),
                        'goals_preview': self._get_goals_preview(emb.scenario),
                    })

            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Ошибка обработки эмбеддинга {emb.pk}: {e}")
                continue

        results.sort(key=lambda x: x['similarity'], reverse=True)
        top_results = results[:top_k]

        logger.info(
            f"Найдено {len(top_results)} похожих сценариев "
            f"(всего проверено: {len(all_embeddings)}, "
            f"выше порога: {len(results)})"
        )

        return top_results

    def _get_stages_preview(self, scenario, max_stages: int = 3):
        """Краткое описание этапов для контекста."""
        try:
            stages = json.loads(scenario.stages) if scenario.stages else []
            if not isinstance(stages, list):
                return ''
            preview = []
            for s in stages[:max_stages]:
                if isinstance(s, dict):
                    name = s.get('name', '')
                    desc = s.get('description', '')[:100]
                    preview.append(f"{name}: {desc}")
            return ' | '.join(preview)
        except (json.JSONDecodeError, TypeError):
            return ''

    def _get_goals_preview(self, scenario):
        """Краткое описание целей."""
        try:
            goals = json.loads(scenario.goals) if scenario.goals else {}
            if isinstance(goals, dict):
                return goals.get('educational', goals.get('practical', ''))[:200]
            return ''
        except (json.JSONDecodeError, TypeError):
            return ''

    def build_rag_context(self, similar_scenarios: list) -> str:
        """
        Строит текстовый контекст из найденных примеров для добавления в промпт.
        """
        if not similar_scenarios:
            return ""

        parts = ["\n\n## ПРИМЕРЫ УСПЕШНЫХ СЦЕНАРИЕВ ИЗ БАЗЫ\n"]
        parts.append(
            "Ниже приведены примеры сценариев, которые были ранее созданы для похожих запросов. "
            "Используй их как ориентир по стилю, глубине проработки и структуре, "
            "но НЕ копируй дословно.\n"
        )

        for i, result in enumerate(similar_scenarios, 1):
            parts.append(f"### Пример {i} (сходство: {result['similarity']})")
            parts.append(f"- Название: {result['title']}")
            parts.append(f"- Тема: {result['theme']}")
            parts.append(f"- Направление: {result['direction']}")
            parts.append(f"- Формат: {result['format_type']}")
            parts.append(f"- Класс: {result['grade']}")

            if result.get('goals_preview'):
                parts.append(f"- Цели: {result['goals_preview']}")

            if result.get('stages_preview'):
                parts.append(f"- Примеры этапов: {result['stages_preview']}")

            parts.append("")

        return '\n'.join(parts)