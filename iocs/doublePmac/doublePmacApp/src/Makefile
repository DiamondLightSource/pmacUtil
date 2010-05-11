TOP=../..

include $(TOP)/configure/CONFIG

PROD_IOC_vxWorks = doublePmac

# doublePmac.dbd will be installed into <top>/dbd
DBD += doublePmac.dbd

# doublePmac.dbd will be created from these files
doublePmac_DBD += base.dbd
doublePmac_DBD += pmacOutParse.dbd
doublePmac_DBD += asyn.dbd
doublePmac_DBD += motorSupport.dbd
doublePmac_DBD += drvAsynSerialPort.dbd
doublePmac_DBD += pmacAsynMotor.dbd
doublePmac_DBD += pmacAsynIPPort.dbd
doublePmac_DBD += stream.dbd
doublePmac_DBD += genSubRecord.dbd
doublePmac_DBD += pmacInclude.dbd
doublePmac_DBD += utility.dbd


# doublePmac_registerRecordDeviceDriver.cpp will be created
# doublePmac.dbd
doublePmac_SRCS += doublePmac_registerRecordDeviceDriver.cpp

# These two lines are needed for non-vxWorks builds, such as Linux
doublePmac_SRCS_DEFAULT += doublePmacMain.cpp
doublePmac_SRCS_vxWorks += -nil-

# Add locally compiled object code
#doublePmac_SRCS +=

# The following adds object code from base/src/vxWorks
doublePmac_OBJS_vxWorks += $(EPICS_BASE_BIN)/vxComLibrary

# We need to link this IOC Application against the EPICS Base libraries
doublePmac_LIBS += pmacIoc
doublePmac_LIBS += pmacAsynMotor
doublePmac_LIBS += pmacAsynIPPort
doublePmac_LIBS += stream pcre
doublePmac_LIBS += pmacStatus
doublePmac_LIBS += motor
doublePmac_LIBS += asyn
doublePmac_LIBS += genSub
doublePmac_LIBS += utility
doublePmac_LIBS += $(EPICS_BASE_IOC_LIBS)

DATA += PMAC_processed.pmc

include $(TOP)/configure/RULES

%_processed.pmc: ../%.pmc ../*.pmc
	dls-pmc-preprocessor.py  -c -o $@ -I $(PMACSTATUS)/data:$(PMACUTIL)/data $<


