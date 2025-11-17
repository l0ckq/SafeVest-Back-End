from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from safevest.models import (
    Empresa, Setor, Profile, Veste, UsoVeste, LeituraSensor, Alerta
)
from safevest.api.serializers import *
from safevest.api.filters import *


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Admin vê todas, outros só sua empresa
        user = self.request.user
        if user.is_staff:
            return Empresa.objects.all()
        
        try:
            user_empresa = user.profile.empresa
            return Empresa.objects.filter(id=user_empresa.id)
        except Profile.DoesNotExist:
            return Empresa.objects.none()


class SetorViewSet(viewsets.ModelViewSet):
    serializer_class = SetorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa', 'ativo']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Setor.objects.all()
        
        try:
            user_empresa = user.profile.empresa
            return Setor.objects.filter(empresa=user_empresa)
        except Profile.DoesNotExist:
            return Setor.objects.none()


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa', 'role', 'ativo']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Profile.objects.select_related('user', 'empresa').all()
        
        try:
            user_empresa = user.profile.empresa
            return Profile.objects.filter(empresa=user_empresa).select_related('user', 'empresa')
        except Profile.DoesNotExist:
            return Profile.objects.none()


class VesteViewSet(viewsets.ModelViewSet):
    """
    ViewSet unificado para vestes com todas as funcionalidades
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['empresa', 'setor', 'ativa', 'profile']
    
    def get_queryset(self):
        user = self.request.user
        queryset = Veste.objects.select_related(
            'empresa', 'setor', 'profile__user'
        ).prefetch_related('leituras')
        
        if user.is_staff:
            return queryset
        
        try:
            user_empresa = user.profile.empresa
            return queryset.filter(empresa=user_empresa)
        except Profile.DoesNotExist:
            return Veste.objects.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return VesteListSerializer
        elif self.action == 'retrieve':
            return VesteDetailSerializer
        elif self.action == 'mapa':
            return VesteMapaSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VesteCreateUpdateSerializer
        return VesteListSerializer

    # Manter todas as actions customizadas da views.py
    @action(detail=False, methods=['get'])
    def mapa(self, request):
        vestes = self.get_queryset().filter(ativa=True)
        empresa_id = request.query_params.get('empresa')
        if empresa_id:
            vestes = vestes.filter(empresa_id=empresa_id)
        
        serializer = VesteMapaSerializer(vestes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def atribuir(self, request, pk=None):
        # ... (código da action)
        pass
    
    @action(detail=True, methods=['post'])
    def liberar(self, request, pk=None):
        # ... (código da action)
        pass
    
    @action(detail=False, methods=['get'])
    def disponiveis(self, request):
        vestes = self.get_queryset().filter(
            profile__isnull=True,
            ativa=True
        )
        empresa_id = request.query_params.get('empresa')
        if empresa_id:
            vestes = vestes.filter(empresa_id=empresa_id)
        
        serializer = VesteListSerializer(vestes, many=True)
        return Response(serializer.data)