from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from django.db import transaction, IntegrityError
from rest_framework.permissions import IsAuthenticated

from .models import Alerta, Veste, Empresa, Profile, Setor
from .api import serializers 

# ==================================================
# CLASS-BASED VIEWS (CBV)
# ==================================================

class OnboardingView(APIView):
    """
    VIEW MANTIDA PARA COMPATIBILIDADE - Agora usando signup_empresa_admin
    """
    permission_classes = [] 
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return signup_empresa_admin(request)

class VesteBulkCreateView(APIView):
    def post(self, request, *args, **kwargs):
        seriais = request.data.get('seriais', [])
        if not isinstance(seriais, list) or not seriais:
            return Response(
                {"erro": "'seriais' deve ser uma lista não-vazia."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        criadas_count, ignoradas_count = 0, 0
        seriais_criados, seriais_ignorados = [], []
        
        for serial in seriais:
            serial_limpo = str(serial).strip()
            if not serial_limpo: 
                continue
                
            _, created = Veste.objects.get_or_create(
                numero_de_serie=serial_limpo, 
                defaults={'profile': None}
            )
            
            if created:
                criadas_count += 1
                seriais_criados.append(serial_limpo)
            else:
                ignoradas_count += 1
                seriais_ignorados.append(serial_limpo)
        
        feedback = { 
            "mensagem": f"{criadas_count} criadas, {ignoradas_count} ignoradas.", 
            "criadas": seriais_criados, 
            "ignoradas": seriais_ignorados 
        }
        return Response(feedback, status=status.HTTP_201_CREATED)

class AlertaListCreate(generics.ListCreateAPIView):
    queryset = Alerta.objects.all().order_by('-timestamp')
    serializer_class = serializers.AlertaSerializer

class UserByEmailView(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request, *args, **kwargs):
        email = request.query_params.get('email', '').strip()
        if not email:
            return Response(
                {"erro": "O parâmetro 'email' é obrigatório."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.filter(
                email=email, 
                profile__deletado=False
            ).first()
            
            if not user:
                return Response(
                    {"erro": "Usuário não encontrado."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            return Response({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "email": user.email,
                "groups": [g.name for g in user.groups.all()]
            })
            
        except Exception as e:
            return Response(
                {"erro": f"Erro ao buscar usuário: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ==================================================
# FUNCTION-BASED VIEWS (FBV) - EMPRESA & USUÁRIOS
# ==================================================

@api_view(['POST'])
@transaction.atomic
def signup_empresa_admin(request):
    """
    Cadastro inicial: Empresa + Primeiro Administrador
    """
    data = request.data
    
    required_fields = ['nome_empresa', 'cnpj', 'nome_admin', 'email_admin', 'senha_admin']
    for field in required_fields:
        if not data.get(field):
            return Response(
                {"erro": f"Campo obrigatório: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Verificar duplicatas
    if Empresa.objects.filter(cnpj=data['cnpj']).exists():
        return Response(
            {"erro": "Já existe uma empresa com este CNPJ"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=data['email_admin']).exists() or \
       User.objects.filter(email=data['email_admin']).exists():
        return Response(
            {"erro": "Já existe um usuário com este email"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # 1. Criar Empresa
        empresa = Empresa.objects.create(
            nome_empresa=data['nome_empresa'],
            cnpj=data['cnpj']
        )
        
        # 2. Criar Setor padrão
        setor_admin = Setor.objects.create(
            empresa=empresa,
            nome="Administração"
        )
        
        # 3. Criar User
        user = User.objects.create_user(
            username=data['email_admin'],
            email=data['email_admin'],
            password=data['senha_admin'],
            first_name=data['nome_admin']
        )
        
        # 4. Adicionar ao grupo Administrador
        grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        user.groups.add(grupo_admin)
        
        # 5. Criar Profile
        Profile.objects.create(
            user=user,
            empresa=empresa,
            setor=setor_admin
        )
        
        return Response({
            "mensagem": "Empresa e administrador criados com sucesso!",
            "empresa_id": empresa.id,
            "user_id": user.id,
            "redirect_to": "/templates/login.html"
        }, status=status.HTTP_201_CREATED)
        
    except IntegrityError:
        return Response(
            {"erro": "Erro de integridade no banco de dados. Verifique os dados."},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"erro": f"Erro interno: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@transaction.atomic
@permission_classes([IsAuthenticated])
def criar_usuario_colaborador(request):
    """
    Cadastro de usuários comuns (apenas para administradores)
    """
    if not request.user.groups.filter(name='Administrador').exists():
        return Response(
            {"erro": "Apenas administradores podem criar usuários"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    data = request.data
    required_fields = ['nome_completo', 'email', 'funcao', 'password']
    
    for field in required_fields:
        if not data.get(field):
            return Response(
                {"erro": f"Campo obrigatório: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Verificar email duplicado
    if User.objects.filter(email=data['email']).exists() or \
       User.objects.filter(username=data['email']).exists():
        return Response(
            {"erro": "Já existe um usuário com este email"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        profile_admin = request.user.profile
        empresa = profile_admin.empresa
        
        # Buscar ou criar setor padrão
        setor_default = Setor.objects.filter(empresa=empresa).first()
        if not setor_default:
            setor_default = Setor.objects.create(empresa=empresa, nome="Geral")
        
        # Criar User
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password'],
            first_name=data['nome_completo']
        )
        
        # Adicionar grupo
        grupo, _ = Group.objects.get_or_create(name=data['funcao'])
        user.groups.add(grupo)
        
        # Criar Profile
        Profile.objects.create(
            user=user,
            empresa=empresa,
            setor=setor_default
        )
        
        return Response({
            "mensagem": f"Usuário {data['nome_completo']} criado com sucesso!",
            "user_id": user.id,
            "email": user.email,
            "funcao": data['funcao']
        }, status=status.HTTP_201_CREATED)
        
    except Profile.DoesNotExist:
        return Response(
            {"erro": "Perfil de administrador não encontrado"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except IntegrityError:
        return Response(
            {"erro": "Erro ao criar usuário. Verifique os dados."},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"erro": f"Erro interno: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def usuario_detalhe(request, user_id):
    """
    Detalhar, editar ou excluir usuário
    """
    try:
        # Verificar permissão
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {"erro": "Apenas administradores podem gerenciar usuários"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Buscar usuário
        admin_profile = request.user.profile
        user = User.objects.get(id=user_id)
        user_profile = user.profile
        
        # VERIFICAÇÃO DO SOFT DELETE (CORRIGIDA)
        if user_profile.deletado:
            return Response(
                {"erro": "Usuário não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar se pertence à mesma empresa
        if user_profile.empresa != admin_profile.empresa:
            return Response(
                {"erro": "Usuário não pertence à sua empresa"},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'GET':
            return Response({
                "id": user.id,
                "nome_completo": user.first_name,
                "email": user.email,
                "username": user.username,
                "funcao": user.groups.first().name if user.groups.exists() else "Sem grupo",
                "setor": user_profile.setor.nome if user_profile.setor else None,
                "ativo": user_profile.ativo,
                "empresa": user_profile.empresa.nome_empresa,
                "data_criacao": user.date_joined
            })

        elif request.method == 'PUT':
            data = request.data
            
            with transaction.atomic():
                # Atualizar User
                if 'nome_completo' in data:
                    user.first_name = data['nome_completo']
                
                if 'email' in data and data['email'] != user.email:
                    if User.objects.filter(email=data['email']).exclude(id=user_id).exists():
                        return Response(
                            {"erro": "Já existe um usuário com este email"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    user.email = data['email']
                    user.username = data['email']
                
                user.save()
                
                # Atualizar Profile
                if 'setor_id' in data:
                    try:
                        novo_setor = Setor.objects.get(
                            id=data['setor_id'], 
                            empresa=admin_profile.empresa
                        )
                        user_profile.setor = novo_setor
                    except Setor.DoesNotExist:
                        return Response(
                            {"erro": "Setor não encontrado"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                if 'ativo' in data:
                    user_profile.ativo = data['ativo']
                
                user_profile.save()
                
                # Atualizar grupo
                if 'funcao' in data:
                    user.groups.clear()
                    novo_grupo, _ = Group.objects.get_or_create(name=data['funcao'])
                    user.groups.add(novo_grupo)
            
            return Response({
                "mensagem": "Usuário atualizado com sucesso!",
                "user_id": user.id
            })

        elif request.method == 'DELETE':
            return excluir_usuario(user, admin_profile)

    except (User.DoesNotExist, Profile.DoesNotExist):
        return Response(
            {"erro": "Usuário não encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"erro": f"Erro interno: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def excluir_usuario(user, admin_profile):
    """
    Função auxiliar para exclusão de usuário (SOFT DELETE)
    """
    # Não permitir excluir a si mesmo
    if user == admin_profile.user:
        return Response(
            {"erro": "Você não pode excluir sua própria conta"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar se é o último administrador
    if user.groups.filter(name='Administrador').exists():
        administradores_restantes = User.objects.filter(
            profile__empresa=admin_profile.empresa,
            profile__deletado=False,
            groups__name='Administrador'
        ).exclude(id=user.id).count()
        
        if administradores_restantes == 0:
            return Response(
                {"erro": "Não é possível excluir o último administrador da empresa"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Verificar vestes associadas
    if user.profile.vestes.exists():
        return Response(
            {"erro": "Não é possível excluir usuário com vestes associadas. Transfira as vestes primeiro."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # SOFT DELETE
    user_profile = user.profile
    user_profile.deletado = True
    user_profile.deletado_em = timezone.now()
    user_profile.ativo = False
    user_profile.save()
    
    # Desativar usuário
    user.is_active = False
    user.save()
    
    return Response({
        "mensagem": f"Usuário {user.get_full_name() or user.username} excluído com sucesso!",
        "user_id": user.id,
        "soft_delete": True
    })

# ==================================================
# FUNCTION-BASED VIEWS (FBV) - CONSULTAS & DASHBOARD
# ==================================================

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def editar_empresa(request):
    """
    Editar dados da empresa (apenas administradores)
    """
    if not request.user.groups.filter(name='Administrador').exists():
        return Response(
            {"erro": "Apenas administradores podem editar dados da empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        admin_profile = request.user.profile
        empresa = admin_profile.empresa
        data = request.data
        
        if 'nome_empresa' in data:
            empresa.nome_empresa = data['nome_empresa']
            empresa.save()
            
            return Response({
                "mensagem": "Empresa atualizada com sucesso!",
                "nome_empresa": empresa.nome_empresa
            })
        else:
            return Response(
                {"erro": "Campo 'nome_empresa' é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        return Response(
            {"erro": f"Erro interno: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def listar_usuarios_empresa(request):
    """
    Listar todos os usuários ATIVOS da mesma empresa
    """
    try:
        user_profile = request.user.profile
        empresa = user_profile.empresa
        
        usuarios = []
        for profile in Profile.objects.filter(
            empresa=empresa, 
            deletado=False
        ).select_related('user', 'setor'):
            user = profile.user
            if user.is_active:
                usuarios.append({
                    "id": user.id,
                    "nome_completo": user.first_name,
                    "email": user.email,
                    "funcao": user.groups.first().name if user.groups.exists() else "Sem grupo",
                    "setor": profile.setor.nome if profile.setor else None,
                    "ativo": profile.ativo,
                    "data_criacao": user.date_joined.strftime("%d/%m/%Y %H:%M"),
                    "ultimo_login": user.last_login.strftime("%d/%m/%Y %H:%M") if user.last_login else "Nunca"
                })
        
        return Response({
            "empresa": empresa.nome_empresa,
            "total_usuarios": len(usuarios),
            "usuarios": usuarios
        })
        
    except Profile.DoesNotExist:
        return Response(
            {"erro": "Perfil não encontrado"},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_estatisticas(request):
    """
    Estatísticas para dashboard
    """
    try:
        user_profile = request.user.profile
        empresa = user_profile.empresa
        
        # Estatísticas básicas
        total_usuarios = Profile.objects.filter(
            empresa=empresa, deletado=False
        ).count()
        
        total_vestes = Veste.objects.filter(profile__empresa=empresa).count()
        vestes_em_uso = Veste.objects.filter(
            profile__empresa=empresa, profile__isnull=False
        ).count()
        
        alertas_recentes = Alerta.objects.filter(
            profile__empresa=empresa,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Últimos alertas
        ultimos_alertas = Alerta.objects.filter(
            profile__empresa=empresa
        ).select_related('profile__user').order_by('-timestamp')[:5]
        
        alertas_data = []
        for alerta in ultimos_alertas:
            alertas_data.append({
                "tipo": alerta.tipo_alerta,
                "usuario": alerta.profile.user.first_name or alerta.profile.user.username,
                "timestamp": alerta.timestamp.strftime("%d/%m/%Y %H:%M"),
                "gravidade": "alta" if alerta.tipo_alerta == "Emergência" else "media"
            })
        
        return Response({
            "empresa": empresa.nome_empresa,
            "estatisticas": {
                "total_usuarios": total_usuarios,
                "total_vestes": total_vestes,
                "vestes_em_uso": vestes_em_uso,
                "vestes_disponiveis": total_vestes - vestes_em_uso,
                "alertas_7_dias": alertas_recentes,
                "taxa_uso": f"{(vestes_em_uso / total_vestes * 100) if total_vestes > 0 else 0:.1f}%"
            },
            "ultimos_alertas": alertas_data
        })
        
    except Profile.DoesNotExist:
        return Response({"erro": "Perfil não encontrado"}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_setores_empresa(request):
    """
    Listar setores da empresa do usuário logado
    """
    try:
        user_profile = request.user.profile
        empresa = user_profile.empresa
        
        setores = Setor.objects.filter(empresa=empresa).values('id', 'nome')
        
        return Response({
            "empresa": empresa.nome_empresa,
            "setores": list(setores)
        })
        
    except Profile.DoesNotExist:
        return Response({"erro": "Perfil não encontrado"}, status=400)

# ==================================================
# FUNCTION-BASED VIEWS (FBV) - PERFIL
# ==================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_foto_perfil(request):
    """
    Upload de foto de perfil
    """
    try:
        user_profile = request.user.profile
        
        if 'foto_perfil' not in request.FILES:
            return Response({"erro": "Nenhuma imagem enviada"}, status=400)
        
        arquivo = request.FILES['foto_perfil']
        if arquivo.size > 5 * 1024 * 1024:  # 5MB
            return Response({"erro": "Arquivo muito grande. Máximo 5MB."}, status=400)
        
        if not arquivo.content_type.startswith('image/'):
            return Response({"erro": "Apenas imagens são permitidas"}, status=400)
        
        user_profile.foto_perfil = arquivo
        user_profile.save()
        
        return Response({
            "mensagem": "Foto atualizada com sucesso!",
            "foto_url": user_profile.foto_perfil.url if user_profile.foto_perfil else None
        })
        
    except Exception as e:
        return Response({"erro": f"Erro ao fazer upload: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def perfil_usuario(request):
    """
    Retorna os dados do usuário logado
    """
    try:
        user = request.user
        profile = user.profile
        
        return Response({
            "id": user.id,
            "nome_completo": user.first_name,
            "email": user.email,
            "username": user.username,
            "funcao": user.groups.first().name if user.groups.exists() else "Sem grupo",
            "empresa": profile.empresa.nome_empresa,
            "setor": profile.setor.nome if profile.setor else None,
            "ativo": profile.ativo,
            "foto_perfil": profile.foto_perfil.url if profile.foto_perfil else None,
            "data_criacao": user.date_joined,
            "ultimo_login": user.last_login
        })
        
    except Profile.DoesNotExist:
        return Response({"erro": "Perfil não encontrado"}, status=400)