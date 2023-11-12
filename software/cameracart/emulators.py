import time
import random

class GPIOSimulator:
    def __init__(self):
        self.BCM = None
        self.IN = None
        self.PUD_DOWN = None

    def setmode(self, input1):
        pass

    def setup(self, input1=None, input2=None, pull_up_down=None):
        pass

    @staticmethod
    def input(pin):
        time.sleep(.4)
        random_choice = random.choice([True, False])
        return random_choice

class GPSSimulator:
    def __init__(self):
        pass

    class GPS():
        def __init__(self, arg, **kwargs):
            pass

        def send_command(self, bytes):
            if bytes == b'PMTK220, 1000':
                pass

        def update(self):
            print('GPS')

class SerialSimulatior:
    def __init__(self):
        pass

    class Serial():
        def __init__(self, arg, **kwargs):
            pass