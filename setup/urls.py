from django.contrib import admin
from django.urls import path, include
from safevest.api import viewsets
from rest_framework import routers, permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from django.conf import settings
from django.conf.urls.static import static

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

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rota principal já abre o Swagger
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # Outras documentações
    path('swaggerjson/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Rotas da API
    path('api/', include(route.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
