from django.db import models
from rest_framework import serializers


class MediaFileField(serializers.FileField):
    def to_representation(self, value):
        return value.url if value else None


class ModelSerializer(serializers.ModelSerializer):
    """FileFields become /media/... paths; base.renderers makes them full URLs."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.FileField: MediaFileField,
    }
