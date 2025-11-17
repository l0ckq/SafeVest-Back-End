from rest_framework import serializers

from safevest.models import Veste

class VesteBaseSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.CharField(source='empresa.nome', read_only=True)
    setor_nome = serializers.CharField(source='setor.nome', read_only=True, allow_null=True)
    operador_email = serializers.CharField(source='profile.user.email', read_only=True, allow_null=True)
    operador_nome = serializers.SerializerMethodField()

    class Meta:
        model = Veste
        fields = [
            'id', 'numero_de_serie', 'empresa', 'empresa_nome', 
            'setor', 'setor_nome', 'profile', 'operador_email',
            'operador_nome', 'esta_em_uso', 'ativa', 'criado_em'
        ]

    def get_operador_nome(self, obj):
        if obj.profile and obj.profile.user:
            return f"{obj.profile.user.first_name} {obj.profile.user.last_name}".strip()
        return None


# Herdar do base para evitar repetição
class VesteListSerializer(VesteBaseSerializer):
    class Meta(VesteBaseSerializer.Meta):
        fields = VesteBaseSerializer.Meta.fields


class VesteDetailSerializer(VesteBaseSerializer):
    ultimas_leituras = serializers.SerializerMethodField()
    empresa = serializers.SerializerMethodField()
    setor = serializers.SerializerMethodField()
    operador = serializers.SerializerMethodField()

    class Meta(VesteBaseSerializer.Meta):
        fields = VesteBaseSerializer.Meta.fields + [
            'ultimas_leituras', 'atualizado_em'
        ]

    def get_ultimas_leituras(self, obj):
        leituras = obj.leituras.all().order_by('-timestamp')[:10]  # Aumentei para 10
        return LeituraSensorSerializer(leituras, many=True).data

    def get_empresa(self, obj):
        return {
            'id': obj.empresa.id,
            'nome': obj.empresa.nome,
            'cnpj': obj.empresa.cnpj,
        }

    def get_setor(self, obj):
        if not obj.setor:
            return None
        return {
            'id': obj.setor.id,
            'nome': obj.setor.nome,
            'empresa_id': obj.setor.empresa.id,
        }

    def get_operador(self, obj):
        if not obj.profile:
            return None
        return {
            'id': obj.profile.id,
            'email': obj.profile.user.email,
            'nome': f"{obj.profile.user.first_name} {obj.profile.user.last_name}".strip(),
            'role': obj.profile.get_role_display(),
            'role_codigo': obj.profile.role,
        }