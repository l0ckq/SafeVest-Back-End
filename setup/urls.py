from django.contrib import admin
from django.urls import path, include
from safevest.api import viewsets 
from safevest.views import AlertaListCreate, VesteBulkCreateView, OnboardingView 
# Imports necessários do DRF e SimpleJWT
from rest_framework import routers, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# Imports para a documentação Swagger (drf-yasg)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from django.conf import settings
from django.conf.urls.static import static

# --- Configuração da Documentação Swagger ---
schema_view = get_schema_view(
    openapi.Info(
        title="SafeVest API",
        default_version='v1',
        description="Sistema para controle de dados dos coletes SafeVest.",
        terms_of_service="https://www.google.com/policies/terms/", # Trocar por um link real se houver
        contact=openapi.Contact(email="contato@safevest.com"), # Trocar por um email real
        license=openapi.License(name="Licença do Projeto"), # Definir a licença
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# --- Roteador para as ViewSets (CRUD Automático) ---
# O DefaultRouter cria automaticamente as URLs para listagem, detalhe, criação, etc.
route = routers.DefaultRouter()
route.register(r'empresa', viewsets.EmpresaViewSet, basename='empresa')
route.register(r'setor', viewsets.SetorViewSet, basename='setor')
route.register(r'profile', viewsets.ProfileViewSet, basename='profile') # Usando Profile
route.register(r'veste', viewsets.VesteViewSet, basename='veste')
route.register(r'usoveste', viewsets.UsoVesteViewSet, basename='usoveste')
route.register(r'leiturasensor', viewsets.LeituraSensorViewSet, basename='leiturasensor')

# --- Lista de URLs Específicas da API ---
# Aqui colocamos as rotas do roteador e as nossas rotas customizadas.
api_urlpatterns = [
    # Inclui todas as rotas geradas pelo DefaultRouter
    path('', include(route.urls)), 
    
    # Rotas para as Views Customizadas que criamos
    path('alertas/', AlertaListCreate.as_view(), name='alerta-list-create'),
    path('vestes/bulk-create/', VesteBulkCreateView.as_view(), name='veste-bulk-create'),
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    
    # Rotas para obter e atualizar o token JWT (para login)
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# --- URLs Principais do Projeto ---
# Define as rotas raiz do seu site.
urlpatterns = [
    # Rota para a interface de administração do Django
    path('admin/', admin.site.urls),
    
    # Rota principal ('/') aponta para a documentação Swagger
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    
    # Delega todas as URLs que começam com 'api/' para serem tratadas por api_urlpatterns
    path('api/', include(api_urlpatterns)), 
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)