from django.urls import path
from .deck_views.create import create_deck
from .deck_views.deck_management import get_all_decks, deck_update
from .deck_views.deck_management import delete_deck
from .deck_views.deck_management import get_deck, get_standard_decks
from .deck_views.deck_management import add_deck_to_user
from .flashcards_views.create_flashcard import create_flashcard
from .flashcards_views.flashcard_management import get_all_flashcard

urlpatterns = [
    path('create-deck/',
         create_deck, name="create_deck"),
    path('get-all-decks/<int:page_number>/',
         get_all_decks, name="get_decks"),
    path('update-deck/',
         deck_update, name="deck_update"),
    path('delete-deck/',
         delete_deck, name="delete_deck"),
    path('get-deck/',
         get_deck, name='get_deck'),
    path('get-standard-decks/<int:page_number>/',
         get_standard_decks, name='get_standard_decks'),
    path('add-deck-to-user/',
         add_deck_to_user, name='add_standard_deck_to_user'),
    path("create-flashcard/",
         create_flashcard, name="create_flashcard"),
    path("get-all-flashcard/<int:page_number>/",
         get_all_flashcard, name="get_all_flashcard")
]
