from django.urls import path
from .deck_views.create import create_deck
from .deck_views.deck_management import get_all_decks, deck_update
from .deck_views.deck_management import delete_deck, cron_job
from .deck_views.deck_management import get_deck, get_standard_decks
from .deck_views.deck_management import add_deck_to_user
from .flashcards_views.create_flashcard import create_flashcard
from .flashcards_views.flashcard_management import get_all_flashcard, update_flashcard
from .flashcards_views.flashcard_management import get_one_flashcard, delete_flashcard
from .audio_text_views.text import get_translated_word, get_example_sentences
from .audio_text_views.text import get_correct_word
from .audio_text_views.audio import get_pronunciations
from .study.study_views import get_flashcards_for_study

urlpatterns = [
    path('create-deck/',
         create_deck, name="create_deck"),
    path('get-all-decks/<int:page_number>/',
         get_all_decks, name="get_decks"),
    path('update-deck/<int:deckId>/',
         deck_update, name="deck_update"),
    path('delete-deck/<int:deckId>/',
         delete_deck, name="delete_deck"),
    path('get-deck/<int:deckId>/',
         get_deck, name='get_deck'),
    path('get-standard-decks/<int:page_number>/',
         get_standard_decks, name='get_standard_decks'),
    path('add-deck-to-user/<int:deckId>/',
         add_deck_to_user, name='add_standard_deck_to_user'),
    path("create-flashcard/<int:deckId>/",
         create_flashcard, name="create_flashcard"),
    path("get-all-flashcard/<int:page_number>/<int:deckId>/",
         get_all_flashcard, name="get_all_flashcard"),
    path("update-flashcard/<int:flashcardId>/<int:deckId>/",
         update_flashcard, name="update_flashcard"),
    path("delete-flashcard/<int:flashcardId>/<int:deckId>/",
         delete_flashcard, name="delete_flashcard"),
    path("get-traslated-word/",
         get_translated_word, name="get_translated_word"),
    path("get-example-sentences/",
         get_example_sentences, name="get_example_sentences"),
    path("get-pronunciations/",
         get_pronunciations, name="get_pronunciations"),
    path('voices/',
         get_pronunciations, name='available_voices'),
    path('get-correct-word/',
         get_correct_word, name="get_correct_word"),
    #     path("get-correct-phrase/",
    #          get_correct_phrase, name="get_correct_phrase")
    path("get-one-flashcard/<int:flashcardId>/<int:deckId>/",
         get_one_flashcard, name="get_one_flashcard"),
    path("get-flashcards-for-study/<int:deckId>/",
         get_flashcards_for_study, name="get_flashcards_for_study"),
    path("cron-job/",
         cron_job, name="cron_job")

]
