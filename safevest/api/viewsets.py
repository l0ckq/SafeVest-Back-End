from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from safevest.models import Empresa, Setor, Usuario, Veste, UsoVeste, LeituraSensor
from .serializers import (
    EmpresaSerializer,
    SetorSerializer,
    UsuarioSerializer,
    VesteSerializer,
    UsoVesteSerializer,
    LeituraSensorSerializer
)
from drf_yasg.utils import swagger_auto_schema
from safevest.api import serializers
from django_filters.rest_framework import DjangoFilterBackend

class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    @swagger_auto_schema(
        operation_description="Lista todas as empresas existentes",
        responses={200: serializers.EmpresaSerializer(many=True)}
    ) #decorador para descrição do método
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Cadastra uma empresa",
        responses={201: "Nova empresa cadastrada"}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    @swagger_auto_schema(
            operation_description="Retorna a empresa conforme ID",
            responses={200: "Empresa encontrada"}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Edita os dados da empresa",
        responses={200: "Dados atualizados"}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Excluí a empresa",
        responses={204: "Empresa excluída"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class SetorViewSet(viewsets.ModelViewSet):
    queryset = Setor.objects.all()
    serializer_class = SetorSerializer
    @swagger_auto_schema(
        operation_description="Lista todos os setores existentes",
        responses={200: serializers.SetorSerializer(many=True)}
    ) #decorador para descrição do método
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Cadastra um setor",
        responses={201: "Novo setor cadastrado"}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    @swagger_auto_schema(
            operation_description="Retorna o setor conforme ID",
            responses={200: "Setor encontrado"}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Edita os dados do setor",
        responses={200: "Dados atualizados"}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Excluí o setor",
        responses={204: "Setor excluída"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    @swagger_auto_schema(
        operation_description="Lista todas as categorias existentes",
        responses={200: serializers.UsuarioSerializer(many=True)}
    ) #decorador para descrição do método
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Cadastra um usuário",
        responses={201: "Novo usuário cadastrado"}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    @swagger_auto_schema(
            operation_description="Retorna o usuário conforme ID",
            responses={200: "Usuário encontrado"}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Edita os dados do usuário",
        responses={200: "Dados atualizado"}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Excluí o usuário",
        responses={204: "Usuário excluído"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)



class VesteViewSet(viewsets.ModelViewSet):
    queryset = Veste.objects.all()
    serializer_class = VesteSerializer
    @swagger_auto_schema(
        operation_description="Lista todas as vestes existentes",
        responses={200: serializers.VesteSerializer(many=True)}
    ) #decorador para descrição do método
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Cadastra uma veste",
        responses={201: "Nova veste cadastrado"}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    @swagger_auto_schema(
            operation_description="Retorna a veste conforme ID",
            responses={200: "Veste encontrada"}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Edita os dados da veste",
        responses={200: "Veste atualizado"}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    @swagger_auto_schema(
        operation_description="Excluí a veste",
        responses={204: "Veste excluída"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['numero_de_serie'] # Permite filtrar pelo número de série (serial)


class UsoVesteViewSet(viewsets.ModelViewSet):
    queryset = UsoVeste.objects.all()
    serializer_class = UsoVesteSerializer

    @action(detail=False, methods=['get'], url_path='vestes-usuario/(?P<id_usuario>[^/.]+)')
    def listar_vestes_usuario(self, request, id_usuario=None):
        try:
            usuario = Usuario.objects.get(pk=id_usuario)
        except Usuario.DoesNotExist:
            return Response({"detail": "Usuário não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        vestes = Veste.objects.filter(id_usuario=usuario)  
        serializer = VesteSerializer(vestes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class LeituraSensorViewSet(viewsets.ModelViewSet):
    queryset = LeituraSensor.objects.all()
    serializer_class = LeituraSensorSerializer
    @swagger_auto_schema(
        operation_description="Lista todos os setores e seus dados",
        responses={200: serializers.LeituraSensorSerializer(many=True)}
    ) #decorador para descrição do método
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)