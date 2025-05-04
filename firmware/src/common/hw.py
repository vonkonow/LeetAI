import config.config as config
import board # input output
import digitalio # input output config
import analogio
import busio # SPI for display
import displayio # display module
from adafruit_st7735r import ST7735R # display driver
import adafruit_imageload           # import .bmp sprite map
import neopixel
import bitbangio                       	                          # type: ignore

if config.HW_VERSION == 1.0:
    AN1 = analogio.AnalogIn(config.AN1_PIN)
    AN2 = analogio.AnalogIn(config.AN2_PIN)
    HYSTERESS = 10
    wheel1_old = int(AN1.value/256)
    wheel1_edge = True
    wheel2_old = int(AN2.value/256)
    wheel2_edge = True
    prev = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    pressed=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

if config.HW_VERSION == 1.1:
    i2c0 = bitbangio.I2C(config.SCL0_PIN, config.SDA0_PIN)  # scl, sda
    wheel0_old = 0
    i2c1 = bitbangio.I2C(config.SCL1_PIN, config.SDA1_PIN)  # scl, sda
    wheel1_old = 0
    prev = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    pressed=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]   

# Define column pins
col=[]
col_pin=config.COL_PINS
for b in col_pin:
    col.append(digitalio.DigitalInOut(b))
    col[-1].direction = digitalio.Direction.INPUT
    col[-1].pull=digitalio.Pull.UP

row0 = digitalio.DigitalInOut(config.ROW0_PIN)
row1 = digitalio.DigitalInOut(config.ROW1_PIN)
row0.pull = digitalio.Pull.UP
row1.pull = digitalio.Pull.UP
row0.direction = digitalio.Direction.OUTPUT
row0.value = False
row1.direction = digitalio.Direction.OUTPUT
row1.value = False

def check_keys():
    row1.direction = digitalio.Direction.OUTPUT
    row0.direction = digitalio.Direction.INPUT
    for i in range(config.KEY_COL):
        if col[i].value == 0:
            pressed[i] = 1
            prev[i] = 1
        else:
            pressed[i] = 0
            prev[i] = 0
    row0.direction = digitalio.Direction.OUTPUT
    row1.direction = digitalio.Direction.INPUT
    for i in range(config.KEY_COL):
        if col[i].value == 0:
            pressed[config.KEY_COL+i] = 1
            prev[config.KEY_COL+i] = 1
        else:
            pressed[config.KEY_COL+i] = 0
            prev[config.KEY_COL+i] = 0
    return(pressed)

# new key pressed since last?
def key_new(pos):
    if pos < config.KEY_COL:
        row1.direction = digitalio.Direction.OUTPUT
        row0.direction = digitalio.Direction.INPUT
        row = pos
    else:       
        row0.direction = digitalio.Direction.OUTPUT
        row1.direction = digitalio.Direction.INPUT
        row = pos - config.KEY_COL
    if not col[row].value and prev[pos] == 0:
        prev[pos] = 1 
        return True
    if col[row].value:
        prev[pos] = 0
    return False

# new key changed since last? 
def key_change(pos):
    if pos < config.KEY_COL:
        row1.direction = digitalio.Direction.OUTPUT
        row0.direction = digitalio.Direction.INPUT
        row = pos
    else:       
        row0.direction = digitalio.Direction.OUTPUT
        row1.direction = digitalio.Direction.INPUT
        row = pos - config.KEY_COL
    val = not col[row].value
    new = True if col[row].value == prev[pos] else False
    prev[pos] = not col[row].value
    return((val, new))


def get_enc1():
    result = bytearray(2)
    while not i2c1.try_lock():
        pass
    try:
        i2c1.writeto_then_readfrom(0x36, bytes([0x0c]), result)
    finally:
        i2c1.unlock()
        return(result)
    
def get_enc0():
    result = bytearray(2)
    while not i2c0.try_lock():
        pass
    try:
        i2c0.writeto_then_readfrom(0x36, bytes([0x0c]), result)
    finally:
        i2c0.unlock()
        return(result)
    
# wheel 0 is the lower and wheel 1 is the upper. dist is the hysteress before triggering event.
def check_rotation(wheel, dist):
    global wheel0_old, wheel1_old
    try:
        if wheel == 1:
            wheel_new = int.from_bytes(get_enc1())
            wheel_old = wheel1_old
        else:
            wheel_new = int.from_bytes(get_enc0())
            wheel_old = wheel0_old
        diff = abs(wheel_old - wheel_new)
        # this test is not needed, but no/small rotation is most likely => faster if exit here...
        if diff < dist: 
            return 0 
        
        # test counter clockwise (increased value)
        edge = wheel_old + dist
        if wheel_new > edge and diff < 2048:
            if wheel == 0:
                wheel0_old = wheel_new
            else:
                wheel1_old = wheel_new
            return -1
        elif edge > 4095:
            edge -= 4095
            if wheel_new > edge and wheel_new < 2048:
                if wheel == 0:
                    wheel0_old = wheel_new
                else:
                    wheel1_old = wheel_new
                return -1

        # test clockwise (decreased value)
        edge = wheel_old - dist
        if wheel_new < edge and diff < 2048:
            if wheel == 0:
                wheel0_old = wheel_new
            else:
                wheel1_old = wheel_new
            return 1
        elif edge < 0:
            edge += 4095
            if wheel_new < edge and wheel_new > 2048:
                if wheel == 0:
                    wheel0_old = wheel_new
                else:
                    wheel1_old = wheel_new
                return 1
        return 0
    except Exception as e:
        print("Error in check_rotation:", e)
        # If I2C communication fails, return 0 (no rotation)
        # This prevents the TypeError and allows the system to continue functioning
        return 0

def check_analog_rotation(dir):
    # check if analog wheel has rotated more than the HYSTERESS since last time
    # handles edge case when wheel goes from max to zero (increase edge), or zero to max (decrease edge)
    # dir: 0=wheel1 inc, 1=wheel1 dec, 2=wheel2 inc, 3=wheel2 dec
    global wheel1_old
    global wheel1_edge
    global wheel2_old
    global wheel2_edge
    if dir < 2:
        sample = int(AN1.value/256)
        old = wheel1_old
        edge = wheel1_edge
    else:
        sample = int(AN2.value/256)
        old = wheel2_old
        edge = wheel2_edge

    if sample > (old + HYSTERESS):
        if old > HYSTERESS:
            # print("inc", sample, old)
            if dir < 2:
                wheel1_edge = True
                wheel1_old = sample
            else:
                wheel2_edge = True
                wheel2_old = sample
            if dir == 0 or dir == 2: # increase (ccw)
                return True
        elif edge:
            # print("dec edge", sample, old)
            if dir < 2:
                wheel1_edge = False
                wheel1_old = sample
            else:
                wheel2_edge = False
                wheel2_old = sample
            if dir == 1 or dir == 3: # decrease (cw, edge case)
                return True
        if dir < 2:
            wheel1_old = sample
        else:
            wheel2_old = sample
    if sample < (old - HYSTERESS):
        if old < (205 - HYSTERESS):
            # print("dec", sample, old)
            if dir < 2:
                wheel1_edge = True
                wheel1_old = sample
            else:
                wheel2_edge = True
                wheel2_old = sample
            if dir == 1 or dir == 3: # decr��? (cw)
                return True
        elif edge:
            # print("inc edge", sample, old)
            if dir < 2:
                wheel1_edge = False
                wheel1_old = sample
            else:
                wheel2_edge = False
                wheel2_old = sample
            if dir == 0 or dir == 2: # increase (ccw, edge case)
                return True
        if dir < 2:
            wheel1_old = sample
        else:
            wheel2_old = sample
    return False

num_pixels = config.NEOPIXEL_NUM
pixels = neopixel.NeoPixel(config.NEOPIXEL_PIN, num_pixels, brightness=0.2)


# Setup builtin (blue) LED 
builtinLed = digitalio.DigitalInOut(config.BUILTIN_LED_PIN)     # Builtin LED
builtinLed.direction = digitalio.Direction.OUTPUT   # Set as output

# Define display pins
PICO_PIN = config.PICO_PIN # data
CLK_PIN = config.CLK_PIN # clock
RST_PIN = config.RST_PIN # reset
CS_PIN = config.CS_PIN # chip select
DC_PIN = config.DC_PIN # data/command
BL_PIN = config.BL_PIN # backlight

# Initialize the display
displayio.release_displays()
spi = busio.SPI(clock=CLK_PIN, MOSI=PICO_PIN)
dispWidth = config.DISPLAY_WIDTH
dispHeight = config.DISPLAY_HEIGHT
display_bus = displayio.FourWire(spi, command=DC_PIN, chip_select=CS_PIN, reset=RST_PIN)
display = ST7735R(
    display_bus,
    width=dispWidth,
    height=dispHeight,
    bgr=True,
    rowstart=1, # 0 on some panels...
    colstart=2, # 0 on some panels...
    rotation=270,
    auto_refresh=False
)
bl = digitalio.DigitalInOut(BL_PIN)
bl.direction = digitalio.Direction.OUTPUT
bl.value = True # Turn on backlight

# Create displayIO group to hold all sprites
displayGroup = displayio.Group(scale=1)
#display.show(displayGroup)
display.root_group = displayGroup

class SpriteText:
    font_sheet, bwPalette = adafruit_imageload.load("lib/font.bmp",bitmap=displayio.Bitmap,palette=displayio.Palette)
    def __init__(self, x, y, str):
        self.group = displayio.Group()
        self.group.x = x
        self.group.y = y
        self.str = str
        self.array=[]
        displayGroup.append(self.group)
        for i in range(len(str)):
            self.array.append(displayio.TileGrid(self.font_sheet, pixel_shader=self.bwPalette,width = 1,height = 1,tile_width = 8,tile_height = 8))
            self.group.append(self.array[i])
            self.array[i].x = i * 7
            self.array[i].y = 0
            self.array[i][0] = ord(str[i]) - 32
    def showValue(self, value):
        tmp = value
        for s in reversed(self.array):
            s[0] = 16 + tmp % 10
            tmp = int(tmp/10)
    def showText(self, text):
        for i in range(len(self.array)):
            if i < len(text) and (ord(text[i]) - 32) > 0:
                self.array[i][0] = ord(text[i]) - 32
            else:
                self.array[i][0] = 0
    def delete(self):
        for g in self.group:
            self.group.pop()
            self.array.pop()
            
    # define destructor...
