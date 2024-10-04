from django.urls import path
from .views import view_test

urlpatterns = [
    path('view/', view_test, name="view_test")
]
