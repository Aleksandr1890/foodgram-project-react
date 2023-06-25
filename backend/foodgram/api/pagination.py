from rest_framework.pagination import PageNumberPagination


class CustomPageSizePagination(PageNumberPagination):
    """Пагинатор для параметра limit"""
    page_size = 5
    page_size_query_param = 'limit'
    max_page_size = 20
