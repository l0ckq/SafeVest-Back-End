import django_filters
from .models import Veste, LeituraSensor, Alerta


class VesteFilter(django_filters.FilterSet):
    numero_de_serie = django_filters.CharFilter(lookup_expr='icontains')
    empresa = django_filters.NumberFilter(field_name='empresa__id')
    setor = django_filters.NumberFilter(field_name='setor__id')
    
    class Meta:
        model = Veste
        fields = ['numero_de_serie', 'empresa', 'setor', 'ativa', 'profile']


class LeituraSensorFilter(django_filters.FilterSet):
    data_inicio = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    data_fim = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    veste_serial = django_filters.CharFilter(field_name='veste__numero_de_serie', lookup_expr='icontains')
    
    class Meta:
        model = LeituraSensor
        fields = ['veste', 'status']


class AlertaFilter(django_filters.FilterSet):
    data_inicio = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    data_fim = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    class Meta:
        model = Alerta
        fields = ['profile', 'tipo_alerta', 'resolvido']