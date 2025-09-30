# /safevest/api/serializers.py (Versão Corrigida e Limpa)

from rest_framework import serializers
from safevest.models import Alerta, Empresa, Setor, Usuario, Veste, UsoVeste, LeituraSensor

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class SetorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setor
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'

# O VesteSerializer antigo foi REMOVIDO daqui.

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
        fields = ['id', 'usuario', 'leitura_associada', 'tipo_alerta', 'timestamp']

class UsuarioResumidoSerializer(serializers.ModelSerializer):
    setor = SetorSerializer(read_only=True)
    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nome_completo', 'setor']
        
class VesteSerializer(serializers.ModelSerializer):
    usuario = UsuarioResumidoSerializer(read_only=True, allow_null=True)
    class Meta:
        model = Veste
        # Ajuste para garantir que todos os campos do modelo Veste atualizado estejam aqui
        fields = ['id_veste', 'numero_de_serie', 'usuario']