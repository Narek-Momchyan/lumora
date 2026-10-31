from base.serializers import ModelSerializer
from .models import HeaderLabel, Language, Logo, SidebarItem


class LogoSerializer(ModelSerializer):
    class Meta:
        model = Logo
        fields = "__all__"


class LanguageSerializer(ModelSerializer):
    class Meta:
        model = Language
        fields = "__all__"


class SidebarItemSerializer(ModelSerializer):
    class Meta:
        model = SidebarItem
        fields = "__all__"


class HeaderLabelSerializer(ModelSerializer):
    class Meta:
        model = HeaderLabel
        fields = "__all__"
