from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# ============================
# USER CUSTOMIZADO (LOGIN POR EMAIL)
# ============================

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O usuário deve ter um email.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)

    # campos obrigatórios do Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # sem username

    objects = UserManager()

    def __str__(self):
        return self.email



# ============================
# EMPRESA
# ============================

class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome



# ============================
# SETOR
# ============================

class Setor(models.Model):
    nome = models.CharField(max_length=255)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="setores")

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"



# ============================
# PROFILE (administrador/supervisor/operador)
# ============================

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True)

    ROLE_CHOICES = (
        ("admin", "Administrador"),
        ("supervisor", "Supervisor"),
        ("operador", "Operador"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="operador")

    ativo = models.BooleanField(default=True)
    deletado = models.BooleanField(default=False)
    deletado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} ({self.role})"



# ============================
# VESTE
# ============================

class Veste(models.Model):
    numero_de_serie = models.CharField(max_length=255, unique=True)
    profile = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.SET_NULL)

    # Opcional: pode associar um setor nativo
    setor = models.ForeignKey(Setor, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Veste {self.numero_de_serie}"



# ============================
# USO DE VESTE
# ============================

class UsoVeste(models.Model):
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    inicio_uso = models.DateTimeField(auto_now_add=True)
    fim_uso = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.profile.user.email} usando {self.veste.numero_de_serie}"



# ============================
# LEITURA DE SENSORES
# ============================

class LeituraSensor(models.Model):
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE)

    bpm = models.IntegerField()
    temp = models.FloatField()
    humi = models.FloatField()
    mq2 = models.FloatField()

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Leitura {self.veste.numero_de_serie} ({self.timestamp})"



# ============================
# ALERTAS
# ============================

class Alerta(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True)
    leitura_associada = models.ForeignKey(LeituraSensor, on_delete=models.CASCADE)

    tipo_alerta = models.CharField(max_length=255)

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alerta {self.tipo_alerta} - {self.timestamp}"