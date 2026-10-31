from base.serializers import ModelSerializer
from .models import Language, Logo


class LogoSerializer(ModelSerializer):
    class Meta:
        model = Logo
        fields = "__all__"


class LanguageSerializer(ModelSerializer):
    class Meta:
        model = Language
        fields = "__all__"
