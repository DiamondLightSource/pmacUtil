#!/bin/env dls-python2.6
from pkg_resources import require
require("cothread")
import cothread
import time
from random import random
from cothread.catools import *

autoincr=20
# set m510=autoincr on 172.23.88.172
# set m510=autoincr*2 with old method
start = 23.0
steps = 7000

new = True

while True:
    mres = caget("BL18B-OP-DCM-01:XTAL1:BRAGG.MRES") * 4
    velo = caget("BL18B-OP-DCM-01:XTAL1:BRAGG.VELO")
    if new:
        caput("BL18B-OP-DCM-01:XTAL1:BRAGG.VAL", start-0.1, wait=True, timeout=100)
        caput("BL18B-OP-DCM-01:PC:START", start)
        caput("BL18B-OP-DCM-01:PC:STOP", start)        
    else:
        caput("BL18B-OP-DCM-01:XTAL1:BRAGG.VAL", start, wait=True, timeout=100)    
        cothread.Sleep(2)                
        start = caget("BL18B-OP-DCM-01:XTAL1:E1.RBV")
        caput("BL18B-OP-DCM-01:PC:START", start + autoincr*mres/2.0)            
        caput("BL18B-OP-DCM-01:PC:STOP", start - autoincr*mres/2.0)                
    caput("BL18B-EA-DET-01:MCA-01:EraseStart", 1)
    cothread.Sleep(2)
    dist = steps * mres * autoincr * 2
    stop = start + dist
    hz = steps / (dist / velo)
    caput("BL18B-OP-DCM-01:XTAL1:BRAGG.VAL", stop, wait=True, timeout=100)
    nord = caget("BL18B-EA-DET-01:MCA-01:mca1.NORD")
    if nord not in range(steps-20, steps+50):
        print "*****Error", nord, hz
        break
    print nord, hz

# fails at 10, 555Hz after about 10 reps
# fails at 20, 277Hz after about 5 reps
