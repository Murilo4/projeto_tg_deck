from rest_framework import serializers
from .models import Deck


class DeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'user_id', 'deck_name', 'favorite', 'situation',
            'description_deck', 'new_deck', 'learning',
            'review', 'img_url'
        )

    def create(self, validated_data):
        deck = Deck(**validated_data)
        deck.save()
        return deck


class DeckUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'deck_name', 'favorite', 'situation',
            'description_deck', 'new_deck', 'learning',
            'review', 'img_url'
        )

    def update(self, validated_data):
        deck = Deck(**validated_data)
        deck.save()
        return deck


class DeckGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'deck_name', 'favorite', 'situation',
            'description_deck', 'new_deck', 'learning',
            'review', 'img_url'
        )
