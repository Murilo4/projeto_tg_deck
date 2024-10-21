from django.db import models
import requests
from django.core.exceptions import ValidationError
import os
SECRET_KEY = os.getenv('URL_TO_USER_DATA_BASE')


class Deck(models.Model):
    type_deck = models.CharField(max_length=50, default="Custom")
    title = models.CharField(max_length=255, null=False)
    color_predefinition = models.IntegerField(default=None)
    description_deck = models.TextField(null=True)
    public = models.BooleanField(default=0)
    allow_copy = models.BooleanField(default=0)
    stars = models.FloatField(default=None)
    reviews = models.IntegerField(default=None)
    image = models.CharField(max_length=555)
    difficult = models.CharField(max_length=50, default=None)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'deck'


class DeckFlashCard(models.Model):
    deck_id = models.IntegerField(null=False)
    flashcard_id = models.IntegerField(null=False)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'deck_flashcard'


class DeckFlashCardExample(models.Model):
    deck_flashcard_id = models.IntegerField(null=False)
    example_id = models.IntegerField(null=False)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'deck_flashcard_example'


class Exemple(models.Model):
    text_exemple = models.TextField()
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'exemple'


class FlashCard(models.Model):
    keyword = models.CharField(max_length=255, default=None)
    main_phrase = models.TextField()
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'flashcard'


class FlashCardPriority(models.Model):
    deck_flashcard_id = models.IntegerField(null=False)
    user_id = models.IntegerField(null=False)
    priority = models.DecimalField(max_digits=5, decimal_places=2)
    date_to_study = models.DateTimeField(default=None,  null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'flashcard_priority'


class Pronunciation(models.Model):
    keyword = models.CharField(max_length=255, default=None)
    audio_url = models.CharField(max_length=255, default=None)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pronunciation'


class UserDeck(models.Model):
    deck_id = models.IntegerField()
    user_id = models.IntegerField()
    learning = models.IntegerField(null=True, default=0)  # Permitir null ou definir 0 como padrão
    reviewing = models.IntegerField(null=True, default=0)  # Permitir null ou definir 0 como padrão
    new_deck = models.IntegerField(null=True, default=0)  # Permitir null ou definir 0 como padrão
    favorite = models.BooleanField(null=True, default=False)  # Permitir null ou definir False como padrão
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Valida o user_id ao tentar salvar o deck
        response = requests.get(
            f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/get-user-to-deck/{self.user_id}/')
        if response.status_code == 404:
            raise ValidationError(f'Usuário com ID {self.user_id} não existe.')

    class Meta:
        unique_together = (('user_id', 'deck_id'),)
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'deck_id'], name='unique_user_deck')
        ]
        db_table = 'user_deck'


class UserDeckPreferences(models.Model):
    deck_id = models.IntegerField(null=False)
    user_id = models.IntegerField(null=False)
    new_per_day = models.IntegerField(default=None)
    learning_per_day = models.IntegerField(default=None)
    review_per_day = models.IntegerField(default=None)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_deck_preferences'


class UserFlashCard(models.Model):
    deck_flashcard_id = models.IntegerField(null=False)
    user_id = models.IntegerField(null=False)
    situation = models.CharField(max_length=50)
    two_star = models.IntegerField(default=None)
    three_star = models.IntegerField(default=None)
    four_star = models.IntegerField(default=None)
    five_star = models.IntegerField(default=None)
    last_feedback = models.IntegerField(default=None)
    last_time = models.DateTimeField(default=None)
    next_time = models.DateTimeField(default=None)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_flashcard'
