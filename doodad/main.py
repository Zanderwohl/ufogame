import tomli
from machine import Pin

led = Pin(25, Pin.OUT)
led.off()

toml_dict = {}
try:
    with open("config.toml", "rb") as f:
        toml_dict = tomli.load(f)
except tomli.TOMLDecodeError:
    print("Could not load config.toml")
    exit(1)

id = toml_dict["id"]
print(f"My ID is {id:x}!")
