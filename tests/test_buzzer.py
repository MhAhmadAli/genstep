from gpiozero import Buzzer

bz = Buzzer(8)
bz.on()

bz.beep(on_time=1, off_time=1, n=5, background=False)
