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
DB += gather.template
DB += motorstatus.template
DB += translated_motor.template
DB += autohome.template
DB += dls_pmac_asyn_motor.template
DB += dls_pmac_cs_asyn_motor.template
<<<<<<< .working
=======
DB += dls_pmac_patch_asyn_motor.template
DB += encoder_loss_detection.template
>>>>>>> .merge-right.r61748
DB += nanomotor_pmac.template
DB += nanomotor_axis.template
DB += compensationtable.template
DB += energyModes.template
DB += motion_stop.template
DB += encoderReadback.template
DB += positionCompare.template
DB += pmacStatus.template
DB += pmacStatusAxis.template
DB += pmacStatus8Axes.template
DB += pmacStatus32Axes.template
DB += B22_optics_box.template

# not using streams since this doesnt work with tpmac
#DB += energise_streams.template

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE
<<<<<<< .working
=======

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

../O.Common/dls_pmac_patch_asyn_motor.template: ../dls_pmac_asyn_motor_extras.template ../dls_pmac_asyn_motor_eloss_extras.template ../dls_pmac_asyn_motor_patch_extras.template
	cat $(MOTOR)/db/basic_asyn_motor.template > $@
	cat $^ >> $@

>>>>>>> .merge-right.r61748
