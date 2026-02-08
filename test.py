import lcm
import sys 
import random
import time

from pathlib import Path
home = str(Path.home())

sys.path.insert(0, home + '/agv1/agv1msg/')
from gps_t import *
from state_t import *



class Timer():
    def __init__(self, period):
        self.period = period
        self.next = time.time()+ self.period
    
    def timeout(self):
        if(time.time()> self.next):
            self.next += self.period
            return True

        return False 

class Rate():
    def __init__(self, hz):
        self.period = 1/hz
        self.next_time = time.time()+self.period
    
    def sleep(self):
        remaining = self.next_time - time.time()
        if(remaining>0):
            time.sleep(remaining)
        self.next_time += self.period



lc=lcm.LCM()
dh =0.01
rate = Rate(100)
while True:

    gps = gps_t()

    gps.fix = 4
    gps.latitude = 123456
    gps.longitude = 456786
    gps.altitude = 0

    gps.heading = 147
    gps.ground_speed = 2.25 + random.random()
    
    state = state_t()

    
    lc.publish("gps", gps.encode())
    lc.publish("state", state.encode())
    rate.sleep()
    