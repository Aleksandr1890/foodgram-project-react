# Foodgram project - продуктовый помощник

## Описание проекта:

**Проект с помощью API позволяет:**

- публиковать рецепты
- добавлять рецепты в избранное
- подписываться на авторов рецептов
- скачивать продукты для выбранных блюд

## Технологии:

- Python
- Django
- Django Rest Framework
- PostgreSQL
- gunicorn
- nginx

## Запуск и работа с проектом

Чтобы развернуть проект, вам потребуется:

1. Клонировать репозиторий GitHub (не забываем создать виртуальное окружение и установить зависимости):
git clone https://github.com/Aleksandr1890/foodgram-project-react

2. Собрать контейнеры:
cd foodgram-project-react/infra
docker-compose up -d --build

3. Сделать миграции, собрать статику и создать суперпользователя

## Примеры запросов:

```
http://127.0.0.1:8000/api/users/
```

```
http://127.0.0.1:8000/api/v1/receips/
```

```
http://127.0.0.1:8000/api/v1/tags/
```

## Автор:

**Александр Семенов**

[GitHub Pages](https://github.com/Aleksandr1890)
