"""Code compiled by Isaac Mantelli based on public sources."""

import paho.mqtt.client as mqtt
import csv

from tkinter import *
from tkinter import ttk

broker_address = '10.42.0.1' # this is the IP address of the RPi 4
client = mqtt.Client('Pi4') # this is the username of the RPi 4
filepath = '/home/pi4/Documents/moisture_logs/1.csv' # where to save the data

class App(Frame):
	"""The following code combines available Paho MQTT examples with 
	Tkinter examples in an object-oriented programming (OOP) wrapper. 
	For more information on both modules, see:
	(For Paho MQTT)
		pypi.org/project/paho-mqtt//
		docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
	(For Tkinter)
		docs.python.org/3/library/tkinter.html
		tkdocs.com/tutorial
	
	The OOP wrapper is derived from the Python docs section titled 
	"Important Tk Concepts." The tk "main loop" (expressed at the end of
	the code as app.mainloop()) is the topmost level of the code, while 
	the MQTT framework exists inside of the main loop. This layering
	helps to better incorporate the messages received through the
	MQTT subscription into the components of the window.
	
	Some variable names have been changed to be relevant to the current 
	problem, but most code is taken directly from one of the four 
	sources listed above. MQTT code from PyPi has been modified (mostly
	by simply adding self.xxxx) to work it into the class structure.
	"""
	def __init__(self, root, client, address):
		super().__init__(root)
		self.current_moisture = str(50) # added attribute 
		self.readback = Text(root, width=40, height=10)
		self.readback.grid()
		self.readback.tag_add('moisture','1.0','2.0')
		self.readback.tag_configure(
			'moisture',font=('Calibri', 20, 'bold'),justify='center'
		)
		
		# work in the MQTT client and callbacks
		self.client = client
		self.address = address
		self.client.on_message = self.on_message
		self.client.on_connect = self.on_connect
		self.client.connect(address)
	
	def update_readback(self):
		"""Uses code from tkdocs to first delete the original soil
		moisture value and then replace it with the new value.
		(See: tkdocs.com/tutorial/text.html, sections "The Basics" and
		"Deleting Text".)
		"""
		self.readback.delete('1.0','2.0')
		self.readback.insert('1.0',
			'Soil moisture: ' + self.current_moisture + '%',
			('moisture'))

	"""
	The following 8 lines are taken from the basic example provided
	in the pypi.org source. There are three modifications:
		1) The client subscribes to 'soilmoisture/#' (# means 'all').
		2) The on_message function updates the current_moisture
			attribute with the newly received sensor reading instead
			of printing to the terminal as in the example.
		3) client.loop_forever() has been changed to client.loop_start()
			to fit within the Tkinter main loop. The 'new' function 
			startmqtt() helps cleanly start the connection.
	"""	
	def on_connect(self, client, userdata, flags, rc):
		print(f'Connected with result code {rc}')
		client.subscribe('soilmoisture/#')
	
	def on_message(self, client, userdata, msg):
		self.current_moisture = msg.payload.decode("utf-8")
		self.update_readback()

	def startmqtt(self):
		self.client.loop_start()

	
root = Tk() # Create a Tkinter instance
app = App(root, client, broker_address) # Create an App instance
app.startmqtt() # Start the MQTT connection
app.mainloop() # Start the window
