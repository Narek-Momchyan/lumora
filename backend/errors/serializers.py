from base.serializers import ModelSerializer
from .models import ErrorMessage


class ErrorMessageSerializer(ModelSerializer):
    class Meta:
        model = ErrorMessage
        fields = "__all__"
