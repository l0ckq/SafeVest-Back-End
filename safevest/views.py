from rest_framework import generics
from ..models import Alerta
from . import serializers

class AlertaListCreate(generics.ListCreateAPIView):
    queryset = Alerta.objects.all()
    serializer_class = serializers.AlertaSerializer