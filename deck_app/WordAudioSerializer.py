from rest_framework import serializers
from .models import Translation, Example, Pronunciation


class TranslationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translation
        fields = ["text_translation"]

    def create(self, validated_data):
        return Translation.objects.create(**validated_data)


class ExampleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Example
        fields = ['text_example']  # Certifique-se de que este campo está correto

    def create(self, validated_data):
        return Example.objects.create(**validated_data)


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


