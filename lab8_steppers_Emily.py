# stepper_class_shiftregister_multiprocessing.py
#
# Stepper class
#
# Because only one motor action is allowed at a time, multithreading could be
# used instead of multiprocessing. However, the GIL makes the motor process run 
# too slowly on the Pi Zero, so multiprocessing is needed.

import time
import multiprocessing
from shifter import Shifter   # our custom Shifter class
import math
import RPi.GPIO as GPIO
class Stepper:
    """
    Supports operation of an arbitrary number of stepper motors using
    one or more shift registers.
  
    A class attribute (shifter_outputs) keeps track of all
    shift register output values for all motors.  In addition to
    simplifying sequential control of multiple motors, this schema also
    makes simultaneous operation of multiple motors possible.
   
    Motor instantiation sequence is inverted from the shift register outputs.
    For example, in the case of 2 motors, the 2nd motor must be connected
    with the first set of shift register outputs (Qa-Qd), and the 1st motor
    with the second set of outputs (Qe-Qh). This is because the MSB of
    the register is associated with Qa, and the LSB with Qh (look at the code
    to see why this makes sense).
 
    An instance attribute (shifter_bit_start) tracks the bit position
    in the shift register where the 4 control bits for each motor
    begin.
    """

    # Class attributes:
    num_steppers = 0      # track number of Steppers instantiated
    shifter_outputs = 0   # track shift register outputs for all motors
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 2500          # delay between motor steps [us]
    steps_per_degree = 4096/360     # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter            # shift register
        self.angle = multiprocessing.Value('d', 0.0)  # current output shaft angle
        self.step_state = 0         # track position in sequence
        self.shifter_bit_start = 4*Stepper.num_steppers  # starting bit position
        self.lock = lock            # multiprocessing lock

        Stepper.num_steppers += 1   # increment the instance count

    # Signum function:
    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8      # ensure result stays in [0,7]
        
        # 4-bit coil pattern for this motor
        mask   = 0b1111 << self.shifter_bit_start
        pattern = Stepper.seq[self.step_state] << self.shifter_bit_start

        # Clear existing bits only for this motor
        Stepper.shifter_outputs &= ~mask
        # Set this motor's new coil pattern
        Stepper.shifter_outputs |= pattern

        self.s.shiftByte(Stepper.shifter_outputs)

        # update shared angle
        with self.angle.get_lock():
            self.angle.value += dir / Stepper.steps_per_degree
            self.angle.value %= 360
            print(self.angle.value)

    # Move relative angle from current position:
    def __rotate(self, delta):
        self.lock.acquire()                 # wait until the lock is available
        numSteps = int(Stepper.steps_per_degree * abs(delta))    # find the right # of steps
        dir = self.__sgn(delta)        # find the direction (+/-1)
        for s in range(numSteps):      # take the steps
            self.__step(dir)
            time.sleep(Stepper.delay/1e6)
        self.lock.release()

    # Move relative angle from current position:
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()

    # Move to an absolute angle taking the shortest possible path:
    def goAngle(self, tarAngle):
        # read angle safely
        with self.angle.get_lock():
            curAngle = self.angle.value

        # shortest path math: force into [-180, 180]
        delta = ((tarAngle - curAngle + 540) % 360) - 180

        p = multiprocessing.Process(target=self.__rotate, args=(delta,))
        p.start()
    #moves the motor in the XZ when given our angular position with respect to the center and zero and a targets angular position with respect to the center and zero     
    def goAngleXZ(self, targetAngle,selfPosAngle):
        alpha=.5*(2*math.pi-abs(targetAngle-selfPosAngle))
        if (xyAngle-selfPosAngle <0):
            alpha=-alpha
        self.goAngle(alpha)
   #moves the motor in the Y when given our angular position with respect to the center and zero and a targets angular position with respect to th ecenter and zero and circle radius our own height and target height     
    def goAngleY(self, targetAngle, selfPosAngle, selfHeight, radius,targetHeight):
        C=math.sqrt((2*radius^2)-(2*radius^2)*math.cos(targetAngle-selfPosAngle))
        phi=math.atan((targtHeight-selfHeight)/C)
        self.goAngle(phi)
    
    # Set the motor zero point
    def zero(self):
        with self.angle.get_lock():
            self.angle.value = 0.0


# Example use:

if __name__ == '__main__':

    s = Shifter(data=14,latch=15,clock=18)   # set up Shifter

    # Use multiprocessing.Lock() to prevent motors from trying to 
    # execute multiple operations at the same time:
    lock1 = multiprocessing.Lock()
    #lock2 = multiprocessing.Lock()

    # Instantiate 2 Steppers:
    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock1)


    GPIO.setup(23, GPIO.OUT, initial=0)

    GPIO.output(23,1)
    time.sleep(3)
    GPIO.output(23,0)

    
    # Zero the motors:
    m1.zero()
    m2.zero()

    # Move as desired, with eacg step occuring as soon as the previous 
    # step ends:
    m1.goangle(90)
    #print("moved to 180 degrees")
    #m1.rotate(45)
    #print("moved to 45 degrees")
    m1.goangle(45)
    #print("moved to 0 degrees")
    m1.goangle(0)

    # If separate multiprocessing.lock objects are used, the second motor
    # will run in parallel with the first motor:
    m2.goangle(90)
   # m2.rotate(-45)
    m2.goangle(45)
    m2.goangle(0)

    
    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
    try:
        while True:
            pass
    except:
        print('\nend')

