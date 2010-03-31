TOP=../..

include $(TOP)/configure/CONFIG

include $(TOP)/configure/RULES

buildInstall: protection_processed.pmc

%_processed.pmc: ../%-top.pmc
	dls-pmc-preprocessor.py -c -o $@ -I ..:$(TPMAC)/data:$(TOP)/data:/dls_sw/work/motion/Common $<

pmc:
	dls-pmc-preprocessor.py -c -d -o protection.pmc -I $(TOP)/data protection-top.pmc
