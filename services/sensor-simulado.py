import paho.mqtt.client as mqtt
import time
import json
import random
from datetime import datetime

# --- CREDENCIAIS CORRIGIDAS E CONSISTENTES ---
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh" # Formato correto que você descobriu
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/dados_sensores"

vestes_em_uso = [
    {"veste": 1, "usuario": 1}, # CORREÇÃO: Nomes dos campos alinhados com o models.py
    {"veste": 2, "usuario": 2},
    {"veste": 3, "usuario": 4},
]

print("--- Iniciando Simulador de Sensor ---")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sensor_simulador_1")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(BROKER_ADDRESS, BROKER_PORT)
print(f"Sensor Simulado conectado ao Broker: {BROKER_ADDRESS}")
client.loop_start()

try:
    while True:
        veste_info = random.choice(vestes_em_uso)
        batimento = random.randint(70, 110)
        temp_a = round(random.uniform(36.1, 37.2), 2)
        if random.random() < 0.15:
            batimento = random.randint(121, 170)
            temp_a = round(random.uniform(37.8, 39.5), 2)

        # CORREÇÃO: Payload agora usa os mesmos nomes de campos do seu models.py
        payload = {
            "veste": veste_info["veste"],
            "usuario": veste_info["usuario"],
            "timestamp": datetime.now().isoformat(),
            "batimento": batimento,
            "temperatura_A": temp_a,
            "temperatura_C": temp_a,
            "nivel_co": round(random.uniform(5, 20), 2),
            "nivel_bateria": round(random.uniform(80.0, 99.9), 2),
        }
        
        payload_json = json.dumps(payload)
        client.publish(MQTT_TOPIC, payload_json)
        print(f"-> Enviado: {payload_json}")
        time.sleep(5)
except KeyboardInterrupt:
    print("\nSimulador encerrado.")
    client.loop_stop()
    client.disconnect()