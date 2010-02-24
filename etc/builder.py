from iocbuilder import AutoSubstitution, SetSimulation, Device, Architecture
from iocbuilder.arginfo import *

from iocbuilder.modules.tpmac import tpmac
from iocbuilder.modules.motor import basic_asyn_motor, MotorRecord
from iocbuilder.modules.calc import Calc
from iocbuilder.modules.seq import Seq

import os, sys

class autohome(AutoSubstitution):
    TemplateFile = 'autohome.template'                                               
SetSimulation(autohome, None)

class dls_pmac_asyn_motor(AutoSubstitution, MotorRecord):
    Dependencies = (tpmac, Calc)
    # Substitution attributes
    TemplateFile = 'dls_pmac_asyn_motor.template'

def dls_pmac_asyn_motor_sim(**args):
    # if it's a simulation, just connect it to a basic_asyn_motor 
    return basic_asyn_motor(**filter_dict(args, basic_asyn_motor.Arguments))
SetSimulation(dls_pmac_asyn_motor, dls_pmac_asyn_motor_sim)


class dls_pmac_cs_asyn_motor(AutoSubstitution, MotorRecord):
    Dependencies = (tpmac, Calc)
    # Substitution attributes
    TemplateFile = 'dls_pmac_cs_asyn_motor.template'

def dls_pmac_cs_asyn_motor_sim(**args):
    # if it's a simulation, just connect it to a basic_asyn_motor 
    return basic_asyn_motor(**filter_dict(args, basic_asyn_motor.Arguments))
SetSimulation(dls_pmac_cs_asyn_motor, dls_pmac_cs_asyn_motor_sim)

class CS_3jack(AutoSubstitution):
    TemplateFile = '3jack.template'    
                
class CS_3jack_mirror(AutoSubstitution):
    TemplateFile = '3jack-mirror.template'    

SetSimulation(CS_3jack, None)     
SetSimulation(CS_3jack_mirror, None)

class gather(AutoSubstitution, Device):
    '''Setup PMAC or Geobrick gathering template'''

    Dependencies = (Seq,)
    LibFileList = ["pmacUtil"]
    DbdFileList = ["pmacUtilSupport"]    

    def PostIocInitialise(self):
        if Architecture() == "linux-x86":
            print 'seq(gather,"P=%(P)s,M=%(M)s")' % self.args
        else:        
            print 'seq &gather,"P=%(P)s,M=%(M)s"' % self.args

    # Substitution attributes
    TemplateFile = 'gather.template'

class pmacVariableWrite(AutoSubstitution):
    '''Couple of records to write variables to a Delta tau'''
    TemplateFile = 'pmacVariableWrite.template'

class positionCompare(AutoSubstitution):
    '''Setup position compare on a delta tau. Needs PLC_PMAC_position_compare
    or PLC_BRICK_position_compare'''
    Dependencies = (Calc,)    
    TemplateFile = 'positionCompare.template'
