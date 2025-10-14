import paho.mqtt.client as mqtt
import time
import json
import random
from datetime import datetime

# --- CONFIGURAÇÕES ---
# O objetivo é centralizar as variáveis para facilitar a manutenção,
# permitindo que o script se conecte a diferentes ambientes (desenvolvimento, produção)
# apenas alterando estas linhas.
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh" # Formato user:vhost que descobrimos funcionar
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/dados_sensores"

# --- SIMULAÇÃO DE DADOS ---
# Em um ambiente de produção, cada veste física enviaria seu próprio número de série.
# Para simular múltiplos dispositivos, criamos uma lista de seriais que nosso script
# escolherá aleatoriamente.
# IMPORTANTE: Estes seriais precisam existir na sua tabela 'Veste' no banco de dados.
vestes_em_operacao = [
    "SV-DEMO-01",
    "SV-DEMO-02",
    "SV-DEMO-03",
]

print("--- Iniciando Simulador de Sensor ---")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sensor_simulador_1")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(BROKER_ADDRESS, BROKER_PORT)
print(f"Sensor Simulado conectado ao Broker: {BROKER_ADDRESS}")
# Usamos loop_start() para que a conexão MQTT rode em uma thread separada,
# não bloqueando nosso loop principal de envio de dados.
client.loop_start()

try:
    while True:
        # Escolhe um número de série aleatório para simular um colete enviando dados.
        serial_selecionado = random.choice(vestes_em_operacao)
        
        # Gera dados de sensor realistas.
        batimento = random.randint(70, 110)
        temp_a = round(random.uniform(36.1, 37.2), 2)

        # Simula uma chance de 15% de ocorrer um evento anormal, para testar a lógica de alerta.
        if random.random() < 0.15:
            batimento = random.randint(121, 170)
            temp_a = round(random.uniform(37.8, 39.5), 2)

        # Monta o payload (pacote de dados) que será enviado.
        # A estrutura do payload é o "contrato" entre o sensor e quem o escuta (o Cérebro).
        # Ele só contém informações que o próprio colete conhece.
        payload = {
            "numero_de_serie": serial_selecionado,
            "timestamp": datetime.now().isoformat(),
            "batimento": batimento,
            "temperatura_A": temp_a,
            "temperatura_C": temp_a, # Simplificado para usar o mesmo valor
            "nivel_co": round(random.uniform(5, 20), 2),
            "nivel_bateria": round(random.uniform(80.0, 99.9), 2),
        }
        
        payload_json = json.dumps(payload)
        client.publish(MQTT_TOPIC, payload_json)
        print(f"-> Enviado: {payload_json}")
        
        # Pausa a execução por 5 segundos antes de enviar o próximo dado.
        time.sleep(5)

except KeyboardInterrupt:
    print("\nSimulador encerrado pelo usuário.")
    client.loop_stop()
    client.disconnect()