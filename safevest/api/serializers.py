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

class VesteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Veste
        fields = '__all__'

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