from rest_framework import serializers
from .models import Deck, UserDeckPreferences
from .models import UserDeck
from datetime import datetime


class PersonDeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'id', 'type_deck', 'title', 'description_deck',
            'color_predefinition', 'reviews', 'image',
            'stars', 'public', 'allow_copy'
        )

    def create(self, validated_data):
        deck = Deck(**validated_data)
        deck.save()
        return deck


class PersonDeckUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'id', 'type_deck', 'title', 'description_deck',
            'color_predefinition', 'reviews', 'image',
            'stars', 'public', 'allow_copy'
        )

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()  # Salva as alterações no banco de dados
        return instance


class UserDeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDeck
        fields = (
            'deck_id', 'user_id', 'learning',
            'reviewing', 'favorite'
        )

    def create(self, validated_data):
        user_deck = UserDeck(**validated_data)
        user_deck.save()
        return user_deck


class PersonDeckGetSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="type_deck")
    colorPredefinition = serializers.IntegerField(source="color_predefinition")
    description = serializers.CharField(source="description_deck")
    lastModification = serializers.SerializerMethodField()
    createdData = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = (
            'id', 'type', 'colorPredefinition', 'title',
            'image', 'lastModification', 'createdData',
            'description', 'public', 'difficult', 'stars',
            'reviews'
        )

    def get_lastModification(self, obj):
        # Calcula a diferença de dias entre 'updated_at' e o tempo atual
        # Considera o timezone do 'updated_at'
        now = datetime.now(obj.updated_at.tzinfo)
        delta = now - obj.updated_at
        return delta.days

    def get_createdData(self, obj):
        now = datetime.now(obj.created_at.tzinfo)
        delta = now - obj.created_at
        return delta.days


class PersonDeckGetStandardSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="type_deck")
    colorPredefinition = serializers.IntegerField(source="color_predefinition")
    description = serializers.CharField(source="description_deck")
    lastModification = serializers.SerializerMethodField()
    createdData = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = (
            'id', 'type', 'colorPredefinition', 'title',
            'image', 'lastModification', 'createdData',
            'description', 'difficult', 'stars',
            'reviews'
        )

    def get_lastModification(self, obj):
        # Calcula a diferença de dias entre 'updated_at' e o tempo atual
        # Considera o timezone do 'updated_at'
        now = datetime.now(obj.updated_at.tzinfo)
        delta = now - obj.updated_at
        return delta.days

    def get_createdData(self, obj):
        now = datetime.now(obj.created_at.tzinfo)
        delta = now - obj.created_at
        return delta.days


class CreateStandardDecks(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'id', 'title', 'type_deck', 'description_deck',
            'color_predefinition', 'reviews', 'image',
            'stars', 'public', 'allow_copy', 'difficult'
        )


class UDPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDeckPreferences
        fields = (
            'deck_id', 'user_id', 'new_per_day', 'learning_per_day',
            'review_per_day'
        )

    def create(self, validated_data):
        user_deck_preferences = UserDeckPreferences(**validated_data)
        user_deck_preferences.save()
        return user_deck_preferences
