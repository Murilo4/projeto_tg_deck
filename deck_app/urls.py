from django.urls import path
from .views.create import create_deck
from .views.deck_management import get_all_decks, deck_update
from .views.deck_management import deck_delete
from .views.deck_management import get_deck, get_standard_decks
from .views.deck_management import add_deck_to_user
from .views.filters import get_decks_by_page

urlpatterns = [
    path('create-deck/',
         create_deck, name="create_deck"),
    path('get-all-decks/',
         get_all_decks, name="get_decks"),
    path('update-deck/',
         deck_update, name="deck_update"),
    path('delete-deck/',
         deck_delete, name="delete_deck"),
    path('set-pages/<int:page_number>',
         get_decks_by_page, name='get_decks_by_page'),
    path('get-deck/',
         get_deck, name='get_deck'),
    path('get-standard-decks/',
         get_standard_decks, name='get_standard_decks'),
    path('add-deck-to-user/',
         add_deck_to_user, name='add_standard_deck_to_user'),
]
