import re

def validar_cnpj(cnpj: str) -> bool: # Funciona via dígitos verificadores
    cnpj = re.sub(r'\D', '', cnpj)  # remove caracteres não numéricos
    if len(cnpj) != 14 or cnpj in (c * 14 for c in "1234567890"):
        return False

    def calcular_digito(cnpj_parcial):
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(a) * b for a, b in zip(cnpj_parcial, pesos[-len(cnpj_parcial):]))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    digito1 = calcular_digito(cnpj[:12])
    digito2 = calcular_digito(cnpj[:12] + digito1)

    return cnpj[-2:] == digito1 + digito2
