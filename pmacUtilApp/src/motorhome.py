#!/usr/bin/env dls-python
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
# The second figure shows what happens when the axis starts off the home switch. 
# E.g. Pos = 20000 cts, Index = 0 cts
# \image html HSW_DIR2.png "HSW_DIR homing, Figure 2"
HSW_DIR = 4
## Home on release of a limit (htype Enum passed to PLC.add_motor()).
#  This can also be used for homing on a rotary encoder (back of motor)
#  with an index mark on the rotation: Drive to limit and then home away
#  from limit to the first index mark.
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
# -# (Prehome Move) Jog in -hdir until following error - Ixx97 (in-position 
# trigger mode) set to 3 for this phase.
# -# (Fast Search) Jog in hdir until index/home switch
# -# (Fast Retrace) Jog in -hdir until off the index/home switch
# -# (Home) Home
#
# Finally do post home move if any.
#
HSW_HSTOP = 7

## String list of htypes
htypes_str = ["HOME", "LIMIT", "HSW", "HSW_HLIM", "HSW_DIR", "RLIM", "NOTHING", "HSW_HSTOP"]
all_htypes = [globals()[x] for x in htypes_str]

## Function to return all htypes apart from passed args
def htypes_without(*args):
    return [h for h in all_htypes if h not in args]

# Setup some controller types
## PMAC controller (ctype passed to PLC.__init__()).
PMAC = 0
## Geobrick controller (ctype passed to PLC.__init__()).
GEOBRICK = 1
## Geobrick controller (ctype passed to PLC.__init__()).
BRICK = 1

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

## Object that encapsulates everything we need to know about a motor
class Motor:
    PHASE_PRE_HOME_MOVE = 0
    PHASE_FAST_SEARCH = 1
    PHASE_FAST_RETRACE = 2
    instances = []
    def __init__(self, ax, enc_axes, ctype, ms=None):
        # Axis number
        self.ax = int(ax)
        # Each time we create a motor store its index
        self.i = len(self.instances)
        self.isHomed = False
        assert ax not in [m.ax for m in self.instances], \
            "Motor object already exists for axis %d" % ax
        # Add this instance to list of motor instances
        self.instances.append(self)
        assert len(self.instances) < 16, \
            "Only 16 motors may be defined in a single PLC"     
        # Add encoder axes to be zeroed
        self.enc_axes = enc_axes
        # Add other properties
        if ms:
            self.ms = ms       
        elif ctype == GEOBRICK:
            if ax < 9:
                # nx for internal amp, GEOBRICK            
                self.nx = ((ax-1)/4)*10 + ((ax-1)%4+1) 
            else:
                # macrostation number for external amp, GEOBRICK                        
                self.ms = 2*(ax-9)-(ax-9)%2 
        else:
            # macrostation number, PMAC                                
            self.ms = 2*(ax-1)-(ax-1)%2
        # set jdist and jdist_overrides defaults
        self.jdist = None
        self.jdist_default = None
        self.jdist_overrides = None

    ## Pick a predefined override for jdist from the self.jdist_override tuple.
    # \param phase_code The phase code specified as a number.
    # PHASE_PRE_HOME_MOVE = 0, PHASE_FAST_SEARCH = 1, PHASE_FAST_RETRACE = 2.
    def override_jdist_for_phase(self, phase_code):
        if self.jdist_default is None:
            self.jdist_default = self.jdist
        if self.jdist_overrides is not None and phase_code < len(self.jdist_overrides) and self.jdist_overrides[phase_code] is not None:
            self.jdist = self.jdist_overrides[phase_code]
        else:
            self.jdist = self.jdist_default

    ## Release the override affecting the current motor
    def release_jdist_override(self):
        self.jdist = self.jdist_default



## Object that encapsulates a homing group
class Group:
    def __init__(self, group, pre, post, checks):
        # group number
        self.group = group
        assert group in range(1,11), "Group %d not in range 1..10" % group
        self.pre = pre
        self.post = post
        self.checks = checks
        # list of actions
        self.actions = []

    def addMotor(self, motor, htype, post):
        self.actions.append((motor, htype, post))        

## Create an object that can create a homing PLC for some motors.
# \param plc plc number (any free plc number on the PMAC)
# \param timeout timout for any move in ms
# \param ctype The controller type, will be PMAC (=0) or GEOBRICK (=1)
#
# All other parameters setup defaults that can be overridden for a particular
# motor in add_motor()
class PLC:       
    def __init__(self, plc, timeout=600000, htype=HOME, jdist=0, post=None,
            ctype=PMAC, allow_debug=True):
        ## Dict of group objects created when a motor is added to a group,
        ## indexed by group number
        self.groups = {}
        ## plc number
        self.plc = int(plc)
        self.timeout = timeout
        self.comment = ""
        ## Default default homing type for any motor added, see add_motor()
        self.htype = htype
        ## Default after trigger jog dist for any motor added, see add_motor()
        self.jdist = jdist
        ## Add a private flag that allows the following errror check to be supressed.
        ## This is needed for HSW_HSTOP
        self._check_following_error = True
        ## Default post home behaviour for any motor added, see add_motor()        
        self.post = post
        self.__cmd1 = []
        self.__cmd2 = []
        self.__cmd3 = []  # Commands executed after movement
        self.allow_debug = allow_debug
        ## The controller type, will be PMAC or GEOBRICK
        self.ctype = ctype
        if self.ctype == PMAC:
            self.controller = "PMAC"
        elif self.ctype == BRICK:
            self.controller = "GeoBrick"
        else:
            raise TypeError, "Invalid ctype: %d, should be 0 (PMAC) or 1 (BRICK)" % self.ctype
            
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
                if getattr(self.groups[group], v):
                    print >> sys.stderr, \
                        "*** Warning: Configuring %s for group %d, " \
                        "information already exists"  % (v, group)
                setattr(self.groups[group], v, locals()[v])
    
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
    # - \ref motorhome::HSW_HSTOP "HSW_HSTOP"
    # \param jdist Distance to jog by after finding the trigger. Should always 
    # be in -hdir. E.g if ix23 = -1, jdist should be +ve. This should only be
    # needed for reference marks or bouncy limit switches. A recommended 
    # value in these cases is about 1000 counts in -hdir.
    # \param jdist_overrides A tuple of values which each override jdist in 
    # one phase of the homing protocol. The list should be in the order 
    # (PRE_HOME_MOVE_JDIST, FAST_SEARCH_JDIST, FAST_RETRACE_JDIST).
    # 'None' is a valid value - eg: (None, 1000, None) will only override the jdist 
    # value of the Fast Search phase.
    # \param post Where to move after the home. This can be:
    # - None or 0: Stay at the home position
    # - an integer: move to this position in motor cts
    # - "z" +  an integer: move to this position in motor cts and zero using a HMZ
    # - "r" +  an integer: move relative by this amount. For example: post="r100"
    # - "i": go to the initial position (does nothing for HOME htype motors)
    # - "h": go to the hign limit (ix13)
    # - "l": go to the low limit (ix14)    
    # - "H": go to the hardware high limit
    # - "L": go to the hardware low limit
    # \param ms Override value for the macrostation associated with this axis 
    def add_motor(self, axis, group=1, htype=None, jdist=None, jdist_overrides=None, post=None,
            enc_axes=[], ms = None):
        # Override defaults
        if htype == None: htype = self.htype
        if jdist == None: jdist = self.jdist
        if post == None: post = self.post                
        # If we need to add a motor
        motor = None
        for m in Motor.instances:
            if m.ax == axis:
                motor = m
        if motor == None:
            # this object contains info about a particular motor 
            motor = Motor(ax=axis, enc_axes=enc_axes, ctype=self.ctype, ms=ms)
        # If this is a homing operation, make sure motor isn't already homed in 
        # an earlier op
        if htype != NOTHING:
            assert not motor.isHomed, \
                "Two homing operations requested for axis %d" % axis
            motor.isHomed = True
            motor.jdist = jdist
            # Check the override is a tuple
            if isinstance(jdist_overrides, tuple) or jdist_overrides is None:
                motor.jdist_overrides = jdist_overrides
            else:
                raise ValueError("jdist_overrides expects a tuple, you may need to add '(..., None)' to the end of single values.")
        # this dict gives details of each group, it contains a list of
        # (motors axis, post move) tuples
        if group not in self.groups:
            self.groups[group] = Group(group=group, checks=[], pre="", post="")            
        self.groups[group].addMotor(motor, htype, post)

    # Select all motors in this group with a defined htype
    def __sel(self, htypes=None):
        return [m for m, htype, post in self.group.actions
            if htypes is None or htype in htypes]        
            
    def __set_jdist_hdir(self, htypes, reverse=False):
        # set jdist reg to be a large distance in hdir, or in -hdir if reverse
        if reverse:
            self.__cmd1 += ["\t\tm%d72=%d*(-i%d23/ABS(i%d23))" % 
                (m.ax,LARGEJ,m.ax,m.ax) for m in self.__sel(htypes)]
        else:
            self.__cmd1 += ["\t\tm%d72=%d*(i%d23/ABS(i%d23))" % 
                (m.ax,LARGEJ,m.ax,m.ax) for m in self.__sel(htypes)]

    def __home(self, htypes):
        # home command
        self.__cmd2 += ["#%dhm"%m.ax for m in self.__sel(htypes)]

    def __set_motor_position_trigger_mode_for_homing(self, htypes):
        for m in self.__sel(htypes):
            self.__cmd1.append("I%d97 = 3; in-position trigger on following error\n" % m.ax)
            self.__cmd3.append("I%d97 = 0; in-position trigger on hardware capture\n" % m.ax)
        self._check_following_error = False

    def __jog_until_trig(self, htypes, reverse=False):
        # jog until trigger, go dist past trigger
        self.__set_jdist_hdir(htypes,reverse)
        self.__cmd2 += ["#%dJ^*^%d" % 
            (m.ax,m.jdist) for m in self.__sel(htypes)]

    def __jog_inc(self, htypes, reverse=False):
        # jog incremental by jdist reg
        self.__set_jdist_hdir(htypes,reverse)
        self.__cmd2 += ["#%dJ^*" % m.ax for m in self.__sel(htypes)]

    def __set_hflags(self, htypes, inv=False):
        # set the hflags of all types of motors in htypes
        for d in self.__sel(htypes):
            if inv:
                val = "P%d%02d"%(self.plc,d.i+52)
            else:
                val = "P%d%02d"%(self.plc,d.i+36)            
            if hasattr(d, "nx"):
                # geobrick internal axis
                self.__cmd1.append("i7%02d2=%s"%(d.nx,val))
            else:
                # ms external axis                  
                self.__cmd1.append("MSW%d,i912,%s"%(d.ms,val))

    def __check_not_aborted(self, f, tabs=1):        
        for i in range(tabs):
            f.write("\t")
        if self.allow_debug:
            f.write('if (HomingStatus = StatusHoming or HomingStatus = StatusDebugHoming)\n')
        else:
            f.write('if (HomingStatus=StatusHoming)\n')    

    def __write_cmds(self, f, state, lim_htypes=None, ferr_htypes=None, lim_mtrs=None):
        # process self.__cmd1 and self.__cmd2 and write them out
        has_pre = state == "PreHomeMove" and self.group.pre
        has_post = state == "PostHomeMove" and self.group.post
        if self.__cmd1 or self.__cmd2 or has_pre or has_post:
            if self.allow_debug:
                f.write('\t; Wait for user to tell us to continue if in debug\n')
                f.write('\tif (HomingStatus = StatusDebugHoming)\n')
                f.write('\t\tHomingStatus = StatusPaused\n')
                f.write('\t\twhile (HomingStatus = StatusPaused)\n')
                f.write('\t\tendw\n')
                f.write('\tendif\n\n')            
            f.write('\t;---- %s State ----\n'%state)
            self.__check_not_aborted(f)
            f.write('\t\tHomingState=State%s\n'%state)
            f.write('\t\t; Execute the move commands\n')
        if has_pre:
            f.write('\t\t%s\n' % self.group.pre)

        # Write first 2 command sets to file
        self.__write_cmd_set_to_file(f, self.__cmd1, use_cmd=False)
        self.__write_cmd_set_to_file(f, self.__cmd2, use_cmd=True)
        
        if self.__cmd1 or self.__cmd2:
            # setup a generic wait for move routine      
            self.InPosition = "&".join(["m%d40"%m.ax for m in self.__sel()])
            # create a list of checks and results
            checks = []
            results = []
            # for the following error, always check, but ferr_htypes are the only ones that should fail
            ffcheckstr = "|".join("m%d42" % m.ax for m in self.__sel()) 
            if self._check_following_error and ffcheckstr:
                checks.append((ffcheckstr, "0", "StatusFFErr", "Following error check"))                
            ffresultstr = "|".join("m%d42" % m.ax for m in self.__sel(htypes=ferr_htypes)) 
            if self._check_following_error and ffresultstr:
                results.append((ffresultstr, "0", "StatusFFErr", "Following error check"))            
            # reset the following error check flag for future stages
            self._check_following_error = True
            # only check the limit switches of htypes
            if lim_mtrs == None:
                lim_mtrs = self.__sel(lim_htypes)                        
            lstr = "|".join("m%d30" % m.ax for m in lim_mtrs)                 
            if lstr:
                lchk = (lstr, "0", "StatusLimit", "Limit check")
                checks.append(lchk)
                results.append(lchk)
            # Add any custom checks
            c_checks = [list(x) + ["Custom check"] for x in self.group.checks]             
            checks += c_checks
            results += c_checks
            # write the text
            self.checks = ""
            for exp, val, stat, chktxt in checks:
                self.checks += "\t\tand (%s = %s) ; %s\n" % (exp, val, chktxt)
            self.results = ""
            for exp, val, stat, chktxt in results:
                self.results += "\t\tif (%s != %s) ; %s failed\n" % (exp, val, chktxt)
                self.results += "\t\t\tHomingStatus = %s\n" % stat
                self.results += "\t\tendif\n"
            f.write(wait_for_move % self.__dict__)

        # Write third command set to file
        self.__write_cmd_set_to_file(f, self.__cmd3, use_cmd=False)

        if has_post:
            self.__check_not_aborted(f, tabs = 2)
            f.write('\t\t\t%s\n' % self.group.post)
            f.write('\t\tendif\n')            
        if self.__cmd1 or self.__cmd2 or self.__cmd3 or has_pre or has_post:    
            self.__cmd1 = []            
            self.__cmd2 = []
            self.__cmd3 = []
            f.write('\tendif\n\n')
    
    ## Write out a given list of command to a file
    def __write_cmd_set_to_file(self, f, cmd_list, use_cmd=False):
        out = [[]]
        max_line_len = 248 if use_cmd else 254
        for t in cmd_list:
            if len(" ".join(out[-1]+[t]))<max_line_len and len(out[-1])<32:
                out[-1].append(t)
            else:
                out += [[t]]
        for l in [(" ".join(l)) for l in out]:
            if l and use_cmd:
                f.write('\t\tcmd "%s"\n'%l)
            elif l:
                f.write("\t\t"+l+"\n")

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
        for g, group in sorted(self.groups.items()):
            self.comment += "; Group %d:\n" % g
            for motor, htype, post in group.actions:
                self.comment += ";  Axis %d: htype = %s, jdist = %s, post = %s" % (motor.ax, htypes_str[htype], motor.jdist, post)
                if motor.enc_axes:
                    self.comment += ", enc_axes = %s" % motor.enc_axes
                self.comment += "\n"
                
        f.write(header % self.__dict__)        
        plc = self.plc
        
        # default to old non-pausing behaviour
        f.write("if (HomingStatus != StatusHoming)\n")
        if self.allow_debug:
            f.write("and (HomingStatus != StatusDebugHoming)\n")        
        f.write("\tHomingStatus = StatusHoming\n")
        f.write("endif\n\n")                        
        
        #---- Configuring state ----
        f.write(";---- Configuring State ----\n")
        f.write("HomingState=StateConfiguring\n")
        f.write(";Save the Homing group to px03\n")
        f.write("HomingBackupGroup=HomingGroup\n")        
        f.write(";Save high soft limits to P variables px04..x19\n")
        f.write(" ".join(["P%d%02d=i%d13" % 
            (plc,m.i+04,m.ax) for m in Motor.instances])+"\n")
        f.write(";Save the low soft limits to P variables px20..x35\n")
        f.write(" ".join(["P%d%02d=i%d14" % 
            (plc,m.i+20,m.ax) for m in Motor.instances])+"\n")
        f.write(";Save the home capture flags to P variables px36..x51\n")
        cmds = []
        mschecks = []
        for m in Motor.instances:
            if hasattr(m, "nx"):
                cmds.append("P%d%02d=i7%02d2"%(plc,m.i+36,m.nx))
            else:
                cmds.append("MSR%d,i912,P%d%02d"%(m.ms,plc,m.i+36))
                mschecks.append("P%d%02d=0" % (plc,m.i+36))
        f.write(" ".join(cmds)+"\n")                
        if mschecks:                
            f.write(";If any are zero then there is probably a macro error\n")                
            f.write('if (%s)\n'%(" or ".join(mschecks)))
            f.write("\tHomingStatus=StatusInvalid\n")
            f.write('endif\n')
        f.write(";Store 'not flag' to use in moving off a flag in P variables px52..x67\n")
        f.write(" ".join(["P%d%02d=P%d%02d^$C"%(plc,m.i+52,plc,m.i+36) for m in Motor.instances])+"\n")
        f.write(";Save the limit flags to P variables px68..x83\n")
        f.write(" ".join(["P%d%02d=i%d24"%(plc,m.i+68,m.ax) for m in Motor.instances])+"\n")
        f.write(";Save the current position to P variables px84..x99\n")
        f.write(" ".join(["P%d%02d=M%d62"%(plc,m.i+84,m.ax) for m in Motor.instances])+"\n")
        f.write(';Clear the soft limits\n')
        f.write(" ".join(["i%d13=0"%m.ax for m in Motor.instances])+"\n")
        f.write(" ".join(["i%d14=0"%m.ax for m in Motor.instances])+"\n")       
        f.write("\n")
                
        # write some PLC for each group
        put_back_avail = []
        for g, group in sorted(self.groups.items()):
            test = "HomingBackupGroup = 1"
            if g != 1:
                test += " or HomingBackupGroup = %d" % g            
            f.write("if (%s)\n" % test)
            if self.allow_debug:
                f.write("and (HomingStatus = StatusHoming or HomingStatus = StatusDebugHoming)\n")
            else:
                f.write("and (HomingStatus = StatusHoming)\n")            
            ## Store the motor group that is currently being generated          
            self.group = group
            f.write("\tHomingGroup=%d\n\n"%g) 

            #---- Remove all the home flags for this group ---- 
            ems = self.__sel(htypes = htypes_without(NOTHING))          
            f.write("\t;Clear home flags\n")
            f.write("\t"+" ".join(["m%d45=0"%m.ax for m in ems])+"\n")
            
            #---- PreHomeMove State ----
            # Set the pre-home move jdist override
            for m in Motor.instances:
                m.override_jdist_for_phase(Motor.PHASE_PRE_HOME_MOVE)
            # for hsw_dir motors, set the trigger to be the inverse flag
            self.__set_hflags([HSW_DIR],inv=True)
            # for hsw_hstop the motor position trigger should be set to
            # trigger on following error (value 3) and reset after movement
            self.__set_motor_position_trigger_mode_for_homing([HSW_HSTOP])
            # for hsw/hsw_dir motors jog until trigger in direction of -ix23
            self.__jog_until_trig([HSW,HSW_DIR,HSW_HSTOP],reverse=True)
            # for rlim motors jog in direction of -ix23
            self.__jog_inc([RLIM],reverse=True)          
            # for hsw_hlim motors jog until trigger in direction of ix23        
            self.__jog_until_trig([HSW_HLIM])
            # add the commands, HSW_DIR can't hit the limit
            self.__write_cmds(f,"PreHomeMove", lim_htypes=[HSW_DIR], ferr_htypes=htypes_without(HSW_HSTOP)) 

            # for hsw_hlim we could have gone past the limit and hit the limit switch
            ems = self.__sel([HSW_HLIM])
            if ems:
                f.write('\t;---- Check if HSW_HLIM missed home mark and hit a limit ----\n')
                self.__check_not_aborted(f)               
                f.write('\t\t; Execute the move commands if on a limit\n')            
            for m in ems:
                # if stopped on position limit, jog until trigger in direction of -ix23
                f.write('\t\tif (m%d30=1)\n'%m.ax)
                f.write('\t\t\tm%d72=%d*(-i%d23/ABS(i%d23))\n'%(m.ax,LARGEJ,m.ax,m.ax))
                f.write('\t\t\tcmd "#%dJ^*^%d"\n'%(m.ax,m.jdist))
                f.write('\t\tendif\n')
            if ems:
                lstr = "|".join("m%d30"%m.ax for m in ems)
                self.checks += "\t\tand (%s=0) ; Should not stop on position limit for selected motors\n" % lstr
                self.results += "\t\tif (%s=1) ; If a motor hit a limit\n" % lstr
                self.results += "\t\t\tHomingStatus = StatusLimit\n"
                self.results += "\t\tendif\n"
                f.write(wait_for_move % self.__dict__) 
                f.write('\tendif\n\n')

            #---- FastSearch State ----
            # Set the fast search jdist override
            for m in Motor.instances:
                m.override_jdist_for_phase(Motor.PHASE_FAST_SEARCH)
            # for hsw_dir motors, set the trigger to be the original flag
            self.__set_hflags([HSW_DIR]) 
            # for all motors except hsw_hlim jog until trigger in direction of ix23
            self.__jog_until_trig(htypes = htypes_without(HOME, NOTHING))
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"FastSearch",lim_htypes=htypes_without(HOME, NOTHING, LIMIT, RLIM))
            
            # store home points
            ems = self.__sel(htypes_without(HOME, NOTHING))  
            if ems:
                f.write('\t;---- Store the difference between current pos and start pos ----\n')
                self.__check_not_aborted(f)
                for m in ems:
                    # put back pos = (start pos - current pos) converted to counts + jdist - home off * 16
                    f.write('\t\tP%d%02d=(P%d%02d-M%d62)/(I%d08*32)+%d-(i%d26/16)\n'%(plc,m.i+84,plc,m.i+84,m.ax,m.ax,m.jdist,m.ax))
                    assert m.ax not in put_back_avail, "Group %(grp)s, axis %(ax)d has already been homed, this isn't right..." %m
                    put_back_avail.append(m.ax)
                f.write('\tendif\n\n')  
                
            #---- FastRetrace State ----
            # Set the fast retrace jdist override
            for m in Motor.instances:
                m.override_jdist_for_phase(Motor.PHASE_FAST_RETRACE)
            htypes = htypes_without(HOME, NOTHING)
            # for limit/hsw_* motors, set the trigger to be the inverse flag
            self.__set_hflags(htypes,inv=True)
            # then jog until trigger in direction of -ix23
            self.__jog_until_trig(htypes,reverse=True)
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"FastRetrace",lim_htypes=htypes_without(HOME, NOTHING, LIMIT, RLIM))

            # check that the limit flags are reasonable for LIMIT motors, and remove limits if so  
            ems = self.__sel([LIMIT])  
            if ems:
                f.write('\t;---- Check if any limits need disabling ----\n')
                self.__check_not_aborted(f)     
                f.write("\t\t;Save the user home flags to P variables px52..x67\n")
                f.write("\t\t;NOTE: this overwrites inverse flag (ran out of P vars), so can't use inverse flag after this point\n\t")                
                cmds = []
                for m in ems:
                    if hasattr(m, "nx"):
                        cmds.append("P%d%02d=i7%02d3"%(plc,m.i+52,m.nx))
                    else:
                        cmds.append("MSR%d,i913,P%d%02d"%(m.ms,plc,m.i+52))                             
                f.write("\t\t" + " ".join(cmds)+"\n")
            for m in ems:
                f.write("\t\t; if capture on flag, and flag high, then we need to disable limits\n")
                f.write("\t\tif (P%d%02d&2=2 and P%d%02d&8=0)\n"%(plc,m.i+36,plc,m.i+36))
                f.write("\t\t\t; ix23 (h_vel) should be opposite to ix26 (h_off) and in direction of home flag\n")
                f.write("\t\t\tif (P%d%02d=1 and i%d23>0 and i%d26<1)\n"%(plc,m.i+52,m.ax,m.ax))
                f.write("\t\t\tor (P%d%02d=2 and i%d23<0 and i%d26>-1)\n"%(plc,m.i+52,m.ax,m.ax))
                f.write("\t\t\t\ti%d24=i%d24 | $20000\n"%(m.ax,m.ax))
                f.write("\t\t\telse\n")
                f.write("\t\t\t\t; if it isn't then set it into invalid error\n")
                f.write("\t\t\t\tHomingStatus=StatusInvalid\n")
                f.write("\t\t\tendif\n")
                f.write("\t\tendif\n")
            if ems:
                f.write('\tendif\n\n')                

            # Release all jdist overrides
            for m in Motor.instances:
                m.release_jdist_override()

            #---- Homing State ----        
            htypes = htypes_without(NOTHING)
            # for all motors, set the trigger to be the home flag
            self.__set_hflags(htypes)
            # Then execute the home command
            self.__home(htypes)
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"Homing",lim_htypes=htypes_without(NOTHING, RLIM))

            # restore limit flags for LIMIT motors  
            ems = self.__sel([LIMIT])  
            if ems:
                f.write('\t;---- Restore limits if needed ----\n')
                f.write('\t;Restore the limit flags to P variables px68..x83\n\t')        
                f.write(" ".join(["i%d24=P%d%02d"%(m.ax,plc,m.i+68) for m in ems])+"\n")
                f.write("\n")                

            # Zero all encoders
            ems = self.__sel(htypes)          
            cmds = []
            for m in ems:
                for e in m.enc_axes:
                    cmds.append("#%dhmz"%e)
            if cmds:
                f.write('\t;---- Zero encoder channels ----\n')
                self.__check_not_aborted(f) 
                f.write("\t\tcmd \"" + " ".join(cmds)+"\"\n")                
                f.write('\tendif\n\n')  

            # check motors ALL have home complete flags set
            if ems:
                f.write('\t;---- Check if all motors have homed ----\n')
                self.__check_not_aborted(f) 
                f.write('\tand (%s=0)\n'%("&".join(["m%d45"%m.ax for m in ems])))
                f.write('\t\tHomingStatus=StatusIncomplete\n')
                f.write('\tendif\n\n')          
                              
            #---- Put Back State ----        
            # these are the motors that require a limit check
            lim_mtrs = []
            # these are the motors that will be zeroed
            z_mtrs = []
            # for all motors with post, do the post home move
            for m, htype, post in self.group.actions:
                if post=="i":
                    assert htype != HOME, "Home and put back not available on group %(grp)s, axis %(ax)d, with HOME htype" %m.__dict__
                    assert htype != NOTHING or m.ax in put_back_avail, "Home and put back not available on group %(grp)s, axis %(ax)d, as it hasn't been homed at this point" %m.__dict__
                    # go to initial pos
                    self.__cmd1.append("m%d72=P%d%02d"%(m.ax,plc,m.i+84))
                    self.__cmd2.append("#%dJ=*"%m.ax)
                    lim_mtrs.append(m)
                elif post=="h":
                    # go to high soft limit
                    self.__cmd1.append("m%d72=P%d%02d"%(m.ax,plc,m.i+04))
                    self.__cmd2.append("#%dJ=*"%m.ax)
                    lim_mtrs.append(m)    
                elif post=="l":
                    # go to low soft limit
                    self.__cmd1.append("m%d72=P%d%02d"%(m.ax,plc,m.i+20))
                    self.__cmd2.append("#%dJ=*"%m.ax)
                    lim_mtrs.append(m)        
                elif post=="H":
                    # go to high hard limit, don't check for limits
                    self.__cmd2.append("#%dJ+"%m.ax)      
                elif post=="L":
                    # go to low hard limit, don't check for limits
                    self.__cmd2.append("#%dJ-"%m.ax)    
                elif type(post)==str and post.startswith("r"):
                    # jog relative by post[1:]
                    self.__cmd2.append("#%dJ=%d"%(m.ax,int(post[1:])))     
                    lim_mtrs.append(m)                                                                   
                elif type(post)==str and post.startswith("z"):
                    # go to post[1:]
                    self.__cmd2.append("#%dJ=%d"%(m.ax,int(post[1:])))                                                    
                    lim_mtrs.append(m)
                    z_mtrs.append(m)                    
                elif post not in (None, 0, "0"):
                    # go to post
                    self.__cmd2.append("#%dJ=%d"%(m.ax,post))
                    lim_mtrs.append(m)                    
            # add the commands, wait for the moves to complete
            self.__write_cmds(f,"PostHomeMove", lim_mtrs = lim_mtrs)
            # make the current position zero if required
            if z_mtrs:
                cmds = ["#%dhmz"%m.ax for m in z_mtrs]
                f.write('\t;---- Make current position zero ----\n')
                self.__check_not_aborted(f) 
                f.write("\t\tcmd \"" + " ".join(cmds)+"\"\n")                
                f.write('\tendif\n\n')  

            # End of per group bit
            f.write("endif\n\n")

        #----- Done -----
        f.write(";---- Done ----\n")
        self.__check_not_aborted(f, tabs=0)
        f.write("\t;If we've got this far without failing, set status and state done\n")        
        f.write('\tHomingStatus=StatusDone\n') 
        f.write('\tHomingState=StateDone\n') 
        f.write("\t;Restore the homing group from px03\n")
        f.write("\tHomingGroup=HomingBackupGroup\n")         
        f.write("endif\n\n")

        #----- Tidying Up -----
        f.write(";---- Tidy Up ----\n")
        f.write(";Stop all motors if they don't have a following error\n")
        for m in Motor.instances:
            # if no following error
            f.write('if (m%d42=0)\n'%m.ax)
            f.write('\tcmd "#%dJ/"\n'%m.ax)
            f.write('endif\n')
        f.write(';Restore the high soft limits from P variables px04..x19\n')   
        f.write(" ".join(["i%d13=P%d%02d"%(m.ax,plc,m.i+04) for m in Motor.instances])+"\n")
        f.write(';Restore the low soft limits from P variables px20..x35\n')        
        f.write(" ".join(["i%d14=P%d%02d"%(m.ax,plc,m.i+20) for m in Motor.instances])+"\n")
        f.write(';Restore the home capture flags from P variables px36..x51\n')        
        cmds = []
        for m in Motor.instances:
            if hasattr(m, "nx"):
                cmds.append("i7%02d2=P%d%02d"%(m.nx,plc,m.i+36))
            else:
                cmds.append("MSW%d,i912,P%d%02d"%(m.ms,plc,m.i+36))   
        f.write(" ".join(cmds)+"\n")        
        f.write(';Restore the limit flags to P variables px68..x83\n')        
        f.write(" ".join(["i%d24=P%d%02d"%(m.ax,plc,m.i+68) for m in Motor.instances])+"\n")
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
#define StatusPaused      8
#define StatusDebugHoming 9
HomingStatus = StatusDone

; Homing Group P Variable
#define HomingGroup       P%(plc)s02
HomingGroup = 0

; Homing Group Backup P Variable
#define HomingBackupGroup P%(plc)s03
HomingBackupGroup = 0

OPEN PLC%(plc)s CLEAR

"""
wait_for_move = """\t\t; Wait for the move to complete
\t\ttimer = 20 MilliSeconds ; Small delay to start moving
\t\twhile (timer > 0)
\t\tendw
\t\ttimer = %(timeout)s MilliSeconds ; Now start checking the conditions
\t\twhile (%(InPosition)s=0) ; At least one motor should not be In Position
%(checks)s\t\tand (timer > 0) ; Check for timeout
\t\tand (HomingStatus = StatusHoming or HomingStatus = StatusDebugHoming) ; Check that we didn't abort
\t\tendw
\t\t; Check why we left the while loop
%(results)s\t\tif (timer<0 or timer=0) ; If we timed out
\t\t\tHomingStatus = StatusTimeout
\t\tendif
"""

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
