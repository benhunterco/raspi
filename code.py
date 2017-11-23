#!/usr/bin/python
from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor
import time
import atexit
import threading
import RPi.GPIO as GPIO
import time
import os
import glob

# create a default object, no changes to I2C address or frequency
mh = Adafruit_MotorHAT(addr = 0x60)

# create empty threads (these will hold the stepper 1 and 2 threads)
st1 = threading.Thread()
#might not be neededst2 = threading.Thread()




# light sensor

__author__ = 'Gus (Adapted from Adafruit)'
__license__ = "GPL"
__maintainer__ = "pimylifeup.com"

GPIO.setmode(GPIO.BOARD)

#define the pin that goes to the circuit
pin_to_circuit = 11

def rc_time (pin_to_circuit):
    count = 0

    #Output on the pin for
    GPIO.setup(pin_to_circuit, GPIO.OUT)
    GPIO.output(pin_to_circuit, GPIO.LOW)
    time.sleep(0.1)

    #Change the pin back to input
    GPIO.setup(pin_to_circuit, GPIO.IN)

    #Count until the pin goes high
    while (GPIO.input(pin_to_circuit) == GPIO.LOW):
        count += 1

    return count


# temperatrue sensor

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_f









# recommended for auto-disabling motors on shutdown!
def turnOffMotors():
    mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)

atexit.register(turnOffMotors)

myStepper1 = mh.getStepper(50, 2)      # 200 steps/rev, motor port #2
myStepper1.setSpeed(60)          # 30 RPM


stepstyles = [Adafruit_MotorHAT.SINGLE, Adafruit_MotorHAT.DOUBLE, Adafruit_MotorHAT.INTERLEAVE, Adafruit_MotorHAT.MICROSTEP]

def stepper_worker(stepper, numsteps, direction, style):
    #print("Steppin!")
    stepper.step(numsteps, direction, style)
    #print("Done")

key = True
count = 0
print("verifying direction of motor")
myStepper1.step(20, Adafruit_MotorHAT.FORWARD, Adafruit_MotorHAT.SINGLE)
direction = raw_input("open or close? ")
myStepper1.step(20, Adafruit_MotorHAT.BACKWARD, Adafruit_MotorHAT.SINGLE)
if (direction == "close"):
    openDir = Adafruit_MotorHAT.BACKWARD
    closeDir = Adafruit_MotorHAT.FORWARD
else:
    openDir = Adafruit_MotorHAT.FORWARD
    closeDir = Adafruit_MotorHAT.BACKWARD

while (key):
    myStepper1.step(20, openDir, Adafruit_MotorHAT.SINGLE)
    value = raw_input("All the way open? (yes/no)")
    if value == "yes":
        key = False
    else:
        count += 20

position = count
while (True):
    if not st1.isAlive():
        light = rc_time(pin_to_circuit)
        temp = read_temp()
        #here we decide how to move our motor
        #if the temperature is too hot or too cold, we will close or open.
        #if it is in between, we prioritize light.
        steps = 0
        moveDir = openDir
        if temp > 80:
            #in this case, we fully close. as in step close position steps
            steps = position
            moveDir = closeDir
        elif temp < 60:
            #in this case, it is quite chilly, open the blinds
            steps = count - position
            moveDir = openDir

        else:
            if temp > 70:
                tolerance = 500 * ((temp - 70) / 10)
                print(tolerance)
                if light > (900 + tolerance):
                    #in this case, it is too dark for the given temperature
                    #so we open up
                    if (count - position) < 25:
                        steps = count - position
                        print("hot special-dark")
                    else:
                        steps = 25
                        print("step 25, hot-dark")
                    moveDir = openDir
                elif light < 900:
                    if position < 25:
                        steps = position
                        print("hot special-bright")
                    else:
                        steps = 25
                        print("step 25, hot-bright")
                    moveDir = closeDir
                else:
                    #we are at a tolerable light here, don't move
                    steps = 0
                    moveDir = openDir
            elif temp < 70:
                tolerance = 500 * ((70 - temp) / 10)
                print(tolerance)
                if light < (900 - tolerance):
                    if position < 25:
                        steps = position
                        print("cold special")
                    else:
                        steps = 25
                        print("step 25, cold")
                    moveDir = closeDir
                elif light > 900:
                    if (count - position) < 25:
                        steps = count - position
                        print("cold special-dark")
                    else:
                        steps = 25
                        print("step 25, cold-dark")
                    moveDir = openDir
                else:
                    steps = 0
                    moveDir = closeDir
            else:
                #this is at exactly 70 degrees, we decide direction purely on light
                if light > 900:
                    if (count - position) < 25:
                        steps = count - position
                    else:
                        steps = 25
                    moveDir = openDir
                elif light < 900:
                    if position < 25:
                        steps = position
                    else:
                        steps = 25
                    moveDir = closeDir
                else:
                    #the ultimate temperature
                    steps = 0
                    moveDir = openDir
        if moveDir == closeDir:
            position -= steps
        else:
            position += steps
        print(temp)
        print(light)
        print("Moving: " , moveDir , ", Steps: " , steps)
        st1 = threading.Thread(target=stepper_worker, args=(myStepper1, steps, moveDir, Adafruit_MotorHAT.SINGLE,))
        st1.start()

    time.sleep(0.1)  # Small delay to stop from constantly polling threads (see: https://forums.adafruit.com/viewtopic.php?f=50&t=104354&p=562733#p562733)
