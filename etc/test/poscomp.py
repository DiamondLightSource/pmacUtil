#!/bin/env dls-python2.6
import sys
from pkg_resources import require
require('cothread')
import cothread
from cothread.catools import *
from optparse import OptionParser


class PositionCompare:
    OUTPUT = {'off': 0, 'on': 1, 'auto': 2}
    def __init__(self, basepv):
        self.pv_base = basepv
        
        self.mon_poscts = None
        self.poscts = None
        self.mon_poscompstate = None
        self.poscompstate = None
    
    def buildpvs(self):
        # Get the PV name of the associated motor record
        self.pv_motor             = str(caget(self.pv_base + ":MOTOR"))
        # Motor record fields
        self.pv_motor_egu         = self.pv_motor + ".EGU"
        self.pv_motor_rbv         = self.pv_motor + ".RBV"
        self.pv_motor_mres        = self.pv_motor + ".MRES"
        self.pv_motor_velo        = self.pv_motor + ".VELO"
        self.pv_motor_vmax        = self.pv_motor + ".VMAX"
        self.pv_motor_rep         = self.pv_motor + ".REP"
        # Position compare records
        self.pv_outputmode        = self.pv_base  + ":CTRL"
        self.pv_range_start       = self.pv_base  + ":START"
        self.pv_range_start_cts   = self.pv_base  + ":CONVSTART"
        self.pv_range_stop        = self.pv_base  + ":STOP"
        self.pv_output_init       = self.pv_base  + ":INIT"
        self.pv_pulse_period      = self.pv_base  + ":STEP"
        self.pv_pulse_period_cts  = self.pv_base  + ":CONVSTEP"
        self.pv_pulse_period_rbv  = self.pv_base  + ":STEP:RBV"
        self.pv_pulse_width       = self.pv_base  + ":PULSE"
        self.pv_pulse_width_cts   = self.pv_base  + ":CONVPULSE"
        self.pv_pulse_width_rbv   = self.pv_base  + ":PULSE:RBV"
        self.pv_compare_state_rbv = self.pv_base  + ":STATE"
        self.pv_npulses_rbv       = self.pv_base  + ":NPULSES"
        
        # Get a couple of constants from the control system
        self.motor_vmax = caget(self.pv_motor_vmax)
        self.motor_mres = caget(self.pv_motor_mres)
        
    def _cbposition(self, position):
        """Callback on CA monitor events on the position readback. Just latches the current position"""
        self.poscts = position
    def _cbstate(self, state):
        """Callback on CA montior events on the position compare state PV. Prints a message each time the state changes."""
        self.poscompstate = str(state)
        s = "Compare state: \'%s\'  position: \'%s\' [cts]"%(self.poscompstate, str(self.poscts))
        print s
        
    def setupmonitors( self ):
        self.mon_poscts = camonitor( self.pv_motor_rep, self._cbposition )
        self.mon_poscompstate = camonitor( self.pv_compare_state_rbv, self._cbstate, datatype=DBR_STRING )
    def disablemonitors( self ):
        self.mon_poscts.close()
        self.mon_poscompstate.close()
    
    def _calcmovetimeout(self, endpos):
       (velo, rbv) = caget([self.pv_motor_velo, self.pv_motor_rbv])
       timeout = (abs( endpos - rbv )/velo) + 5.0
       return timeout

    def configure(self, period, width, startpos=0.0, stoppos=0.0, outputmode=OUTPUT['auto'], velo=None):
        """Configure the position compare with pulse period and width in EGU and optionally 
           start and stop position (default is not to use start/stop)"""
        caput( self.pv_pulse_period,   float(period),     wait=True)
        caput( self.pv_pulse_width,    float(width),      wait=True)
        caput( self.pv_range_start,    float(startpos),   wait=True)
        caput( self.pv_range_stop,     float(stoppos),    wait=True)
        caput( self.pv_outputmode,     int(outputmode),   wait=True)
        if velo:
            caput( self.pv_motor_velo, float(velo),       wait=True)
        self.npulses = caget( self.pv_npulses_rbv )
        
    def flyback( self, startpoint, outputmode=0 ):
        """Drive the motor back to it's defined start point at the VMAX velocity.
           VELO is latched at the beginning and restored at the end of the move."""
        startpoint = float(startpoint)
        # Latch the current velocity in order to restore later
        # Get the current position to calculate moving distance
        # Latch the outputmode in order to restore at the end
        latching_pvs = [self.pv_motor_velo, self.pv_outputmode]
        latching_data = caget( latching_pvs )

        # Set the VELO to be VMAX for full speed flyback
        caput( self.pv_motor_velo, self.motor_vmax, wait=True )
        # Set the outputmode (whether to do position compare on the flyback or not)
        caput( self.pv_outputmode, outputmode )
        
        # Calculate the timeout for the full move
        timeout = self._calcmovetimeout( startpoint )
        # Demand the move and wait until completion or timeout [s]
        caput( self.pv_motor, startpoint, timeout = timeout, wait=True )
        
        # Restore various PVs as we found them before the move
        caput( latching_pvs, latching_data, wait=True )

    def driveposcomp( self, endpoint, velo=None ):
        """Drive the motor to endpoint with position compare output enabled. """
        endpoint = float(endpoint)
        velo = float(velo)
        latching_pvs = [self.pv_motor_velo, self.pv_outputmode]
        latching_data = caget(latching_pvs)
        
        if velo:
            velo=float(velo)
            caput( self.pv_motor_velo, velo, wait=True )
    
        # Enable the position compare output
        caput( self.pv_outputmode, self.OUTPUT['auto'], wait=True )
        
        # Demand the move and wait until completion or timeout [s]
        timeout = self._calcmovetimeout( endpoint )
        caput( self.pv_motor, endpoint, timeout = timeout, wait=True )
        
        # Restore various PVs as we found them before the move
        caput( latching_pvs, latching_data, wait=True )
    
    
def main():
    parser = OptionParser("""usage: %prog [options] BASEPV DEST

%prog will run the position compare application named BASEPV from it's current position to destination DEST.
""")
    parser.add_option("-p", "--period", action="store",
                      dest="period", default=1.0,
                      help="Specify the output pulse period distance in engineering units. Default is 1.0")
    parser.add_option("-w", "--width", action="store",
                      dest="width", default=0.5,
                      help="Specify the output pulse width distance in engineering units. Default 0.5")
    parser.add_option("-v", "--velocity", action="store",
                      dest="velocity", default=None,
                      help="Specify the drive velocity. Default is to use the current setting of the VELO field.")
    parser.add_option("-r", "--roi", action="store",
                      dest="roi", default=None,
                      help="Specify a region-of-interest - a range [start:stop] where the position compare is active. Default is not to define a roi. Example: --roi=1.0:2.0")
    (options, args) = parser.parse_args()
    if len(args) < 2:
        parser.error("### ERROR ### Too few arguments supplied.")
        sys.exit(1)
        
    basepv = args[0]
    destination = float(args[1])
    
    start,stop = None,None
    if options.roi:
        (start,stop) = [float(p) for p in options.roi.split(':')]
    options.period   = float(options.period)
    options.width    = float(options.width)
    options.velocity = float(options.velocity)

    pc = PositionCompare( basepv )
    pc.buildpvs()
    pc.configure( options.period, options.width, 
                  startpos = start, stoppos = stop )
    pc.setupmonitors()
    latch_pos = caget( pc.pv_motor_rbv )
    pc.driveposcomp( destination, velo = options.velocity )
    pc.flyback( latch_pos )
    pc.disablemonitors()
    
if __name__=="__main__":
    main()
    
    
