import csv

from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка данных из csv файла'

    def handle(self, *args, **options):
        with open(
            './data/ingredients.csv',
            'r',
            encoding='utf-8'
        ) as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            bulk_create_data = (
                Ingredient(name=row[0], measurement_unit=row[1])
                for row in reader
            )
            Ingredient.objects.bulk_create(bulk_create_data)
