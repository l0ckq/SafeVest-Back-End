# safevest/api/views.py (Versão Corrigida)

from rest_framework import generics
from .models import Alerta # 
from .api import serializers # 

class AlertaListCreate(generics.ListCreateAPIView):
    queryset = Alerta.objects.all()
    serializer_class = serializers.AlertaSerializer