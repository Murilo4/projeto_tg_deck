from django.db import models
import requests
from django.core.exceptions import ValidationError
import os
SECRET_KEY = os.getenv('URL_TO_USER_DATA_BASE')


class Deck(models.Model):
    user_id = models.IntegerField(default='')
    deck_name = models.CharField(max_length=100, null=False)
    favorite = models.BooleanField(default=False)
    situation = models.TextField(default='New')
    description_deck = models.TextField(null=True)
    new_deck = models.IntegerField(default=1)
    learning = models.IntegerField(default=0)
    review = models.IntegerField(default=0)
    img_url = models.CharField(max_length=555)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'deck'

    def clean(self):
        # Valida o user_id ao tentar salvar o deck
        response = requests.get(
            f'http://localhost:8000/get-user-to-deck/{self.user_id}/')
        if response.status_code == 404:
            raise ValidationError(f'Usuário com ID {self.user_id} não existe.')
