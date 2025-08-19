from rest_framework import serializers
from safevest.models import Empresa, Setor, Usuario, Veste, UsoVeste, LeituraSensor

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'


class SetorSerializer(serializers.ModelSerializer):
    empresa = serializers.StringRelatedField(read_only=True)  # mostra o nome da empresa
    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(), source="empresa", write_only=True
    )

    class Meta:
        model = Setor
        fields = ['id', 'nome', 'empresa', 'empresa_id']


class UsuarioSerializer(serializers.ModelSerializer):
    empresa = serializers.StringRelatedField(read_only=True)
    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(), source="empresa", write_only=True, required=False
    )
    setor = serializers.StringRelatedField(read_only=True)
    setor_id = serializers.PrimaryKeyRelatedField(
        queryset=Setor.objects.all(), source="setor", write_only=True, required=False
    )

    class Meta:
        model = Usuario
        fields = [
            'id_usuario',
            'nome_completo',
            'email',
            'ativo',
            'criado_em',
            'empresa', 'empresa_id',
            'setor', 'setor_id',
        ]


class VesteSerializer(serializers.ModelSerializer):
    id_usuario = serializers.StringRelatedField(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(), source="id_usuario", write_only=True
    )

    class Meta:
        model = Veste
        fields = ['id_veste', 'id_usuario', 'usuario_id']


class UsoVesteSerializer(serializers.ModelSerializer):
    id_veste = serializers.StringRelatedField(read_only=True)
    veste_id = serializers.PrimaryKeyRelatedField(
        queryset=Veste.objects.all(), source="id_veste", write_only=True
    )

    class Meta:
        model = UsoVeste
        fields = ['id_uso', 'id_veste', 'veste_id', 'inicio_uso', 'fim_uso']


class LeituraSensorSerializer(serializers.ModelSerializer):
    id_veste = serializers.StringRelatedField(read_only=True)
    veste_id = serializers.PrimaryKeyRelatedField(
        queryset=Veste.objects.all(), source="id_veste", write_only=True
    )

    class Meta:
        model = LeituraSensor
        fields = [
            'id_leitura',
            'id_veste', 'veste_id',
            'timestamp',
            'batimento',
            'temperatura_A',
            'temperatura_C',
            'nivel_co',
            'nivel_bateria',
        ]
