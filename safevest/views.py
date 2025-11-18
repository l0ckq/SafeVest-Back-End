from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import Group

from django.contrib.auth import get_user_model
User = get_user_model()

from django.db import transaction, IntegrityError
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Alerta, Veste, Empresa, Profile
from .api import serializers

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
            .select_related("profile__empresa")
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
            "groups": [g.name for g in user.groups.all()]
        })

# ==================================================
# FUNCTION-BASED VIEWS (FBV)
# ==================================================

from services.validador_cnpj import validar_cnpj
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# endpoint auxiliar para o Cérebro buscar uma veste por numero_de_serie
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buscar_veste_por_serial(request):
    serial = request.query_params.get('numero_de_serie', '').strip()
    if not serial:
        return Response({"erro": "Parâmetro 'numero_de_serie' é obrigatório."}, status=400)

    try:
        veste = Veste.objects.filter(numero_de_serie=serial).select_related('profile__user').first()
        if not veste:
            # devolve lista vazia para manter compatibilidade com o código do cérebro
            return Response([], status=200)

        resposta = {
            "id_veste": veste.id,
            # se existir profile, retorna id do user, senão None
            "usuario": veste.profile.user.id if (hasattr(veste, 'profile') and veste.profile) else None,
            "numero_de_serie": veste.numero_de_serie
        }
        return Response([resposta], status=200)

    except Exception as e:
        return Response({"erro": f"Erro ao buscar veste: {str(e)}"}, status=500)

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

        user = User.objects.create_user(
            username=data['email_admin'],
            email=data['email_admin'],
            password=data['senha_admin'],
            first_name=data['nome_admin']
        )
        grupo, _ = Group.objects.get_or_create(name='Administrador')
        user.groups.add(grupo)

        Profile.objects.create(user=user, empresa=empresa)
        return Response({"mensagem": "Empresa e admin criados com sucesso!"}, status=201)

    except Exception as e:
        return Response({"erro": f"Erro interno: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def criar_usuario_colaborador(request):
    data = request.data
    
    # Extração de dados do JSON
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    grupo_nome = data.get('grupo')

    # Validações
    if not email or not password or not grupo_nome:
        return Response({"erro": "Email, senha e função são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        try:
            grupo_obj = Group.objects.get(name=grupo_nome)
        except Group.DoesNotExist:
            return Response({"erro": f"A função '{grupo_nome}' não existe no sistema."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"erro": "Este email já está cadastrado."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            email=email, 
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        # ---------------------------

        # Adiciona ao Grupo
        user.groups.add(grupo_obj)

        # Cria o Profile
        admin_profile = request.user.profile
        Profile.objects.create(
            user=user,
            empresa=admin_profile.empresa,
            ativo=True
        )

        return Response({"mensagem": "Usuário criado com sucesso!"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        if 'user' in locals():
            user.delete()
        return Response({"erro": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
@permission_classes([IsAuthenticated]) # Pode manter assim por enquanto para não dar erro de permissão
def listar_usuarios_empresa(request):
    """Listar todos os usuários da empresa (ativos e inativos)"""
    
    try:
        # Pega a empresa do admin logado
        empresa = request.user.profile.empresa
        
        # Filtra profiles da empresa que NÃO foram 'soft deleted'
        # Usamos select_related para deixar o banco de dados mais rápido
        profiles = empresa.profiles.filter(deletado=False).select_related('user')

        data = []
        for p in profiles:
            user = p.user
            
            # Lógica inteligente de nome (Nome Completo ou Email)
            nome_exibicao = user.get_full_name()
            if not nome_exibicao:
                nome_exibicao = user.email # Fallback

            # Pega o nome do grupo (Função)
            funcao = "Sem função"
            if user.groups.exists():
                funcao = user.groups.first().name
            
            data.append({
                "id": user.id,
                "nome": nome_exibicao,
                "email": user.email,
                "funcao": funcao,
                "ativo": p.ativo
            })

        # Retorna no formato que seu JS espera: data.usuarios
        return Response({"usuarios": data})

    except Exception as e:
        return Response({"erro": str(e)}, status=400)

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
        "ativo": profile.ativo,
        "foto_perfil": profile.foto_perfil.url if profile.foto_perfil else None
    })
