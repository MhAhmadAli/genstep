from gpiozero import DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

factory = PiGPIOFactory()
# Sensor 1 (bottom / downward-facing): Trig 18, Echo 25
sensor = DistanceSensor(echo=25, trigger=18, max_distance=4, pin_factory=factory)

while True:
    print(f"Distance: {sensor.distance * 100:.2f} cm")
    sleep(0.5)
