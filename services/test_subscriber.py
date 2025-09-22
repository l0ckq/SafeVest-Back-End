import paho.mqtt.client as mqtt

BROKER_ADDRESS = "jaragua-01.lmq.cloudamqp.com"
BROKER_PORT = 1883
MQTT_USERNAME = "qyyguyzh:qyyguyzh" 
MQTT_PASSWORD = "e8juWkMvJQhVSgudnSPZBS0vtj3COZuv"
MQTT_TOPIC = "safevest/teste"

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("--- OUVINTE CONECTADO COM SUCESSO! ---")
        client.subscribe(MQTT_TOPIC)
        print(f"--- Aguardando mensagens no tópico '{MQTT_TOPIC}' ---")
    else:
        print(f"--- FALHA NA CONEXÃO! Código de erro: {rc} ---")

def on_message(client, userdata, msg):
    print(f"\n>>> MENSAGEM RECEBIDA: {msg.payload.decode('utf-8')} <<<")
    client.loop_stop()
    client.disconnect()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ouvinte_teste_123")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

try:
    print("Tentando conectar o Ouvinte...")
    client.connect(BROKER_ADDRESS, BROKER_PORT)
    client.loop_forever()
except Exception as e:
    print(f"Ocorreu um erro ao tentar conectar: {e}")

print("Ouvinte encerrado.")