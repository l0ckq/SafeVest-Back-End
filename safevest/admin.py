from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from safevest.models import User, Empresa, Profile, Veste, UsoVeste, LeituraSensor, Alerta

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    ordering = ('email',)
    
    # O que aparece na lista (Adicionei first_name e last_name aqui)
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')

    # Formulário de EDIÇÃO (Quando você clica para editar alguém)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informações Pessoais'), {'fields': ('first_name', 'last_name')}),
        (_('Permissões'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Datas importantes'), {'fields': ('last_login', 'date_joined')}),
    )

    # Formulário de CRIAÇÃO (Quando você clica em 'Adicionar Usuário')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )

# Registrar os outros modelos normalmente (Mantive igual ao seu)
admin.site.register(Empresa)
admin.site.register(Profile)
admin.site.register(Veste)
admin.site.register(UsoVeste)
admin.site.register(LeituraSensor)
admin.site.register(Alerta)