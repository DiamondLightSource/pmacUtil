TOP=../..

include $(TOP)/configure/CONFIG

# ------------------------
# Build an IOC Application
# ------------------------

PROD_IOC = protectionEx

# sim.dbd will be installed into <top>/dbd
DBD += protectionEx.dbd

# sim.dbd will be created from these files
protectionEx_DBD += base.dbd
protectionEx_DBD += asyn.dbd
protectionEx_DBD += motorSupport.dbd
protectionEx_DBD += devSoftMotor.dbd
protectionEx_DBD += pmacAsynIPPort.dbd
protectionEx_DBD += pmacAsynMotor.dbd
protectionEx_DBD += calcSupport.dbd
protectionEx_DBD += stdSupport.dbd
protectionEx_DBD += sscanSupport.dbd

# sim_registerRecordDeviceDriver.cpp will be created
# sim.dbd
protectionEx_SRCS += protectionEx_registerRecordDeviceDriver.cpp

# These two lines are needed for non-vxWorks builds, such as Linux
protectionEx_SRCS_DEFAULT += protectionExMain.cpp
protectionEx_SRCS_vxWorks += -nil-

# Add locally compiled object code
#sim_SRCS +=

# The following adds object code from base/src/vxWorks
protectionEx_OBJS_vxWorks += $(EPICS_BASE_BIN)/vxComLibrary

# This line says that this IOC Application depends on the
# xxx Support Module
protectionEx_LIBS += calc
protectionEx_LIBS += pmacAsynMotor
protectionEx_LIBS += pmacAsynIPPort
protectionEx_LIBS += softMotor
protectionEx_LIBS += motor
protectionEx_LIBS += sscan
protectionEx_LIBS += std
protectionEx_LIBS += asyn

# We need to link this IOC Application against the EPICS Base libraries
protectionEx_LIBS += $(EPICS_BASE_IOC_LIBS)

include $(TOP)/configure/RULES

