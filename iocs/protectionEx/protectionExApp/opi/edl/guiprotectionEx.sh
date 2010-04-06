#!/bin/sh
EDMDATAFILES=$(BL15I)/iocs/protectionEx/data:$(MOTOR)/data:$(BLGUI)/data:$(PMACUTIL)/data edm -eolc -x protectionEx.edl
