from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from django.db import transaction, IntegrityError
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Alerta, Veste, Empresa, Profile, Setor
from .api import serializers

# Permissões específicas por cargo
from .api.permissoes import (
    IsAdministrador,
    IsSupervisor,
    IsOperador,
)

from services.anonymize import anonymize_user

# ==================================================
# CLASS-BASED VIEWS (CBV)
# ==================================================

class OnboardingView(APIView):
    """View compatível com o cadastro inicial"""
    permission_classes = []

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return signup_empresa_admin(request)


class VesteBulkCreateView(APIView):
    """Criação em massa de Vestes (apenas administradores)"""
    permission_classes = [IsAuthenticated, IsAdministrador]

    def post(self, request, *args, **kwargs):
        seriais = request.data.get('seriais', [])
        if not isinstance(seriais, list) or not seriais:
            return Response({"erro": "'seriais' deve ser uma lista não-vazia."}, status=400)

        criadas, ignoradas = [], []
        for serial in seriais:
            numero = str(serial).strip()
            if not numero:
                continue
            _, created = Veste.objects.get_or_create(numero_de_serie=numero)
            (criadas if created else ignoradas).append(numero)

        return Response({
            "mensagem": f"{len(criadas)} criadas, {len(ignoradas)} ignoradas.",
            "criadas": criadas,
            "ignoradas": ignoradas
        }, status=201)


class AlertaListCreate(generics.ListCreateAPIView):
    """Listagem e criação de alertas (apenas da empresa do usuário)"""
    serializer_class = serializers.AlertaSerializer
    permission_classes = [IsAuthenticated, (IsAdministrador | IsSupervisor | IsOperador)]

    def get_queryset(self):
        return Alerta.objects.filter(profile__empresa=self.request.user.profile.empresa).order_by('-timestamp')

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


class UserByEmailView(APIView):
    """Busca usuário por e-mail, limitado à empresa"""
    permission_classes = [IsAuthenticated, (IsAdministrador | IsSupervisor)]

    def get(self, request):
        email = request.query_params.get('email', '').strip()
        if not email:
            return Response({"erro": "O parâmetro 'email' é obrigatório."}, status=400)

        empresa_user = request.user.profile.empresa
        user = (
            User.objects
            .filter(Q(email=email) | Q(username=email), profile__empresa=empresa_user, profile__deletado=False)
            .select_related("profile__empresa", "profile__setor")
            .first()
        )
        if not user:
            return Response({"erro": "Usuário não encontrado ou pertence a outra empresa."}, status=404)

        profile = user.profile
        return Response({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "email": user.email,
            "empresa": profile.empresa.nome_empresa,
            "setor": profile.setor.nome if profile.setor else None,
            "groups": [g.name for g in user.groups.all()]
        })

# ==================================================
# FUNCTION-BASED VIEWS (FBV)
# ==================================================

from services.validators import validar_cnpj

@api_view(['POST'])
@transaction.atomic
def signup_empresa_admin(request):
    data = request.data
    campos = ['nome_empresa', 'cnpj', 'nome_admin', 'email_admin', 'senha_admin']
    if any(not data.get(c) for c in campos):
        return Response({"erro": "Todos os campos são obrigatórios."}, status=400)

    if not validar_cnpj(data['cnpj']): # Validação
        return Response({"erro": "CNPJ inválido."}, status=400)

    if Empresa.objects.filter(cnpj=data['cnpj']).exists():
        return Response({"erro": "CNPJ já cadastrado."}, status=400)
    if User.objects.filter(email=data['email_admin']).exists():
        return Response({"erro": "Email já cadastrado."}, status=400)

    try:
        empresa = Empresa.objects.create(nome_empresa=data['nome_empresa'], cnpj=data['cnpj'])
        setor_admin = Setor.objects.create(empresa=empresa, nome="Administração")

        user = User.objects.create_user(
            username=data['email_admin'],
            email=data['email_admin'],
            password=data['senha_admin'],
            first_name=data['nome_admin']
        )
        grupo, _ = Group.objects.get_or_create(name='Administrador')
        user.groups.add(grupo)

        Profile.objects.create(user=user, empresa=empresa, setor=setor_admin)
        return Response({"mensagem": "Empresa e admin criados com sucesso!"}, status=201)

    except Exception as e:
        return Response({"erro": f"Erro interno: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdministrador])
@transaction.atomic
def criar_usuario_colaborador(request):
    """Criação de usuários comuns (apenas administradores)"""
    data = request.data
    campos = ['nome_completo', 'email', 'funcao', 'password']
    if any(not data.get(c) for c in campos):
        return Response({"erro": "Preencha todos os campos obrigatórios."}, status=400)

    empresa = request.user.profile.empresa
    setor = Setor.objects.filter(empresa=empresa).first() or Setor.objects.create(empresa=empresa, nome="Geral")

    if User.objects.filter(email=data['email']).exists():
        return Response({"erro": "Email já cadastrado."}, status=400)

    user = User.objects.create_user(
        username=data['email'],
        email=data['email'],
        password=data['password'],
        first_name=data['nome_completo']
    )

    grupo, _ = Group.objects.get_or_create(name=data['funcao'])
    user.groups.add(grupo)

    Profile.objects.create(user=user, empresa=empresa, setor=setor)
    return Response({"mensagem": "Usuário criado com sucesso!"}, status=201)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsAdministrador])
def usuario_detalhe(request, user_id):
    """Detalha, edita ou exclui um usuário (apenas da empresa)"""
    admin_profile = request.user.profile
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile

        if profile.empresa != admin_profile.empresa:
            return Response({"erro": "Usuário pertence a outra empresa."}, status=403)
        if profile.deletado:
            return Response({"erro": "Usuário não encontrado."}, status=404)

        if request.method == 'GET':
            return Response({
                "id": user.id,
                "nome": user.first_name,
                "email": user.email,
                "funcao": user.groups.first().name if user.groups.exists() else "Sem grupo",
                "setor": profile.setor.nome if profile.setor else None
            })

        elif request.method == 'PUT':
            data = request.data
            if 'email' in data and data['email'] != user.email:
                if User.objects.filter(email=data['email']).exclude(id=user.id).exists():
                    return Response({"erro": "Email já em uso."}, status=400)
                user.email = data['email']
                user.username = data['email']

            if 'nome' in data:
                user.first_name = data['nome']
            user.save()

            if 'setor_id' in data:
                try:
                    setor = Setor.objects.get(id=data['setor_id'], empresa=admin_profile.empresa)
                    profile.setor = setor
                except Setor.DoesNotExist:
                    return Response({"erro": "Setor inválido."}, status=400)

            if 'funcao' in data:
                user.groups.clear()
                novo, _ = Group.objects.get_or_create(name=data['funcao'])
                user.groups.add(novo)

            profile.save()
            return Response({"mensagem": "Usuário atualizado com sucesso."})

        elif request.method == 'DELETE':
            return excluir_usuario(user, admin_profile)

    except User.DoesNotExist:
        return Response({"erro": "Usuário não encontrado."}, status=404)


def excluir_usuario(user, admin_profile):
    """Soft delete com verificações"""
    if user == admin_profile.user:
        return Response({"erro": "Você não pode se excluir."}, status=400)

    if user.groups.filter(name='Administrador').exists():
        count_admins = User.objects.filter(
            profile__empresa=admin_profile.empresa,
            profile__deletado=False,
            groups__name='Administrador'
        ).exclude(id=user.id).count()
        if count_admins == 0:
            return Response({"erro": "Não é possível excluir o último administrador."}, status=400)

    if user.profile.vestes.exists():
        return Response({"erro": "Usuário possui vestes associadas."}, status=400)

    profile = user.profile
    
    anonymize_user(user, profile)
    
    return Response({"mensagem": "Usuário excluído e anonimizado com sucesso (soft delete)."})

@api_view(['GET'])
@permission_classes([IsAuthenticated, (IsAdministrador | IsSupervisor)])
def listar_usuarios_empresa(request):
    """Listar usuários ativos da mesma empresa"""
    empresa = request.user.profile.empresa
    usuarios = Profile.objects.filter(empresa=empresa, deletado=False).select_related('user', 'setor')

    data = []
    for p in usuarios:
        if not p.user.is_active:
            continue
        data.append({
            "id": p.user.id,
            "nome": p.user.first_name,
            "email": p.user.email,
            "funcao": p.user.groups.first().name if p.user.groups.exists() else "Sem grupo",
            "setor": p.setor.nome if p.setor else None,
            "ativo": p.ativo
        })

    return Response({"empresa": empresa.nome_empresa, "usuarios": data})


@api_view(['GET'])
@permission_classes([IsAuthenticated, (IsAdministrador | IsSupervisor)])
def dashboard_estatisticas(request):
    """Dashboard da empresa (usuários, vestes, alertas)"""
    empresa = request.user.profile.empresa

    total_usuarios = Profile.objects.filter(empresa=empresa, deletado=False).count()
    total_vestes = Veste.objects.filter(profile__empresa=empresa).count()
    vestes_em_uso = Veste.objects.filter(profile__empresa=empresa, profile__isnull=False).count()

    alertas_semana = Alerta.objects.filter(
        profile__empresa=empresa,
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).count()

    return Response({
        "empresa": empresa.nome_empresa,
        "usuarios": total_usuarios,
        "vestes_total": total_vestes,
        "vestes_em_uso": vestes_em_uso,
        "alertas_7_dias": alertas_semana
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_setores_empresa(request):
    """Listar setores da empresa"""
    empresa = request.user.profile.empresa
    setores = Setor.objects.filter(empresa=empresa).values('id', 'nome')
    return Response({"empresa": empresa.nome_empresa, "setores": list(setores)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_foto_perfil(request):
    """Upload de foto de perfil"""
    user_profile = request.user.profile
    arquivo = request.FILES.get('foto_perfil')

    if not arquivo:
        return Response({"erro": "Nenhuma imagem enviada."}, status=400)
    if arquivo.size > 5 * 1024 * 1024:
        return Response({"erro": "Arquivo muito grande (máx 5MB)."}, status=400)
    if not arquivo.content_type.startswith('image/'):
        return Response({"erro": "Apenas imagens são permitidas."}, status=400)

    user_profile.foto_perfil = arquivo
    user_profile.save()
    return Response({
        "mensagem": "Foto atualizada com sucesso!",
        "foto_url": user_profile.foto_perfil.url
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def perfil_usuario(request):
    """Retorna dados do usuário logado"""
    user = request.user
    profile = user.profile

    return Response({
        "id": user.id,
        "nome": user.first_name,
        "email": user.email,
        "funcao": user.groups.first().name if user.groups.exists() else "Sem grupo",
        "empresa": profile.empresa.nome_empresa,
        "setor": profile.setor.nome if profile.setor else None,
        "ativo": profile.ativo,
        "foto_perfil": profile.foto_perfil.url if profile.foto_perfil else None
    })
