TOP = ../..
include $(TOP)/configure/CONFIG
include pmacCoord_RELEASE

# this is the dls-xml-iocbuilder.py file
XMLBUILDER := dls-xml-iocbuilder.py
#XMLBUILDER := /dls_sw/work/common/python/iocbuilder/xmlbuilder/xmlbuilder.py

# set to -d to get debugging
DEBUG :=

# Create an IOC from all .xml files and all .py files
IOCS := $(patsubst %.xml, %, $(wildcard *.xml)) $(patsubst %.py, %, $(wildcard *.py))
#IOCS := positionCompare

# These are the IOCS we don't want to make simulations out of
#NO_SIMS :=

# Make simulations from all IOCS not in NO_SIMS
#SIMS := $(patsubst %, %_sim, $(filter-out $(NO_SIMS), $(IOCS)))

# These are the IOC dirs to make
IOC_DIRS := $(patsubst %, $(TOP)/iocs/%, $(IOCS) $(SIMS))

# Add the created iocs to the install target, and add defs.pmc for each ioc
install: $(IOC_DIRS) $(patsubst %, %/defs.pmc, $(IOC_DIRS))

# General rule for building a Standard IOC from an XML file
$(TOP)/iocs/%: %.xml
	$(XMLBUILDER) $(DEBUG) -e $<
	
# General rule for building a Simulation IOC from an XML file
$(TOP)/iocs/%_sim: %.xml
	$(XMLBUILDER) $(DEBUG) -e --sim=linux-x86 $<
	
# Alternate rule for building a Standard IOC from a python file
$(TOP)/iocs/%: %.py
	./$< $(DEBUG) $*
	
# Alternate rule for building a Simulation IOC from a python file
$(TOP)/iocs/%_sim: %.py
	./$< $(DEBUG) --sim=linux-x86 $*
	
# Rule for making a pmc file from a psub file
$(TOP)/iocs/%/defs.pmc: %.psub $(IOC_DIRS)
	msi -I.:$(PMACCOORD)/data:$(TOP)/data $< > $@	

# Remove the generated iocs on clean
clean:
	rm -rf $(IOC_DIRS)
