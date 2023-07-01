from csv import DictReader

from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка данных из csv файла'

    def handle(self, *args, **options):
        with open(
            './data/ingredients.csv',
                'r',
                encoding='utf-8'
        ) as file:
            reader = DictReader(file)
            next(reader)
            for row in reader:
                Ingredient.objects.create(
                    name=row[0],
                    measurement_unit=row[1]
                )
