from csv import DictReader

from django.conf import settings
from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка данных из csv файла'
#
#    def handle(self, *args, **kwargs):
#        with open(
#            './data/ingredients.csv',
#            'r',
#            encoding='utf-8'
#        ) as file:
#            reader = DictReader(file)
#            Ingredient.objects.bulk_create(
#                Ingredient(**data) for data in reader)
#        self.stdout.write(self.style.SUCCESS('Все ингридиенты загружены!'))

    def handle(self, *args, **options):
        for row in DictReader(
                open('./data/ingredients.csv', encoding='UTF-8')
        ):
            Ingredient(
                name=row[0],
                measurement_unit=row[1]
            ).save()
