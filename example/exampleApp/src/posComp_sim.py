#!/bin/env python2.4

from pkg_resources import require
require("dls.serial_sim==1.2")

#from dls.serial_sim import serial_device
#from serial_sim import serial_device

import re, os

class PosComp(serial_device):
	Terminator = "\r"
	
	def __init__(self):
		self.verbose = 1
		self.pvars = (0,1,0,0,0,0.0,0,0,0,0,0,0)
			
	# This function must be defined. This is called by the serial_sim system
	# whenever an asyn command is send down the line. Must return a string
	# with a response to the command.
	def reply (self, command):
		if self.verbose > 0:
			print "Got cmd: %s"%[command]
		cmd = command.lower().strip()
		retVal = ""
		
		if cmd == "p1500..1505":
			retVal = "%i %i %i %i %i %.3f"%self.pvars[0:6]

		if cmd == "p1506..1511":
			retVal = "%i %i %i %i %i %i"%self.pvars[6:12]

		if self.verbose > 1:
			print "Returning: \'%s\'"%retVal
		return retVal
		
if __name__ == "__main__":
	import os
	sim = PosComp()
	sim.start_serial("MIRROR_HM_SER")
	print os.environ["MIRROR_HM_SER"]
	sim.start_ip(9005)
	
