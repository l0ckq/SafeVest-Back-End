# /safevest/api/serializers.py

from rest_framework import serializers
# Importa da pasta pai 'safevest'
from ..models import Empresa, Setor, Profile, Veste, UsoVeste, LeituraSensor, Alerta 
from django.contrib.auth.models import User

# Serializer básico para o User nativo do Django
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

# --- Serializers Principais ---

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class SetorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setor
        fields = '__all__'

# Serializer para o Profile, que inclui os dados do User aninhados
class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) # Mostra os dados do User ao invés do ID
    # Para mostrar o nome do Setor e da Empresa:
    setor = SetorSerializer(read_only=True)
    empresa = EmpresaSerializer(read_only=True)
    class Meta:
        model = Profile
        fields = '__all__' # Inclui user, empresa, setor, ativo, foto_perfil

# Serializer resumido, útil para aninhamentos
class ProfileResumidoSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Profile
        fields = ['user', 'empresa', 'setor'] # Apenas o essencial

# Serializer da Veste, mostrando o Profile aninhado
class VesteSerializer(serializers.ModelSerializer):
    # Usa o serializer resumido para mostrar quem está usando a veste
    profile = ProfileResumidoSerializer(read_only=True, allow_null=True) 
    class Meta:
        model = Veste
        fields = '__all__' # Inclui id, numero_de_serie, profile

class UsoVesteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsoVeste
        fields = '__all__'

class LeituraSensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeituraSensor
        fields = '__all__'

class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = '__all__'