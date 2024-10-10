from django.urls import path
from .views.create import create_deck
from .views.deck_management import get_all_decks

urlpatterns = [
    path('create-deck/', create_deck, name="create_deck"),
    path('get-decks/', get_all_decks, name="get_decks")
]
