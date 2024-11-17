from rest_framework import serializers
from .models import Deck, UserDeckPreferences
from datetime import datetime
from .models import UserFlashCard, UserDeck, DeckFlashCard
from django.db.models import Max


class PersonDeckCreateSerializer(serializers.ModelSerializer):
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


class PersonDeckSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="type_deck")
    color = serializers.IntegerField(
        source="color_predefinition")
    description = serializers.CharField(
        source="description_deck")

    class Meta:
        model = Deck
        fields = (
            'id', 'type', 'title', 'description',
            'color', 'reviews', 'image',
            'stars', 'public', 'allow_copy'
        )

    def create(self, validated_data):
        deck = Deck(**validated_data)
        deck.save()
        return deck


class PersonDeckUpdateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='description_deck',
                                        required=False, allow_blank=True)
    color = serializers.CharField(source='color_predefinition',
                                  required=False)
    img = serializers.CharField(source="image",
                                required=False)
    copy = serializers.CharField(source="allow_copy",
                                 required=False)
    deckName = serializers.CharField(source="title",
                                     required=False)

    class Meta:
        model = Deck
        fields = (
            'id', 'type_deck', 'deckName', 'description',
            'color', 'reviews', 'img',
            'stars', 'public', 'copy'
        )

    def update(self, instance, validated_data):
        description = validated_data.get('description', None)
        if description == "":
            validated_data['description'] = None
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

    user_id = serializers.IntegerField()
    deck_id = serializers.IntegerField()
    learning = serializers.IntegerField(default=0)
    reviewing = serializers.IntegerField(default=0)
    favorite = serializers.BooleanField(default=False)


class PersonDeckGetSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="type_deck")
    colorPredefinition = serializers.IntegerField(source="color_predefinition")
    description = serializers.CharField(source="description_deck")
    lastModification = serializers.SerializerMethodField()
    createdData = serializers.SerializerMethodField()
    favorite = serializers.SerializerMethodField()
    flashcards = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = (
            'id', 'type', 'colorPredefinition', 'title',
            'image', 'lastModification', 'createdData',
            'description', 'public', 'difficult', 'stars',
            'reviews', 'favorite', 'flashcards'
        )

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
        user_deck = UserDeck.objects.filter(
            deck_id=obj.id, user_id=user_id).first()
        return user_deck.favorite if user_deck else 0


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

    user_id = serializers.IntegerField()
    deck_id = serializers.IntegerField()
    new_per_day = serializers.IntegerField(default=2)
    learning_per_day = serializers.IntegerField(default=5)
    review_per_day = serializers.IntegerField(default=2)


class UDPreferencesUpdateSerializer(serializers.ModelSerializer):
    new = serializers.IntegerField(source="new_per_day",
                                   required=False)
    learning = serializers.IntegerField(source="learning_per_day",
                                        required=False)
    review = serializers.IntegerField(source="learning_per_day",
                                      required=False)

    class Meta:
        model = UserDeckPreferences
        fields = (
            'deck_id', 'user_id', 'new', 'learning',
            'review'
        )

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
