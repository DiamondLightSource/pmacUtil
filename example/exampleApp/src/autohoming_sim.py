#!/bin/env python2.4

from pkg_resources import require
require("dls.serial_sim==1.2")

from dls.serial_sim import serial_device

class AutoHomePmac(serial_device):
	term = "\r"
	
	def __init__(self, status, state, group, startPlc):
		self.pvarStatus = str(status).lower()
		#self.pvarStatus = "p%d"%status
		self.pvarState = str(state).lower()
		#self.pvarState = "p%d"%state
		self.pvarGroup = str(group).lower()
		#self.pvarGroup = "p%d"%group
		self.startCmd = str(startPlc).lower()
		#self.startCmd = "ena plc%d"%startPlc
		
		self.status = 0
		self.state  = 0
		self.group  = 0
		
		
	# This function must be defined. This is called by the serial_sim system
	# whenever an asyn command is send down the line. Must return a string
	# with a response to the command.
	def reply (self, command):
		print "Got cmd: %s"%[command]
		cmd = command.lower().strip()
		retVal = ""
		
		# if user starts the homing procedure
		if (cmd == self.startCmd):
			self.status = 1
			self.state = 1
			
		# status and state update (EPICS template will poll this cmd regularly)
		elif (cmd == "%s %s"%(self.pvarStatus, self.pvarState)):
			retVal = "%d %d"%(self.status, self.state)
			
		# user send abort command
		elif (cmd == "%s=2"%self.pvarStatus):
			self.status = 2
		
		# user changes which group to home
		elif (cmd[:6] == "%s="%self.pvarGroup):
			try:
				self.group = int(cmd[6:])
			except:
				print "autohoming simulation error: invalid int: %s"%cmd[6:]
		
		# fall through to unknown command...
		else:
			print "autohoming simulation error: unknown command %s (%s)"%(command, cmd)

		return retVal
		
if __name__ == "__main__":
	import os
	sim = AutoHomePmac("P1030","P1031","P1032","ENA PLC7")
	sim.start_serial("MIRROR_HM_SER")
	print os.environ["MIRROR_HM_SER"]
	
