import socket
import os
import time
from bluetooth import *
import xbox

class Connections():
	'''
	Sets up all the connections for running the rover, from a bluetooth app, xbox controller, and a unix socket for
	communication to thread running the LED screen

	'''
	def __init__(self):
		self.type = "b"
		self.joy = None
		self.bt_sock = None
		self.check = 0
		self.led = 0
		self.screen_sock = None

	def _btConnect(self):
		'''
		Initializes the server side for bluetooth communication, with a timeout of 1 second between data from the app
		'''
		server_sock = BluetoothSocket(RFCOMM)
		server_sock.bind(("",PORT_ANY))
		server_sock.listen(1)

		port = server_sock.getsockname()[1]
		uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

		advertise_service( server_sock, "raspberrypi",
						   service_id = uuid,
						   service_classes = [uuid, SERIAL_PORT_CLASS],
						   profiles = [SERIAL_PORT_PROFILE],
						   )
		print "waiting for connection on RFCOMM channel %d" % port
		client_socket, client_info = server_sock.accept()
		client_socket.setblocking(0)
		print "Accepted connection from ", client_info
		self.bt_sock = client_socket
		self.bt_sock.settimeout(1)

	def _xBoxConnect(self):
		'''
		Initializes a listener for the Xbox controller
		'''
		self.joy = xbox.Joystick()
		print 'Waiting on Xbox connect'
		while not self.joy.connected():
			time.sleep(1)
		print 'Accepted connection from  Xbox controller', self.joy.connected()

	def _btVals(self):
		'''
		Parses values from the bluetooth app as drive, turning, and LED screen commands
		these values should be:

		v: [-100,100]
		r: [-100,100]
		led: [0-3]

		'''
		try:
			sockData = self.bt_sock.recv(1024)
			v,s,c = ord(sockData[3]),ord(sockData[7]),ord(sockData[-1])
			self.led = ord(sockData[11])
			self.bt_sock.send('1')
			return (v-100,s-100)
		except:
			pass

	def _xboxVals(self):
		'''
		Parses values from the Xbox controller. By default the speed is halved, and the "A" button
		is used as a boost button. The D-pad controls the LED screen

		'''

		if self.joy.connected():
			if self.joy.dpadUp():
				self.led = 0
			elif self.joy.dpadRight():
				self.led = 1
			elif self.joy.dpadDown():
				self.led = 2
			elif self.joy.dpadLeft():
				self.led = 3

			v,r = int(self.joy.leftY()*50),int(self.joy.rightX()*100)
			if self.joy.A():
				v *= 2

			return (v,r)
		else:
			return

	def unixSockConnect(self):
		'''
		Connects to a unix socket from the process running the LED screen, which expects
		values of strings [0-3]

		'''
		if os.path.exists("/tmp/screen_socket") :
			client = socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
			client.connect("/tmp/screen_socket")
			self.screen_sock = client
			print "connected to socket"
		else:
			print "Couldn't connect to LED socket"

	def connect(self,type):
		'''
		Connects to a controller based on what type it is told from command line arg

		:param str type: The tpye of controller being connected, b (default) for 
							bluetooth app and x for xbox controller 

		'''
		if type == "b":
			self._btConnect()
		elif type == "x":
			self._xBoxConnect()
		else:
			return -1
		self.type = type

	def getDriveVals(self):
		'''
		Returns the driving values based on which controller is connected
		'''

		if self.type == 'b':
			v,r = self._btVals()
		elif self.type == 'x':
			v,r = self._xboxVals()
		return v,r


	def sendUnixData(self):
		'''
		Sends the LED screen process commands for the face over unix socket
		'''
		self.screen_sock.send(str(self.led))


	def closeConnections(self):
		'''
		Closes all the connections opened by the Rover
		'''

		if self.type == 'b':
			try:
				self.bt_sock.send('0')
				time.sleep(0.25)
				self.bt_sock.close()
			except:
				pass
		elif self.type == 'x':
			self.joy.close()

		if self.screen_sock != None:
			self.screen_sock.close()
