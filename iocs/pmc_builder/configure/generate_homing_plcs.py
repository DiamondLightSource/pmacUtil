#!/bin/env dls-python2.4

# Import the motorhome PLC generation library
from motorhome import *

# find the plc number, component name and filename
num, name, filename = parse_args()

# set some defaults
plc = PLC(num, post = "i", ctype=GEOBRICK)

# configure the axes according to name
if name == "M1":
    for axis in (1,2,3):
        plc.add_motor(axis, htype = HSW_DIR)
elif name == "M2":
    for axis in (4,5,6):
        plc.add_motor(axis, htype = HSW_DIR)
    plc.add_motor(7, htype = HSW, jdist = -2800)        
elif name == "BPM1":    
    plc.add_motor(1, htype = LIMIT)
    plc.add_motor(2, htype = HSW_HLIM, jdist=100)  
elif name == "S1":
    for axis in (1,2,3,4):
        plc.add_motor(axis, htype = HSW, jdist=-1000)      
elif name == "M3":
    for axis in (5,6,7):
        plc.add_motor(axis, htype = HSW_DIR)
    plc.add_motor(8, htype = HSW, jdist = -1000)        
elif name == "M4":
    for axis in (1,2,3):
        plc.add_motor(axis, htype = HSW_DIR)
    plc.add_motor(4, htype = HSW, jdist = 1000)       
elif name == "BOX1":
    for axis in (1,2,3,4):
        plc.add_motor(axis, htype = LIMIT)
elif name == "BOX2":
    for axis in (5,6,7,8):
        plc.add_motor(axis, htype = LIMIT)        
elif name == "BOX1Z":
    plc.add_motor(5, htype = LIMIT)        
elif name == "BOX2Z":
    plc.add_motor(7, htype = LIMIT)            
else:
    sys.stderr.write("***Error: Can't make homing PLC %d for %s\n" % (num, name))
    sys.exit(1)

# write out the plc
plc.write(filename)
