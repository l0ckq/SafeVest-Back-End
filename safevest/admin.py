from django.contrib import admin
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Empresa, Setor, Profile, Veste, UsoVeste, LeituraSensor, Alerta

# Configuração customizada do User no Admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'

class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'groups']
    search_fields = ['username', 'email', 'first_name', 'last_name']

# Re-registrar User admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome_empresa', 'cnpj', 'criado_em', 'total_usuarios']
    list_filter = ['criado_em']
    search_fields = ['nome_empresa', 'cnpj']
    readonly_fields = ['criado_em']
    
    def total_usuarios(self, obj):
        return obj.profiles.filter(deletado=False).count()
    total_usuarios.short_description = 'Total Usuários'

@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa', 'total_usuarios']
    list_filter = ['empresa']
    search_fields = ['nome', 'empresa__nome_empresa']
    
    def total_usuarios(self, obj):
        return obj.profiles.filter(deletado=False).count()
    total_usuarios.short_description = 'Usuários no Setor'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'empresa', 'setor', 'ativo', 'deletado', 'deletado_em']
    list_filter = ['empresa', 'setor', 'ativo', 'deletado']
    search_fields = ['user__username', 'user__email', 'user__first_name']
    readonly_fields = ['deletado_em']
    actions = ['ativar_usuarios', 'desativar_usuarios']
    
    def ativar_usuarios(self, request, queryset):
        updated = queryset.update(ativo=True)
        self.message_user(request, f"{updated} usuários ativados.")
    ativar_usuarios.short_description = "Ativar usuários selecionados"
    
    def desativar_usuarios(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, f"{updated} usuários desativados.")
    desativar_usuarios.short_description = "Desativar usuários selecionados"

@admin.register(Veste)
class VesteAdmin(admin.ModelAdmin):
    list_display = ['numero_de_serie', 'profile', 'em_uso']
    list_filter = ['profile__empresa', 'profile']
    search_fields = ['numero_de_serie']
    
    def em_uso(self, obj):
        return obj.profile is not None
    em_uso.boolean = True
    em_uso.short_description = 'Em Uso'

@admin.register(LeituraSensor)
class LeituraSensorAdmin(admin.ModelAdmin):
    list_display = ['veste', 'timestamp', 'batimento', 'temperatura_A', 'nivel_co']
    list_filter = ['veste', 'timestamp']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ['profile', 'tipo_alerta', 'timestamp']
    list_filter = ['tipo_alerta', 'timestamp', 'profile__empresa']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

@admin.register(UsoVeste)
class UsoVesteAdmin(admin.ModelAdmin):
    list_display = ['veste', 'profile', 'inicio_uso', 'fim_uso', 'duracao']
    list_filter = ['profile__empresa', 'inicio_uso']
    date_hierarchy = 'inicio_uso'
    
    def duracao(self, obj):
        if obj.fim_uso:
            return obj.fim_uso - obj.inicio_uso
        return "Em uso"
    duracao.short_description = 'Duração'

admin.site.site_header = "SafeVest Administration"
admin.site.site_title = "SafeVest Admin"
admin.site.index_title = "Bem-vindo ao Sistema SafeVest"