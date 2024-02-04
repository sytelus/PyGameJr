from typing import Optional, List, Tuple, Dict, Union, Sequence, Iterable
from collections import namedtuple
from dataclasses import dataclass, field
import math
import os
import timeit
from enum import Enum
import random

import numpy as np

import pygame
import pymunk
from pymunk import pygame_util, Vec2d
from pygamejr import utils

RGBAOutput = Tuple[int, int, int, int]
PyGameColor = Union[pygame.Color, int, str, Tuple[int, int, int], RGBAOutput, Sequence[int]]
_images:Dict[str, pygame.Surface] = {} # cache of all loaded images

NumericNamedTuple = namedtuple('NumericNamedTuple', ['x', 'y'])
NumericNamedTuple.__doc__ = """A named tuple with two numeric fields x and y."""
NumericNamedTuple.__annotations__ = {'x': Union[int, float], 'y': Union[int, float]}

# types that accepts tuples of vectors
Coordinates=Union[Tuple[float, float], Vec2d, NumericNamedTuple]
Vector2=Union[Tuple[float, float], Vec2d, NumericNamedTuple]

def get_image(image_path:str, cache=True)->pygame.Surface:
    """
    Load an image from a file. If the image has already been loaded, return the cached image.
    """
    if image_path not in _images:
        image = pygame.image.load(utils.full_path_abs(image_path))
        if cache:
            _images[image_path] = image
    else:
        image = _images[image_path]
    return image

def polygon_points(sides:int, left:int, top:int, polygon_width:int, polygon_height:int)->List[Tuple[int, int]]:
    """
    Computes the coordinates of the points of a regular polygon.
    """

    # The distance from the center to a corner (radius)
    radius_x = polygon_width / 2
    radius_y = polygon_height / 2

    # Calculate the center of the polygon
    center_x = left + radius_x
    center_y = top + radius_y

    # Calculate the points of the polygon
    polygon_points = []
    for i in range(sides):
        angle = math.radians(360 / sides * i - 90)  # Subtract 90 degrees to start from the top
        x = center_x + radius_x * math.cos(angle)
        y = center_y + radius_y * math.sin(angle)
        polygon_points.append((x, y))

    return polygon_points

def get_bounding_rect(polygon_points:Iterable[Coordinates])->Tuple[float, float, float, float, float, float]:
    """
    Returns a pygame.Rect that contains all of the points in the polygon.
    """

    # Unzip the polygon points into two separate lists of x coordinates and y coordinates
    x_coordinates, y_coordinates = zip(*polygon_points)

    # Use min and max to find the bounding coordinates
    min_x = min(x_coordinates)
    min_y = min(y_coordinates)
    max_x = max(x_coordinates)
    max_y = max(y_coordinates)

    return max_x - min_x, max_y - min_y, min_x, min_y, max_x, max_y

def has_transparency(surface:pygame.Surface)->bool:
    """
    Returns True if the surface has transparency, False otherwise.
    """
    if surface.get_flags() & pygame.SRCALPHA:
        # Surface is per pixel alpha
        mask = pygame.mask.from_surface(surface)
        return mask.count() < mask.get_rect().width * mask.get_rect().height
    elif surface.get_colorkey() is not None:
        # Surface is color key alpha
        return True
    else:
        # No transparency
        return False

def collide_mask_ex(left:pygame.sprite.Sprite, right:pygame.sprite.Sprite)->bool:
    """collision detection between two sprites, using masks or rectangles.

    pygame.sprite.collide_mask(SpriteLeft, SpriteRight): bool

    Tests for collision between two sprites. If both sprites have a "mask" attribute,
    it tests if their bitmasks overlap. If either sprite does not have a mask,
    it uses rectangle collision detection instead. Sprites must have a "rect" and
    an optional "mask" attribute.

    """
    # Check if both sprites have a mask
    left_has_mask = hasattr(left, 'mask') and left.mask is not None # type: ignore
    right_has_mask = hasattr(right, 'mask') and right.mask is not None # type: ignore

    # If both have masks, use mask collision detection
    if left_has_mask and right_has_mask:
        xoffset = right.rect[0] - left.rect[0] # type: ignore
        yoffset = right.rect[1] - left.rect[1] # type: ignore
        return left.mask.overlap(right.mask, (xoffset, yoffset)) # type: ignore

    # Otherwise, use rectangle collision detection
    else:
        return left.rect.colliderect(right.rect) # type: ignore

@dataclass
class Grounding:
    normal:Vec2d=Vec2d.zero()
    penetration:Vec2d=Vec2d.zero()
    impulse:Vec2d=Vec2d.zero()
    position:Vec2d=Vec2d.zero()
    has_body:bool=False
    friction:float=0.0
    velocity:Vec2d=Vec2d.zero()

@dataclass
class AnimationSpec:
    frame_time_s:float=0.1
    last_frame_time:float=timeit.default_timer()
    loop:bool=True
    started:bool=False
    image_index:int=0

    def __post_init__(self):
        pass

    def start(self, loop:bool=True, from_index=0, frame_time_s:float=0.1):
        self.started = True
        self.loop = loop
        self.frame_time_s = frame_time_s
        self.image_index = from_index
        self.last_frame_time = timeit.default_timer()

    def stop(self):
        self.started = False

    def update(self, image_count:int)->None:
        if not self.started:
            return
        current_time = timeit.default_timer()
        if current_time - self.last_frame_time > self.frame_time_s:
            self.last_frame_time = current_time
            self.image_index += 1
            if self.image_index >= image_count:
                if self.loop:
                    self.image_index = 0
                else:
                    self.image_index -= 1
                    self.stop()

@dataclass
class ImageSpec:
    image:pygame.Surface
    image_scale_xy:Tuple[float,float]=(1., 1.)
    image_transparency_enabled:bool=False

@dataclass
class DrawOptions:
    angle_line_width:int=0
    angle_line_color:PyGameColor="black"
    center_radius:float=0
    center_color:PyGameColor="magenta"

class ImagePaintMode(Enum):
    CENTER = 1
    TILE = 2

@dataclass
class TextInfo:
    text:str
    pos:Coordinates=(0, 0)
    font_name:Optional[str]=None
    font_size:int=20
    color:PyGameColor="black"
    background_color:Optional[PyGameColor] = None

@dataclass
class CostumeSpec:
    name:str
    image_paths:Iterable[str]
    _scale_xy:Tuple[float,float]=(1., 1.)
    transparent_color:Optional[PyGameColor]=None
    transparency_enabled:bool=False
    _images:List[pygame.Surface]=field(default_factory=list)
    _scaled_images:List[pygame.Surface]=field(default_factory=list)
    paint_mode:ImagePaintMode=ImagePaintMode.CENTER
    animation:AnimationSpec = field(default_factory=AnimationSpec)

    @property
    def scale_xy(self)->Tuple[float,float]:
        return self._scale_xy
    @scale_xy.setter
    def scale_xy(self, value:Tuple[float,float]):
        self._scale_xy = value

        # scale current images
        self._scaled_images = []
        for image in self._images:
            self._scaled_images.append(self._get_scaled_image(image))

    def _get_scaled_image(self, image:pygame.Surface)->pygame.Surface:
        if self.scale_xy != (1., 1.):
            scaled_image = pygame.transform.scale(
                image,(image.get_width()*self.scale_xy[0], \
                        image.get_height()*self.scale_xy[1]
                ))
            return scaled_image
        else:
            return image

    def __len__(self)->int:
        return len(self._images)

    def update(self)->None:
        self.animation.update(len(self._images))

    def get_image(self, scaled=True)->pygame.Surface:
        return self._scaled_images[self.animation.image_index]

    def add_images(self, image_paths:Union[str, Iterable[str]],
                   cache:bool=True)->None:
        if isinstance(image_paths, str):
            image_paths = [image_paths] # type: ignore

        for image_path in image_paths:
            # load image
            image = get_image(image_path, cache=cache)
            # set transparency
            if self.transparent_color is not None:
                image.set_colorkey(self.transparent_color)
            else:
                if self.transparency_enabled and has_transparency(image):
                        image = image.convert_alpha()
            self._images.append(image)
            self._scaled_images.append(self._get_scaled_image(image))


@dataclass
class CameraControls:
    zoom_in_key='z'
    zoom_out_key='x'
    pan_left_key='a'
    pan_right_key='d'
    pan_up_key='w'
    pan_down_key='s'
    rotate_left_key='q'
    rotate_right_key='e'
    zoom_speed:float=1.1
    pan_speed:float=10.
    rotate_speed:float=5.
    reset_key:str='r'
class Camera:
    def __init__(self) -> None:
        self.bottom_left:Vec2d=Vec2d.zero()
        self.angle:float=0
        self.scale=1.0
        self._update_transform()

    def _update_transform(self):
        if self.angle == 0:
            self.theta = 0
            self.rotation_matrix = np.eye(2)
        else:
            # Convert angle to radians
            self.theta = np.radians(self.angle)
            # Create rotation matrix
            self.rotation_matrix = np.array([[np.cos(self.theta), -np.sin(self.theta)],
                                        [np.sin(self.theta),  np.cos(self.theta)]])
        # Create scaling matrix
        self.scaling_matrix = np.array([[self.scale, 0],
                                [0, self.scale]])

    def apply(self, points:List[Vec2d],
              translate=True, scale=True, rotate=True)->List[Vec2d]:
        if self.angle == 0 and self.scale == 1.0 and self.bottom_left == Vec2d.zero():
            return points

        points = np.array(points) # type: ignore

        if scale:
            points = np.dot(points, self.scaling_matrix)

        if rotate:
            points = np.dot(points, self.rotation_matrix.T)

        if translate:
            points = points - self.bottom_left # type: ignore

        return [Vec2d(*v) for v in points]

    def move_by(self, delta:Coordinates):
        self.bottom_left += Vec2d(*delta)
        self._update_transform()
    def move_to(self, pos:Coordinates):
        self.bottom_left = Vec2d(*pos)
        self._update_transform()
    def turn_by(self, angle:float):
        self.angle += angle
        self._update_transform()
    def turn_to(self, angle:float):
        self.angle = angle
        self._update_transform()
    def zoom_by(self, scale:float):
        self.scale *= scale
        self._update_transform()
    def zoom_to(self, scale:float):
        self.scale = scale
        self._update_transform()
    def reset(self):
        self.bottom_left = Vec2d.zero()
        self.angle = 0
        self.scale = 1.0
        self._update_transform()


def rectangle_from_line(p1:Vec2d, p2:Vec2d)->List[Vec2d]:
    """Create a rectangle around a line of width 1."""
    # Calculate the vector representing the line
    line_vec = p2 - p1

    # Calculate a perpendicular vector (for width)
    perp_vec = Vec2d(-line_vec[1], line_vec[0])

    # Normalize and scale the perpendicular vector to half the rectangle's width
    perp_vec = perp_vec / perp_vec.length * 0.5

    # Calculate the four corners of the rectangle
    corner1 = p1 + perp_vec
    corner4 = p2 + perp_vec
    corner3 = p2 - perp_vec
    corner2 = p1 - perp_vec

    return [corner1, corner2, corner3, corner4]

def tile_image(image:pygame.Surface, dest:pygame.Surface, start_xy:Coordinates)->None:
    start_x, start_y = start_xy
    source_width, source_height = image.get_width(), image.get_height()
    dest_width, dest_height = dest.get_width(), dest.get_height()

    # Adjust start_x and start_y for negative values to ensure tiling works correctly
    if start_x < 0:
        start_x = source_width - (-start_x % source_width)
    if start_y < 0:
        start_y = source_height - (-start_y % source_height)

    # Calculate the starting points for tiling considering negative offsets
    start_x = start_x % source_width - source_width
    start_y = start_y % source_height - source_height

    # Tile the image across the dest
    for x in range(round(start_x), dest_width, source_width):
        for y in range(round(start_y), dest_height, source_height):
            dest.blit(image, (x, y))

def clamp(value:float, min_value:float, max_value:float)->float:
    """Clamps a value to a range."""
    return max(min(value, max_value), min_value)

def interpolate(start:float, end:float, max_amount:float)->float:
    """Interpolates between two values."""
    return start + clamp((end - start), -max_amount, max_amount)

def draw_shape(screen:pygame.Surface, shape:pymunk.Shape,
                   texts:Dict[str, TextInfo],
                   color:PyGameColor, border:int,
                   draw_options:Optional[DrawOptions],
                   camera:Camera,
                   costume:Optional[CostumeSpec]=None)->None:

    # points in shape are centered at origin without rotation
    radius:Optional[float] = None
    if isinstance(shape, pymunk.Poly):
        vertices = shape.get_vertices()
    elif isinstance(shape, pymunk.Segment):
        vertices = rectangle_from_line(shape.a, shape.b)
    elif isinstance(shape, pymunk.Circle):
        vertices = [Vec2d(shape.radius, shape.radius), Vec2d(shape.radius, -shape.radius),
                    Vec2d(-shape.radius, -shape.radius), Vec2d(-shape.radius, shape.radius)]
        radius = shape.radius
    else:
        raise ValueError(f"Unknown shape type: {type(shape)}")

    # add centroid that we will remove later
    vertices.append(Vec2d(0, 0))
    # add unit vector for angle line that we will remove later
    vertices.append(Vec2d(1, 0))

    #first rotate these points
    if shape.body.angle != 0:
        vertices = [v.rotated(shape.body.angle) for v in vertices]

    # get vertices in global coordinates
    vertices = [v + shape.body.position for v in vertices]

    # apply camera transformations
    vertices = camera.apply(vertices)
    radius = radius * camera.scale if radius is not None else None

    # flip y to get pygame coordinates
    vertices = [Vec2d(v.x, screen.get_height()-v.y) for v in vertices]

    # remove the centroid from the vertices
    centroid, unit_vec = vertices[-2], vertices[-1]
    unit_vec = unit_vec - centroid
    vertices = vertices[:-2]

    # draw the shape on shape surface
    # we don't draw directly on screen as it doesn't support transparency
    # get bounding rect of the shape
    width, height, min_x, min_y, max_x, max_y = get_bounding_rect(vertices)
    shape_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    shape_surface.fill((0, 0, 0, 0)) # transparent initial surface

    if radius is not None:
        pygame.draw.circle(shape_surface, color, (width/2., height/2.), radius, border)
    else:
        pygame.draw.polygon(shape_surface, color, [(v.x-min_x, v.y-min_y) for v in vertices], border)

    shape_screen_offset = Vec2d(min_x, min_y)

    # now we have the vertices in global pygame coordinates, let's figure out image
    # prepare image if any
    if costume is not None:
        # create a mask for the shape
        mask = pygame.Surface((width, height), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0)) # transparent initial surface

        # draw the shape on the mask with solid alpha to mask image later
        solid_color = (255, 255, 255, 255)
        if radius is not None:
            pygame.draw.circle(mask, solid_color, (width/2, height/2), radius, border)
        else:
            pygame.draw.polygon(mask, solid_color, [(v.x-min_x, v.y-min_y) for v in vertices], border)

        # get the image to draw on the shape
        image = costume.get_image()

        # apply camera scale to image
        if camera.scale != 1.0:
            image = pygame.transform.scale(image, (int(image.get_width()*camera.scale),
                                                   int(image.get_height()*camera.scale)))
        if costume.paint_mode == ImagePaintMode.CENTER:
            pass # no need to do anything
        else:
            # create a surface to do tiling of same size as the shape
            tiled_dest = pygame.Surface((width, height), pygame.SRCALPHA)
            tiled_dest.fill((0, 0, 0, 0)) # transparent initial surface
            # tile the image across the surface
            tile_image(image, tiled_dest, (0, 0))
            image = tiled_dest

        # apply body and camera rotation
        angle = shape.body.angle + camera.theta
        if angle != 0:
            # add 180 degree to flip y
            image = pygame.transform.rotate(image, math.degrees(angle))

        # first draw image on the shape surface
        # coordinates for this image are such that to match the centroid of the shape with the centroid of the image
        abs_top_left = centroid - Vec2d(image.get_width()/2, image.get_height()/2)
        rel_top_left = abs_top_left - shape_screen_offset
        shape_surface.blit(image, rel_top_left)
        # now mask the image
        shape_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    # draw debug line from centroid to angle
    if draw_options and draw_options.angle_line_width:
        line_len = max(width, height, 2) / 2.0 if radius is None else radius
        start_pos = centroid - shape_screen_offset
        end_pos = start_pos + (unit_vec * line_len)
        pygame.draw.line(shape_surface, draw_options.angle_line_color, start_pos, end_pos,
                            round(draw_options.angle_line_width*camera.scale))

    draw_texts(shape_surface, texts)

    # finally blit the shape on the screen
    screen.blit(shape_surface, shape_screen_offset)



def draw_texts(surface:pygame.Surface, texts:Dict[str, TextInfo], offset:Vec2d=Vec2d.zero()):
    for name, text_info in texts.items():
        font = pygame.font.Font(text_info.font_name, text_info.font_size)
        text_surface = font.render(text_info.text, True, text_info.color, text_info.background_color)
        pos = Vec2d(*text_info.pos) + offset
        surface.blit(text_surface, pos)

def print_to(surface:pygame.Surface, text:str, topleft:Coordinates=Vec2d.zero(),
             font_name:Optional[str]=None, font_size:int=20,
             color:PyGameColor="black", background_color:Optional[PyGameColor]=None):
    """Prints the given text to the given surface at the given position."""
    font = pygame.font.Font(font_name, font_size)
    text_surface = font.render(text, True, color, background_color)
    surface.blit(text_surface, topleft)

def tiled_blit(source:pygame.Surface, start_xy:Tuple[float, float], dest:pygame.Surface):
    start_x, start_y = start_xy
    source_width, source_height = source.get_width(), source.get_height()
    dest_width, dest_height = dest.get_width(), dest.get_height()

    # Adjust start_x and start_y for negative values to ensure tiling works correctly
    if start_x < 0:
        start_x = source_width - (-start_x % source_width)
    if start_y < 0:
        start_y = source_height - (-start_y % source_height)

    # Calculate the starting points for tiling considering negative offsets
    start_x = start_x % source_width - source_width
    start_y = start_y % source_height - source_height

    # Tile the source across the dest
    for x in range(round(start_x), dest_width, source_width):
        for y in range(round(start_y), dest_height, source_height):
            dest.blit(source, (x, y))

def random_color(random_alpha=False)->PyGameColor:
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255),
            random.randint(0, 255) if random_alpha else 255)

def is_second_rect_outside(xy1, xy2, xy1_prime, xy2_prime):
    """
    Check if the second rectangle has any part outside the first rectangle.

    Parameters:
    - first_rect: Tuple of (x1, y1, x2, y2) representing the first rectangle.
    - second_rect: Tuple of (x1', y1', x2', y2') representing the second rectangle.

    Returns:
    - True if the second rectangle has any part outside the first one, otherwise False.
    """
    x1, y1 = xy1
    x2, y2 = xy2
    x1_prime, y1_prime = xy1_prime  # Unpack the second rectangle coordinates
    x2_prime, y2_prime = xy2_prime  # Unpack the second rectangle coordinates

    # Check if the second rectangle is outside the first rectangle in any direction
    if x1_prime < x1 or x2_prime > x2 or y1_prime < y1 or y2_prime > y2:
        return True
    else:
        return False