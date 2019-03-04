from rest_framework import serializers
from .models import TextGenerator

class TextGeneratorSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'query',
            'text',
            'created_at',
        )
        model = TextGenerator

