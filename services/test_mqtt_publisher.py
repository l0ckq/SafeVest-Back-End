# test_mqtt_publisher.py
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

# Configurações (igual ao cerebro-service)
BROKER = "jaragua-01.lmq.cloudamqp.com"
PORT = 1883
USER = "qyyguyzh:qyyguyzh"
PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
TOPIC = "safevest/sensores"

def publicar_dados_teste():
    client = mqtt.Client(client_id="esp32_simulator")
    client.username_pw_set(USER, PASSWORD)
    
    try:
        client.connect(BROKER, PORT)
        print("✅ Conectado para testes")
        
        # Dados de exemplo - USE O NÚMERO DE SÉRIE DE UMA VESTE QUE EXISTE NO SEU BANCO
        dados_teste = {
            "device_id": "VS001",  # ⚠️ SUBSTITUA por um número de série que existe no seu banco
            "bpm": 75,
            "temp": 36.5,
            "co": 12.5,
            "battery": 85.0,
            "timestamp": datetime.now().isoformat()
        }
        
        client.publish(TOPIC, json.dumps(dados_teste))
        print(f"📤 Dados publicados: {dados_teste}")
        
        time.sleep(1)
        client.disconnect()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    publicar_dados_teste()