from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from django.db import transaction, IntegrityError
from rest_framework.permissions import IsAuthenticated

from .models import Alerta, Veste, Empresa, Profile, Setor
from .api import serializers 

class OnboardingView(APIView):
    """
    VIEW MANTIDA PARA COMPATIBILIDADE - Agora usando signup_empresa_admin
    """
    permission_classes = [] 
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Reaproveita a lógica da função signup_empresa_admin
        return signup_empresa_admin(request)

class VesteBulkCreateView(APIView):
    # permission_classes = [permissions.IsAdminUser]
    def post(self, request, *args, **kwargs):
        seriais = request.data.get('seriais', [])
        if not isinstance(seriais, list) or not seriais:
            return Response({"erro": "'seriais' deve ser uma lista não-vazia."}, status=status.HTTP_400_BAD_REQUEST)

        criadas_count, ignoradas_count = 0, 0
        seriais_criados, seriais_ignorados = [], []
        
        for serial in seriais:
            serial_limpo = str(serial).strip()
            if not serial_limpo: continue
            _, created = Veste.objects.get_or_create(
                numero_de_serie=serial_limpo, defaults={'profile': None}
            )
            if created:
                criadas_count += 1; seriais_criados.append(serial_limpo)
            else:
                ignoradas_count += 1; seriais_ignorados.append(serial_limpo)
        
        feedback = { 
            "mensagem": f"{criadas_count} criadas, {ignoradas_count} ignoradas.", 
            "criadas": seriais_criados, 
            "ignoradas": seriais_ignorados 
        }
        return Response(feedback, status=status.HTTP_201_CREATED)

class AlertaListCreate(generics.ListCreateAPIView):
    queryset = Alerta.objects.all().order_by('-timestamp')
    serializer_class = serializers.AlertaSerializer
    # permission_classes = [permissions.IsAuthenticated]

class UserByEmailView(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request, *args, **kwargs):
        email = request.query_params.get('email', '').strip()
        if not email:
            return Response({"erro": "O parâmetro 'email' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Se houver múltiplos, pega o primeiro (já tratamos as duplicatas)
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"erro": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)
                
            return Response({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "email": user.email,
                "groups": [g.name for g in user.groups.all()]
            })
        except Exception as e:
            return Response({"erro": f"Erro ao buscar usuário: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@transaction.atomic
def signup_empresa_admin(request):
    """
    Cadastro inicial: Empresa + Primeiro Administrador
    (Versão otimizada reaproveitando a lógica do OnboardingView)
    """
    data = request.data
    
    # Validar dados obrigatórios
    required_fields = ['nome_empresa', 'cnpj', 'nome_admin', 'email_admin', 'senha_admin']
    for field in required_fields:
        if not data.get(field):
            return Response(
                {"erro": f"Campo obrigatório: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Verificar se CNPJ já existe
    if Empresa.objects.filter(cnpj=data['cnpj']).exists():
        return Response(
            {"erro": "Já existe uma empresa com este CNPJ"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar se email já existe (tanto username quanto email)
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
        
        # 3. Criar User (usando mesma lógica do OnboardingView)
        user = User.objects.create_user(
            username=data['email_admin'],
            email=data['email_admin'],
            password=data['senha_admin'],
            first_name=data['nome_admin']
        )
        
        # 4. Adicionar ao grupo Administrador
        grupo_admin, created = Group.objects.get_or_create(name='Administrador')
        user.groups.add(grupo_admin)
        
        # 5. Criar Profile
        profile = Profile.objects.create(
            user=user,
            empresa=empresa,
            setor=setor_admin
        )
        
        return Response({
            "mensagem": "Empresa e administrador criados com sucesso!",
            "empresa_id": empresa.id,
            "user_id": user.id,
            "redirect_to": "/templates/login.html"  # útil para o frontend
        }, status=status.HTTP_201_CREATED)
        
    except IntegrityError as e:
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
def criar_usuario_colaborador(request):
    """
    Cadastro de usuários comuns (apenas para administradores autenticados)
    (Versão otimizada com melhor tratamento de erros)
    """
    # Verificar autenticação
    if not request.user.is_authenticated:
        return Response(
            {"erro": "Autenticação necessária"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Verificar se é administrador
    if not request.user.groups.filter(name='Administrador').exists():
        return Response(
            {"erro": "Apenas administradores podem criar usuários"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    data = request.data
    required_fields = ['nome_completo', 'email', 'funcao', 'password']
    
    # Validar campos obrigatórios
    for field in required_fields:
        if not data.get(field):
            return Response(
                {"erro": f"Campo obrigatório: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Verificar se email já existe
    if User.objects.filter(email=data['email']).exists() or \
       User.objects.filter(username=data['email']).exists():
        return Response(
            {"erro": "Já existe um usuário com este email"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Buscar empresa do administrador logado
        profile_admin = request.user.profile
        empresa = profile_admin.empresa
        setor_default = Setor.objects.filter(empresa=empresa).first()
        
        if not setor_default:
            setor_default = Setor.objects.create(
                empresa=empresa,
                nome="Geral"
            )
        
    except Profile.DoesNotExist:
        return Response(
            {"erro": "Perfil de administrador não encontrado"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Criar User
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password'],
            first_name=data['nome_completo']
        )
        
        # Adicionar ao grupo correspondente
        grupo, created = Group.objects.get_or_create(name=data['funcao'])
        user.groups.add(grupo)
        
        # Criar Profile
        profile = Profile.objects.create(
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
        
    except IntegrityError as e:
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
        # Só administradores podem gerenciar usuários
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {"erro": "Apenas administradores podem gerenciar usuários"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Buscar usuário (dentro da mesma empresa do admin logado)
        try:
            admin_profile = request.user.profile
            user = User.objects.get(id=user_id)
            user_profile = user.profile
            
            # Verificar se o usuário pertence à mesma empresa
            if user_profile.empresa != admin_profile.empresa:
                return Response(
                    {"erro": "Usuário não pertence à sua empresa"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except (User.DoesNotExist, Profile.DoesNotExist):
            return Response(
                {"erro": "Usuário não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'GET':
            # Detalhar usuário
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
            # Editar usuário
            data = request.data
            
            with transaction.atomic():
                # Atualizar User
                if 'nome_completo' in data:
                    user.first_name = data['nome_completo']
                
                if 'email' in data and data['email'] != user.email:
                    # Verificar se novo email já existe
                    if User.objects.filter(email=data['email']).exclude(id=user_id).exists():
                        return Response(
                            {"erro": "Já existe um usuário com este email"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    user.email = data['email']
                    user.username = data['email']  # Atualizar username também
                
                user.save()
                
                # Atualizar Profile
                if 'setor_id' in data:
                    try:
                        novo_setor = Setor.objects.get(id=data['setor_id'], empresa=admin_profile.empresa)
                        user_profile.setor = novo_setor
                    except Setor.DoesNotExist:
                        return Response(
                            {"erro": "Setor não encontrado"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                if 'ativo' in data:
                    user_profile.ativo = data['ativo']
                
                user_profile.save()
                
                # Atualizar grupo/função
                if 'funcao' in data:
                    # Remover grupos existentes
                    user.groups.clear()
                    
                    # Adicionar novo grupo
                    novo_grupo, created = Group.objects.get_or_create(name=data['funcao'])
                    user.groups.add(novo_grupo)
            
            return Response({
                "mensagem": "Usuário atualizado com sucesso!",
                "user_id": user.id
            })

        elif request.method == 'DELETE':
            # Excluir usuário
            return excluir_usuario(user, admin_profile)

    except Exception as e:
        return Response(
            {"erro": f"Erro interno: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def excluir_usuario(user, admin_profile):
    """
    Função auxiliar para exclusão de usuário com validações (SOFT DELETE)
    """
    from django.utils import timezone
    
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
            profile__deletado=False,  # ← CONSIDERA APENAS ATIVOS
            groups__name='Administrador'
        ).exclude(id=user.id).count()
        
        if administradores_restantes == 0:
            return Response(
                {"erro": "Não é possível excluir o último administrador da empresa"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Verificar se usuário tem vestes associadas
    vestes_associadas = user.profile.vestes.exists()
    if vestes_associadas:
        return Response(
            {"erro": "Não é possível excluir usuário com vestes associadas. Transfira as vestes primeiro."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # SOFT DELETE (SEGURO)
    user_profile = user.profile
    user_profile.deletado = True
    user_profile.deletado_em = timezone.now()
    user_profile.ativo = False
    user_profile.save()
    
    # Desativar usuário (impedir login)
    user.is_active = False
    user.save()
    
    return Response({
        "mensagem": f"Usuário {user.get_full_name() or user.username} excluído com sucesso!",
        "user_id": user.id,
        "soft_delete": True
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def editar_empresa(request):
    """
    Editar dados da empresa (apenas administradores)
    """
    try:
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {"erro": "Apenas administradores podem editar dados da empresa"},
                status=status.HTTP_403_FORBIDDEN
            )
        
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
        # FILTRAR APENAS NÃO DELETADOS
        for profile in Profile.objects.filter(
            empresa=empresa, 
            deletado=False  # ← FILTRO IMPORTANTE
        ).select_related('user', 'setor'):
            user = profile.user
            # Só incluir usuários ativos
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