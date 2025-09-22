# /services/sensor_simulator.py
import paho.mqtt.client as mqtt
import time
import json
import random
from datetime import datetime

# --- CREDENCIAIS ATUALIZADAS --- #
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh"
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/dados_sensores"

vestes_em_uso = [
    {"id_veste": 1, "id_usuario": 1},
    {"id_veste": 2, "id_usuario": 2},
    {"id_veste": 3, "id_usuario": 4},
]

print("--- Iniciando Simulador de Sensor ---")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sensor_simulador_1")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(BROKER_ADDRESS, BROKER_PORT)
print(f"Sensor Simulado conectado ao Broker: {BROKER_ADDRESS}")
client.loop_start()

try:
    while True:
        veste = random.choice(vestes_em_uso)
        batimento = random.randint(70, 110)
        temp_a = round(random.uniform(36.1, 37.2), 2)
        if random.random() < 0.15:
            batimento = random.randint(121, 170)
            temp_a = round(random.uniform(37.8, 39.5), 2)

        payload = {
            "id_veste": veste["id_veste"],
            "id_usuario": veste["id_usuario"],
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