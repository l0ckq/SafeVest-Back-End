# safevest/api/views.py (Versão Corrigida)

from rest_framework import generics
from .models import Alerta # 
from .api import serializers # 

# A view já estava quase perfeita, só precisava dos imports corretos.
class AlertaListCreate(generics.ListCreateAPIView):
    queryset = Alerta.objects.all()
    serializer_class = serializers.AlertaSerializer # Aponta para o serializer correto