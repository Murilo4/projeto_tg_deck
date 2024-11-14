from rest_framework import serializers
from .models import Deck, UserDeckPreferences
from datetime import datetime
from .models import UserFlashCard, UserDeck, DeckFlashCard
from django.db.models import Max


class PersonDeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'id', 'type_deck', 'title', 'description_deck',
            'color_predefinition', 'reviews', 'image',
            'stars', 'public', 'allow_copy', 'new_deck'
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
    favorite = serializers.SerializerMethodField()
    flashcards = serializers.SerializerMethodField()
    lastTime = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = (
            'id', 'type', 'colorPredefinition', 'title',
            'image', 'lastModification', 'createdData',
            'description', 'public', 'difficult', 'stars',
            'reviews', 'favorite', 'flashcards',
            'lastTime'
        )

    def get_lastTime(self, obj):
        # Aqui você busca o último UserFlashCard relacionado
        last_time_entry = UserFlashCard.objects.filter(
            deck_flashcard__deck=obj).order_by('-last_time').first()
        return last_time_entry.last_time if last_time_entry else None

    def get_flashcards(self, obj):
        # Corrige a relação para contar o número de flashcards associados ao deck
        return DeckFlashCard.objects.filter(deck=obj).count()

    def get_lastModification(self, obj):
    # Calcula a diferença em milissegundos desde o Unix epoch (1970-01-01)
        epoch = datetime(1970, 1, 1, tzinfo=obj.updated_at.tzinfo)
        delta = obj.updated_at - epoch
        return int(delta.total_seconds() * 1000)

    def get_createdData(self, obj):
        # Calcula a diferença em milissegundos desde o Unix epoch (1970-01-01)
        epoch = datetime(1970, 1, 1, tzinfo=obj.created_at.tzinfo)
        delta = obj.created_at - epoch
        return int(delta.total_seconds() * 1000)

    def get_last_study_time(self, obj):
        user_id = self.context.get('user_id')
        # Encontra o último tempo de estudo do usuário para o deck
        last_study = UserFlashCard.objects.filter(
            deck_flashcard__deck_id=obj.id,
            user_id=user_id
        ).aggregate(last_time=Max('last_time'))['last_time']
        return last_study

    def get_favorite(self, obj):
        user_id = self.context.get('user_id')
        # Verifica se o deck é favorito para o usuário
        user_deck = UserDeck.objects.filter(deck_id=obj.id, user_id=user_id).first()
        return user_deck.favorite if user_deck else None


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
        epoch = datetime(1970, 1, 1, tzinfo=obj.updated_at.tzinfo)
        delta = obj.updated_at - epoch
        return int(delta.total_seconds() * 1000)

    def get_createdData(self, obj):
        epoch = datetime(1970, 1, 1, tzinfo=obj.created_at.tzinfo)
        delta = obj.created_at - epoch
        return int(delta.total_seconds() * 1000)


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
