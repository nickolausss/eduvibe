from django.core.management.base import BaseCommand
from scenarios.embedding_service import EmbeddingService


class Command(BaseCommand):
    help = 'Создаёт эмбеддинги для всех сценариев без эмбеддинга'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Размер пакета (по умолчанию 50)',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        self.stdout.write(self.style.NOTICE('Начинаю создание эмбеддингов...'))

        service = EmbeddingService()
        total = service.embed_all_scenarios(batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS(f'Готово! Обработано сценариев: {total}'))