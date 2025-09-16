# /services/test_publisher.py
import paho.mqtt.client as mqtt
import time

# --- ATENÇÃO: PREENCHA COM AS MESMAS CREDENCIAIS DO OUTRO ARQUIVO ---
BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh" # <<< VAMOS USAR A VERSÃO SIMPLES PRIMEIRO
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/teste"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="falante_teste_123")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

try:
    print("Tentando conectar o Falante...")
    client.connect(BROKER_ADDRESS, BROKER_PORT)
    print("Falante conectado com sucesso!")
    
    mensagem = "Olá, Mundo! A conexão funciona!"
    print(f"Enviando a mensagem: '{mensagem}'")
    client.publish(MQTT_TOPIC, mensagem)
    
    print("Mensagem enviada. Desconectando em 3 segundos...")
    time.sleep(3)
    client.disconnect()
    print("Falante desconectado.")

except Exception as e:
    print(f"Ocorreu um erro ao tentar conectar ou publicar: {e}")