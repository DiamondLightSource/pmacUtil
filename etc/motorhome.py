#!/usr/bin/env python2.4
## \namespace motorhome
# This contains a class and helper function for making automated homing 
# routines.
# You should use the PLC object to create an autohoming PLC, then load it onto
# the PMAC or GEOBRICK. You will need the \ref autohome.vdb "autohome.template"
# EPICS template to be able to start, stop and monitor this PLC.
# 
# The following terms will be used in the documentation:
# - hdir = the homing direction. If ixx23 is +ve, hdir is in the direction
# of the high limit. If ixx23 is -ve, hdir is in the direction of the low limit
# - Jog until xx = the <tt>#\<axis\>J^\<jdist\></tt> command. This tells the 
# pmac to jog until it sees the home flag, then move jdist counts

import sys, re

# Setup some Homing types
## Dumb home, shouldn't be needed (htype Enum passed to PLC.add_motor()).
HOME = 0
## Home on a limit switch.
# -# (Fast Search) Jog in hdir (direction of ixx23) until limit switch activates
# -# (Fast Retrace) Jog in -hdir until limit switch deactivates
# -# (Home) Disable limits and home
#
# Finally re-enable limits and do post home move if any.
#
# This example shows homing on -ve limit with -ve hdir. 
# E.g. ixx23 = -1, msyy,i912 = 2, msyy,i913 = 2.
# \image html LIMIT.png "LIMIT homing"
LIMIT = 1
## Home on a home switch or index mark (htype Enum passed to PLC.add_motor()).
# -# (Prehome Move) Jog in -hdir until either index/home switch (Figure 1) or 
# limit switch (Figure 2)
# -# (Fast Search) Jog in hdir until index/home switch
# -# (Fast Retrace) Jog in -hdir until off the index/home switch
# -# (Home) Home
#
# Finally do post home move if any.
#
# This example shows homing on an index with -ve hdir and +ve jdist. 
# E.g. ixx23 = -1, msyy,i912 = 1, jdist = 1000.
#
# The first figure shows what happens when the index is in -hdir of the 
# starting position. E.g. Pos = -10000 cts, Index = 0 cts
# \image html HSW.png "HSW homing, Figure 1"
# The second figure shows what happens when the index is in hdir of the 
# starting position. E.g. Pos = 10000 cts, Index = 0 cts
# \image html HSW2.png "HSW homing, Figure 2"
# \b NOTE: if using a reference mark, set jdist as described under 
# PLC.add_motor()
HSW = 2
## Home on a home switch or index mark near the limit switch in hdir 
# (htype Enum passed to PLC.add_motor()).
# -# (Prehome Move) Jog in hdir until either index/home switch (Figure 1) or 
# limit switch (Figure 2)
#  -# If limit switch hit, jog in -hdir until index/home switch
# -# (Fast Search) Jog in hdir until index/home switch
# -# (Fast Retrace) Jog in -hdir until off the index/home switch
# -# (Home) Home
#
# Finally do post home move if any.
#
# This example shows homing on an index with -ve hdir and +ve jdist. 
# E.g. ixx23 = -1, msyy,i912 = 1, jdist = 1000.
#
# The first figure shows what happens when the index is in hdir of the 
# starting position. E.g. Pos = 20000 cts, Index = 0 cts
# \image html HSW_HLIM.png "HSW_HLIM homing, Figure 1"
# The second figure shows what happens when the index is in -hdir of the 
# starting position. E.g. Pos = -5000 cts, Index = 0 cts
# \image html HSW_HLIM2.png "HSW_HLIM homing, Figure 2"
# \b NOTE: if using a reference mark, set jdist as described under 
# PLC.add_motor()
HSW_HLIM = 3
## Home on a directional home switch (newport style) 
# (htype Enum passed to PLC.add_motor()).
# -# (Prehome Move) Jog in -hdir until off the home switch
# -# (Fast Search) Jog in hdir until the home switch is hit
# -# (Fast Retrace) Jog in -hdir until off the home switch
# -# (Home) Home
#
# Finally do post home move if any.
#
# This example shows homing on a directional home switch with -ve hdir.
# E.g. ixx23 = -1, msyy,i912 = 2, msyy,i913 = 0.
#
# The first figure shows what happens when the axis starts on the home switch. 
# E.g. Pos = -20000 cts, Index = 0 cts
# \image html HSW_DIR.png "HSW_DIR homing, Figure 1"
# The second figure shows what happens when the axis starts on the home switch. 
# E.g. Pos = 20000 cts, Index = 0 cts
# \image html HSW_DIR2.png "HSW_DIR homing, Figure 2"
HSW_DIR = 4
## Home on release of a limit (htype Enum passed to PLC.add_motor()).
# -# (Prehome Move) Jog in -hdir until the limit switch is hit
# -# (Fast Search) Jog in hdir until the limit switch is released
# -# (Fast Retrace) Jog in -hdir until the limit switch is hit
# -# (Home) Home
#
# Finally do post home move if any.
#
# This example shows homing off the -ve limit with +ve hdir. 
# E.g. ixx23 = 1, msyy,i912 = 10, msyy,i913 = 2.
# \image html RLIM.png "RLIM homing"
RLIM = 5
## Don't do any homing, just the post home move 
# (htype Enum passed to PLC.add_motor()).
NOTHING = 6
## Home on a home switch or index mark on a stage that has no limit switches.
#  Detection of following error due to hitting the hard stop is taken as the
#  limit indication.
# (htype Enum passed to PLC.add_motor()).
# -# (Prehome Move) Jog in hdir until either index/home switch (Figure 1) or 
# following error
#  -# If following error, jog in -hdir until index/home switch
# -# (Fast Search) Jog in hdir until index/home switch
# -# (Fast Retrace) Jog in -hdir until off the index/home switch
# -# (Home) Home
#
# Finally do post home move if any.
#
HSW_HSTOP = 7

## String list of htypes
htypes = ["HOME", "LIMIT", "HSW", "HSW_HLIM", "HSW_DIR", "RLIM", "NOTHING", "HSW_HSTOP"]


# Setup some controller types
## PMAC controller (ctype passed to PLC.__init__()).
PMAC = 0
## Geobrick controller (ctype passed to PLC.__init__()).
GEOBRICK = 1
## Geobrick controller (ctype passed to PLC.__init__()).
BRICK = 1
## Twinned Geobrick (a la I15)
TWINBRICK = 2

## The distance in counts to move when doing large moves
LARGEJ = 100000000

## Helper function that parses the filename.
# Expects sys.argv[1] to be of the form \c PLC<num>_<name>_HM.pmc
# \return (num, name, filename)
def parse_args():
    # find the plc number and name from the filename
    filename = sys.argv[1]
    result = re.search(r"PLC(\d+)_(.*)_HM\.pmc", filename)
    if result is not None:
        num, name = result.groups()
    else:
        sys.stderr.write(
            "***Error: Incorrectly formed homing plc filename: %s\n" % filename)
        sys.exit(1)
    return int(num), name, filename     

## Create an object that can create a homing PLC for some motors.
# \param plc plc number (any free plc number on the PMAC)
# \param timeout timout for any move in ms
# \param ctype The controller type, will be PMAC (=0) or GEOBRICK (=1)
# \param protection_plc The PMAC is using the protection PLC4 rather than 
# the encoder loss PLC4 (or no PLC4).  If True, code is planted that
# disables the limit protection during the execution of the homing PLC.
# All other parameters setup defaults that can be overridden for a particular
# motor in add_motor()
class PLC:       
    def __init__(self, plc, timeout=600000, htype=HOME, jdist=0, post=None,
            ctype=PMAC, protection_plc=False):
        ## List of motor objects added by add_motor()
        self.motors = []
        self.__d = { "plc": int(plc), "timeout": timeout, "comment": ""}
        ## Default default homing type for any motor added, see add_motor()
        self.htype = htype
        ## Default after trigger jog dist for any motor added, see add_motor()
        self.jdist = jdist
        ## Default post home behaviour for any motor added, see add_motor()        
        self.post = post
        self.__cmd1 = []
        self.__cmd2 = []
        self.groups = {}
        ## The controller type, will be PMAC or GEOBRICK
        self.ctype = ctype
        if self.ctype == PMAC:
            self.__d["controller"] = "PMAC"
        elif self.ctype == BRICK:
            self.__d["controller"] = "GeoBrick"
        elif self.ctype == TWINBRICK:
            self.__d["controller"] = "Twinned GeoBrick"
        else:
            raise TypeError, "Invalid ctype: %d, should be 0, 1 or 2"
            
        ## Controls planting of protection PLC code
        self.protection_plc = protection_plc

    ## Add code hooks and extra checks to a group home.
    # \param group Group number to configure
    # \param pre Execute the following piece of code before the prehome
    # move of this group, as long as no previous group has finished with an 
    # error
    # \param post Execute the following piece of code after the posthome
    # move of this group, as long as the group home and posthome move completed
    # successfully
    # \param checks List of extra checks that the should be performed
    # for this group at each stage. Should be a list of tuples of
    # (check, result, status) where:
    # - check is a valid pmac expression
    # - result is the value that check should normally evaluate to
    # - status is the HomingStatus number to fail with if check != result
    # (val of the autohome.vdb::record(mbbi,"$(P):HM:STATUS"))
    # e.g. \c [('m1231&m1332','0', 5)] will check that m1231&m1332=0 during each
    # stage, and set the HomingStatus = StatusLimit if the check fails
    def configure_group(self, group, checks=None, pre=None, post=None):
        assert group in self.groups, \
            "You must add motors to group %d before configuring it" % group       
        for v in ["checks", "pre", "post"]:
            if locals()[v] is not None:
                if self.groups[group][v]:
                    print >> sys.stderr, \
                        "*** Warning: Configuring %s for group %d, " \
                        "information already exists"  % (v, group)
                self.groups[group][v] = locals()[v]
    
    ## Add a motor for the PLC to home. If htype, jdist or post are not
    # specified, they take the default value as specified when creating PLC().
    # \param axis Motor axis number
    # \param enc_axes Specify some associated encoder axes. These axis will have
    # their flags inverted as well as ax. They will also be hmz'd after other
    # axes are homed.
    # \param group Homing group. Each group will be homed sequentially, I.e all 
    # of group 2 together, then all of group 3 together, etc. When asked to home
    # group 1, the PLC will home group 1 then all other defined groups 
    # sequentially, so you shouldn't add axes to group 1 if you are going to
    # use multiple groups in your homing PLC
    # \param htype Homing type enum (hdir is homing direction). 
    # Should be one of:
    # - \ref motorhome::HOME "HOME"
    # - \ref motorhome::LIMIT "LIMIT"
    # - \ref motorhome::HSW "HSW"
    # - \ref motorhome::HSW_HLIM "HSW_HLIM"
    # - \ref motorhome::HSW_DIR "HSW_DIR"
    # - \ref motorhome::RLIM "RLIM"                    
    # - \ref motorhome::NOTHING "NOTHING"              
    # \param jdist Distance to jog by after finding the trigger. Should always 
    # be in -hdir. E.g if ix23 = -1, jdist should be +ve. This should only be
    # needed for reference marks or bouncy limit switches. A recommended 
    # value in these cases is about 1000 counts in -hdir.
    # \param post Where to move after the home. This can be:
    # - None: Stay at the home position
    # - an integer: move to this position in motor cts
    # - "r" +  an integer: move relative by this amount. For example: post="r100"
    # - "i": go to the initial position (does nothing for HOME htype motors)
    # - "h": go to the hign limit (ix13)
    # - "l": go to the low limit (ix14)    
    def add_motor(self, axis, group=1, htype=None, jdist=None, post=None,
            enc_axes=[]):
        axis, group = int(axis), int(group)
        if len(self.motors)>=16:        
            raise IndexError, "Only 16 motors may be defined in a single PLC"
        if group not in range(1,8):
            raise IndexError, "Group %d not in range 1..7" % group
        if group not in self.groups:
            self.groups[group] = dict(checks=[], pre="", post="")
        d = { "ax": axis,
              "grp": group,
              "enc_axes": []
            }
        self.__d["comment"] += "; Axis %d: group = %d" % (axis, group)
        for eaxis in enc_axes:
            ed = dict(ax = eaxis)
            if self.ctype == GEOBRICK or (self.ctype == TWINBRICK and eaxis < 9):
                # nx for internal amp or redirected encoder, GEOBRICK            
                ed["nx"] = ((eaxis-1)/4)*10 + ((eaxis-1)%4+1) 
            elif self.ctype == TWINBRICK:
                # mx for slave brick, TWINBRICK, encoders cannot be redirected                        
                ed["mx"] = ((eaxis-9)/4)*10 + ((eaxis-9)%4+1)            
            else:
                # macrostation number, PMAC             
                ed["ms"] = 2*(eaxis-1)-(eaxis-1)%2
            d["enc_axes"].append(ed)                           
        if enc_axes:
            self.__d["comment"] += ", enc_axes = %s" % enc_axes
        if self.ctype == GEOBRICK or self.ctype == TWINBRICK:
            if axis < 9:
                # nx for internal amp, GEOBRICK            
                d["nx"] = ((axis-1)/4)*10 + ((axis-1)%4+1) 
            elif self.ctype == TWINBRICK:
                # mx for slave brick, TWINBRICK                        
                d["mx"] = ((axis-9)/4)*10 + ((axis-9)%4+1)
            else:
                # macrostation number for external amp, GEOBRICK                        
                d["ms"] = 2*(axis-9)-(axis-9)%2 
        else:
            # macrostation number, PMAC                                
            d["ms"] = 2*(axis-1)-(axis-1)%2 
        for var in ["htype","jdist","post"]:
            if eval(var)!=None:
                d[var]=eval(var)
            else:
                d[var]=eval("self."+var)
            if var == "htype":
                self.__d["comment"] += ", %s = %s"%(var, htypes[d[var]])
            else:
                self.__d["comment"] += ", %s = %s"%(var, d[var])
        self.motors.append(d)
        self.__d["comment"] += "\n"

    def __set_jdist_hdir(self, htypes, reverse=False):
        # set jdist reg to be a large distance in hdir, or in -hdir if reverse
        if reverse:
            self.__cmd1 += ["m%d72=%d*(-i%d23/ABS(i%d23))" % 
                (m["ax"],LARGEJ,m["ax"],m["ax"]) for i,m in self.__sel(htypes)]
        else:
            self.__cmd1 += ["m%d72=%d*(i%d23/ABS(i%d23))" % 
                (m["ax"],LARGEJ,m["ax"],m["ax"]) for i,m in self.__sel(htypes)]

    def __home(self, htypes):
        # home command
        self.__cmd2 += ["#%dhm"%m["ax"] for i,m in self.__sel(htypes)]

    def __jog_until_trig(self, htypes, reverse=False):
        # jog until trigger, go dist past trigger
        self.__set_jdist_hdir(htypes,reverse)
        self.__cmd2 += ["#%dJ^*^%d" % 
            (m["ax"],m["jdist"]) for i,m in self.__sel(htypes)]

    def __jog_inc(self, htypes, reverse=False):
        # jog incremental by jdist reg
        self.__set_jdist_hdir(htypes,reverse)
        self.__cmd2 += ["#%dJ^*" % m["ax"] for i,m in self.__sel(htypes)]

    def __set_hflags(self, htypes, inv=False):
        # set the hflags of all types of motors in htypes
        for i,m in self.__sel(htypes):
            if inv:
                val = "P%d%02d"%(self.__d["plc"],i+52)
            else:
                val = "P%d%02d"%(self.__d["plc"],i+36)
            for d in [m] + m["enc_axes"]:
                if d.has_key("nx"):                
                    # geobrick internal axis
                    self.__cmd1.append("i7%02d2=%s"%(d["nx"],val))
                elif d.has_key("mx"):
                    # geobrick slave axis
                    self.__cmd1.append("MXW0,i7%02d2,%s"%(d["mx"],val))                 
                else:
                    # ms external axis                  
                    self.__cmd1.append("MSW%d,i912,%s"%(d["ms"],val))

    def __write_cmds(self, f, state, htypes=None, ferr_htypes=None):
        # process self.__cmd1 and self.__cmd2 and write them out
        has_pre = state == "PreHomeMove" and self.groups[self.group]["pre"]
        has_post = state == "PostHomeMove" and self.groups[self.group]["pre"]
        if self.__cmd1 or self.__cmd2 or has_pre or has_post:
            f.write('\t;---- %s State ----\n'%state)
            f.write('\tif (HomingStatus=StatusHoming)\n')
            f.write('\t\tHomingState=State%s\n'%state)                            
            f.write('\t\t; Execute the move commands\n')
        if has_pre:
            f.write('\t\t%s\n' % self.groups[self.group]["pre"])
        out = [[]]
        for t in self.__cmd1:
            if len(" ".join(out[-1]+[t]))<254 and len(out[-1])<32:
                out[-1].append(t)
            else:
                out += [[t]]
        for l in [(" ".join(l)) for l in out]:
            if l:
                f.write("\t\t"+l+"\n")
        out = [[]]
        for t in self.__cmd2:
            if len(" ".join(out[-1]+[t]))<248 and len(out[-1])<32:
                out[-1].append(t)
            else:
                out += [[t]]
        for l in [(" ".join(l)) for l in out]:
            if l:
                f.write('\t\tcmd "%s"\n'%l)
        if self.__cmd1 or self.__cmd2:
            # setup a generic wait for move routine in self.__d         
            inpos = ["m%d40"%m["ax"] for i,m in self.__sel()]
            self.__d["InPosition"] = "&".join(inpos)
            self.__d["FFErr"] = "|".join("m%d42" % 
                m["ax"] for i,m in self.__sel()) 
            self.__d["FFErrCh"] = "|".join("m%d42" % 
                m["ax"] for i,m in self.__sel(htypes=ferr_htypes)) 
            if not self.__d["FFErrCh"]:
                self.__d["FFErrCh"] = '0'
            # only check the limit switches of htypes 
            self.__d["LimitCheck"] = ""
            self.__d["LimitResults"] = ""            
            lstr = "|".join("m%d30"%m["ax"] for i,m in self.__sel(htypes))            
            if lstr:
                self.__d["LimitCheck"] += "\t\tand (%s=0) ; Should not stop on position limit for selected motors\n" % lstr
                self.__d["LimitResults"] += "\t\tif (%s=1) ; If a motor hit a limit\n" % lstr
                self.__d["LimitResults"] += "\t\t\tHomingStatus = StatusLimit\n"
                self.__d["LimitResults"] += "\t\tendif\n"
            self.__d["checks"] = ""
            self.__d["results"] = ""            
            if self.groups[self.group]:
                for exp, val, stat in self.groups[self.group]["checks"]:
                    self.__d["checks"] += "\t\tand (%s = %s) ; Custom check\n" % (exp, val)
                    self.__d["results"] += "\t\tif (%s != %s) ; Custom check failed\n" % (exp, val)
                    self.__d["results"] += "\t\t\tHomingStatus = %s\n" % stat
                    self.__d["results"] += "\t\tendif\n"
            f.write(wait_for_move%self.__d)
        if has_post:
            f.write('\t\tif (HomingStatus=StatusHoming)\n')        
            f.write('\t\t\t%s\n' % self.groups[self.group]["post"])
            f.write('\t\tendif\n')            
        if self.__cmd1 or self.__cmd2 or has_pre or has_post:    
            self.__cmd1 = []            
            self.__cmd2 = []                
            f.write('\tendif\n\n')
    
    def __sel(self,htypes=None):
        if htypes:
            return [(i,m) for i,m in enumerate(self.motors) 
                if m["htype"] in htypes and self.group==m["grp"]]
        else:
            return [(i,m) for i,m in enumerate(self.motors) 
                if self.group==m["grp"]]

    ## Write the PLC text to a filename string f
    def write(self,f):
        # open the file and write the header
        f = open(f,"w")
        self.writeFile(f)
        f.close()


    ## Write the PLC text to a file object f
    def writeFile(self,f):  
        if len(self.groups) != 1:
            assert 1 not in self.groups, \
                "Shouldn't add motors to group 1 if multiple groups are defined"
        f.write(header%self.__d)
        plc = self.__d["plc"]
        ems = [(i,m) for i,m in enumerate(self.motors)]
        
        #---- Configuring state ----
        f.write(";---- Configuring State ----\n")
        f.write("HomingState=StateConfiguring\n")
        f.write(";Save the Homing group to px03\n")
        f.write("HomingBackupGroup=HomingGroup\n")        
        f.write(";Save high soft limits to P variables px04..x19\n")
        f.write(" ".join(["P%d%02d=i%d13" % 
            (plc,i+04,m["ax"]) for i,m in ems])+"\n")
        f.write(";Save the low soft limits to P variables px20..x35\n")
        f.write(" ".join(["P%d%02d=i%d14" % 
            (plc,i+20,m["ax"]) for i,m in ems])+"\n")
        f.write(";Save the home capture flags to P variables px36..x51\n")
        cmds = []
        mschecks = []
        for i,m in ems:
            if m.has_key("nx"):
                cmds.append("P%d%02d=i7%02d2"%(plc,i+36,m["nx"]))
            elif m.has_key("mx"):
                cmds.append("MXR0,i7%02d2,P%d%02d"%(m["mx"],plc,i+36))            
                mschecks.append("P%d%02d=0" % (plc,i+36))                
            else:
                cmds.append("MSR%d,i912,P%d%02d"%(m["ms"],plc,i+36))
                mschecks.append("P%d%02d=0" % (plc,i+36))
        f.write(" ".join(cmds)+"\n")                
        if mschecks:                
            f.write(";If any are zero then there is probably a macro error\n")                
            f.write('if (%s)\n'%(" or ".join(mschecks)))
            f.write("\tHomingStatus=StatusInvalid\n")
            f.write('endif\n')
        f.write(";Store 'not flag' to use in moving off a flag in P variables px52..x67\n")
        f.write(" ".join(["P%d%02d=P%d%02d^$C"%(plc,i+52,plc,i+36) for i,m in ems])+"\n")
        f.write(";Save the limit flags to P variables px68..x83\n")
        f.write(" ".join(["P%d%02d=i%d24"%(plc,i+68,m["ax"]) for i,m in ems])+"\n")
        f.write(";Save the current position to P variables px84..x99\n")
        f.write(" ".join(["P%d%02d=M%d62"%(plc,i+84,m["ax"]) for i,m in ems])+"\n")
        f.write(';Clear the soft limits\n')
        f.write(" ".join(["i%d13=0"%m["ax"] for i,m in ems])+"\n")
        f.write(" ".join(["i%d14=0"%m["ax"] for i,m in ems])+"\n")
        #########################################################
        # TODO: Clear encoder capture register                  #
        #########################################################          
        f.write("\n")
                
        # write some PLC for each group
        for g in sorted(self.groups.keys()):
            f.write("if (HomingBackupGroup=1 and HomingStatus=StatusHoming)\n")
            if g!=1:
                f.write("or (HomingBackupGroup=%d and HomingStatus=StatusHoming)\n"%g)  
            ## Store the motor group that is currently being generated          
            self.group = g
            f.write("\tHomingGroup=%d\n\n"%g) 

            #---- Disable any protection ---- 
            if self.protection_plc:
                ems = self.__sel()          
                f.write("\t;Disable protection PLC\n")
                f.write("\t"+" ".join(["P4%02d=P4%02d|$4"%(m["ax"],m["ax"]) for i,m in ems])+"\n")
            
            #---- PreHomeMove State ----
            # for hsw_dir motors, set the trigger to be the inverse flag
            self.__set_hflags([HSW_DIR],inv=True)
            # for hsw/hsw_dir motors jog until trigger in direction of -ix23
            self.__jog_until_trig([HSW,HSW_DIR,HSW_HSTOP],reverse=True)
            # for rlim motors jog in direction of -ix23
            self.__jog_inc([RLIM],reverse=True)          
            # for hsw_hlim motors jog until trigger in direction of ix23        
            self.__jog_until_trig([HSW_HLIM])
            # add the commands, HSW_DIR can't hit the limit
            self.__write_cmds(f,"PreHomeMove",htypes=[HSW_DIR], ferr_htypes=[HOME, LIMIT, HSW, HSW_HLIM, HSW_DIR, RLIM, NOTHING]) 

            # for hsw_hlim we could have gone past the limit and hit the limit switch
            ems = self.__sel([HSW_HLIM])
            if ems:
                f.write('\t;---- Check if HSW_HLIM missed home mark and hit a limit ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n')                
                f.write('\t\t; Execute the move commands if on a limit\n')            
            for i,m in ems:
                # if stopped on position limit, jog until trigger in direction of -ix23
                f.write('\t\tif (m%d30=1)\n'%m["ax"])
                f.write('\t\t\tm%d72=%d*(-i%d23/ABS(i%d23))\n'%(m["ax"],LARGEJ,m["ax"],m["ax"]))
                f.write('\t\t\tcmd "#%dJ^*^%d"\n'%(m["ax"],m["jdist"]))
                f.write('\t\tendif\n')
            if ems:
                lstr = "|".join("m%d30"%m["ax"] for i,m in ems)
                self.__d["LimitCheck"] += "\t\tand (%s=0) ; Should not stop on position limit for selected motors\n" % lstr
                self.__d["LimitResults"] += "\t\tif (%s=1) ; If a motor hit a limit\n" % lstr
                self.__d["LimitResults"] += "\t\t\tHomingStatus = StatusLimit\n"
                self.__d["LimitResults"] += "\t\tendif\n"
                f.write(wait_for_move%self.__d) 
                f.write('\tendif\n\n')

            #---- FastSearch State ----        
            htypes = [LIMIT,HSW,HSW_DIR,HSW_HLIM,RLIM,HSW_HSTOP]
            # for hsw_dir motors, set the trigger to be the original flag
            self.__set_hflags([HSW_DIR]) 
            # for all motors except hsw_hlim jog until trigger in direction of ix23
            self.__jog_until_trig(htypes)
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"FastSearch",htypes=[HSW,HSW_DIR,HSW_HLIM,RLIM,HSW_HSTOP],
                ferr_htypes=[HOME, LIMIT, HSW, HSW_HLIM, HSW_DIR, RLIM, NOTHING])
            
            # store home points
            ems = self.__sel(htypes+[HSW_HLIM])  
            if ems:
                f.write('\t;---- Store the difference between current pos and start pos ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n')
                for i,m in ems:
                    # put back pos = (start pos - current pos) converted to counts + jdist - home off * 16
                    f.write('\t\tP%d%02d=(P%d%02d-M%d62)/(I%d08*32)+%d-(i%d26/16)\n'%(plc,i+84,plc,i+84,m["ax"],m["ax"],m["jdist"],m["ax"]))
                f.write('\tendif\n\n')  
                
            #---- FastRetrace State ----
            htypes = [LIMIT,HSW,HSW_HLIM,HSW_DIR,RLIM,HSW_HSTOP]
            # for limit/hsw_* motors, set the trigger to be the inverse flag
            self.__set_hflags(htypes,inv=True)
            # then jog until trigger in direction of -ix23
            self.__jog_until_trig(htypes,reverse=True)
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"FastRetrace",htypes=[LIMIT,HSW,HSW_HLIM,HSW_DIR,HSW_HSTOP])

            # check that the limit flags are reasonable for LIMIT motors, and remove limits if so  
            ems = self.__sel([LIMIT])  
            if ems:
                f.write('\t;---- Check if any limits need disabling ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n')     
                f.write("\t\t;Save the user home flags to P variables px52..x67\n")
                f.write("\t\t;NOTE: this overwrites inverse flag (ran out of P vars), so can't use inverse flag after this point\n\t")                
                cmds = []
                for i,m in ems:
                    if m.has_key("nx"):
                        cmds.append("P%d%02d=i7%02d3"%(plc,i+52,m["nx"]))
                    elif m.has_key("mx"):
                        cmds.append("MXR0,i7%02d3,P%d%02d"%(m["mx"],plc,i+52))                        
                    else:
                        cmds.append("MSR%d,i913,P%d%02d"%(m["ms"],plc,i+52))                             
                f.write("\t\t" + " ".join(cmds)+"\n")
            for i,m in ems:
                f.write("\t\t; if capture on flag, and flag high, then we need to disable limits\n")
                f.write("\t\tif (P%d%02d&2=2 and P%d%02d&8=0)\n"%(plc,i+36,plc,i+36))
                f.write("\t\t\t; ix23 (h_vel) should be opposite to ix26 (h_off) and in direction of home flag\n")
                f.write("\t\t\tif (P%d%02d=1 and i%d23>0 and i%d26<1)\n"%(plc,i+52,m["ax"],m["ax"]))
                f.write("\t\t\tor (P%d%02d=2 and i%d23<0 and i%d26>-1)\n"%(plc,i+52,m["ax"],m["ax"]))
                f.write("\t\t\t\ti%d24=i%d24 | $20000\n"%(m["ax"],m["ax"]))
                f.write("\t\t\telse\n")
                f.write("\t\t\t\t; if it isn't then set it into invalid error\n")
                f.write("\t\t\t\tHomingStatus=StatusInvalid\n")
                f.write("\t\t\tendif\n")
                f.write("\t\tendif\n")
            if ems:
                f.write('\tendif\n\n')                

            #---- Homing State ----        
            htypes = [HOME,LIMIT,HSW,HSW_HLIM,HSW_DIR,RLIM,HSW_HSTOP]
            # for all motors, set the trigger to be the home flag
            self.__set_hflags(htypes)
            # Then execute the home command
            self.__home(htypes)
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"Homing",htypes=htypes)

            # Zero all encoders
            ems = self.__sel(htypes)          
            cmds = []
            for i,m in ems:
                for ed in m["enc_axes"]:
                    cmds.append("#%dhmz"%ed["ax"])
            if cmds:
                f.write('\t;---- Zero encoder channels ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n') 
                f.write("\t\tcmd \"" + " ".join(cmds)+"\"\n")                
                f.write('\tendif\n\n')  

            # check motors ALL have home complete flags set
            if ems:
                f.write('\t;---- Check if all motors have homed ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n') 
                f.write('\tand (%s=0)\n'%("&".join(["m%d45"%m["ax"] for i,m in ems])))
                f.write('\t\tHomingStatus=StatusIncomplete\n')
                f.write('\tendif\n\n')          
                              
            #---- Put Back State ----        
            # for all motors with post, do the home move
            for i,m in [(i,m) for i,m in enumerate(self.motors) if m["post"]!=None and m["grp"]==self.group]:
                if m["post"]=="i":
                    if m["htype"] not in [HOME, NOTHING]:
                        # go to initial pos
                        self.__cmd1.append("m%d72=P%d%02d"%(m["ax"],plc,i+84))
                        self.__cmd2.append("#%dJ=*"%m["ax"])
                elif m["post"]=="h":
                    # go to high soft limit
                    self.__cmd1.append("m%d72=P%d%02d"%(m["ax"],plc,i+04))
                    self.__cmd2.append("#%dJ=*"%m["ax"])        
                elif m["post"]=="l":
                    # go to low soft limit
                    self.__cmd1.append("m%d72=P%d%02d"%(m["ax"],plc,i+20))
                    self.__cmd2.append("#%dJ=*"%m["ax"])        
                elif type(m["post"])==str and m["post"].startswith("r"):
                    # jog relative by m["post"][1:]
                    self.__cmd2.append("#%dJ=%d"%(m["ax"],int(m["post"][1:])))                                                    
                else:
                    # go to m["post"]
                    self.__cmd2.append("#%dJ=%d"%(m["ax"],m["post"]))
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"PostHomeMove")

            #---- Enable any protection ---- 
            if self.protection_plc:
                ems = self.__sel()          
                f.write("\t;Enable protection PLC\n")
                f.write("\t"+" ".join(["P4%02d=P4%02d&$fffffb"%(m["ax"],m["ax"]) for i,m in ems])+"\n")

            # End of per group bit
            f.write("endif\n\n")

        #----- Done -----
        f.write(";---- Done ----\n")
        f.write('if (HomingStatus = StatusHoming)\n')
        f.write("\t;If we've got this far without failing, set status and state done\n")        
        f.write('\tHomingStatus=StatusDone\n') 
        f.write('\tHomingState=StateDone\n') 
        f.write("\t;Restore the homing group from px03\n")
        f.write("\tHomingGroup=HomingBackupGroup\n")         
        f.write("endif\n\n")

        #----- Tidying Up -----
        ems = [(i,m) for i,m in enumerate(self.motors)]
        f.write(";---- Tidy Up ----\n")
        f.write(";Stop all motors if they don't have a following error\n")
        for i,m in ems:
            # if no following error
            f.write('if (m%d42=0)\n'%m["ax"])
            f.write('\tcmd "#%dJ/"\n'%m["ax"])
            f.write('endif\n')
        f.write(';Restore the high soft limits from P variables px04..x19\n')   
        f.write(" ".join(["i%d13=P%d%02d"%(m["ax"],plc,i+04) for i,m in ems])+"\n")
        f.write(';Restore the low soft limits from P variables px20..x35\n')        
        f.write(" ".join(["i%d14=P%d%02d"%(m["ax"],plc,i+20) for i,m in ems])+"\n")
        f.write(';Restore the home capture flags from P variables px36..x51\n')        
        cmds = []
        for i,m in ems:
            for d in [m] + m["enc_axes"]:        
                if d.has_key("nx"):
                    cmds.append("i7%02d2=P%d%02d"%(d["nx"],plc,i+36))
                elif d.has_key("mx"):
                    cmds.append("MXW0,i7%02d2,P%d%02d"%(d["mx"],plc,i+36))                    
                else:
                    cmds.append("MSW%d,i912,P%d%02d"%(d["ms"],plc,i+36))   
        f.write(" ".join(cmds)+"\n")        
        f.write(';Restore the limit flags to P variables px68..x83\n')        
        f.write(" ".join(["i%d24=P%d%02d"%(m["ax"],plc,i+68) for i,m in ems])+"\n")
        f.write("\n")
        f.write("DISABLE PLC%s\n"%plc)
        f.write("CLOSE\n")

header = """CLOSE

;####################################################
; Autogenerated Homing PLC for %(controller)s, DO NOT MODIFY
%(comment)s;####################################################

; Use a different timer for each PLC
#define timer             i(5111+(%(plc)s&30)*50+%(plc)s%%2)
; Make timer more readable
#define MilliSeconds      * 8388608/i10

; Homing State P Variable
#define HomingState       P%(plc)s00
#define StateIdle         0
#define StateConfiguring  1
#define StateMoveNeg      2
#define StateMovePos      3
#define StateHoming       4
#define StatePostHomeMove 5
#define StateAligning     6
#define StateDone         7
#define StateFastSearch   8
#define StateFastRetrace  9
#define StatePreHomeMove  10
HomingState = StateIdle

; Homing Status P Variable
#define HomingStatus      P%(plc)s01
#define StatusDone        0
#define StatusHoming      1
#define StatusAborted     2
#define StatusTimeout     3
#define StatusFFErr       4
#define StatusLimit       5
#define StatusIncomplete  6
#define StatusInvalid     7
HomingStatus = StatusDone

; Homing Group P Variable
#define HomingGroup       P%(plc)s02
HomingGroup = 0

; Homing Group Backup P Variable
#define HomingBackupGroup P%(plc)s03
HomingBackupGroup = 0

OPEN PLC%(plc)s CLEAR

HomingStatus = StatusHoming

"""
wait_for_move = """\t\t; Wait for the move to complete
\t\ttimer = 20 MilliSeconds ; Small delay to start moving
\t\twhile (timer > 0)
\t\tendw
\t\ttimer = %(timeout)s MilliSeconds ; Now start checking the conditions
\t\twhile (%(InPosition)s=0) ; At least one motor should not be In Position
\t\tand (%(FFErr)s=0) ; No following errors should be set for any motor
%(LimitCheck)s\t\tand (timer > 0) ; Check for timeout
\t\tand (HomingStatus = StatusHoming) ; Check that we didn't abort
%(checks)s\t\tendw
\t\t; Check why we left the while loop
\t\tif (%(FFErrCh)s=1) ; If a motor hit a following error
\t\t\tHomingStatus = StatusFFErr
\t\tendif
%(LimitResults)s\t\tif (timer<0 or timer=0) ; If we timed out
\t\t\tHomingStatus = StatusTimeout
\t\tendif
%(results)s"""

if __name__=="__main__":
    p = PLC(1,timeout=100000,htype=HOME,jdist=0,ctype=GEOBRICK)
    p.add_motor(1,group=2,jdist=100)
    p.add_motor(2,group=2,htype=LIMIT,jdist=200)
    p.add_motor(3,group=6,htype=HSW,jdist=300)
    p.add_motor(4,group=3,htype=HSW_HLIM,jdist=400)
    p.add_motor(5,group=3,htype=HSW,jdist=500,post="i")
    p.add_motor(6,group=3,htype=HSW_HLIM,jdist=600)
    p.add_motor(7,group=3,htype=HSW_DIR,jdist=700,post="l")    
    p.add_motor(8,group=3,jdist=100)
    p.add_motor(9,group=2,htype=LIMIT,jdist=200)
    p.add_motor(10,group=3,htype=HSW,jdist=300)
    p.add_motor(11,group=3,htype=HSW_HLIM,jdist=400)
    p.add_motor(12,group=3,htype=HSW,jdist=500,post="h")
    p.add_motor(13,group=3,htype=HSW_HLIM,jdist=600)
    p.add_motor(14,group=3,htype=RLIM,jdist=700,post=100)    
    p.add_motor(15,group=4,htype=RLIM,jdist=800,post=150)            
    p.add_motor(16,group=4,htype=RLIM,jdist=800,post=-100)                
    p.write("/tmp/test_home_PLC.pmc")

    p = PLC(2,timeout=100000)
#    p.add_motor(1,htype=LIMIT, enc_axes=[9])    
    p.add_motor(1,htype=HSW, post="i", enc_axes=[9])
    p.configure_group(1,[('m1231&m1332','0', 5)], "pre_stuff", "post_stuff")    
    p.write("/tmp/test_home_PLC2.pmc")

    plc = PLC(14, post = None)
    for axis in (9,10,11): # All 3 jacks grouped together
        plc.add_motor(axis, group=2, jdist=1000, htype=HSW_HLIM)
    for axis in (12,13): # Both translations grouped together
        plc.add_motor(axis, group=3, jdist=0, htype=RLIM)
    plc.add_motor(14, group=4, jdist=0, htype=RLIM)   
    plc.configure_group(3,[('m1231&m1332','0', 5), ('m1232&m1331','0', 5)])
    plc.write("/tmp/PLC14_TFM_HM.pmc")     
