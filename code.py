"""
Simple text script for Adafruit 2.13" 212x104 tri-color display
Supported products:
  * Adafruit 2.13" Tri-Color Display Breakout
  * Adafruit 2.13" Tri-Color Display FeatherWing
    https://www.adafruit.com/product/4086 (breakout) or
    https://www.adafruit.com/product/4128 (FeatherWing)

  This program requires the adafruit_il0398 library and the
  adafruit_display_text library in the CIRCUITPY /lib folder
  for CircuitPython 5.0 and above which has displayio support.
"""

import alarm
import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn

import displayio
import adafruit_il0398
import terminalio
from adafruit_display_text import label

from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.polygon import Polygon

from adafruit_datetime import datetime, date

import adafruit_sdcard
import storage

import ipaddress
import ssl
import wifi
import socketpool
import json
import adafruit_requests


spi = board.SPI()  # Uses SCK and MOSI
sd_cs = DigitalInOut(board.D6)

#sdcard = adafruit_sdcard.SDCard(spi, sd_cs)
#vfs = storage.VfsFat(sdcard)
#storage.mount(vfs, "/sd")

# Get wifi details and more from a secrets.py file
try:
	from secrets import secrets
except ImportError:
	print("WiFi secrets are kept in secrets.py, please add them there!")
	raise

binData = ""
binUrl = "https://guernsey.isl-fusion.com/api/address/%s"%secrets["address"]
nextDate = datetime(2000, 1, 1)
curDate = datetime(2000, 1, 1)
timeUrl = "http://worldtimeapi.org/api/timezone/Europe/London"

binTypes = {
	"6xrmSxaifN5h3LXb" : {
		"name" : "Waste",
		"icon" : "/img/waste.bmp"
	},
	"xjVCX1y84wps6gTw" : {
		"name" : "Waste",
		"icon" : "/img/waste.bmp"
	},
	"FBWme5sNe7evoDY5" : {
		"name" : "Plastic",
		"icon" : "/img/blue.bmp"
	},
	"a7TGSliXHW6r4hml" : {
		"name" : "Cardboard",
		"icon" : "/img/clear.bmp"
	},
	"fGPdmGlQV2dflSsG" : {
		"name" : "Glass",
		"icon" : "/img/glass.bmp"
	},
	"kGWWDB87GxV4bj6C" : {
		"name" : "Food",
		"icon" : "/img/food.bmp"
	}
}

BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300

# Change text colors, choose from the following values:
# BLACK, RED, WHITE
FOREGROUND_COLOR = BLACK
BACKGROUND_COLOR = WHITE

# Initialise the power pin and power the screen
epd_pwr = DigitalInOut(board.IO33)
epd_pwr.direction = Direction.OUTPUT
epd_pwr.value = True

# Gets the battery percentage
batPin =  AnalogIn(board.VBAT)
voltage = (batPin.value*2)/10000
print("Battery: " + str(voltage))

# Then connects to said WiFi
print("Connecting to %s"%secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!"%secrets["ssid"])
print("My IP address is", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())


binResponse = requests.get(binUrl)
if binResponse.status_code == 200:
	binData = binResponse.json()
else:
	print(binResponse.status_code)

if binData["address"]:
	dates = sorted(list(binData["servicedates"].keys()))
	print(dates)
	nextDate = datetime.fromisoformat(binData["servicedates"][dates[0]]["date"])
	print(binData["servicedates"][dates[0]]["date"])
	print(str(nextDate))

else:
    print("Invalid address ID!")


# Get the current date from timeUrl
timeResponse = requests.get(timeUrl)
if timeResponse.status_code == 200:
	timeData = timeResponse.json()
else:
	print(timeResponse.status_code)

if timeData["abbreviation"]:
	curDate = datetime.fromisoformat(timeData["datetime"])
	print(timeData["datetime"])
	print(str(curDate))

else:
    print("Invalid time address!")


# Used to ensure the display is free in CircuitPython
displayio.release_displays()

# Define the pins needed for display use
# This pinout is for a Tiny2S and may be different for other boards
epd_cs = board.IO14
epd_dc = board.IO9
epd_reset = board.IO8
epd_busy = board.IO38

# Create the displayio connection to the display pins
display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs,
                                 reset=epd_reset, baudrate=1000000)
time.sleep(1)  # Wait a bit

# Create the display object - the third color is red (0xff0000)
display = adafruit_il0398.IL0398(display_bus, width=DISPLAY_WIDTH,
                                 height=DISPLAY_HEIGHT,
                                 rotation=0, busy_pin=epd_busy,
                                 highlight_color=RED)

# Create a display group for our screen objects
g = displayio.Group()


# Set a background
background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
# Map colors in a palette
palette = displayio.Palette(1)
palette[0] = BACKGROUND_COLOR

# Create a Tilegrid with the background and put in the displayio group
t = displayio.TileGrid(background_bitmap, pixel_shader=palette)
g.append(t)

# Create the UI
# Black (or red) bar on the left
col = RED if nextDate.day == curDate.day else BLACK
g.append(Rect(0, 0, 50, DISPLAY_HEIGHT, fill=col))

# ~~~Battery indicator~~~
# Create the outline
g.append(RoundRect(336, 4, 56, 27, 1, fill=None, outline=BLACK, stroke=5))
g.append(Rect(390, 13, 6, 9, fill=BLACK))

# Create the little bars
if voltage <= 3.71:
	g.append(Rect(342, 10, 5, 15, fill=RED))

elif voltage > 3.71:
	g.append(Rect(342, 10, 10, 15, fill=BLACK))

	if voltage >= 3.79:
		g.append(Rect(353, 10, 10, 15, fill=BLACK))
	
	if voltage >= 3.84:
		g.append(Rect(364, 10, 10, 15, fill=BLACK))

	if voltage >= 3.98:
		g.append(Rect(375, 10, 10, 15, fill=BLACK))



# Create a group for the date label
dateGroup = displayio.Group(scale=4, x=20, y=290)
dateText = str(nextDate.day)
dateTextArea = label.Label(terminalio.FONT, text=dateText, color=WHITE, label_direction="UPR")
dateGroup.append(dateTextArea)  # Add this text to the text group
g.append(dateGroup)

# ~~~Bin display~~~
for j in range(len(binData["servicedates"][dates[0]]["services"])):
	try:
		service = binData["servicedates"][dates[0]]["services"][str(j)]
	except:
		service = binData["servicedates"][dates[0]]["services"][j]
	
	# General waste
	if "6xrmSxaifN5h3LXb" in service:
		bitmapGroup = displayio.Group(scale=1, x=53, y=114)
		bitmap = displayio.OnDiskBitmap(binTypes["6xrmSxaifN5h3LXb"]["icon"])
		bitmapGroup.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))
		g.append(bitmapGroup)
		print("Waste")
	
	# General waste
	if "xjVCX1y84wps6gTw" in service:
		bitmapGroup = displayio.Group(scale=1, x=53, y=114)
		bitmap = displayio.OnDiskBitmap(binTypes["xjVCX1y84wps6gTw"]["icon"])
		bitmapGroup.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))
		g.append(bitmapGroup)
		print("Waste")
	
	# Plastic
	if "FBWme5sNe7evoDY5" in service:
		bitmapGroup = displayio.Group(scale=1, x=139, y=114)
		bitmap = displayio.OnDiskBitmap(binTypes["FBWme5sNe7evoDY5"]["icon"])
		bitmapGroup.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))
		g.append(bitmapGroup)
		print("Plastic")
	
	# Cardboard
	if "a7TGSliXHW6r4hml" in service:
		bitmapGroup = displayio.Group(scale=1, x=139, y=114)
		bitmap = displayio.OnDiskBitmap(binTypes["a7TGSliXHW6r4hml"]["icon"])
		bitmapGroup.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))
		g.append(bitmapGroup)
		print("Cardboard")
	
	# Food
	if "kGWWDB87GxV4bj6C" in service:
		bitmapGroup = displayio.Group(scale=1, x=225, y=114)
		bitmap = displayio.OnDiskBitmap(binTypes["kGWWDB87GxV4bj6C"]["icon"])
		bitmapGroup.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))
		g.append(bitmapGroup)
		print("Food")
	
	# Glass
	if "fGPdmGlQV2dflSsG" in service:
		bitmapGroup = displayio.Group(scale=1, x=311, y=114)
		bitmap = displayio.OnDiskBitmap(binTypes["fGPdmGlQV2dflSsG"]["icon"])
		bitmapGroup.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))
		g.append(bitmapGroup)
		print("Glass")

		#print(binData["services"][service]["name"])


# Then display the group
display.show(g)

# Refresh the display to have everything show on the display
# NOTE: Do not refresh eInk displays more often than 180 seconds!
display.refresh()

# Give it a few seconds to let it finish refreshing the display
#while display.busy() == True:
#	print("busy!")
#	time.sleep(1)

time.sleep(30)

# Close the web requests nicely :)
binResponse.close()
binResponse = None

timeResponse.close()
timeResponse = None

# Preparing to go to sleep :)
# Turns off the power to the screen
print("power off")
epd_pwr.value = False

# Disables the power to the LED (saves a bit of juice ;))
#ledPwr = DigitalInOut(board.IO2)
#ledPwr.direction = Direction.OUTPUT
#ledPwr.value = False

# Create a an alarm that will trigger 12 hours from now.
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 43200)
# Exit the program, and then deep sleep until the alarm wakes us.
alarm.exit_and_deep_sleep_until_alarms(time_alarm)