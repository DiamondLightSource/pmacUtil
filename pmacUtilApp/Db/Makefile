TOP=../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE

#----------------------------------------------------
#  Optimization of db files using dbst (DEFAULT: NO)
#DB_OPT = YES

#----------------------------------------------------
# In a Diamond Support Module, install
# templates like this
#
DB += energise.template
DB += pmacVariableWrite.template
DB += gather.template
DB += motorstatus.template
DB += translated_motor.template
DB += autohome.template
DB += dls_pmac_asyn_motor.template
DB += dls_pmac_prot_asyn_motor.template
DB += dls_pmac_cs_asyn_motor.template
DB += encoder_loss_detection.template
DB += nanomotor_pmac.template
DB += nanomotor_axis.template
DB += patch_panel_asyn_motor.template
DB += compensationtable.template
DB += energyModes.template
DB += motion_stop.template
DB += bender.template
DB += dls_readback_asyn_motor.template
DB += encoderReadback.template
DB += positionCompare.template
DB += pmacStatus.template
DB += pmacStatusAxis.template
DB += pmacStatus8Axes.template
DB += pmacStatus32Axes.template
DB += motor_record_move.template

# not using streams since this doesnt work with tpmac
#DB += energise_streams.template

#----------------------------------------------------
# In a Diamond IOC Application, build db files from
# template files like this
#
#DB += BL06I-MO-IOC-01.db
#DB += BL06I-MO-IOC-01_sim.db

#USES_TEMPLATE += $(MOTOR)/db/motor.template
#USES_TEMPLATE += $(MOTOR)/db/basic_motor.template

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

../O.Common/dls_pmac_asyn_motor.template: ../dls_pmac_asyn_motor_extras.template ../dls_pmac_asyn_motor_eloss_extras.template
	cat $(MOTOR)/db/basic_asyn_motor.template > $@
	cat $^ >> $@
	
../O.Common/dls_pmac_prot_asyn_motor.template: ../dls_pmac_asyn_motor_extras.template ../dls_pmac_asyn_motor_prot_extras.template
	cat $(MOTOR)/db/basic_asyn_motor.template > $@
	cat $^ >> $@
	
../O.Common/dls_pmac_cs_asyn_motor.template: ../dls_pmac_cs_asyn_motor_extras.template
	cat $(MOTOR)/db/basic_asyn_motor.template > $@
	cat $< >> $@

../O.Common/dls_readback_asyn_motor.template: ../dls_pmac_asyn_motor_extras.template
	cat ../readback_asyn_motor.template > $@
	cat $< >> $@

