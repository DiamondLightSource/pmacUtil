#!/dls_sw/tools/bin/python2.4

from pkg_resources import require
require('dls.autotestframework')
from dls.autotestframework import *

################################################
# Test suite for the PMAC limit protection PLC
    
class ProtectionTestSuite(TestSuite):

    def createTests(self):
        # Define the targets for this test suite
        Target("simulation", self, [
            ModuleEntity('pmacUtil'),
            IocEntity('ioc', directory='iocs/protectionEx', bootCmd='bin/linux-x86/stprotectionEx.boot'),
            SimulationEntity('pmac', runCmd='dls-pmac-sim --noconsole --rpc=9100 etc/test/protection.cfg', rpcPort=9100),
            EpicsDbEntity('db', directory='iocs/protectionEx/db', fileName='protectionEx.db')])

        # The tests
        CaseHitHighLimit(self)
        CaseHitLowLimit(self)
        CaseNormalOffOn(self)
        CaseOnLimitOffOn(self)
        CaseRecoverLimitOffOn(self)
        CaseLockOut(self)
        CaseLockOutOffOn(self)
        CaseNormalHoming(self)
        CaseOnLimitHoming(self)
        CaseRecoverLimitHoming(self)
        CaseLockOutHoming(self)
        CaseNormalEncoderLoss(self)
        CaseEncoderLossOffOn(self)
        CaseHomingEncoderLoss(self)
        CaseOnLimitEncoderLoss(self)
        
################################################
# Intermediate test case class that provides some utility functions
# for this suite

class ProtectionCase(TestCase):

    def enable(self, p):
        self.putPv(p+":PROT:ENABLE", 1)
    
    def disable(self, p):
        self.putPv(p+":PROT:ENABLE", 0)
    
    def setRecoveryVelocity(self, p, v):
        self.putPv(p+":PROT:RECOVERVEL", v)
    
    def recover(self, p):
        '''Triggers a recovery.'''
        self.putPv(p+":PROT:RECOVER", 0)
        self.putPv(p+":PROT:RECOVER", 1)
        self.putPv(p+":PROT:RECOVER", 0)

    def forceHighLimitClear(self, axis):
        self.simulation("pmac").writeMVar('pmac1', axis*100+57, 0)

    def activateHoming(self, axis):
        v = int(self.simulation("pmac").readPVar('pmac1', 400+axis))
        v = v | 4
        self.simulation("pmac").writePVar('pmac1', 400+axis, v)

    def deactivateHoming(self, axis):
        v = int(self.simulation("pmac").readPVar('pmac1', 400+axis))
        v = v & ~4
        self.simulation("pmac").writePVar('pmac1', 400+axis, v)

    def setEncoderLoss(self, axis, eloss):
        self.simulation("pmac").writeMVar('pmac1', axis*100+84, eloss)
    
    def verifyState(self, p, state):
        '''Verifies the current protection state.'''
        self.verifyPv(p+":PROT:STATE", state)

    def verifyKilled(self, axis):
        ampEna = self.simulation("pmac").readMVar('pmac1', axis*100+39)
        self.verify(ampEna, 0)

    def verifyNotKilled(self, axis):
        ampEna = self.simulation("pmac").readMVar('pmac1', axis*100+39)
        self.verify(ampEna, 1)

    def verifyFollowingErrorLimit(self, axis, val):
        errLim = self.simulation("pmac").readIVar('pmac1', axis*100+11)
        self.verify(errLim, val)

    def verifyVelocity(self, axis, val):
        errLim = self.simulation("pmac").readIVar('pmac1', axis*100+22)
        self.verify(errLim, val)

    def waitForStateTransition(self, p, fromState, toState, timeout=500):
        curState = self.getPv(p+':PROT:STATE')
        while fromState == curState and timeout > 0:
            self.sleep(0.1)
            timeout -= 0.1
            curState = self.getPv(p+':PROT:STATE')
        if curState != toState:
            self.fail('%s:PROT:STATE[%s] did not become %s' % (p, curState, toState))

    def moveTo(self, p, to):
        '''Moves the motor to the specified position.'''
        self.moveMotorTo(p, to)
        self.sleep(1)

    def jogNegative(self, p):
        self.putPv(p+'.VAL', -11, wait=False)

    def jogPositive(self, p):
        self.putPv(p+'.VAL', 11, wait=False)

    def stop(self, p):
        self.putPv(p+'.STOP', 1, wait=False)

    def verifyPosition(self, p, pos):
        '''Verifies the motor is at the given position.'''
        self.verifyPvFloat(p+'.RBV', pos, 0.01)

    def verifyNotInPosition(self, p, pos):
        '''Verifies the motor is not at the given position.'''
        d = self.getPv(p+'.RBV')
        if not(d < (pos - 0.01) or d > (pos + 0.01)):
            self.fail("%s[%s] == %s +/-%s" % (p+'.RBV', d, pos, 0.01))

    def verifyResolutionAndVelocity(self, p, mres, eres, vmax, velo):
        '''Verifies the motor record MRES, ERES, VMAX and VELO fields.'''
        self.verifyPvFloat(p+'.MRES', mres, 0.00001)
        self.verifyPvFloat(p+'.ERES', eres, 0.00001)
        self.verifyPvFloat(p+'.VMAX', vmax, 0.00001)
        self.verifyPvFloat(p+'.VELO', velo, 0.00001)
        
        
################################################
# Test cases

stateNormal = 1
stateOnLimit = 2
stateRecoverLimit = 3
stateEncoderLoss = 4
stateHoming = 5
stateNotProtected = 6
stateRestoreLoopMode1 = 7
stateRestoreLoopMode2 = 8
stateRestoreLoopMode3 = 9
stateLockOut = 10
p = "PROTECTIONEX:MOTOR"
    
class CaseHitHighLimit(ProtectionCase):
    def runTest(self):
        '''Hitting the high limit.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.25)
        self.verifyFollowingErrorLimit(1, 3200)
        # Wait for recovered
        self.diagnostic('Wait for recovery', 3)
        self.waitForStateTransition(p, stateRecoverLimit, stateRestoreLoopMode1)
        self.waitForStateTransition(p, stateRestoreLoopMode1, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)

class CaseHitLowLimit(ProtectionCase):
    def runTest(self):
        '''Hitting the low limit.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the negative limit
        self.diagnostic('Jogging negative', 3)
        self.jogNegative(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.25)
        self.verifyFollowingErrorLimit(1, 3200)
        # Wait for recovered
        self.diagnostic('Wait for recovery', 3)
        self.waitForStateTransition(p, stateRecoverLimit, stateRestoreLoopMode1)
        self.waitForStateTransition(p, stateRestoreLoopMode1, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)

class CaseNormalOffOn(ProtectionCase):
    def runTest(self):
        '''Protection switched off and on in the normal state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Disable recovery
        self.diagnostic('Disable recovery', 3)
        self.disable(p)
        self.waitForStateTransition(p, stateNormal, stateNotProtected)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Enable recovery
        self.diagnostic('Enable recovery', 3)
        self.enable(p)
        self.waitForStateTransition(p, stateNotProtected, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseOnLimitOffOn(ProtectionCase):
    def runTest(self):
        '''Protection switched off and on in the on limit state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Disable recovery
        self.diagnostic('Disable recovery', 3)
        self.disable(p)
        self.waitForStateTransition(p, stateOnLimit, stateNotProtected)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Move off the limit
        self.diagnostic('Move off the limit', 3)
        self.moveTo(p, 2)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Enable recovery
        self.diagnostic('Enable recovery', 3)
        self.enable(p)
        self.waitForStateTransition(p, stateNotProtected, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Make sure it stays in the normal state
        self.diagnostic('Check state remains normal', 3)
        self.sleep(3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseRecoverLimitOffOn(ProtectionCase):
    def runTest(self):
        '''Protection switched off and on in the on recover state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.25)
        self.verifyFollowingErrorLimit(1, 3200)
        # Disable recovery
        self.diagnostic('Disable recovery', 3)
        self.disable(p)
        self.waitForStateTransition(p, stateRecoverLimit, stateRestoreLoopMode2)
        self.waitForStateTransition(p, stateRestoreLoopMode2, stateNotProtected)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        # Move off the limit
        self.diagnostic('Move off the limit', 3)
        self.moveTo(p, 2)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Enable recovery
        self.diagnostic('Enable recovery', 3)
        self.enable(p)
        self.waitForStateTransition(p, stateNotProtected, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Make sure it stays in the normal state
        self.diagnostic('Check state remains normal', 3)
        self.sleep(3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseLockOut(ProtectionCase):
    def runTest(self):
        '''Time out of recovery move.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.setRecoveryVelocity(p, 0.0)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.0)
        self.verifyFollowingErrorLimit(1, 3200)
        # Wait for lock out
        self.diagnostic('Wait for lock out', 3)
        self.waitForStateTransition(p, stateRecoverLimit, stateLockOut)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        self.setRecoveryVelocity(p, 0.25)
        # Force exit from lock out
        self.diagnostic('Force exit from lock out', 3)
        self.forceHighLimitClear(1)
        self.waitForStateTransition(p, stateLockOut, stateRestoreLoopMode1)
        self.waitForStateTransition(p, stateRestoreLoopMode1, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Move away from the forced limit
        self.diagnostic('Move away from forced limit', 3)
        self.moveTo(p, 2)
        self.verifyState(p, stateNormal)
        
class CaseLockOutOffOn(ProtectionCase):
    def runTest(self):
        '''Time out of recovery move.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.setRecoveryVelocity(p, 0.0)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.0)
        self.verifyFollowingErrorLimit(1, 3200)
        # Wait for lock out
        self.diagnostic('Wait for lock out', 3)
        self.waitForStateTransition(p, stateRecoverLimit, stateLockOut)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        self.setRecoveryVelocity(p, 0.25)
        # Disable recovery
        self.diagnostic('Disable recovery', 3)
        self.disable(p)
        self.waitForStateTransition(p, stateLockOut, stateRestoreLoopMode2)
        self.waitForStateTransition(p, stateRestoreLoopMode2, stateNotProtected)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        # Move off the limit
        self.diagnostic('Move off the limit', 3)
        self.moveTo(p, 2)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Enable recovery
        self.diagnostic('Enable recovery', 3)
        self.enable(p)
        self.waitForStateTransition(p, stateNotProtected, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Make sure it stays in the normal state
        self.diagnostic('Check state remains normal', 3)
        self.sleep(3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseNormalHoming(ProtectionCase):
    def runTest(self):
        '''Auto-homing in the normal state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Activate homing
        self.diagnostic('Activate homing', 3)
        self.activateHoming(1)
        self.waitForStateTransition(p, stateNormal, stateHoming)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Deactivate homing
        self.diagnostic('Deactivate homing', 3)
        self.deactivateHoming(1)
        self.waitForStateTransition(p, stateHoming, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseOnLimitHoming(ProtectionCase):
    def runTest(self):
        '''Auto-homing in the on limit state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Activate homing
        self.diagnostic('Activate homing', 3)
        self.activateHoming(1)
        self.waitForStateTransition(p, stateOnLimit, stateHoming)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Move off the limit
        self.diagnostic('Move off the limit', 3)
        self.moveTo(p, 2)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Deactivate homing
        self.diagnostic('Deactivate homing', 3)
        self.deactivateHoming(1)
        self.waitForStateTransition(p, stateHoming, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseRecoverLimitHoming(ProtectionCase):
    def runTest(self):
        '''Auto-homing in the lock out state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.25)
        self.verifyFollowingErrorLimit(1, 3200)
        # Activate homing
        self.diagnostic('Activate homing', 3)
        self.activateHoming(1)
        self.waitForStateTransition(p, stateRecoverLimit, stateRestoreLoopMode3)
        self.waitForStateTransition(p, stateRestoreLoopMode3, stateHoming)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Move off the limit
        self.diagnostic('Move off the limit', 3)
        self.moveTo(p, 2)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Deactivate homing
        self.diagnostic('Deactivate homing', 3)
        self.deactivateHoming(1)
        self.waitForStateTransition(p, stateHoming, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseLockOutHoming(ProtectionCase):
    def runTest(self):
        '''Auto-homing in the recover limit state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.setRecoveryVelocity(p, 0.0)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.0)
        self.verifyFollowingErrorLimit(1, 3200)
        # Wait for lock out
        self.diagnostic('Wait for lock out', 3)
        self.waitForStateTransition(p, stateRecoverLimit, stateLockOut)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        self.setRecoveryVelocity(p, 0.25)
        # Activate homing
        self.diagnostic('Activate homing', 3)
        self.activateHoming(1)
        self.waitForStateTransition(p, stateLockOut, stateRestoreLoopMode3)
        self.waitForStateTransition(p, stateRestoreLoopMode3, stateHoming)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Move off the limit
        self.diagnostic('Move off the limit', 3)
        self.moveTo(p, 2)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Deactivate homing
        self.diagnostic('Deactivate homing', 3)
        self.deactivateHoming(1)
        self.waitForStateTransition(p, stateHoming, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseNormalEncoderLoss(ProtectionCase):
    def runTest(self):
        '''Encoder loss in the normal state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Assert encoder loss
        self.diagnostic('Assert encoder loss', 3)
        self.setEncoderLoss(1, 0)
        self.waitForStateTransition(p, stateNormal, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        # Recover
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateEncoderLoss, stateNormal)
        self.waitForStateTransition(p, stateNormal, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        # Deassert encoder loss
        self.diagnostic('Deassert encoder loss', 3)
        self.setEncoderLoss(1, 1)
        self.sleep(10)
        self.verifyState(p, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        # Recover
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateEncoderLoss, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseHomingEncoderLoss(ProtectionCase):
    def runTest(self):
        '''Encoder loss in the homing state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Activate homing
        self.diagnostic('Activate homing', 3)
        self.activateHoming(1)
        self.waitForStateTransition(p, stateNormal, stateHoming)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Assert encoder loss
        self.diagnostic('Assert encoder loss', 3)
        self.setEncoderLoss(1, 0)
        self.waitForStateTransition(p, stateHoming, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        # Deactivate homing
        self.diagnostic('Deactivate homing', 3)
        self.deactivateHoming(1)
        self.sleep(10)
        self.verifyState(p, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        # Deassert encoder loss
        self.diagnostic('Deassert encoder loss', 3)
        self.setEncoderLoss(1, 1)
        self.sleep(10)
        self.verifyState(p, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        # Recover
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateEncoderLoss, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseEncoderLossOffOn(ProtectionCase):
    def runTest(self):
        '''Protection off and on in the encoder loss state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Assert encoder loss
        self.diagnostic('Assert encoder loss', 3)
        self.setEncoderLoss(1, 0)
        self.waitForStateTransition(p, stateNormal, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        # Deassert encoder loss
        self.diagnostic('Deassert encoder loss', 3)
        self.setEncoderLoss(1, 1)
        self.sleep(10)
        self.verifyState(p, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        # Switch protection off
        self.diagnostic('Switching protection off', 3)
        self.disable(p)
        self.waitForStateTransition(p, stateEncoderLoss, stateNotProtected)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Switch protection on
        self.diagnostic('Switching protection on', 3)
        self.enable(p)
        self.waitForStateTransition(p, stateNotProtected, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)

class CaseOnLimitEncoderLoss(ProtectionCase):
    def runTest(self):
        '''Encoder loss in the on limit state.'''
        self.diagnostic('Moving to start position', 3)
        self.moveTo(p, 1)
        # Verify initial state
        self.diagnostic('Verify initial state', 3)
        self.verifyState(p, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Jog to the positive limit
        self.diagnostic('Jogging positive', 3)
        self.jogPositive(p)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Assert encoder loss
        self.diagnostic('Assert encoder loss', 3)
        self.setEncoderLoss(1, 0)
        self.waitForStateTransition(p, stateOnLimit, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)
        # Deassert encoder loss
        self.diagnostic('Deassert encoder loss', 3)
        self.setEncoderLoss(1, 1)
        self.sleep(10)
        self.verifyState(p, stateEncoderLoss)
        self.verifyFollowingErrorLimit(1, 1)
        # Recover
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateEncoderLoss, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        # Wait for the return to the on limit state
        self.diagnostic('Return to on limit', 3)
        self.waitForStateTransition(p, stateNormal, stateOnLimit)
        self.verifyFollowingErrorLimit(1, 1)
        self.verifyKilled(1)
        self.verifyVelocity(1, 0.5)
        # Enter the recovery state
        self.diagnostic('Initiate recovery', 3)
        self.recover(p)
        self.waitForStateTransition(p, stateOnLimit, stateRecoverLimit)
        self.verifyVelocity(1, 0.25)
        self.verifyFollowingErrorLimit(1, 3200)
        # Wait for recovered
        self.diagnostic('Wait for recovery', 3)
        self.waitForStateTransition(p, stateRecoverLimit, stateRestoreLoopMode1)
        self.waitForStateTransition(p, stateRestoreLoopMode1, stateNormal)
        self.verifyFollowingErrorLimit(1, 3200)
        self.verifyVelocity(1, 0.5)
        self.verifyKilled(1)


################################################
# Main entry point

if __name__ == "__main__":
    # Create and run the test sequence
    ProtectionTestSuite()

    
