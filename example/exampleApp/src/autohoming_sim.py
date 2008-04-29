#!/bin/env python2.4

from pkg_resources import require
require("dls.serial_sim==1.2")

from dls.serial_sim import serial_device
import re, os

class AutoHomePmac(serial_device):
	term = "\r"
	
	def __init__(self, plcs):
		
		self.homingDb = {}
		
		# Create a dictionary with all the PLC P variables
		# The variables in the list are:
		# 00: State
		# 01: Status
		# 02: Group
		for plc in plcs:
			self.homingDb.update( {plc: [0.0]*100} )
		self.motors = [0]*32
		
		self.verbose = 1
		
	def state(self, plc, state):
		self.homingDb[plc][0] = int(state)
		
	def status(self, plc, status):
		self.homingDb[plc][1] = int(status)
		
	def pos(self, motor, position):
		self.motors[motor] = int(position)
		
	# This function must be defined. This is called by the serial_sim system
	# whenever an asyn command is send down the line. Must return a string
	# with a response to the command.
	def reply (self, command):
		if self.verbose > 0:
			print "Got cmd: %s"%[command]
		cmd = command.lower().strip()
		retVal = ""
		
		# if user starts the homing procedure
		if (cmd[:10] == "enable plc"):
			plc = int(cmd[10:])
			self.homingDb[plc][0] = 1
			self.homingDb[plc][1] = 1

		# if user is writing to a P variable
		elif ( re.match(r'p\d{3,4}\s*=\s*\d+', cmd) ):
			pvar = cmd.split("=")[0]
			plc = int(pvar[1:][:(len(pvar)-3)])
			var = int(pvar[1:][(len(pvar)-3):])
			
			value = float(cmd.split("=")[1])
			print "Writing: PLC = %d Var = %d Value = %.3f"%(plc, var, value)
			self.homingDb[plc][var] = value
			
		# status and state update (EPICS template will poll this cmd regularly)
		elif ( re.match(r'p\d{3,4} p\d{3,4}', cmd) ):
			for pvar in cmd.split():
				plc = int(pvar[1:][:(len(pvar)-3)])
				var = int(pvar[1:][(len(pvar)-3):])
				retVal += "%d "%self.homingDb[plc][var]
		
		# if asking for individual P variable
		elif ( re.match(r'p\d{3,4}', cmd) ):
			plc = int(cmd[1:][:(len(cmd)-3)])
			var = int(cmd[1:][(len(cmd)-3):])
			retVal += "%d"%self.homingDb[plc][var]
		
		# Homing record asking motor status or position
		elif (re.match(r'#\d{1,2}p', cmd) ):
			regmatch = re.match(r'(#)(\d{1,2})(p)', cmd)
			motor = int(regmatch.group(2))
			request = regmatch.group(3)
			retVal = "%d"%self.motors[motor]
			
		
		# fall through to unknown command...
		else:
			if self.verbose > 0:
				print "autohoming simulation error: unknown command %s (%s)"%(command, cmd)

		if self.verbose > 0:
			print "Returning: \'%s\'"%retVal
		return retVal
		
if __name__ == "__main__":
	import os
	sim = AutoHomePmac("P1030","P1031","P1032","ENA PLC7")
	sim.start_serial("MIRROR_HM_SER")
	print os.environ["MIRROR_HM_SER"]
	
