from rest_framework import serializers
from .models import Translation, Example, Pronunciation


class TranslationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translation
        fields = "id", "translation"

    def create(self, validated_data):
        translation = Translation(**validated_data)
        translation.save()
        return translation


class ExampleSerializer(serializers.ModelSerializer):
    textExample = serializers.CharField(source='text_example')

    class Meta:
        model = Example
        fields = ['textExample']


class TranslationSerializer(serializers.ModelSerializer):
    textTranslation = serializers.CharField(source='text_translation')

    class Meta:
        model = Translation
        fields = ['textTranslation']


class PronunciationSerializer(serializers.ModelSerializer):
    audioUrl = serializers.CharField(source='audio_url')

    class Meta:
        model = Pronunciation
        fields = ['keyword', 'audioUrl']
