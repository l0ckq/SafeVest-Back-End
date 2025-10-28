from django.contrib import admin
from django.urls import path, include
from rest_framework import routers, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from safevest.api import viewsets
from safevest.views import (
    AlertaListCreate,
    VesteBulkCreateView, 
    UserByEmailView,
    signup_empresa_admin,  # Usar esta para cadastro inicial
    criar_usuario_colaborador
)

# Swagger docs
schema_view = get_schema_view(
    openapi.Info(
        title="SafeVest API",
        default_version='v1',
        description="Sistema para controle de dados dos coletes SafeVest."
    ),
    public=True,
    permission_classes=[permissions.AllowAny]
)

# --- Router DRF ---
router = routers.DefaultRouter()
router.register(r'empresa', viewsets.EmpresaViewSet, basename='empresa')
router.register(r'setor', viewsets.SetorViewSet, basename='setor')
router.register(r'profile', viewsets.ProfileViewSet, basename='profile')
router.register(r'veste', viewsets.VesteViewSet, basename='veste')
router.register(r'usoveste', viewsets.UsoVesteViewSet, basename='usoveste')
router.register(r'leiturasensor', viewsets.LeituraSensorViewSet, basename='leiturasensor')

# --- URLs ---
urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Routes
    path('api/', include([
        path('', include(router.urls)),  # CRUD automáticos
        
        # Endpoints personalizados existentes
        path('alertas/', AlertaListCreate.as_view(), name='alerta-list-create'),
        path('vestes/bulk-create/', VesteBulkCreateView.as_view(), name='veste-bulk-create'),
        path('user-by-email/', UserByEmailView.as_view(), name='user-by-email'),
        
        # ENDPOINTS PARA CADASTRO (OTIMIZADOS)
        path('signup/', signup_empresa_admin, name='signup-empresa-admin'),  # Cadastro inicial
        path('usuarios/create/', criar_usuario_colaborador, name='criar-usuario'),  # Cadastro colaboradores
        
        # Autenticação JWT
        path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    ])),

    # Swagger
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]