#!/bin/env dls-python2.6
import sys, unittest, ConfigParser
from pkg_resources import require
require('cothread')
import cothread
from cothread.catools import *
from optparse import OptionParser

# Module Under Test Today (MUTT)
import poscomp

class Scaler:
    def __init__(self, basepv, channel):
        self.pv_base = basepv
        self.pv_start = self.pv_base + ".CNT"
        self.pv_mode = self.pv_base + ".CONT"
        self.pv_time = self.pv_base + ".TP"
        self.pv_time_rbv = self.pv_base + ".T"
        self.pv_counters = [self.pv_base+".S%d"%ch for ch in range(1,32+1)]
        self.ch_index = int(channel) - 1
        
    def start(self, time=80.0):
        caput( self.pv_mode, 0, wait=True)
        caput( self.pv_start, "stop", wait=True)
        caput( self.pv_time, float(time), wait=True)
        caput( self.pv_start, "start", wait=False )
        
    def getCount(self):
        caput( self.pv_start, "stop", wait=True)
        count = caget( self.pv_counters )
        runtime = caget( self.pv_time_rbv )
        return (int(count), float(runtime))
        

class ScalerMcs:
    def __init__(self, basepv):
        self.pv_base = basepv
        self.pv_start = self.pv_base + ":EraseStart"
        self.pv_time = self.pv_base + ":PresetReal"
        self.pv_advance = self.pv_base + ":ChannelAdvance"
        self.pv_counts = self.pv_base + ":mca1"
        self.pv_nelm = self.pv_base + ":mca1.NORD"                        
        
    def start(self):
        caput( self.pv_time, 0 )
        caput( self.pv_advance, "External" )        
        caput( self.pv_start, 1, wait=False )
        cothread.Sleep(3)
        
    def getCount(self):
        count = caget( self.pv_counts )
        nelm = caget( self.pv_nelm )
        return (count, nelm)

class PositionCompareTestSuite( unittest.TestSuite ):
    """poscomp.PositionCompare test suite
    This test suite generate the input parameters to the specific test cases
    based on a configuration file. """
    cfg = None
    def createTestsFromConfig( self, configfile ):
        defaults = {'start': 0,
                    'end': 0 }
        self.cfg = ConfigParser.RawConfigParser()
        self.cfg.read(configfile)
        
        # Run through all sections in the config file.
        for sec in self.cfg.sections():
#            print "section: %s"%sec
#            print str(self.cfg.items(sec))
            # Check if a section contain the 'testcase' option and the value of the 
            # 'testcase' option matches the name of a testfunction in the PositionCompareTestCase.
            if not self.cfg.has_option(sec,'testcase'):
                continue
            if not hasattr( PositionCompareTestCase, self.cfg.get(sec, 'testcase') ):
                continue
#            print "Adding user defined test: \'%s\' test function: \'%s\'"%(sec, self.cfg.get(sec, 'testcase'))
            t=PositionCompareTestCase(self.cfg.get(sec, 'testcase'))
            testparameters = dict(self.cfg.items(sec))
            testparameters.update( {'section': sec} )
            t.setTestParam(dict(self.cfg.items(sec)))
            self.addTest(t)


class PositionCompareTestCase( unittest.TestCase ):
    desc = ""
    def setUp(self):
        self.pc = poscomp.PositionCompare(self.param['basepv'])
        self.pc.buildpvs()
        
    def shortDescription(self):
        return self.desc
        
    def setTestParam(self,param):
#        print "--- test parameters: ----\n%s\n------------------------"%str(param)
        self.param=param
        self.desc = self._testMethodDoc+" param=%s"%str(self.param)
        if "scaler" in self.param:        
            self.scaler = Scaler( self.param['scaler'], self.param['scaler_channel'] )
        if "scalermcs" in self.param:
            self.scalermcs = ScalerMcs( self.param['scalermcs'] )        

    ############# define individual checks #####################
    def test_configure(self):
        """Check if the configuration is really valid"""
        
        self.pc.configure( self.param['stepincrement'], 
                      self.param['pulsewidth'], 
                      startpos = self.param['startposition'], 
                      stoppos = self.param['stopposition'] )

        stepinccts   = caget(self.pc.pv_pulse_period_cts)
        stepwidthcts = caget(self.pc.pv_pulse_width_cts)
        self.failUnless(stepinccts == float(self.param['stepincrement'])/self.pc.motor_mres,
                        'Commanded step increment in engineering units does not match step increment in counts')

    def test_simpleposcomp(self):
        """Test of simple position compare move without a ROI window defined """
        self.pc.configure( self.param['stepincrement'], 
                      self.param['pulsewidth'], 
                      startpos = 0.0, 
                      stoppos = 0.0 )
        self.pc.flyback(0.0)
        self.scaler.start()
        self.pc.driveposcomp(self.param['destination'], velo = self.param['velocity'])
        counts,time = self.scaler.getCount()
        self.pc.flyback(0.0)
        
        self.failUnless( count == pc.npulses,
                         'Number of measured counts (%d for %fsec) does not match the expected counts (%d)'%(counts, float(time), self.pc.npulses))

    def test_I11poscomp(self):
        """I11 test with mca"""
        print
        f = open("I11results.csv", "w")
        for r in range(5):
            for t in [30, 45, 60, 90, 120, 150, 180, 300, 600, 900, 1200, 1800, 3600]:
                velocity = 45.0 / t
                self.pc.configure( self.param['stepincrement'], 
                              self.param['pulsewidth'], 
                              self.param['startposition'], 
                              self.param['stopposition'])
                self.pc.flyback(self.param['motorstart'])
                self.scalermcs.start()
                self.pc.driveposcomp(self.param['destination'], velo = velocity)
                counts,nelm = self.scalermcs.getCount()
                self.pc.flyback(self.param['motorstart'])
                print "Time: %s, Velocity: %s, Nelm: %s, Npulses: %s" %(t, velocity, nelm,self.pc.npulses) 
                f.write("# Time: %s, Velocity: %s, Nelm: %s, Npulses: %s\n" %(t, velocity, nelm,self.pc.npulses)) 
                for i in range(nelm):
                    f.write("%s," % counts[i])
                f.write("\n")
                f.flush()
                
                '''                self.failUnless( nelm >= self.pc.npulses - 1,
                                 'Number of measured counts (%d) does not match the expected counts (%d)'%(nelm, self.pc.npulses))        
                self.failUnless( counts[self.pc.npulses + 10] == 0,
                                 'Did not stop within 10 counts (%s!=0)' % counts[self.pc.npulses + 10])'''
        f.close()

    def test_labposcomp(self):
        """Lab test with mca"""
        print
        f = open("labresults.csv", "w")
        for r in range(50):
            for t in [30, 45, 60, 90, 120, 150, 180, 300, 600, 900, 1200, 1800, 3600]:
                velocity = (float(self.param['stopposition']) - float(self.param['startposition'])) / t
                self.pc.configure( self.param['stepincrement'], 
                              self.param['pulsewidth'], 
                              self.param['startposition'], 
                              self.param['stopposition'])
                self.pc.flyback(self.param['motorstart'])
                self.scalermcs.start()
                self.pc.driveposcomp(self.param['destination'], velo = velocity)
                cothread.Sleep(5)
                counts,nelm = self.scalermcs.getCount()
                self.failUnless( nelm >= self.pc.npulses - 1,
                    'Number of measured counts (%d) does not match the expected counts (%d)'%(nelm, self.pc.npulses))
                self.pc.flyback(self.param['motorstart'])
                print "Time: %s, Velocity: %s, Nelm: %s, Npulses: %s" %(t, velocity, nelm,self.pc.npulses) 
                f.write("# Time: %s, Velocity: %s, Nelm: %s, Npulses: %s\n" %(t, velocity, nelm,self.pc.npulses)) 
                for i in range(nelm):
                    f.write("%s," % counts[i])
                f.write("\n")
                f.flush()
                
                '''                 
                self.failUnless( counts[self.pc.npulses + 10] == 0,
                                 'Did not stop within 10 counts (%s!=0)' % counts[self.pc.npulses + 10]) '''
        f.close()
        
if __name__ == '__main__':
    #unittest.main() 
    print "\n    ================== Initialising tests =========================\n"
    suite = PositionCompareTestSuite()
    suite.createTestsFromConfig( sys.argv[1] )
    print "\n    ===================== Running tests ===========================\n"
    unittest.TextTestRunner(verbosity=2).run(suite)

