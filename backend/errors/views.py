from base.views import LangFilteredViewSet
from .models import ErrorMessage
from .serializers import ErrorMessageSerializer


class ErrorMessageViewSet(LangFilteredViewSet):
    queryset = ErrorMessage.objects.all()
    serializer_class = ErrorMessageSerializer
    filter_fields = ["code"]
