from django.db import models
from django.contrib.auth.models import User

class Empresa(models.Model):
    id = models.AutoField(primary_key=True)
    cnpj = models.CharField(max_length=20, unique=True)
    nome_empresa = models.CharField(max_length=200)
    criado_em = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nome_empresa

class Setor(models.Model):
    id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="setores")
    nome = models.CharField(max_length=200)
    def __str__(self): return f"{self.nome} - {self.empresa.nome_empresa}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="profiles")
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles")
    ativo = models.BooleanField(default=True)
    def __str__(self): return self.user.get_full_name() or self.user.username

class Veste(models.Model):
    id = models.AutoField(primary_key=True)
    numero_de_serie = models.CharField(max_length=100, unique=True)
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='vestes')
    def __str__(self): return self.numero_de_serie

class UsoVeste(models.Model):
    id = models.AutoField(primary_key=True)
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    inicio_uso = models.DateTimeField()
    fim_uso = models.DateTimeField(null=True, blank=True)

class LeituraSensor(models.Model):
    id = models.AutoField(primary_key=True)
    veste = models.ForeignKey(Veste, on_delete=models.CASCADE, related_name='leituras')
    timestamp = models.DateTimeField()
    batimento = models.IntegerField()
    temperatura_A = models.DecimalField(max_digits=5, decimal_places=2)
    temperatura_C = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_co = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_bateria = models.DecimalField(max_digits=5, decimal_places=2)

class Alerta(models.Model):
    id = models.AutoField(primary_key=True)
    TIPO_ALERTA_CHOICES = [('Alerta', 'Alerta'), ('Emergência', 'Emergência')]
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='alertas')
    leitura_associada = models.ForeignKey(LeituraSensor, on_delete=models.CASCADE)
    tipo_alerta = models.CharField(max_length=20, choices=TIPO_ALERTA_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.tipo_alerta} para {self.profile.user.username}"