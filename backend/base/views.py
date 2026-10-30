from rest_framework import viewsets
from rest_framework.response import Response


class FilteredReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    filter_fields = ()
    list_limit = None  # newest-first feeds (ledger, bet history) return only the last N rows

    def get_queryset(self):
        qs = super().get_queryset()
        for field in self.filter_fields:
            value = self.request.query_params.get(field)
            if value is not None:
                qs = qs.filter(**{field: value})
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        if self.list_limit:
            qs = qs[: self.list_limit]
        return Response(self.get_serializer(qs, many=True).data)


class SingleObjectViewSet(viewsets.GenericViewSet):
    """GET /api/<name> returns one object instead of a list (like `logos` in Fruit Food).

    Subclasses implement get_object(), usually "the current player's ...".
    """

    def list(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)
