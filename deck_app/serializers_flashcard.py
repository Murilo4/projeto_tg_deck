from rest_framework import serializers
from .models import FlashCard, DeckFlashCard
from .models import UserFlashCard
from datetime import datetime


class CreateFlashCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashCard
        fields = (
            'id', 'keyword', 'main_phrase'
        )

    def create(self, validated_data):
        flashcard = FlashCard(**validated_data)
        flashcard.save()
        return flashcard


class FlashCardGetSerializer(serializers.ModelSerializer):
    LastModification = serializers.SerializerMethodField()
    CreatedRecently = serializers.SerializerMethodField()

    class Meta:
        model = FlashCard
        fields = (
            'id', 'keyword', 'main_phrase', 'LastModification',
            'CreatedRecently'
        )

    def get_LastModification(self, obj):
        # Calcula a diferença de dias entre 'updated_at' e o tempo atual
        # Considera o timezone do 'updated_at'
        now = datetime.now(obj.updated_at.tzinfo)
        delta = now - obj.updated_at
        return delta.days

    def get_CreatedRecently(self, obj):
        now = datetime.now(obj.created_at.tzinfo)
        delta = now - obj.created_at
        return delta.days


class DeckFlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeckFlashCard
        fields = (
            'id', 'deck_id', 'flashcard_id'
        )

    def create(self, validated_data):
        deck_flashcard = DeckFlashCard(**validated_data)
        deck_flashcard.save()
        return deck_flashcard


class UserFlashCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFlashCard
        fields = (
            'deck_flashcard_id', 'user_id', 'situation', 'one_star',
            'two_stars', 'three_stars', 'four_stars', 'five_stars',
            'last_feedback', 'last_time', 'next_time'
        )

    def create(self, validated_data):
        user_flashcard = UserFlashCard(**validated_data)
        user_flashcard.save()
        return user_flashcard


class UserFlashCardGetSerializer(serializers.ModelSerializer):
    LastTime = serializers.SerializerMethodField()

    class Meta:
        model = UserFlashCard
        fields = (
            'situation',  'LastTime'
        )

    def get_LastTime(self, obj):
        if obj.last_time is None:
            now = datetime.now()
        else:
            now = datetime.now(obj.last_time.tzinfo)
        return now
