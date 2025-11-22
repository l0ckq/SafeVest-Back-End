from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()
from ..models import Empresa, Profile, Veste, UsoVeste, LeituraSensor, Alerta

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']
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

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    empresa = EmpresaSerializer(read_only=True)
    nome_usuario = serializers.CharField(source='user.get_full_name', read_only=True)
    email_usuario = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'user', 'empresa', 'ativo', 'foto_perfil', 
            'deletado', 'deletado_em', 'nome_usuario', 'email_usuario'
        ]
        read_only_fields = ['deletado', 'deletado_em']

class ProfileResumidoSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = ['user', 'empresa', 'ativo']

class VesteSerializer(serializers.ModelSerializer):
    profile = ProfileResumidoSerializer(read_only=True)
    em_uso = serializers.SerializerMethodField()

    class Meta:
        model = Veste
        fields = [
            'id',
            'numero_de_serie',
            'empresa',
            'status',
            'profile',
            'em_uso'
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
            'id', 'veste', 'timestamp', 'batimento', 'temperatura_A', 'temperatura_C', 'nivel_co', 'nivel_bateria'
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
        read_only_fields = ['profile']
    
    def create(self, validated_data):
        leitura = validated_data.get("leitura_associada")
        if leitura and leitura.veste and leitura.veste.profile:
            validated_data["profile"] = leitura.veste.profile
        return super().create(validated_data)

# Serializer para criação de usuário
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password']
    