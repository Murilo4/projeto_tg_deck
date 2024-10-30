from rest_framework import serializers
from .models import Translation


class TranslationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translation
        fields = "id", "translation"

    def create(self, validated_data):
        translation = Translation(**validated_data)
        translation.save()
        return translation
