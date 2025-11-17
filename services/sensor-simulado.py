import paho.mqtt.client as mqtt
import time
import json
import random

# --- CONFIGURAÇÕES ---
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh"
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"

# Tópico compatível com o Cérebro SafeVest
MQTT_TOPIC = "vest"

# --- SIMULAÇÃO DE DADOS ---
vestes_em_operacao = [
    "SV-DEMO-01",
    "SV-DEMO-02",
    "SV-DEMO-03",
]

print("--- Iniciando Simulador de Sensor ---")
client = mqtt.Client(client_id="sensor_simulador_1")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(BROKER_ADDRESS, BROKER_PORT)
print(f"Sensor Simulado conectado ao Broker: {BROKER_ADDRESS}")
client.loop_start()

try:
    while True:
        serial_selecionado = random.choice(vestes_em_operacao)
        
        # Gera dados de sensor realistas
        bpm = random.randint(70, 110)
        temp = round(random.uniform(36.1, 37.2), 2)
        humi = round(random.uniform(40.0, 60.0), 2)
        mq2 = round(random.uniform(0.5, 1.5), 2)
        
        # Chance de evento anormal
        if random.random() < 0.15:
            bpm = random.randint(121, 170)
            temp = round(random.uniform(37.8, 39.5), 2)
            humi = round(random.uniform(30.0, 70.0), 2)
            mq2 = round(random.uniform(1.6, 3.0), 2)
        
        # Monta payload compatível com Arduino/Cérebro
        payload = {
            "device_id": serial_selecionado,
            "bpm": bpm,
            "temp": temp,
            "humi": humi,
            "mq2": mq2
        }
        
        payload_json = json.dumps(payload)
        client.publish(MQTT_TOPIC, payload_json)
        print(f"-> Enviado: {payload_json}")
        
        time.sleep(5)

except KeyboardInterrupt:
    print("\nSimulador encerrado pelo usuário.")
    client.loop_stop()
    client.disconnect()