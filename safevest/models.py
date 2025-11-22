from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
from django.conf import settings

class Empresa(models.Model):
    id = models.AutoField(primary_key=True)
    cnpj = models.CharField(max_length=20, unique=True)
    nome_empresa = models.CharField(max_length=200)
    criado_em = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nome_empresa

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="profiles")
    ativo = models.BooleanField(default=True)
    foto_perfil = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    deletado = models.BooleanField(default=False)
    deletado_em = models.DateTimeField(null=True, blank=True)
    
    def __str__(self): 
        full_name = self.user.get_full_name()
        if full_name and full_name.strip():
            return full_name
        return self.user.email

    def soft_delete(self):
        """Método helper para soft delete"""
        self.deletado = True
        self.deletado_em = timezone.now()
        self.ativo = False
        self.save()

        # Também desativa o usuário
        self.user.is_active = False
        self.user.save()

class Veste(models.Model):
    numero_de_serie = models.CharField(max_length=50, unique=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="vestes", null=True, blank=True)
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="vestes")
    status = models.CharField(max_length=20, choices=[
        ('ativa', 'Ativa'),
        ('inativo', 'Inativo'),
    ], default='ativa')

class UsoVeste(models.Model):
    id = models.AutoField(primary_key=True)
    # Se a Veste for deletada, o histórico de uso dela também some
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE) 
    # Se o Profile for deletado, o histórico de uso dele também some
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE) 
    inicio_uso = models.DateTimeField()
    fim_uso = models.DateTimeField(null=True, blank=True)

class LeituraSensor(models.Model):
    id = models.AutoField(primary_key=True)
    # Se a Veste for deletada, as leituras dela também somem
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE, related_name='leituras') 
    timestamp = models.DateTimeField()
    # Campos dos sensores agora são opcionais para maior flexibilidade
    batimento = models.IntegerField(null=True, blank=True)
    temperatura_A = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperatura_C = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nivel_co = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nivel_bateria = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

class Alerta(models.Model):
    id = models.AutoField(primary_key=True)
    TIPO_ALERTA_CHOICES = [('Alerta', 'Alerta'), ('Emergência', 'Emergência')]
    # Se o Profile for deletado, os alertas dele também somem
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='alertas')
    # Se a Leitura que gerou o alerta for deletada, o alerta também some
    leitura_associada = models.ForeignKey(LeituraSensor, on_delete=models.CASCADE) 
    tipo_alerta = models.CharField(max_length=20, choices=TIPO_ALERTA_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        full_name = self.profile.user.get_full_name()
        user_identifier = full_name if full_name and full_name.strip() else self.profile.user.email
        return f"{self.tipo_alerta} para {user_identifier}"
    
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """Cria e salva um usuário comum com email"""
        if not email:
            raise ValueError('O campo de email é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Cria e salva um superusuário"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário precisa ter is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
    
class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()

    def __str__(self):
        return self.email