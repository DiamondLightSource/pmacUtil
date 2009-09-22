TOP=../..

include $(TOP)/configure/CONFIG

# ------------------------
# Build an IOC Application
# ------------------------
DATA += autohoming_sim.py
DATA += posComp_sim.py

#PROD_IOC_vxWorks = example
PROD_IOC = example

# example.dbd will be installed into <top>/dbd
DBD += example.dbd

# example.dbd will be created from these files
example_DBD += base.dbd
example_DBD += asyn.dbd
example_DBD += drvAsynSerialPort.dbd
example_DBD += drvAsynIPPort.dbd
#example_DBD += PythonEmbed.dbd
example_DBD += calcSupport.dbd
#example_DBD += stdSupport.dbd
example_DBD += sscanSupport.dbd
example_DBD += pmacUtilSupport.dbd
example_DBD += motorSupport.dbd
example_DBD += motorSimSupport.dbd
#example_DBD += pmacAsynMotor.dbd
example_DBD += pmacAsynCoord.dbd
example_DBD += pmacAsynMotor.dbd
example_DBD_vxWorks += pmacInclude.dbd


# example_registerRecordDeviceDriver.cpp will be created
# example.dbd
example_SRCS += example_registerRecordDeviceDriver.cpp

# These two lines are needed for non-vxWorks builds, such as Linux
example_SRCS_DEFAULT += exampleMain.cpp
example_SRCS_vxWorks += -nil-

# Add locally compiled object code
#example_SRCS +=

# The following adds object code from base/src/vxWorks
example_OBJS_vxWorks += $(EPICS_BASE_BIN)/vxComLibrary

# This line says that this IOC Application depends on the
# xxx Support Module
example_LIBS += asyn
example_LIBS += pmacUtil
example_LIBS += calc
example_LIBS += sscan
#example_LIBS += std
#example_LIBS += pmacAsynMotor
example_LIBS += pmacAsynCoord
example_LIBS += pmacAsynMotor
example_LIBS_vxWorks += pmacIoc
example_LIBS += motor
example_LIBS += motorSimSupport
#example_LIBS += PythonEmbed
example_LIBS += seq pv

DATA += 3jackexample_processed.pmc

# We need to link this IOC Application against the EPICS Base libraries
example_LIBS += $(EPICS_BASE_IOC_LIBS)

# ---------------------------------------------------
include $(TOP)/configure/RULES

%_processed.pmc: ../%.pmc ../*.pmc
	dls-pmc-preprocessor.py -c -o $@ -I .:..:$(PMACUTIL)/data $<

