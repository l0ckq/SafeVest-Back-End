from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Veste, LeituraSensor, Alerta, Empresa
from .serializers import (
    VesteMapaSerializer,
    VesteListSerializer, 
    VesteDetailSerializer,
    VesteCreateUpdateSerializer,
    LeituraSensorSerializer,
    AlertaSerializer,
    AlertaResolverSerializer,
)


class VesteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar vestes
    """
    queryset = Veste.objects.select_related('empresa', 'setor', 'profile__user').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa', 'setor', 'ativa', 'profile']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return VesteListSerializer
        elif self.action == 'retrieve':
            return VesteDetailSerializer
        elif self.action == 'mapa':
            return VesteMapaSerializer
        return VesteCreateUpdateSerializer
    
    @action(detail=False, methods=['get'])
    def mapa(self, request):
        """
        Endpoint especial para o cerebro: /api/vestes/mapa/
        Retorna todas as vestes ativas com suas empresas e usuários
        """
        vestes = Veste.objects.filter(ativa=True).select_related(
            'empresa', 'profile'
        )
        
        # Filtro por empresa (se fornecido)
        empresa_id = request.query_params.get('empresa')
        if empresa_id:
            vestes = vestes.filter(empresa_id=empresa_id)
        
        serializer = VesteMapaSerializer(vestes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def atribuir(self, request, pk=None):
        """
        Atribui veste a um operador
        POST /api/vestes/{id}/atribuir/
        Body: {"profile_id": 123}
        """
        veste = self.get_object()
        profile_id = request.data.get('profile_id')
        
        if not profile_id:
            return Response(
                {"error": "profile_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import Profile
            profile = Profile.objects.get(id=profile_id)
            
            # Verifica se profile pertence à mesma empresa
            if profile.empresa != veste.empresa:
                return Response(
                    {"error": "Operador não pertence à empresa da veste"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            veste.atribuir_a(profile)
            serializer = VesteDetailSerializer(veste)
            return Response(serializer.data)
            
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def liberar(self, request, pk=None):
        """
        Libera veste do operador atual
        POST /api/vestes/{id}/liberar/
        """
        veste = self.get_object()
        
        try:
            veste.liberar()
            serializer = VesteDetailSerializer(veste)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def disponiveis(self, request):
        """
        Lista vestes disponíveis (sem operador)
        GET /api/vestes/disponiveis/?empresa=1
        """
        vestes = self.get_queryset().filter(
            profile__isnull=True,
            ativa=True
        )
        
        # Filtro por empresa
        empresa_id = request.query_params.get('empresa')
        if empresa_id:
            vestes = vestes.filter(empresa_id=empresa_id)
        
        serializer = VesteListSerializer(vestes, many=True)
        return Response(serializer.data)


class LeituraSensorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para leituras de sensores
    """
    queryset = LeituraSensor.objects.select_related('veste__empresa').all()
    serializer_class = LeituraSensorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['veste']
    
    def get_queryset(self):
        """Permite filtro por empresa através da veste"""
        queryset = super().get_queryset()
        
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id:
            queryset = queryset.filter(veste__empresa_id=empresa_id)
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def recentes(self, request):
        """
        Últimas leituras de todas as vestes
        GET /api/leiturasensor/recentes/?limit=50&empresa=1
        """
        limit = int(request.query_params.get('limit', 50))
        empresa_id = request.query_params.get('empresa')
        
        queryset = self.get_queryset()
        if empresa_id:
            queryset = queryset.filter(veste__empresa_id=empresa_id)
        
        leituras = queryset[:limit]
        serializer = self.get_serializer(leituras, many=True)
        return Response(serializer.data)


class AlertaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para alertas
    """
    queryset = Alerta.objects.select_related(
        'profile__user',
        'profile__empresa',
        'leitura_associada__veste'
    ).all()
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['profile', 'tipo_alerta', 'resolvido']
    
    def get_queryset(self):
        """Permite filtro por empresa"""
        queryset = super().get_queryset()
        
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id:
            queryset = queryset.filter(profile__empresa_id=empresa_id)
        
        return queryset.order_by('-timestamp')
    
    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        """
        Marca alerta como resolvido
        POST /api/alertas/{id}/resolver/
        Body: {"observacao": "Falso alarme"}
        """
        alerta = self.get_object()
        
        if alerta.resolvido:
            return Response(
                {"error": "Alerta já foi resolvido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AlertaResolverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(alerta=alerta, usuario=request.user)
        
        return Response(AlertaSerializer(alerta).data)
    
    @action(detail=False, methods=['get'])
    def pendentes(self, request):
        """
        Lista alertas não resolvidos
        GET /api/alertas/pendentes/?empresa=1
        """
        empresa_id = request.query_params.get('empresa')
        
        queryset = self.get_queryset().filter(resolvido=False)
        if empresa_id:
            queryset = queryset.filter(profile__empresa_id=empresa_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def emergencias(self, request):
        """
        Lista apenas alertas de emergência não resolvidos
        GET /api/alertas/emergencias/?empresa=1
        """
        empresa_id = request.query_params.get('empresa')
        
        queryset = self.get_queryset().filter(
            tipo_alerta="Emergência",
            resolvido=False
        )
        if empresa_id:
            queryset = queryset.filter(profile__empresa_id=empresa_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)