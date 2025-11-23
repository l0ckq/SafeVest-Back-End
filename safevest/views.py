from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
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
        status = request.data.get('status', 'ativa')  # ← Recebe o status do frontend
        
        if not isinstance(seriais, list) or not seriais:
            return Response({"erro": "'seriais' deve ser uma lista não-vazia."}, status=400)
        
        # Pega a empresa do usuário logado
        try:
            empresa = request.user.profile.empresa
        except AttributeError:
            return Response({"erro": "Usuário não possui empresa associada."}, status=400)
        
        criadas, ignoradas = [], []
        
        for serial in seriais:
            numero = str(serial).strip()
            if not numero:
                continue
            
            # Verifica se já existe
            if Veste.objects.filter(numero_de_serie=numero).exists():
                ignoradas.append(numero)
            else:
                # Cria com todos os campos necessários
                Veste.objects.create(
                    numero_de_serie=numero,
                    empresa=empresa,  # ← Empresa do usuário logado
                    status=status,    # ← Status escolhido no form
                    profile=None      # Começa sem associação
                )
                criadas.append(numero)
        
        return Response({
            "mensagem": f"{len(criadas)} veste(s) criada(s), {len(ignoradas)} ignorada(s).",
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
            .filter(
                email=email,
                profile__empresa=empresa_user,
                profile__deletado=False
            )
            .select_related("profile__empresa")
            .first()
        )

        if not user:
            return Response({"erro": "Usuário não encontrado ou pertence a outra empresa."}, status=404)

        profile = user.profile

        return Response({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "empresa": profile.empresa.nome_empresa,
            "groups": [g.name for g in user.groups.all()]
        })

class VesteBuscarView(ListAPIView):
    """
    Busca vestes pelo número de série.
    Retorna informações completas de profile e usuário.
    """
    serializer_class = serializers.VesteSerializer

    def get_queryset(self):
        numero_de_serie = self.request.query_params.get("numero_de_serie", None)
        queryset = Veste.objects.all()

        if numero_de_serie:
            queryset = queryset.filter(numero_de_serie=numero_de_serie)

        # Optimização: traz dados de profile e usuário em um só query
        queryset = queryset.select_related("profile__user", "profile__empresa", "empresa")

        return queryset

# ==================================================
# FUNCTION-BASED VIEWS (FBV)
# ==================================================

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

    if Empresa.objects.filter(cnpj=data['cnpj']).exists():
        return Response({"erro": "CNPJ já cadastrado."}, status=400)
    if User.objects.filter(email=data['email_admin']).exists():
        return Response({"erro": "Email já cadastrado."}, status=400)

    try:
        empresa = Empresa.objects.create(nome_empresa=data['nome_empresa'], cnpj=data['cnpj'])

        user = User.objects.create_user(
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
@permission_classes([IsAuthenticated, IsAdministrador])
def criar_usuario_colaborador(request):
    """
    Cria um novo usuário colaborador na empresa do admin logado.
    Se for Administrador, marca como staff e superuser.
    """
    from django.contrib.auth.models import Group
    
    # Valida dados obrigatórios
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    email = request.data.get('email')
    password = request.data.get('password')
    grupo = request.data.get('grupo')  # "Administrador", "Supervisor", "Operador"
    
    if not all([first_name, last_name, email, password, grupo]):
        return Response(
            {"erro": "Campos obrigatórios: first_name, last_name, email, password, grupo"},
            status=400
        )
    
    # Valida grupo
    if grupo not in ['Administrador', 'Supervisor', 'Operador']:
        return Response(
            {"erro": "Grupo inválido. Use: Administrador, Supervisor ou Operador"},
            status=400
        )
    
    # Verifica se email já existe
    if User.objects.filter(email=email).exists():
        return Response(
            {"erro": "Este email já está cadastrado no sistema."},
            status=400
        )
    
    try:
        # Cria User (sem username, só email)
        usuario = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        
        # ============== FLAGS DE ADMIN ==============
        if grupo == 'Administrador':
            usuario.is_staff = True       # ← Acessa painel admin
            usuario.is_superuser = True   # ← Todas as permissões
            usuario.save()
        # ============================================
        
        # Adiciona ao grupo Django
        grupo_obj, _ = Group.objects.get_or_create(name=grupo)
        usuario.groups.add(grupo_obj)
        
        # Cria Profile vinculado à empresa do admin logado
        Profile.objects.create(
            user=usuario,
            empresa=request.user.profile.empresa,
            ativo=True
        )
        
        return Response({
            "mensagem": f"Usuário {first_name} {last_name} criado com sucesso!",
            "id": usuario.id,
            "email": email,
            "grupo": grupo,
            "is_staff": usuario.is_staff,
            "is_superuser": usuario.is_superuser
        }, status=201)
        
    except Exception as e:
        return Response(
            {"erro": f"Erro ao criar usuário: {str(e)}"},
            status=500
        )

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsAdministrador])
def usuario_detalhe(request, user_id):
    """
    GET: Retorna dados de um usuário específico
    PATCH: Atualiza dados do usuário
    DELETE: Desativa o usuário (soft delete)
    """
    try:
        usuario = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"erro": "Usuário não encontrado"}, status=404)
    
    if request.method == 'GET':
        # Monta resposta
        response_data = {
            "id": usuario.id,
            "first_name": usuario.first_name,
            "last_name": usuario.last_name,
            "email": usuario.email,
            "nome": usuario.get_full_name() or usuario.email,
        }
        
        # Pega função (grupo) do usuário
        grupos = list(usuario.groups.values_list('name', flat=True))
        response_data['funcao'] = grupos[0] if grupos else None
        response_data['groups'] = grupos
        
        # Pega dados do profile
        try:
            profile = usuario.profile
            response_data['ativo'] = profile.ativo and usuario.is_active
            response_data['foto_perfil'] = profile.foto_perfil.url if profile.foto_perfil else None
        except Profile.DoesNotExist:
            response_data['ativo'] = usuario.is_active
            response_data['foto_perfil'] = None
        
        return Response(response_data)
    
    elif request.method == 'PATCH':
        from django.contrib.auth.models import Group
        
        # Atualiza dados básicos do User
        usuario.first_name = request.data.get('first_name', usuario.first_name)
        usuario.last_name = request.data.get('last_name', usuario.last_name)
        
        # Valida email único
        novo_email = request.data.get('email', usuario.email)
        if novo_email != usuario.email:
            if User.objects.filter(email=novo_email).exclude(id=usuario.id).exists():
                return Response(
                    {"erro": "Este email já está em uso por outro usuário."},
                    status=400
                )
            usuario.email = novo_email
        
        usuario.save()
        
        # Atualiza função (grupo)
        funcao = request.data.get('funcao')
        if funcao and funcao in ['Administrador', 'Supervisor', 'Operador']:
            usuario.groups.clear()
            grupo, _ = Group.objects.get_or_create(name=funcao)
            usuario.groups.add(grupo)
            
            # ============== FLAGS DE ADMIN ==============
            if funcao == 'Administrador':
                usuario.is_staff = True       # ← Acessa painel admin
                usuario.is_superuser = True   # ← Todas as permissões
            else:
                usuario.is_staff = False
                usuario.is_superuser = False
            # ============================================
        
        # Atualiza status ativo
        if 'ativo' in request.data:
            novo_status = request.data.get('ativo')
            
            # Atualiza User.is_active
            usuario.is_active = novo_status
            usuario.save()
            
            # Atualiza Profile.ativo (se existir)
            try:
                profile = usuario.profile
                profile.ativo = novo_status
                profile.save()
            except Profile.DoesNotExist:
                # Se não tem profile, cria um
                Profile.objects.create(
                    user=usuario,
                    empresa=request.user.profile.empresa,
                    ativo=novo_status
                )
        
        return Response({
            "mensagem": "Usuário atualizado com sucesso!",
            "id": usuario.id,
            "nome": usuario.get_full_name(),
            "email": usuario.email
        })
    
    elif request.method == 'DELETE':
        # Hard delete - Remove permanentemente do banco
        # IMPORTANTE: Isso vai excluir em cascata os dados relacionados
        # (dependendo do on_delete configurado nos FKs)
        
        nome_usuario = usuario.get_full_name() or usuario.email
        
        # Deleta o usuário (Profile será deletado em CASCADE)
        usuario.delete()
        
        return Response({
            "mensagem": f"Usuário {nome_usuario} foi excluído permanentemente.",
            "tipo": "hard_delete"
        })

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def associar_veste(request, veste_id):
    try:
        veste = Veste.objects.get(id=veste_id)
        
        # PROTEÇÃO: Verifica se está ativa
        if veste.status != 'ativa':
            return Response(
                {"erro": "Não é possível associar vestes inativas."},
                status=400
            )
        
        # PROTEÇÃO: Verifica se já está em uso
        if veste.profile is not None:
            return Response(
                {"erro": "Esta veste já está associada a outro usuário."},
                status=400
            )
        
        # Continua com a associação...
        profile_id = request.data.get('profile_id')
        veste.profile_id = profile_id
        veste.save()
        
        return Response({"mensagem": "Veste associada com sucesso!"})
        
    except Veste.DoesNotExist:
        return Response({"erro": "Veste não encontrada."}, status=404)