from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import Empresa, Setor, Profile, Veste, UsoVeste, LeituraSensor, Alerta

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True}
        }
        
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Já existe um usuário com este email.")
        return value

class EmpresaSerializer(serializers.ModelSerializer):
    total_usuarios = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = ['id', 'nome_empresa', 'cnpj', 'criado_em', 'total_usuarios']
        read_only_fields = ['criado_em', 'total_usuarios']
    
    def get_total_usuarios(self, obj):
        return Profile.objects.filter(empresa=obj, deletado=False).count()

class SetorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setor
        fields = ['id', 'nome', 'empresa']
        read_only_fields = ['empresa']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    setor = SetorSerializer(read_only=True)
    empresa = EmpresaSerializer(read_only=True)
    nome_usuario = serializers.CharField(source='user.get_full_name', read_only=True)
    email_usuario = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'user', 'empresa', 'setor', 'ativo', 'foto_perfil', 
            'deletado', 'deletado_em', 'nome_usuario', 'email_usuario'
        ]
        read_only_fields = ['deletado', 'deletado_em']

class ProfileResumidoSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = ['user', 'empresa', 'setor', 'ativo']

class VesteSerializer(serializers.ModelSerializer):
    profile = ProfileResumidoSerializer(read_only=True)
    numero_serie_display = serializers.CharField(source='numero_de_serie', read_only=True)
    em_uso = serializers.SerializerMethodField()
    
    class Meta:
        model = Veste
        fields = [
            'id', 'numero_de_serie', 'numero_serie_display', 'profile', 
            'em_uso', 'profile'
        ]
    
    def get_em_uso(self, obj):
        return obj.profile is not None

class UsoVesteSerializer(serializers.ModelSerializer):
    veste_info = serializers.CharField(source='veste.numero_de_serie', read_only=True)
    usuario_info = serializers.CharField(source='profile.user.get_full_name', read_only=True)
    
    class Meta:
        model = UsoVeste
        fields = [
            'id', 'veste', 'veste_info', 'profile', 'usuario_info',
            'inicio_uso', 'fim_uso'
        ]

class LeituraSensorSerializer(serializers.ModelSerializer):
    veste_info = serializers.CharField(source='veste.numero_de_serie', read_only=True)
    timestamp_formatado = serializers.DateTimeField(source='timestamp', format="%d/%m/%Y %H:%M", read_only=True)
    
    class Meta:
        model = LeituraSensor
        fields = [
            'id', 'veste', 'veste_info', 'timestamp', 'timestamp_formatado',
            'batimento', 'temperatura_A', 'temperatura_C', 'nivel_co', 'nivel_bateria'
        ]

class AlertaSerializer(serializers.ModelSerializer):
    usuario_info = serializers.CharField(source='profile.user.get_full_name', read_only=True)
    timestamp_formatado = serializers.DateTimeField(source='timestamp', format="%d/%m/%Y %H:%M", read_only=True)
    
    class Meta:
        model = Alerta
        fields = [
            'id', 'profile', 'usuario_info', 'leitura_associada', 
            'tipo_alerta', 'timestamp', 'timestamp_formatado'
        ]

# Serializer para criação de usuário
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'password']
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user