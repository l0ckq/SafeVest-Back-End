from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class Empresa(models.Model):
    cnpj = models.CharField(max_length=20, unique=True)
    nome_empresa = models.CharField(max_length=200)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_empresa


class Setor(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="setores")
    nome = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome_empresa}"


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nome_completo, senha=None, **extra_fields):
        if not email:
            raise ValueError("Usuário precisa de um email")
        email = self.normalize_email(email)
        user = self.model(email=email, nome_completo=nome_completo, **extra_fields)
        user.set_password(senha)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome_completo, senha=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, nome_completo, senha, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    FUNCAO_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('SUPERVISOR', 'Supervisor'),
        ('OPERADOR', 'Operador'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.DO_NOTHING, related_name="usuarios")
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="usuarios")
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    funcao = models.CharField(max_length=20, choices=FUNCAO_CHOICES)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Admin
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome_completo']

    objects = UsuarioManager()

    def __str__(self):
        return f"{self.nome_completo} ({self.funcao})"


class Convite(models.Model):
    FUNCAO_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('SUPERVISOR', 'Supervisor'),
        ('OPERADOR', 'Operador'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE, null=True, blank=True)
    email_convidado = models.EmailField()
    funcao = models.CharField(max_length=20, choices=FUNCAO_CHOICES)
    codigo = models.CharField(max_length=64, unique=True)  # token único
    usado = models.BooleanField(default=False)
    criado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name="convites_criados")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.empresa.nome_empresa}] Convite {self.funcao} - {self.email_convidado}"