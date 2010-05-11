from iocbuilder import AutoSubstitution, SetSimulation, Device, Architecture, ModuleBase
from iocbuilder.arginfo import *

from iocbuilder.modules.motor import basic_asyn_motor, MotorRecord
from iocbuilder.modules.calc import Calc
from iocbuilder.modules.seq import Seq
from iocbuilder.modules.genSub import GenSub
from iocbuilder.modules.streamDevice import AutoProtocol

import os, sys

class PmacUtil(Device):
    Dependencies = (GenSub,Seq)
    LibFileList = ["pmacUtil"]
    DbdFileList = ["pmacUtilSupport"]
    AutoInstantiate = True

class autohome(AutoSubstitution):
    TemplateFile = 'autohome.template'                                               
SetSimulation(autohome, None)

class dls_pmac_asyn_motor(AutoSubstitution, MotorRecord):
    Dependencies = (Calc,)
    # Substitution attributes
    TemplateFile = 'dls_pmac_asyn_motor.template'

def dls_pmac_asyn_motor_sim(**args):
    # if it's a simulation, just connect it to a basic_asyn_motor 
    return basic_asyn_motor(**filter_dict(args, basic_asyn_motor.Arguments))
SetSimulation(dls_pmac_asyn_motor, dls_pmac_asyn_motor_sim)


class dls_pmac_cs_asyn_motor(AutoSubstitution, MotorRecord):
    Dependencies = (Calc,)
    # Substitution attributes
    TemplateFile = 'dls_pmac_cs_asyn_motor.template'

def dls_pmac_cs_asyn_motor_sim(**args):
    # if it's a simulation, just connect it to a basic_asyn_motor 
    return basic_asyn_motor(**filter_dict(args, basic_asyn_motor.Arguments))
SetSimulation(dls_pmac_cs_asyn_motor, dls_pmac_cs_asyn_motor_sim)

class dls_pmac_prot_asyn_motor(AutoSubstitution, MotorRecord):
    Dependencies = (Calc,)
    # Substitution attributes
    TemplateFile = 'dls_pmac_prot_asyn_motor.template'

def dls_pmac_prot_asyn_motor_sim(**args):
    # if it's a simulation, just connect it to a basic_asyn_motor 
    return basic_asyn_motor(**filter_dict(args, basic_asyn_motor.Arguments))
SetSimulation(dls_pmac_prot_asyn_motor, dls_pmac_prot_asyn_motor_sim)

class _pmacStatusAxis(AutoSubstitution, AutoProtocol):
    ProtocolFiles = ['pmac.proto']
    TemplateFile = 'pmacStatusAxis.template'

class pmacStatus(AutoSubstitution, AutoProtocol):
    Dependencies = (PmacUtil,)
    ProtocolFiles = ['pmac.proto']
    TemplateFile = 'pmacStatus.template'
    
    def __init__(self, **args):
    	# init the super class
        self.__super.__init__(**args)
        self.axes = []
        NAXES = int(args["NAXES"])
        assert NAXES in range(1,33), "Number of axes (%d) mut be in range 1..32" % NAXES 
        # for each axis
        for i in range(1, NAXES + 1):
            args["AXIS"] = i
            # make a _pmacStatusAxis instance
            self.axes.append(
                _pmacStatusAxis(
                    **filter_dict(args, _pmacStatusAxis.ArgInfo.Names())))

class CS_3jack(AutoSubstitution):
    TemplateFile = '3jack.template'    
                
class CS_3jack_mirror(AutoSubstitution):
    TemplateFile = '3jack-mirror.template'    

SetSimulation(CS_3jack, None)     
SetSimulation(CS_3jack_mirror, None)

class gather(AutoSubstitution, Device):
    '''Setup PMAC or Geobrick gathering template'''

    Dependencies = (PmacUtil,)

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
