import adafruit_dht
import pulseio
import board
import time
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_connection_manager
import os
import ssl
import socketpool
import wifi
from adafruit_datetime import datetime
import adafruit_ntp
import adafruit_ssd1306
import busio as io

def connect(mqtt_client, userdata, flags, rc):
    # This function will be called when the mqtt_client is connected
    # successfully to the broker.
    print("Connected to MQTT Broker!")
    print("Flags: {0}\n RC: {1}".format(flags, rc))

def disconnect(mqtt_client, userdata, rc):
    # This method is called when the mqtt_client disconnects
    # from the broker.
    print("Disconnected from MQTT Broker!")

def subscribe(mqtt_client, userdata, topic, granted_qos):
    # This method is called when the mqtt_client subscribes to a new feed.
    print("[+] Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def publish(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client publishes data to a feed.
    print("\t [-] Published to {0} with PID {1}".format(topic, pid))

def message(client, topic, message):
    print("New message on topic {0}: {1}".format(topic, message))

def read_sensor_with_retries(retries=50, delay=2):
    for _ in range(retries):
        try:
            temperature = dhtDevice.temperature
            humidity = dhtDevice.humidity
            if temperature is not None and humidity is not None:
                return temperature, humidity
        except RuntimeError as e:
            print(f"Reading from DHT sensor failed: {e}. Retrying...")
            time.sleep(delay)
    raise RuntimeError("Failed to read from DHT sensor after multiple attempts")

def connect_wifi():
    # Connect to Wifi
    print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
    )

def create_mqtt_client():
    # Prepare the mqtt connection
    ssl_context = ssl.create_default_context()

    mqtt_client = MQTT.MQTT(
        broker="io.adafruit.com",
        username=aio_username,
        password=aio_key,
        socket_pool=pool,
        ssl_context=ssl_context,
    )
    return mqtt_client

def get_formatted_datetime(timezone_offset=2, retries=50, delay=2):
    for _ in range(retries):
        try:
            datetime = ntp.datetime
            # Adjust the time for the timezone offset
            formatted_datetime = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
                datetime.tm_year, datetime.tm_mon, datetime.tm_mday,
                datetime.tm_hour, datetime.tm_min, datetime.tm_sec
            )
            return formatted_datetime
        except OSError as e:
            print(f"Fetching time failed: {e}. Retrying...")
            time.sleep(delay)
    raise RuntimeError("Failed to get time from NTP server after multiple attempts")

def setup_display():
    """
    Sets up the display oled
    """
    i2c = io.I2C(board.GP27, board.GP26)
    oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)
    return oled

def show_text(text, line, delay=0, refresh=False):
    """
    Shows texts in lines
    """
    if refresh:
        oled.fill(0)
        oled.show()
    if line == 1:
        y = 0
    elif line == 2:
        y = 10
    elif line == 3:
        y = 20
    elif line == 4:
        y = 30
    elif line == 5:
        y = 40
    elif line == 6:
        y = 50
    if text == 'ok':
        # show special checkbox at the end of the line
        oled.line(117, y + 4, 120, y + 7, 1)
        oled.line(120, y + 7, 125, y + 2, 1)
        oled.show()
    else:
        oled.text(text[:21], 0, y, 1)
        oled.show()
        if len(text) > 21:
            text2 = text[21:]
            oled.text(text2, 0, y + 10, 1)
            oled.show()
    time.sleep(delay)

def connect_mqtt_subscribe():
    """
    Connect to the mqtt and subscribe
    """
    mqtt_connected = False
    show_text('Try connect to mqtt', line=6)
    print("Attempting to connect to %s" % mqtt_client.broker)
    while not mqtt_connected:
        try:
            mqtt_client.connect()
            show_text('ok', line=6)
            mqtt_connected = True
        except Exception as e:
            print(f"Error connecting mqtt: {e}")
            show_text('Error connecting mqtt', line=1, refresh=True)
            show_text(f'{e}', line=2)
    mqtt_client.subscribe(mqtt_topic_temp)
    mqtt_client.subscribe(mqtt_topic_hum)

def disconnect_mqtt_subscribe():
    """
    Disconnect from the mqtt
    """
    print("Unsubscribing from %s" % mqtt_topic_temp)
    mqtt_client.unsubscribe(mqtt_topic_temp)
    print("Unsubscribing from %s" % mqtt_topic_hum)
    mqtt_client.unsubscribe(mqtt_topic_hum)
    print("Disconnecting from %s" % mqtt_client.broker)
    mqtt_client.disconnect()


#############################################
# Main code
# Setup the display

oled = setup_display()

# Blink the screen to know we are booting
oled.fill(1)
oled.show()
time.sleep(1)
oled.fill(0)

show_text('Setting up sensor', line=1, refresh=True)

# Get the dht device of the sensor
dhtDevice = adafruit_dht.DHT11(board.GP22)

show_text('ok', line=1)

# Wifi
show_text('Try connect wifi', line=2)
wifi_connected=False
while not wifi_connected:
    try:
        connect_wifi()
        wifi_connected = True
        print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")
        pool = socketpool.SocketPool(wifi.radio)
        show_text('ok', line=2)
    except ConnectionError as e:
        print(f"Error connecting wifi: {e}")
        show_text('Error connecting Wifi', line=1, refresh=True)
        show_text(f'{e}', line=2)

# Get ntp date
print('Trying to connect to ntp')
show_text('Try connect ntp', line=3)
ntp_connected=False
while not ntp_connected:
    try:
        ntp = adafruit_ntp.NTP(pool, tz_offset=+2)
        ntp_connected = True
        show_text('ok', line=3)
        print(f"Connected to ntp")
    except Exception as e:
        print(f"Error connecting ntp: {e}")
        show_text('Error connecting ntp', line=1, refresh=True)
        show_text(f'{e}', line=2)


# Setting up mqtt
print('Setting up the MQTT')
# Read credentials from file
aio_username = os.getenv("AIO_USERNAME")
aio_key = os.getenv("AIO_KEY")
mqtt_topic_temp = aio_username + "/feeds/Ants_temperature"
mqtt_topic_hum = aio_username + "/feeds/Ants_humidity"
print(f'\tTopic temp: {mqtt_topic_temp}')
print(f'\tTopic hum: {mqtt_topic_hum}')
mqtt_client = create_mqtt_client()
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message


while True:
    connect_mqtt_subscribe()
    temp, hum = read_sensor_with_retries()
    print(f"{get_formatted_datetime()}: Temp: {temp}. Hum: {hum}")
    show_text(f'Time: {get_formatted_datetime()}', line=1, refresh=True)
    show_text(f'Temp: {temp}', line=3)
    show_text(f'Hum : {hum}', line=4)
    mqtt_client.publish(mqtt_topic_temp, temp)
    mqtt_client.publish(mqtt_topic_hum, hum)
    show_text('Sent', line=6)
    show_text('ok', line=6)
    time.sleep(60)
    disconnect_mqtt_subscribe()