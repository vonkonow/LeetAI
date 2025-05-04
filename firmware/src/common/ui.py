"""
UI components for the core module.

This module provides common UI components used across the application.
"""

import displayio
import adafruit_imageload
from src.common import hw
import config.config as config

class DisplayManager:
    """
    A class for managing all UI components.
    
    Attributes:
        display: Display instance
        hw: Hardware interface
        sprites: Dictionaÿ?f sprites
        text_fields: Dictionary of text fields
        colors: Dictionary of colors
    """
    
    def __init__(self, display, hw):
        """
        Initialize a new display manager.
        
        Args:
            display: Display instance
            hw: Hardware interface
        """
        self.display = display
        self.hw = hw
        self.sprites = {}
        self.text_fields = {}
        self.colors = config.UI_COLORS
        
        # Create black background
        self.black_sprite = displayio.TileGrid(
            displayio.Bitmap(config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT, 1),
            pixel_shader=displayio.Palette(1),
            x=0, y=0
        )
        self.display_group = displayio.Group()
        self.display_group.append(self.black_sprite)
        
        # Add display group to hardware display
        self.hw.displayGroup.append(self.display_group)
        self.display.refresh()
        
        # Field-related attributes (optional)
        self.field = None
        self.x_max = None
        self.y_max = None
    
    def initialize_pattern_field(self, sprite_sheet, palette, x_start=0, y_start=0):
        """
        Initialize the pattern field display.
        
        Args:
            sprite_sheet: Sprite sheet for the field
            palette: Color palette for the field
            x_start: Starting x position
            y_start: Starting y position
        """
        self.x_max = config.FIELD_X_MAX
        self.y_max = config.FIELD_Y_MAX
        self.field = Field(self.display_group, sprite_sheet, palette, x_start, y_start, 
                          self.x_max, self.y_max, 
                          tile_width=config.FIELD_TILE_WIDTH, 
                          tile_height=config.FIELD_TILE_HEIGHT)
        self.display.refresh()
    
    def load_song_background(self, song_name: str):
        """
        Load and display the song background image.
        
        Args:
            song_name: Name of the song
        """
        bg = Image(self.display_group, f"assets/images/{song_name}.bmp")
        bg.tile.y = 35
        self.sprites['background'] = bg
        self.display.refresh()
    
    def create_position_sprite(self):
        """Create the position sprite for song playback visualization."""
        sprite_sheet, palette = adafruit_imageload.load(
            "assets/images/4x4.bmp",
            bitmap=displayio.Bitmap,
            palette=displayio.Palette
        )
        pos_sprite = Sprite(self.display_group, sprite_sheet, palette)
        pos_sprite.setSprite(3)
        pos_sprite.setPos(0, 26)
        self.sprites['position'] = pos_sprite
        self.display.refresh()
    
    def create_text_fields(self, title):
        """Create and initialize text fields for display."""
        positions = config.TEXT_FIELD_POSITIONS
        self.text_fields['title'] = self.hw.SpriteText(positions['title'][0], positions['title'][1], title)
        self.text_fields['channel'] = self.hw.SpriteText(positions['channel'][0], positions['channel'][1], "000")
        self.text_fields['note'] = self.hw.SpriteText(positions['note'][0], positions['note'][1], "000")
        self.text_fields['intensity'] = self.hw.SpriteText(positions['intensity'][0], positions['intensity'][1], "000")
        self.text_fields['menu'] = self.hw.SpriteText(positions['menu'][0], positions['menu'][1], "Menu            ")
        self.text_fields['debug'] = self.hw.SpriteText(positions['debug'][0], positions['debug'][1], "                ")
        self.display.refresh()
    
    def update_playback_position(self, position: int):
        """
        Update the position sprite location.
        
        Args:
            position: New position
        """
        if 'position' in self.sprites:
            self.sprites['position'].setPos(position, 26)
        self.display.refresh()
    
    def update_channel_info(self, channel: int, note: int, intensity: int):
        """
        Update the channel information display.
        
        Args:
            channel: Channel number
            note: Note number
            intensity: Note intensity
        """
        if 'channel' in self.text_fields:
            self.text_fields['channel'].showValue(channel)
        if 'note' in self.text_fields:
            self.text_fields['note'].showValue(note)
        if 'intensity' in self.text_fields:
            self.text_fields['intensity'].showValue(intensity)
        self.display.refresh()
    
    def update_menu_text(self, text: str):
        """
        Update the menu text display.
        
        Args:
            text: Menu text to display
        """
        if 'menu' in self.text_fields:
            self.text_fields['menu'].showText(text)
        self.display.refresh()
    
    def show_debug_message(self, message: str):
        """
        Show a debug message.
        
        Args:
            message: Debug message to display
        """
        if 'debug' in self.text_fields:
            self.text_fields['debug'].showText(message)
        self.display.refresh()
    
    def update_mute_leds(self, mute_states: list):
        """
        Update the mute LED states.
        
        Args:
            mute_states: List of mute states
        """

        for i, is_muted in enumerate(mute_states):
            self.hw.pixels[i] = self.colors['mute'] if is_muted else self.colors['off']
    
    def set_pause_led(self, is_paused: bool):
        """
        Set the pause LED state.
        
        Args:
            is_paused: Whether the song is paused
        """
        self.hw.pixels[11] = self.colors['pause'] if is_paused else self.colors['off']
    
    def redraw(self):
        """Redraw the display to clear any glitches."""
        self.display_group.append(self.black_sprite)
        self.display_group.pop()
        self.display.refresh()

class Sprite:
    """
    A sprite that can be displayed on the screen.
    
    Attributes:
        s: The displayio TileGrid object representing the sprite
    """
    
    def __init__(self, grp: displayio.Group, sheet: displayio.Bitmap, 
                 palette: displayio.Palette, tile_width: int = 4, tile_height: int = 4):
        """
        Initialize a new sprite.
        
        Args:
            grp: Display group to add the sprite to
            sheet: Bitmap containing the sprite image
            palette: Color palette for the sprite
            tile_width: Width of each tile in pixels
            tile_height: Height of each tile in pixels
        """
        self.s = displayio.TileGrid(sheet, pixel_shader=palette, 
                                  width=1, height=1, 
                                  tile_width=tile_width, tile_height=tile_height)
        grp.append(self.s)

    def setSprite(self, t: int) -> None:
        """
        Set the sprite's tile index.
        
        Args:
            t: Tile index to set
        """
        self.s[0] = t

    def getSprite(self) -> int:
        """
        Get the sprite's current tile index.
        
        Returns:
            int: Current tile index
        """
        return self.s[0]

    def setPos(self, x: int, y: int) -> None:
        """
        Set the sprite's position.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.s.x = x
        self.s.y = y

class Field:
    """
    A field of sprites that can be displayed on the screen.
    
    Attributes:
        x_max: Maximum X coordinate
        y_max: Maximum Y coordinate
        array: List of sprites in the field
    """
    
    def __init__(self, display_group: displayio.Group, sprite_sheet: displayio.Bitmap, 
                 palette: displayio.Palette, x_start: int, y_start: int, 
                 x_max: int, y_max: int, tile_width: int = None, tile_height: int = None):
        """
        Initialize a new field.
        
        Args:
            display_group: Display group to add the field to
            sprite_sheet: Bitmap containing the sprite images
            palette: Color palette for the sprites
            x_start: Starting X coordinate
            y_start: Starting Y coordinate
            x_max: Maximum X coordinate
            y_max: Maximum Y coordinate
            tile_width: Width of each tile in pixels (defaults to config value)
            tile_height: Height of each tile in pixels (defaults to config value)
        """
        self.x_max = x_max
        self.y_max = y_max
        self.tile_width = tile_width or config.FIELD_TILE_WIDTH
        self.tile_height = tile_height or config.FIELD_TILE_HEIGHT
        self.array = []
        for i in range(x_max * y_max):
            s = Sprite(display_group, sprite_sheet, palette, 
                      tile_width=self.tile_width, tile_height=self.tile_height)
            s.setPos(x_start + (i % x_max) * self.tile_width, 
                    y_start + y_max * self.tile_height - int(i / x_max) * self.tile_height)
            self.array.append(s)
        self.reset(0)

    def setBlock(self, x: int, y: int, block: int) -> None:
        """
        Set a block in the field.
        
        Args:
            x: X coordinate
            y: Y coordinate
            block: Block type to set
        """
        self.array[y * self.x_max + x].setSprite(block)

    def getBlock(self, x: int, y: int) -> int:
        """
        Get a block from the field.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            int: Block type at the specified coordinates
        """
        return self.array[y * self.x_max + x].getSprite()

    def refresh(self) -> None:
        """Refresh all sprites in the field."""
        for s in self.array:
            s.setSprite(s.getSprite())

    def reset(self, sprite_id: int) -> None:
        """
        Reset all sprites in the field to a specific type.
        
        Args:
            sprite_id: Sprite type to set
        """
        for s in self.array:
            s.setSprite(sprite_id)

    def hLine(self) -> None:
        """Draw a horizontal line at the bottom of the field."""
        for i in range(self.x_max):
            self.setBlock(i, self.y_max-1, 2)

class Image:
    """
    An image that can be displayed on the screen.
    
    Attributes:
        display_group: Display group containing the image
    """
    
    def __init__(self, display_group: displayio.Group, image_path: str, width: int = 160, height: int = 128):
        """
        Initialize a new image.
        
        Args:
            display_group: Display group to add the image to
            image_path: Path to the image file
            width: Width of the image in pixels
            height: Height of the image in pixels
        """
        self.display_group = display_group
        self.width = width
        self.height = height
        self.load(image_path)

    def replace(self, image_path: str) -> None:
        """
        Replace the current image with a new one.
        
        Args:
            image_path: Path to the new image file
        """
        self.display_group.pop()
        self.load(image_path)

    def load(self, image_path: str) -> None:
        """
        Load an image from a file.
        
        Args:
            image_path: Path to the image file
        """
        load_bitmap, load_palette = adafruit_imageload.load(image_path, 
                                                          bitmap=displayio.Bitmap, 
                                                          palette=displayio.Palette)
        # Create a single tile that covers the entire bitmap
        load_tile = displayio.TileGrid(load_bitmap, 
                                     pixel_shader=load_palette, 
                                     width=1, height=1, 
                                     tile_width=load_bitmap.width, 
                                     tile_height=load_bitmap.height)
        self.display_group.append(load_tile)
        self.tile = load_tile
        hw.display.refresh()

    def clear(self, color: int) -> None:
        """
        Clear the image with a specific color.
        
        Args:
            color: Color to clear with
        """
        self.display_group.pop()
        load_bitmap = displayio.Bitmap(self.width, self.height, 1)
        load_palette = displayio.Palette(1)
        load_palette[0] = color
        load_sprite = displayio.TileGrid(load_bitmap, 
                                       pixel_shader=load_palette, 
                                       x=0, y=0)
        self.display_group.append(load_sprite)
        hw.display.refresh()

def colorwheel(pos: int) -> tuple:
    """
    Convert a position value (0-255) to an RGB color value.
    
    The colors transition from red to green to blue and back to red.
    
    Args:
        pos: Position value between 0 and 255
        
    Returns:
        tuple: RGB color value as (R, G, B)
    """
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)
