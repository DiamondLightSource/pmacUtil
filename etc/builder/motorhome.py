#!/usr/bin/env python2.4
import sys

# Setup some Homing types
HOME = 0      # Dumb home
LIMIT = 1     # Home on a limit switch
HSW = 2       # Home on a home switch
HSW_HLIM = 3  # Home on a home switch close to HLIM
HSW_DIR = 4   # Home on a directional limit switch (Newport style)
RLIM = 5      # Home on release of a limit

# Setup some controller types
PMAC = 0
GEOBRICK = 1

# The distance to move when doing large moves
LARGEJ = 100000000

class PLC:
    """Create an object that can create a homing PLC for some motors.
    plc = plc number (any free plc number on the PMAC)
    timeout = timout for any move in ms
    htype = default homing type for any motor added, see add_motor
    jdist = default after trigger jog dist, see add_motor
    post = default post home behaviour, see add_motor
    ctype = 0=PMAC, 1=GEOBRICK"""
        
    def __init__(self,plc,timeout=600000,htype=HOME,jdist=0,post=None,ctype=PMAC):
        self.motors = []
        self.d = { "plc": plc, "timeout": timeout, "axes": [] }
        self.htype = htype
        self.jdist = jdist
        self.post = post
        self.cmd1 = []
        self.cmd2 = []
        self.ctype = ctype
        if self.ctype == PMAC:
            self.d["controller"] = "PMAC"
        else:
            self.d["controller"] = "GeoBrick"

    def add_motor(self,axis,group=1,htype=None,jdist=None,post=None):
        """Add a motor for the PLC to home. If htype, jdist or post are not
        specified, they take the default value as specified when creating PLC().
        axis = motor axis number
        group = homing group. Each group will be homed sequentially, I.e all of
        group 2 together, then all of group 3 together, etc. When asked to home
        group 1, the PLC will home group 1 then all other defined groups 
        sequentially, so you shouldn't add axes to group 1 if you are going to
        use multiple groups in your homing PLC
        htype = homing type enum (hdir is homing direction)
        * HOME: dumb home, shouldn't be needed
        * LIMIT: jog in hdir to limit, jog off it, disable limits, home. Use for
        homing against limit switches
        * HSW: jog in -hdir until flag, jog in hdir until flag, jog in -hdir off
        it, home. Use for reference marks or home switches. If using a reference
        mark be sure to set jdist.
        * HSW_HLIM: jog in hdir until flag, if limit switch hit jog in -hdir
        until flag, jog in -hdir off it, home. Use for reference marks or home 
        switches which are generally in hdir from a normal motor position. If
        using a reference mark be sure to set jdist.
        * HSW_DIR: jog in -hdir until not flag, jog in hdir until flag, jog in 
        -hdir until not flag, home. Use for directional (Newport style) home
        switches.
        * RLIM: jog in -hdir to limit, home. Use for homing on release of limit
        switches
        jdist = distance to jog by after finding the trigger. Should always be
        in a -hdir. E.g if ix23 = -1, jdist should be +ve. This should only be
        needed for reference marks or bouncy limit switches. A recommended 
        value in these cases is about 1000 counts in -hdir.
        post = where to move after the home. This can be:
        * None: Stay at the home position
        * an integer: move to this position in motor cts
        * "i": go to the initial position (does nothing for HOME htype motors)
        * "l": go to the low limit (ix13)
        * "h": go to the high limit (ix14)"""
        # jdist should always be opposite direction to ix23, only add it if you have a bouncy limit switch
        if len(self.motors)>=16:
            raise IndexError, "Only 16 motors may be defined in a single PLC"
        if axis in [m["ax"] for m in self.motors]:
            raise IndexError, "Axis %d already defined as a different motor"%axis
        if group>7 or group==0:
            raise IndexError, "Nothing can be in group 0, only 7 groups may be defined in a single PLC"                    
        d = { "ax": axis,
              "ms":2*(axis-1)-(axis-1)%2, # macrostation number, PMAC
              "grp": group,
            }
        if self.ctype == GEOBRICK:
            if axis < 9:
                d["nx"] = ((axis-1)/4)*10 + ((axis-1)%4+1) # nx for internal amp, GEOBRICK
            else:
                d["ms"] = 2*(axis-9)-(axis-9)%2 # macrostation number for external amp, GEOBRICK            
        for var in ["htype","jdist","post"]:
            if eval(var)!=None:
                d[var]=eval(var)
            else:
                d[var]=eval("self."+var)
        self.motors.append(d)
        self.d["axes"] += ["#%d"%axis]

    def set_jdist_hdir(self,htypes,reverse=False):
        # set jdist reg to be a large distance in hdir, or in -hdir if reverse
        if reverse:
            self.cmd1 += [ "m%d72=%d*(-i%d23/ABS(i%d23))"%(m["ax"],LARGEJ,m["ax"],m["ax"]) for i,m in self.sel(htypes) ]
        else:
            self.cmd1 += [ "m%d72=%d*(i%d23/ABS(i%d23))"%(m["ax"],LARGEJ,m["ax"],m["ax"]) for i,m in self.sel(htypes) ]

    def home(self,htypes):
        # home command
        self.cmd2 += [ "#%dhm"%m["ax"] for i,m in self.sel(htypes) ]

    def jog_until_trig(self,htypes,reverse=False):
        # jog until trigger, go dist past trigger
        self.set_jdist_hdir(htypes,reverse)
        self.cmd2 += [ "#%dJ^*^%d"%(m["ax"],m["jdist"]) for i,m in self.sel(htypes) ]

    def jog_inc(self,htypes,reverse=False):
        # jog incremental by jdist reg
        self.set_jdist_hdir(htypes,reverse)
        self.cmd2 += [ "#%dJ^*"%m["ax"] for i,m in self.sel(htypes) ]

    def set_hflags(self, htypes, inv=False):
        # set the hflags of all types of motors in htypes
        for i,m in self.sel(htypes):
            if m.has_key("nx"):                
                t = "i7%02d2="%m["nx"] # geobrick internal axis
            else:
                t = "MSW%d,i912,"%m["ms"] # ms external axis
            if inv:
                self.cmd1.append(t+"P%d%02d"%(self.d["plc"],i+52))
            else:
                self.cmd1.append(t+"P%d%02d"%(self.d["plc"],i+36))

    def write_cmds(self,state,htypes=None):
        # process self.cmd1 and self.cmd2 and write them out, need to do an endif after
        if self.cmd1 or self.cmd2:
            self.f.write('\t;---- %s State ----\n'%state)
            self.f.write('\tif (HomingStatus=StatusHoming)\n')
            self.f.write('\t\tHomingState=State%s\n'%state)                            
            self.f.write('\t\t; Execute the move commands\n')
        out = [[]]
        for t in self.cmd1:
            if len(" ".join(out[-1]+[t]))<254 and len(out[-1])<32:
                out[-1].append(t)
            else:
                out += [[t]]
        for l in [(" ".join(l)) for l in out]:
            if l:
                self.f.write("\t\t"+l+"\n")
        out = [[]]
        for t in self.cmd2:
            if len(" ".join(out[-1]+[t]))<248 and len(out[-1])<32:
                out[-1].append(t)
            else:
                out += [[t]]
        for l in [(" ".join(l)) for l in out]:
            if l:
                self.f.write('\t\tcmd "%s"\n'%l)
        if self.cmd1 or self.cmd2:
            self.cmd1 = []            
            self.cmd2 = []
            # setup a generic wait for move routine in self.d         
            inpos = [ "m%d40"%m["ax"] for i,m in self.sel() ]
#            dv0 = [ "m%d33"%m["ax"] for i,m in self.sel() ]
            self.d["InPosition"] = "&".join(inpos)
            self.d["FFErr"] = "|".join("m%d42"%m["ax"] for i,m in self.sel()) 
            # only check the limit switches of htypes 
            self.d["Limit"] = "|".join("m%d30"%m["ax"] for i,m in self.sel(htypes))
            if not self.d["Limit"]:
                self.d["Limit"]="0"
            self.f.write(wait_for_move%self.d)
            self.f.write('\tendif\n\n')

    
    def sel(self,htypes=None):
        if htypes:
            return [(i,m) for i,m in enumerate(self.motors) if m["htype"] in htypes and self.group==m["grp"]]
        else:
            return [(i,m) for i,m in enumerate(self.motors) if self.group==m["grp"]]

    def returnText(self):
        class Dummy(object):
            content = []
            def write(self, s):
                self.content.append(s)
        f = Dummy()
        self.writeFile(f)
        return "".join(f.content)

    def write(self,f):
        """write(f)
        Write the PLC text to a filename f"""
        # open the file and write the header
        f = open(f,"w")
        self.writeFile(f)
        f.close()

    def writeFile(self,f):                            
        f.write(header%self.d)
        self.f = f
        plc = self.d["plc"]
        ems = [ (i,m) for i,m in enumerate(self.motors) ]
        
        #---- Configuring state ----
        f.write(";---- Configuring State ----\n")
        f.write("HomingState=StateConfiguring\n")
        f.write(";Save the Homing group to px03\n")
        f.write("HomingBackupGroup=HomingGroup\n")        
        f.write(";Save low soft limits to P variables px04..x19\n")
        f.write(" ".join(["P%d%02d=i%d13"%(plc,i+04,m["ax"]) for i,m in ems])+"\n")
        f.write(";Save the high soft limits to P variables px20..x35\n")
        f.write(" ".join(["P%d%02d=i%d14"%(plc,i+20,m["ax"]) for i,m in ems])+"\n")
        f.write(";Save the home capture flags to P variables px36..x51\n")
        cmds = []
        for i,m in ems:
            if m.has_key("nx"):
                cmds.append("P%d%02d=i7%02d2"%(plc,i+36,m["nx"]))
            else:
                cmds.append("MSR%d,i912,P%d%02d"%(m["ms"],plc,i+36))
        f.write(" ".join(cmds)+"\n")
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
        
        # find all the possible groups
        groups = []
        for m in self.motors:
            if m["grp"] not in groups:
                groups.append(m["grp"])
        groups.sort()
        
        # write some PLC for each group
        for g in groups:
            f.write("if (HomingBackupGroup=1 and HomingStatus=StatusHoming)\n")
            if g!=1:
                f.write("or (HomingBackupGroup=%d and HomingStatus=StatusHoming)\n"%g)            
            self.group = g
            f.write("\tHomingGroup=%d\n\n"%g)  
            
            #---- PreHomeMove State ----
            # for hsw_dir motors, set the trigger to be the inverse flag
            self.set_hflags([HSW_DIR],inv=True)
            # for hsw/hsw_dir motors jog until trigger in direction of -ix23
            self.jog_until_trig([HSW,HSW_DIR],reverse=True)
            # for rlim motors jog in direction of -ix23
            self.jog_inc([RLIM],reverse=True)          
            # for hsw_hlim motors jog until trigger in direction of ix23        
            self.jog_until_trig([HSW_HLIM])
            # add the commands, HSW_DIR can't hit the limit
            self.write_cmds("PreHomeMove",htypes=[HSW_DIR]) 

            # for hsw_hlim we could have gone past the limit and hit the limit switch
            ems = self.sel([HSW_HLIM])
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
                self.d["Limit"] = "|".join("m%d30"%m["ax"] for i,m in ems)
                f.write(wait_for_move%self.d) 
                f.write('\tendif\n\n')

            #---- FastSearch State ----        
            htypes = [LIMIT,HSW,HSW_DIR,HSW_HLIM,RLIM]
            # for hsw_dir motors, set the trigger to be the original flag
            self.set_hflags([HSW_DIR]) 
            # for all motors except hsw_hlim jog until trigger in direction of ix23
            self.jog_until_trig(htypes)
            # add the commands, wait for the moves to complete
            self.write_cmds("FastSearch",htypes=[HSW,HSW_DIR,HSW_HLIM,RLIM])
            
            # store home points
            ems = self.sel(htypes+[HSW_HLIM])  
            if ems:
                f.write('\t;---- Store the difference between current pos and start pos ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n')
                for i,m in ems:
                    # put back pos = (start pos - current pos) converted to counts + jdist - home off * 16
                    f.write('\t\tP%d%02d=(P%d%02d-M%d62)/(I%d08*32)+%d-(i%d26/16)\n'%(plc,i+84,plc,i+84,m["ax"],m["ax"],m["jdist"],m["ax"]))
                f.write('\tendif\n\n')  
                
            #---- FastRetrace State ----
            htypes = [LIMIT,HSW,HSW_HLIM,HSW_DIR,RLIM]
            # for limit/hsw_* motors, set the trigger to be the inverse flag
            self.set_hflags(htypes,inv=True)
            # then jog until trigger in direction of -ix23
            self.jog_until_trig(htypes,reverse=True)
            # add the commands, wait for the moves to complete
            self.write_cmds("FastRetrace",htypes=[LIMIT,HSW,HSW_HLIM,HSW_DIR])

            # check that the limit flags are reasonable for LIMIT motors, and remove limits if so  
            ems = self.sel([LIMIT])  
            if ems:
                f.write('\t;---- Check if any limits need disabling ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n')     
                f.write("\t\t;Save the user home flags to P variables px52..x67\n")
                f.write("\t\t;NOTE: this overwrites inverse flag (ran out of P vars), so can't use inverse flag after this point\n\t")                
                cmds = []
                for i,m in ems:
                    if m.has_key("nx"):
                        cmds.append("P%d%02d=i7%02d3"%(plc,i+52,m["nx"]))
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
            htypes = [HOME,LIMIT,HSW,HSW_HLIM,HSW_DIR,RLIM]
            # for all motors, set the trigger to be the home flag
            self.set_hflags(htypes)
            # Then execute the home command
            self.home(htypes)
            # add the commands, wait for the moves to complete
            self.write_cmds("Homing",htypes=htypes)

            # check motors ALL have home complete flags set
            ems = self.sel(htypes)  
            if ems:
                f.write('\t;---- Check if all motors have homed ----\n')
                f.write('\tif (HomingStatus=StatusHoming)\n') 
                f.write('\tand (%s=0)\n'%("&".join(["m%d45"%m["ax"] for i,m in ems])))
                f.write('\t\tHomingStatus=StatusIncomplete\n')
                f.write('\tendif\n\n')          
                              
            #---- Put Back State ----        
            # for all motors with post, do the home move
            for i,m in [ (i,m) for i,m in enumerate(self.motors) if m["post"]!=None and m["grp"]==self.group ]:
                if m["post"]=="i":
                    if m["htype"]!=HOME:
                        # go to initial pos
                        self.cmd1.append("m%d72=P%d%02d"%(m["ax"],plc,i+84))
                        self.cmd2.append("#%dJ=*"%m["ax"])
                elif m["post"]=="l":
                    # go to low soft limit
                    self.cmd1.append("m%d72=P%d%02d"%(m["ax"],plc,i+04))
                    self.cmd2.append("#%dJ=*"%m["ax"])        
                elif m["post"]=="h":
                    # go to high soft limit
                    self.cmd1.append("m%d72=P%d%02d"%(m["ax"],plc,i+20))
                    self.cmd2.append("#%dJ=*"%m["ax"])                    
                else:
                    # go to m["post"]
                    self.cmd2.append("#%dJ=%d"%(m["ax"],m["post"]))
            # add the commands, wait for the moves to complete
            self.write_cmds("PostHomeMove")

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
        ems = [ (i,m) for i,m in enumerate(self.motors) ]
        f.write(";---- Tidy Up ----\n")
        f.write(";Stop all motors if they don't have a following error\n")
        for i,m in ems:
            # if no following error
            f.write('if (m%d42=0)\n'%m["ax"])
            f.write('\tcmd "#%dJ/"\n'%m["ax"])
            f.write('endif\n')
        f.write(';Restore the low soft limits from P variables px04..x19\n')   
        f.write(" ".join(["i%d13=P%d%02d"%(m["ax"],plc,i+04) for i,m in ems])+"\n")
        f.write(';Restore the high soft limits from P variables px20..x35\n')        
        f.write(" ".join(["i%d14=P%d%02d"%(m["ax"],plc,i+20) for i,m in ems])+"\n")
        f.write(';Restore the home capture flags from P variables px36..x51\n')        
        cmds = []
        for i,m in ems:
            if m.has_key("nx"):
                cmds.append("i7%02d2=P%d%02d"%(m["nx"],plc,i+36))
            else:
                cmds.append("MSW%d,i912,P%d%02d"%(m["ms"],plc,i+36))                
        f.write(" ".join(cmds)+"\n")        
        f.write(';Restore the limit flags to P variables px68..x83\n')        
        f.write(" ".join(["i%d24=P%d%02d"%(m["ax"],plc,i+68) for i,m in ems])+"\n")
        f.write("\n")
        f.write("DISABLE PLC%s\n"%plc)
        f.write("CLOSE\n")

header = """CLOSE

;####################################################
; Autogenerated Homing PLC for %(controller)s, DO NOT MODIFY
; Axes: %(axes)s
;####################################################

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
\t\tand (%(Limit)s=0) ; Should not stop on position limit for selected motors
\t\tand (timer > 0) ; Check for timeout
\t\tand (HomingStatus = StatusHoming) ; Check that we didn't abort
\t\tendw
\t\t; Check why we left the while loop
\t\tif (%(FFErr)s=1) ; If a motor hit a following error
\t\t\tHomingStatus = StatusFFErr
\t\tendif
\t\tif (%(Limit)s=1) ; If a motor hit a limit
\t\t\tHomingStatus = StatusLimit
\t\tendif
\t\tif (timer<0 or timer=0) ; If we timed out
\t\t\tHomingStatus = StatusTimeout
\t\tendif
"""


if __name__=="__main__":
    p = PLC(1,timeout=100000,htype=HOME,jdist=0,ctype=GEOBRICK)
    p.add_motor(1,jdist=100)
    p.add_motor(2,htype=LIMIT,jdist=200)
    p.add_motor(3,group=6,htype=HSW,jdist=300)
    p.add_motor(4,htype=HSW_HLIM,jdist=400)
    p.add_motor(5,htype=HSW,jdist=500,post="i")
    p.add_motor(6,htype=HSW_HLIM,jdist=600)
    p.add_motor(7,htype=HSW_DIR,jdist=700,post="l")    
    p.add_motor(8,jdist=100)
    p.add_motor(9,group=2,htype=LIMIT,jdist=200)
    p.add_motor(10,htype=HSW,jdist=300)
    p.add_motor(11,htype=HSW_HLIM,jdist=400)
    p.add_motor(12,htype=HSW,jdist=500,post="h")
    p.add_motor(13,htype=HSW_HLIM,jdist=600)
    p.add_motor(14,htype=RLIM,jdist=700,post=100)    
    p.add_motor(15,group=4,htype=RLIM,jdist=800,post=150)            
    p.add_motor(16,group=4,htype=RLIM,jdist=800,post=-100)                
    p.write("/tmp/test_home_PLC.pmc")
