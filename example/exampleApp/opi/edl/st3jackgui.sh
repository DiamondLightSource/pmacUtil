#!/bin/bash

export EDMDATAFILES=.:/dls_sw/prod/R3.14.8.2/support/motor/6-2-2dls3/data
export EDMDATAFILES=$EDMDATAFILES:/dls_sw/prod/R3.14.8.2/support/BLGui/1-10/data
export EDMDATAFILES=$EDMDATAFILES:/dls_sw/work/R3.14.8.2/support/pmacUtil/data
export EDMDATAFILES=$EDMDATAFILES:/dls_sw/work/R3.14.8.2/support/pmacUtil/example/data
export PATH=$EDMDATAFILES:$PATH
#export EPICS_DISPLAY_PATH=/dls_sw/prod/R3.14.8.2/support/asyn/4-9/medm
edm -x -eolc 3jacktest.edl &
