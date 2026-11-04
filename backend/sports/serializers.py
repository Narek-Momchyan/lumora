from base.serializers import ModelSerializer
from .models import SportsPageLabel


class SportsPageLabelSerializer(ModelSerializer):
    class Meta:
        model = SportsPageLabel
        fields = "__all__"
