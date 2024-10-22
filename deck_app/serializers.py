from rest_framework import serializers
from .models import Deck
from .models import UserDeck


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
        # Atualiza apenas os campos que estão presentes em validated_data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)  # Atualiza o campo se estiver presente
        instance.save()  # Salva as alterações no banco de dados
        return instance


class PersonDeckGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'id', 'title', 'type_deck', 'description_deck',
            'color_predefinition', 'reviews', 'image',
            'stars', 'public', 'allow_copy'
        )


class CreateStandardDecks(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'type_deck', 'title', 'description_deck',
            'color_predefinition', 'reviews', 'image',
            'difficult', 'stars', 'public'
        )

    def create(self, validated_data):
        deck = Deck(**validated_data)
        deck.save()
        return deck


class StandardDeckUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'deck_name', 'favorite', 'situation',
            'description_deck', 'new_deck', 'learning',
            #'color', 
            'review', 'img_url'
        )

    def update(self, instance, validated_data):
        # Atualiza apenas os campos que estão presentes em validated_data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)  # Atualiza o campo se estiver presente
        instance.save()  # Salva as alterações no banco de dados
        return instance


class StandardDeckGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = (
            'deck_name', 'favorite', 'situation',
            'description_deck', 'new_deck', 'learning',
            #'color',
            'review', 'img_url'
        )


class UserDeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDeck
        fields = 'deck_id', 'user_id', 'learning',  'reviewing', 'favorite'

    def create(self, validated_data):
        user_deck = UserDeck(**validated_data)
        user_deck.save()
        return user_deck
