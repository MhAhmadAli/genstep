from gpiozero import DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

factory = PiGPIOFactory()
sensor = DistanceSensor(echo=23, trigger=24, max_distance=4, pin_factory=factory)

while True:
    print(f"Distance: {sensor.distance * 100:.2f} cm")
    sleep(0.5)
