# setup/urls.py (Versão Corrigida)

from django.contrib import admin
from django.urls import path, include
# CORREÇÃO 1: Importamos os módulos do local correto
from safevest.api import viewsets
from safevest.views import AlertaListCreate 
from rest_framework import routers, permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from django.conf import settings
from django.conf.urls.static import static

# ... seu schema_view do Swagger (sem alterações) ...
schema_view = get_schema_view(
    openapi.Info(
        title="SafeVest API",
        default_version='v1',
        description="Sistema para controle de dados",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="safeveste@gmail.com"),
        license=openapi.License(name="Free"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Rotas da API
route = routers.DefaultRouter()
route.register(r'empresa', viewsets.EmpresaViewSet)
route.register(r'setor', viewsets.SetorViewSet)
route.register(r'usuario', viewsets.UsuarioViewSet)
route.register(r'veste', viewsets.VesteViewSet)
route.register(r'usoveste', viewsets.UsoVesteViewSet)
route.register(r'leiturasensor', viewsets.LeituraSensorViewSet)

# Agrupamos TODAS as URLs da API sob o prefixo /api/
api_urlpatterns = [
    path('', include(route.urls)),
    # A rota de alertas agora também faz parte da API
    path('alertas/', AlertaListCreate.as_view(), name='alerta-list-create'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # A linha principal que inclui todas as URLs da API
    path('api/', include(api_urlpatterns)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)