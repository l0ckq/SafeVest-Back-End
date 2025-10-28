from django.contrib import admin
from .models import Empresa, Profile, Veste, Alerta

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'empresa', 'ativo', 'deletado']
    list_filter = ['empresa', 'ativo', 'deletado']

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome_empresa', 'cnpj', 'criado_em']

