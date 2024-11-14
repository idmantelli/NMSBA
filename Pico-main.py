"""Code compiled by Isaac Mantelli based on public sources."""

from mqtt_async import MQTTClient, config
import asyncio
from machine import ADC, Pin

pico_name = "pico1"
led = Pin("LED", Pin.OUT) # Initialize the onboard LED

# HUM_TEMP = Pin(2, Pin.IN) # Define the humidity/temperature sensor
relay = Pin(18, Pin.OUT) # Define the location and behavior of the water pump relay
SOIL1 = ADC(Pin(26)) # Define the location of the first soil moisture sensor
# SOIL2 = ADC(Pin(27))
# SOIL3 = ADC(Pin(28))
HI_ADC = 48600 # Initialize the 'dry' ADC reading
LO_ADC = 19400 # Initialize the 'wet' ADC reading

# Set up the connection to the Raspberry Pi WiFi hotspot
config['ssid'] = 'nmsba-ap'
config['wifi_pw'] = 'nmsba_Connect'
config['server'] = '10.42.0.1'

async def up(client): # respond to connectivity being (re)established
    """This is code taken directly from the mqtt_async docs. It helps keep
    the connection to the broker (Raspberry Pi) clean.
    """
    while True:
        await client.up.wait() # wait on event
        client.up.clear()
        

def read_sensor(sensor, sensor_high_value, sensor_low_value):
    """Read a sensor and convert the raw ADC value to a 'human-readable' percentage.
    This is the main function that most of the script is based on.
    Uses two lines of code from the micropython docs:
        adc = ADC(pin)
        val=adc.read_u16()
    (see: docs.micropython.org/en/latest/library/machine.ADC.html)
    
    Definitions of arguments:
    -sensor: name of ADC input defined at the top (for example, SOIL1)
    -sensor_high_value = highest ADC value, associated with sensor reading in air (dry)
    -sensor_low_value = lowest ADC value, associated with sensor reading in water (wet)
    """
    percent = int(((sensor_high_value - sensor.read_u16()) * 100) \
              /(sensor_high_value - sensor_low_value))
    return percent


"""For the following two functions:
    Use buttons on the Pico's breadboard to get the extreme values of 0% moisture
    (i.e., holding the sensor in the air) and 100% moisture (i.e., placing the
    sensor's tip in water). These values will be saved to the HI_ADC and LO_ADC variables
    defined at the top of the code to calibrate the read_sensor function defined previously.
    For ease, 0% and 100% calibration functions have been split up.
    
    Uses code from the official Raspberry Pi Pico docs:
        from picozero import Button
        button_1 = Button(#) (<- # can be any digital pin number)
        button_1.when_pressed = function_1 (in this case, calibrate_sensor)
    (see: projects.raspberrypi.org/en/projects/introduction-to-the-pico/10)
    
    We are defining 'function_1' in these two functions. Note that these sensors read
    higher values (~44000) for dry conditions and lower values (~22000) for wet conditions.
"""

from picozero import Button
button_calibrate_0_per = Button(14) # Green button connected to pin 14
button_calibrate_100_per = Button(15) # Green button connected to pin 15

def calibrate_sensor_0(sensor):
    """Define the function that will apply to the green button and define '0% moisture'.
    Calls the global variable HI_ADC and assigns it a new value from a dry sensor reading.
    
    Definition of argument:
    -sensor: name of ADC input defined at the top (the sensor we want to calibrate)
    """
    global HI_ADC # tell the function that we are reading a global variable
    HI_ADC = sensor.read_u16() # Use the normal method for reading a moisture sensor

def calibrate_sensor_100(sensor):
    """Define the function that will apply to the blue button and define '100% moisture'.
    Calls the global variable LO_ADC and assigns it a new value from a wet sensor reading.
    
    Definition of argument:
    -sensor: name of ADC input defined at the top (the sensor we want to calibrate)
    """
    global LO_ADC # tell the function that we are reading a global variable
    LO_ADC = sensor.read_u16() # Use the normal method for reading a moisture sensor

button_calibrate_0_per.when_pressed = calibrate_sensor_0
button_calibrate_100_per.when_pressed = calibrate_sensor_100

# These bounds are arbitrary starting values. MQTT communication between Pico and Pi
# could modify these values, or they can be changed manually.
pump_upper_bound = 70 # percent
pump_lower_bound = 40 # percent
async def pump_relay(sensor, sensor_high_value, sensor_low_value):
    """
    Turn on the pump (send a high voltage (3.3V) to a relay) if the soil moisture
    is below a defined percent. Turn off the pump (send a low voltage to a relay)
    if the soil moisture is above a defined percent. The code checks this condition
    only once every 5 seconds to save on power consumption. 
    
    Definitions of arguments:
    -sensor: name of ADC input defined at the top (for example, SOIL1)
    -sensor_high_value = highest ADC value, associated with sensor reading in air
    -sensor_low_value = lowest ADC value, associated with sensor reading in water
    """
    while True:
        await asyncio.sleep(1) # check the moisture levels every 5 seconds to save power
        moisture = read_sensor(SOIL1, HI_ADC, LO_ADC) # use the function above
        if moisture < pump_lower_bound: # if the soil moisture is below bounds,
            relay.value(1) # make the pin high to turn on the relay.
        elif moisture > pump_upper_bound: # if the soil moisture is above bounds,
            relay.value(0) # make the pin low to turn off the relay.

async def measure_moisture(sensor1, sensor2=None, sensor3=None):
    """ Use the first function we defined to read up to 3 soil moisture sensors.
    This function requires that at least one sensor is connected properly, but
    not all 3 sensors need to be connected. Every 30 seconds, take a new reading
    from any enabled sensors and publish the value to the associated topic. The Pi
    on the other end will receive that value and be able to display it.
    
    See Paho's PyPi docs for the original text of client.publish(...).
    
    Definitions of arguments:
    -sensor1: name of first ADC input defined at the top of the code
    -sensor2: name of second ADC input. Default value is None.
    -sensor3: name of third ADC input. Default value is None.
    """
    while True:
        await asyncio.sleep(1) # measure moisture every n seconds.
        moisture1 = read_sensor(SOIL1, HI_ADC, LO_ADC)
        # moisture2 = read_sensor(SOIL2, HI_ADC, LO_ADC)
        # moisture3 = read_sensor(SOIL3, HI_ADC, LO_ADC)
        await client.publish(f'soilmoisture/{pico_name}/sensor1', f'{moisture1}', qos = 1)
        #await client.publish(f'soilmoisture/{pico_name}/sensor2', f'{moisture2}', qos = 1)
        #await client.publish(f'soilmoisture/{pico_name}/sensor2', f'{moisture2}', qos = 1)

"""The following block of code is an example of using the MQTT protocol to subscribe to a
topic that the Raspberry Pi publishes to. In theory, the Pi could publish new min/max
bounds for the water pump to turn on/off, and here the Pico would receive those messages
and update the global pump bound variables defined above. Code is taken from the mqtt_async
official docs and is currently commented out for continued testing."""
# async def change_pump_bounds(client, pico_name):
#     await client.subscribe(f'pump/{pico_name}/upper_bound', qos=1)
#     await client.subscribe(f'pump/{pico_name}/lower_bound', qos=1)
#     async for topic, msg, retained in client.queue:
#         print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')

async def main(client):
    """Use the mqtt_async function client.connect() to connect to the Pi's WiFi hotspot.
    If the connection is successful, the LED on the Pico will turn on to confirm
    everything is working.
    
    Then, use an asyncio Task Group to queue up the main functions in our code
    (measure_moisture, pump_relay). See the official Python docs for more information:
    docs.python.org/3/library/asyncio-task.html (Section "Task Groups")
    """
    await client.connect() # Try to connect to the hotspot...
    led.on() # ...and turn on the LED if successful.

    async with asyncio.Taskgroup() as tg:
        task1 = tg.create_task(measure_moisture(SOIL1))
        task2 = tg.create_task(pump_relay(SOIL1, HI_ADC, LO_ADC))
    
config['queue_len'] = 1
MQTTClient.DEBUG = True
client = MQTTClient(config) # initialize the client using the config parameters at the top
try:
    asyncio.run(main(client))
finally: # When the program finishes:
    client.disconnect() # prevent LmacRxBlk:1 errors
    led.off() # Turn off the onboard LED
    relay.value(0) # Turn off the pump relay (don't want that to run nonstop!)
