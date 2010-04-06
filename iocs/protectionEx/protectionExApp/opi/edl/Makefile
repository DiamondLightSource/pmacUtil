TOP = ../../..
include $(TOP)/configure/CONFIG

DATA += $(patsubst ../%, %, $(wildcard ../*.edl))
DATA += $(patsubst ../%, %, $(wildcard ../*.gif))
DATA += $(patsubst ../%, %, $(wildcard ../*.png))
SCRIPTS += $(patsubst ../%, %, $(wildcard ../*.sh))

include $(TOP)/configure/RULES

%.sh: ../%.sh
	$(MSI) -V $(SYS_BOOT_FLAGS) $(USR_BOOT_FLAGS) $< > $@

