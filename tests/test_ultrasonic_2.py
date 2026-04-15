from gpiozero import DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

factory = PiGPIOFactory()
# Sensor 2 (middle / front-facing): Trig 13, Echo 19
sensor = DistanceSensor(echo=19, trigger=13, max_distance=4, pin_factory=factory)

while True:
    print(f"Distance: {sensor.distance * 100:.2f} cm")
    sleep(0.5)
