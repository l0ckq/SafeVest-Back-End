from rest_framework import viewsets
from ..models import Empresa, Profile, Veste, UsoVeste, LeituraSensor
from .serializers import (
    EmpresaSerializer, ProfileSerializer, VesteSerializer,
    UsoVesteSerializer, LeituraSensorSerializer
)
from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend

# --- ViewSets Padrão (CRUD) ---

class EmpresaViewSet(viewsets.ModelViewSet):
    """
    Endpoint da API para visualizar e editar Empresas.
    """
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    """
    Endpoint da API para visualizar e editar Profiles de Usuários.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

class VesteViewSet(viewsets.ModelViewSet):
    """
    Endpoint da API para visualizar e editar Vestes.
    Suporta filtragem por 'numero_de_serie' e 'profile'.
    Exemplo: /api/veste/?profile=1
    """
    queryset = Veste.objects.all()
    serializer_class = VesteSerializer
    
    # Adicionamos 'profile' aos campos de filtro.
    # Agora podemos buscar todas as vestes de um usuário específico.
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['numero_de_serie', 'profile']

class UsoVesteViewSet(viewsets.ModelViewSet):
    """
    Endpoint da API para gerenciar o histórico de uso das vestes.
    """
    queryset = UsoVeste.objects.all()
    serializer_class = UsoVesteSerializer
    # Sua ação customizada foi removida, pois a funcionalidade agora
    # é coberta de forma mais elegante pelo filtro no VesteViewSet.

class LeituraSensorViewSet(viewsets.ModelViewSet):
    """
    Endpoint da API para visualizar e criar Leituras de Sensores.
    """
    queryset = LeituraSensor.objects.all()
    serializer_class = LeituraSensorSerializer