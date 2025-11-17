from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Empresa, Setor, Profile, Veste, UsoVeste, LeituraSensor, Alerta

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    # Remover username e configurar email como campo principal
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissões'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Datas importantes'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )

    list_display = ('email', 'is_staff', 'is_active')
    search_fields = ('email',)
    ordering = ('email',)

# Registrar os outros modelos normalmente:
admin.site.register(Empresa)
admin.site.register(Setor)
admin.site.register(Profile)
admin.site.register(Veste)
admin.site.register(UsoVeste)
admin.site.register(LeituraSensor)
admin.site.register(Alerta)