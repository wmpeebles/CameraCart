import multiprocessing
import time

class MovementSensor:
    def __init__(self):
        self.moved = True

    def toggle_moved_every_10_seconds(self, queue):
        x = 0
        while x <= 20:
            print(x)
            if x <= 10:
                self.moved = True
                x += 1
            elif x < 20:
                self.moved = False
                x += 1
            elif x == 20:
                self.moved = False
                x = 0
            queue.put(self.moved)
            time.sleep(1)

movement_sensor = MovementSensor()

class Camera:
    def __init__(self, name):
        self.name = name
        self.lock = False

    def trigger(self):
        self.lock = True
        time.sleep(2)
        print(f'Camera {self.name} was triggered.')
        self.lock = False

    def trigger_loop(self, queue):
        while True:
            if self.lock == False:
                if queue.get():
                    process = multiprocessing.Process(target=self.trigger)
                    process.start()
                    # Wait until process is done
                    process.join()

camera0 = Camera(name='One')
camera1 = Camera(name='Two')


def collect_photos_as_fast_as_possible():

    queue = multiprocessing.Queue()
    p2 = multiprocessing.Process(target=movement_sensor.toggle_moved_every_10_seconds, args=(queue,))
    p2.start()

    p0 = multiprocessing.Process(target=camera0.trigger_loop, args=(queue,))
    p0.start()


    p1 = multiprocessing.Process(target=camera1.trigger_loop, args=(queue,))
    p1.start()

    movement_sensor.toggle_moved_every_10_seconds()
    p0.join()
    p1.join()
    p2.join()


while True:
    collect_photos_as_fast_as_possible()