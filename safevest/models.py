from django.db import models

class Empresa(models.Model):
    cnpj = models.CharField(max_length=20, unique=True)
    nome_empresa = models.CharField(max_length=200)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_empresa


class Setor(models.Model):
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="setores"
    )
    nome = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome_empresa}"

class Usuario(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.DO_NOTHING, related_name="usuarios", null=True, blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="usuarios")
    id_usuario = models.AutoField(primary_key=True)
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

class Veste(models.Model):
    id_veste = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING)

class UsoVeste(models.Model):
    id_uso = models.AutoField(primary_key=True)
    id_veste = models.ForeignKey(Veste, on_delete=models.DO_NOTHING)
    inicio_uso = models.DateTimeField()
    fim_uso = models.DateTimeField()

class LeituraSensor(models.Model):
    id_leitura = models.AutoField(primary_key=True)
    id_veste = models.ForeignKey(Veste, on_delete=models.DO_NOTHING)
    timestamp = models.DateTimeField()
    batimento = models.IntegerField()
    temperatura_A = models.DecimalField(max_digits=5, decimal_places=2)
    temperatura_C = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_co = models.DecimalField(max_digits=5, decimal_places=2)
    nivel_bateria = models.DecimalField(max_digits=5, decimal_places=2)