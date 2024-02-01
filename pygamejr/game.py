from typing import List, Tuple, Optional, Set, Dict, Any, Union, Callable, Iterable, Sequence
import random
import math
from dataclasses import dataclass
import timeit
from enum import Enum
import time

import pygame
import pymunk
from pymunk import pygame_util, Vec2d

from pygamejr import utils
from pygamejr import common
from pygamejr.actor import Actor
from pygamejr.common import PyGameColor, DrawOptions, Coordinates, Vector2, ImagePaintMode

TRANSPARENT_COLOR = (0, 0, 0, 0)

show_mouse_coordinates = False # show mouse coordinates in console?

clock = pygame.time.Clock() # game clock
screen:Optional[pygame.Surface] = None # game screen
draw_options:Optional[pygame_util.DrawOptions] = None # pymunk draw options

# For y flip conversion between pymunk and pygame coordinates
pygame_util.positive_y_is_up = True

# pygame setup
pygame.init()
space = pymunk.Space() # physics space

down_keys:Set[str] = set()   # keys currently down
down_mousbuttons:Set[str] = set()  # mouse buttons currently down

noone:Actor = None # type: ignore

# private variables
_actors:Set[Actor] = set() # list of all actors
# for each handler type, keep list of actors that have that handler
_actors_handlers:Dict[int, Set[Actor]] = {}
_running = False # is game currently running?
_default_poly_radius = 1
_sounds:Dict[str, pygame.mixer.Sound] = {} # sounds
_physics_fps_multiplier = 4

@dataclass
class ScreenProps:
    """Screen properties"""
    width:int=1280
    height:int=720
    color:PyGameColor="purple"
    fps:int=60
    image_path:Optional[str]=None
    image:Optional[pygame.Surface]=None # image to display on screen
    image_scaled:Optional[pygame.Surface]=None # scaled image to display on screen
    title:str="PyGameJr Rocks"
_screen_props = ScreenProps()

def is_running()->bool:
    """Is the game currently running?"""
    return _running

def keep_running():
    """
    default game loop
    """
    while _running:
        update()

def screen_top()->int:
    return _screen_props.height
def screen_bottom()->int:
    return 0
def screen_left()->int:
    return 0
def screen_right()->int:
    return _screen_props.width
def screen_center()->Tuple[float, float]:
    return _screen_props.width//2., _screen_props.height//2.


def add_text(text:str, at:Optional[Coordinates]=None,
             font_name:Optional[str]=None, font_size:int=20,
             color:PyGameColor="black", background_color:Optional[PyGameColor]=None,
             name:Optional[str]=None):
    """Print text at position"""
    assert screen is not None, "screen is None"
    at = at if at is not None else screen_center()
    noone.add_text(text=text, pos=at, font_name=font_name, font_size=font_size,
                   color=color, background_color=background_color, name=name)

def remove_text(text:str, name:Optional[str]=None):
    """Remove text from screen"""
    noone.remove_text(text=text, name=name)

def random_color(random_alpha=False)->PyGameColor:
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255),
            random.randint(0, 255) if random_alpha else 255)

def event_to_code(name:str)->int:
    if name == "on_keydown":
        return pygame.KEYDOWN
    elif name == "on_keyup":
        return pygame.KEYUP
    elif name == "on_keypress":
        return pygame.KEYUP
    elif name == "on_mousedown":
        return pygame.MOUSEBUTTONDOWN
    elif name == "on_mouseup":
        return pygame.MOUSEBUTTONUP
    elif name == "on_mousebutton":
        return pygame.MOUSEBUTTONUP
    elif name == "on_mousemove":
        return pygame.MOUSEMOTION
    elif name == "on_mousewheel":
        return pygame.MOUSEWHEEL
    elif name == "on_quit":
        return pygame.QUIT
    else:
        raise ValueError(f"Unknown event name: {name}")

def handle(event_method:Callable, handler:Callable)->None:
    """
    Assign a handler to a given event method.

    :param event_method: The bound method of the event to handle (e.g., obj.on_keydown).
    :param handler: The handler function to replace the original method.
    """
    if not callable(event_method):
        raise ValueError("The first argument must be a callable method.")

    # Retrieve the self instance from the method
    self = event_method.__self__

    # Get the name of the method
    method_name = event_method.__name__

    # register this actor for this event
    event_code = event_to_code(method_name)
    global _actors_handlers
    if event_code not in _actors_handlers:
        _actors_handlers[event_code] = set()
    _actors_handlers[event_code].add(self)

    # Set the handler to replace the original event method, making sure it's bound
    setattr(self, method_name, handler.__get__(self, type(self)))


# TODO: replace asserts with exceptions

def create_image(image_path:Union[str, Iterable[str]],
                bottom_left:Optional[Coordinates]=None,
                center:Optional[Coordinates]=None,
                angle=0.0, border=0,
                transparent_color:Optional[PyGameColor]=None,
                scale_xy:Tuple[float,float]=(1., 1.),
                transparency_enabled:bool=True,
                paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                draw_options:Optional[DrawOptions]=None,
                visible:bool=True,
                density:Optional[float]=None, elasticity:Optional[float]=None, friction:Optional[float]=None,
                mass:Optional[float]=None, moment:Optional[float]=None,
                fixed_object=False, can_rotate=True,
                velocity:Vector2=Vec2d.zero(), angular_velocity:float=0.) -> Actor:

    if isinstance(image_path, str):
        image_path = [image_path]
    else:
        image_path = list(image_path)
    assert len(image_path) > 0, "At least provide one image path."
    image = common.get_image(image_path[0])

    width, height = image.get_size()
    if scale_xy is not None:
        width, height = width*scale_xy[0], height*scale_xy[1]

    assert not(bottom_left is not None and center is not None), "Don't specify both bottom_left and center, only one or the other."
    if center is not None:
        bottom_left = Vec2d(center[0] - width/2., center[1] - height/2.)
    elif bottom_left is not None:
        bottom_left = Vec2d(*bottom_left)
    else:
        bottom_left = Vec2d(0, 0)

    body_type = pymunk.Body.DYNAMIC if any(n is not None for n in (density, mass, moment)) else pymunk.Body.KINEMATIC
    if fixed_object:
        body_type = pymunk.Body.STATIC

    body_args = {}
    if mass is not None:
        body_args['mass'] = mass
        if moment is None:
            moment = pymunk.moment_for_box(mass, (width, height))
    if moment is not None:
        body_args['moment'] = moment
    body = pymunk.Body(body_type=body_type, **body_args)
    body.position = bottom_left[0] + width/2., bottom_left[1] + height/2.
    body.angle = angle
    body.velocity = Vec2d(*velocity)
    body.angular_velocity = math.radians(angular_velocity)

    shape = pymunk.Poly.create_box(body,
                                   size=(width, height),
                                   radius=_default_poly_radius)
    if density is not None:
        shape.density = density
    if elasticity is not None:
        shape.elasticity = elasticity
    if friction is not None:
        shape.friction = friction

    space.add(body, shape)
    if not can_rotate:
        shape.body.moment = float('inf')

    actor = Actor(shape=shape,
                  border=border,
                  color=(0, 0, 0, 0),
                  image_paths=image_path,
                  image_scale_xy=scale_xy,
                  image_transparent_color=transparent_color,
                  image_transparency_enabled=transparency_enabled,
                  image_paint_mode=paint_mode,
                  visible=visible,
                  draw_options=draw_options,)

    _actors.add(actor)

    return actor

def create_rect(width:int=20, height:int=20,
                color:PyGameColor="red",
                image_path:Union[str, Iterable[str]]=[],
                bottom_left:Optional[Coordinates]=None,
                center:Optional[Coordinates]=None,
                angle=0.0, border=0,
                transparent_color:Optional[PyGameColor]=None,
                scale_xy:Tuple[float,float]=(1., 1.),
                transparency_enabled:bool=True,
                paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                draw_options:Optional[DrawOptions]=None,
                visible:bool=True,
                density:Optional[float]=None, elasticity:Optional[float]=None, friction:Optional[float]=None,
                mass:Optional[float]=None, moment:Optional[float]=None,
                fixed_object=False, can_rotate=True,
                velocity:Vector2=Vec2d.zero(), angular_velocity:float=0.) -> Actor:

    body_type = pymunk.Body.DYNAMIC if any(n is not None for n in (density, mass, moment)) else pymunk.Body.KINEMATIC
    if fixed_object:
        body_type = pymunk.Body.STATIC

    assert not(bottom_left is not None and center is not None), "Don't specify both bottom_left and center, only one or the other."
    if center is not None:
        bottom_left = Vec2d(center[0] - width/2., center[1] - height/2.)
    elif bottom_left is not None:
        bottom_left = Vec2d(*bottom_left)
    else:
        bottom_left = Vec2d(0, 0)

    # shape center is at (0,0)
    r_bottom_left = Vec2d(-width/2., -height/2.)

    body_args = {}
    if mass is not None:
        body_args['mass'] = mass
        if moment is None:
            moment = pymunk.moment_for_box(mass, (width, height))
    if moment is not None:
        body_args['moment'] = moment
    body = pymunk.Body(body_type=body_type, **body_args)
    offset = Vec2d(*bottom_left) - r_bottom_left
    body.position = offset # centroid is now zero so no need to add to offset
    body.angle = angle
    body.velocity = Vec2d(*velocity)
    body.angular_velocity = math.radians(angular_velocity)

    shape = pymunk.Poly.create_box(body,
                                   size=(width, height),
                                   radius=0) # moment_for_box doesn't support radius
    if density is not None:
        shape.density = density
    if elasticity is not None:
        shape.elasticity = elasticity
    if friction is not None:
        shape.friction = friction

    space.add(body, shape)
    if not can_rotate:
        shape.body.moment = float('inf')
    actor = Actor(shape=shape,
                  color=color,
                  border=border,
                  image_paths=image_path,
                  image_scale_xy=scale_xy,
                  image_transparent_color=transparent_color,
                  image_transparency_enabled=transparency_enabled,
                  image_paint_mode=paint_mode,
                  visible=visible,
                  draw_options=draw_options,)

    _actors.add(actor)

    return actor

def create_circle(radius:float=20,
                color:PyGameColor="red",
                image_path:Union[str, Iterable[str]]=[],
                bottom_left:Optional[Coordinates]=None,
                center:Optional[Coordinates]=None,
                angle=0.0, border=0,
                transparent_color:Optional[PyGameColor]=None,
                scale_xy:Tuple[float,float]=(1., 1.),
                transparency_enabled:bool=True,
                paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                draw_options:Optional[DrawOptions]=None,
                visible:bool=True,
                density:Optional[float]=None, elasticity:Optional[float]=None, friction:Optional[float]=None,
                mass:Optional[float]=None, moment:Optional[float]=None,
                fixed_object=False, can_rotate=True,
                velocity:Vector2=Vec2d.zero(), angular_velocity:float=0.) -> Actor:

    body_type = pymunk.Body.DYNAMIC if any(n is not None for n in (density, mass, moment)) else pymunk.Body.KINEMATIC
    if fixed_object:
        body_type = pymunk.Body.STATIC

    assert not(bottom_left is not None and center is not None), "Don't specify both bottom_left and center, only one or the other."
    if bottom_left is not None:
        bottom_left = Vec2d(*bottom_left)
        center = (bottom_left[0] + radius, bottom_left[1] + radius)
    elif center is not None:
        center = Vec2d(*center)
    else:
        center = Vec2d(0, 0)

    body_args = {}
    if mass is not None:
        body_args['mass'] = mass
        if moment is None:
            moment = pymunk.moment_for_circle(mass, 0, radius)
    if moment is not None:
        body_args['moment'] = moment
    body = pymunk.Body(body_type=body_type, **body_args)
    body.position = center
    body.angle = angle
    body.velocity = Vec2d(*velocity)
    body.angular_velocity = math.radians(angular_velocity)

    shape = pymunk.Circle(body, radius)
    if density is not None:
        shape.density = density
    if elasticity is not None:
        shape.elasticity = elasticity
    if friction is not None:
        shape.friction = friction

    space.add(body, shape)
    if not can_rotate:
        shape.body.moment = float('inf')

    actor = Actor(shape=shape,
                  color=color,
                  border=border,
                  image_paths=image_path,
                  image_scale_xy=scale_xy,
                  image_transparent_color=transparent_color,
                  image_transparency_enabled=transparency_enabled,
                  image_paint_mode=paint_mode,
                  visible=visible,
                  draw_options=draw_options,)

    _actors.add(actor)

    return actor

def create_ellipse(width:int=20, height:int=20,
                color:PyGameColor="red",
                image_path:Union[str, Iterable[str]]=[],
                bottom_left:Optional[Coordinates]=None,
                center:Optional[Coordinates]=None,
                angle=0.0, border=0,
                transparent_color:Optional[PyGameColor]=None,
                scale_xy:Tuple[float,float]=(1., 1.),
                transparency_enabled:bool=True,
                paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                draw_options:Optional[DrawOptions]=None,
                visible:bool=True,
                density:Optional[float]=None, elasticity:Optional[float]=None, friction:Optional[float]=None,
                mass:Optional[float]=None, moment:Optional[float]=None,
                fixed_object=False, can_rotate=True,
                velocity:Vector2=Vec2d.zero(), angular_velocity:float=0.) -> Actor:

    body_type = pymunk.Body.DYNAMIC if any(n is not None for n in (density, mass, moment)) else pymunk.Body.KINEMATIC
    if fixed_object:
        body_type = pymunk.Body.STATIC

    assert not(bottom_left is not None and center is not None), "Don't specify both bottom_left and center, only one or the other."
    if center is not None:
        bottom_left = Vec2d(center[0] - width/2., center[1] - height/2.)
    elif bottom_left is not None:
        bottom_left = Vec2d(*bottom_left)
    else:
        bottom_left = Vec2d(0, 0)

    body_args = {}
    if mass is not None:
        body_args['mass'] = mass
        if moment is None:
            moment = pymunk.moment_for_box(mass, (width, height))
    if moment is not None:
        body_args['moment'] = moment
    body = pymunk.Body(body_type=body_type, **body_args)
    body.position = bottom_left[0] + width/2., bottom_left[1] + height/2.
    body.angle = angle
    body.velocity = Vec2d(*velocity)
    body.angular_velocity = math.radians(angular_velocity)

    shape = pymunk.Poly.create_box(body,
                                   size=(width, height),
                                   radius=_default_poly_radius)
    if density is not None:
        shape.density = density
    if elasticity is not None:
        shape.elasticity = elasticity
    if friction is not None:
        shape.friction = friction

    space.add(body, shape)
    if not can_rotate:
        shape.body.moment = float('inf')

    actor = Actor(shape=shape,
                  color=color,
                  border=border,
                  image_paths=image_path,
                  image_scale_xy=scale_xy,
                  image_transparent_color=transparent_color,
                  image_transparency_enabled=transparency_enabled,
                  image_paint_mode=paint_mode,
                  visible=visible,
                  draw_options=draw_options,)

    _actors.add(actor)

    return actor


def create_polygon_any(points:Sequence[Coordinates],
                color:PyGameColor="red",
                image_path:Union[str, Iterable[str]]=[],
                bottom_left:Optional[Coordinates]=None,
                center:Optional[Coordinates]=None,
                angle=0.0, border=0,
                transparent_color:Optional[PyGameColor]=None,
                scale_xy:Tuple[float,float]=(1., 1.),
                transparency_enabled:bool=True,
                paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                draw_options:Optional[DrawOptions]=None,
                visible:bool=True,
                density:Optional[float]=None, elasticity:Optional[float]=None, friction:Optional[float]=None,
                mass:Optional[float]=None, moment:Optional[float]=None,
                fixed_object=False, can_rotate=True,
                velocity:Vector2=Vec2d.zero(), angular_velocity:float=0.) -> Actor:

    body_type = pymunk.Body.DYNAMIC if any(n is not None for n in (density, mass, moment)) else pymunk.Body.KINEMATIC
    if fixed_object:
        body_type = pymunk.Body.STATIC

    centroid = sum(points, Vec2d(0., 0.))
    centroid = Vec2d(centroid[0]/len(points), centroid[1]/len(points))
    # let the center be the origin
    points = [Vec2d(*p) - centroid for p in points]

    # new centroid i snow at (0,0)

    r = common.get_bounding_rect(points)
    r_bottom_left = Vec2d(r[2], r[3])

    assert not(bottom_left is not None and center is not None), "Don't specify both bottom_left and center, only one or the other."
    if bottom_left is not None:
        bottom_left = Vec2d(*bottom_left)
        center = bottom_left - r_bottom_left
    elif center is not None:
        center = Vec2d(*center)
    else:
        center = Vec2d(0, 0)

    body_args = {}
    if mass is not None:
        body_args['mass'] = mass
        if moment is None:
            moment = pymunk.moment_for_poly(mass, points, radius=_default_poly_radius)
    if moment is not None:
        body_args['moment'] = moment
    body = pymunk.Body(body_type=body_type, **body_args)
    body.position = center
    body.angle = angle
    body.velocity = Vec2d(*velocity)
    body.angular_velocity = math.radians(angular_velocity)

    shape = pymunk.Poly(body, points, radius=_default_poly_radius)
    if density is not None:
        shape.density = density
    if elasticity is not None:
        shape.elasticity = elasticity
    if friction is not None:
        shape.friction = friction

    space.add(body, shape)
    if not can_rotate:
        shape.body.moment = float('inf')

    actor = Actor(shape=shape,
                  color=color,
                  border=border,
                  image_paths=image_path,
                  image_scale_xy=scale_xy,
                  image_transparent_color=transparent_color,
                  image_transparency_enabled=transparency_enabled,
                  image_paint_mode=paint_mode,
                  visible=visible,
                  draw_options=draw_options,)

    _actors.add(actor)

    return actor

def create_polygon(sides:int, width:int=20, height:int=20,
                color:PyGameColor="red",
                image_path:Union[str, Iterable[str]]=[],
                bottom_left:Optional[Coordinates]=None,
                center:Optional[Coordinates]=None,
                angle=0.0, border=0,
                transparent_color:Optional[PyGameColor]=None,
                scale_xy:Tuple[float,float]=(1., 1.),
                transparency_enabled:bool=True,
                paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                draw_options:Optional[DrawOptions]=None,
                visible:bool=True,
                density:Optional[float]=None, elasticity:Optional[float]=None, friction:Optional[float]=None,
                mass:Optional[float]=None, moment:Optional[float]=None,
                fixed_object=False, can_rotate=True,
                velocity:Vector2=Vec2d.zero(), angular_velocity:float=0.) -> Actor:

    points = common.polygon_points(sides, 0, 0, width, height)

    return create_polygon_any(points=points,
                color=color,
                image_path=image_path,
                bottom_left=bottom_left,
                center=center,
                angle=angle, border=border,
                transparent_color=transparent_color,
                scale_xy=scale_xy,
                transparency_enabled=transparency_enabled,
                paint_mode=paint_mode,
                draw_options=draw_options,
                visible=visible,
                density=density, elasticity=elasticity, friction=friction,
                mass=mass, moment=moment,
                fixed_object=fixed_object, can_rotate=can_rotate,
                velocity=velocity, angular_velocity=angular_velocity)

def create_screen_walls(left:Optional[Union[float, bool]]=None,
                        right:Optional[Union[float, bool]]=None,
                        top:Optional[Union[float, bool]]=None,
                        bottom:Optional[Union[float, bool]]=None,
                        color:PyGameColor=(0, 0, 0, 0),
                        width:int=1, border=0, transparency_enabled:bool=False,
                        density:Optional[float]=None, elasticity:Optional[float]=None, friction:Optional[float]=None) -> None:

    fixed_object=True
    can_rotate=True
    velocity:Vector2=Vec2d.zero()
    angular_velocity:float=0.

    left = (0. if left else None) if isinstance(left, bool) else left
    right = (0. if right else None) if isinstance(right, bool) else right
    top = (0. if top else None) if isinstance(top, bool) else top
    bottom = (0. if bottom else None) if isinstance(bottom, bool) else bottom

    if left is not None:
        actor = create_rect(width=width, height=screen_height(),
                            bottom_left=(left, 0),
                            color=color, border=border,
                            transparency_enabled=transparency_enabled,
                            density=density, elasticity=elasticity, friction=friction,
                            fixed_object=fixed_object, can_rotate=can_rotate,
                            velocity=velocity, angular_velocity=angular_velocity)
    if right is not None:
        actor = create_rect(width=width, height=screen_height(),
                            bottom_left=(screen_width()-right-border*2-width-1, 0),
                            color=color, border=border,
                            transparency_enabled=transparency_enabled,
                            density=density, elasticity=elasticity, friction=friction,
                            fixed_object=fixed_object, can_rotate=can_rotate,
                            velocity=velocity, angular_velocity=angular_velocity)
    if top is not None:
        actor = create_rect(width=screen_width(), height=width,
                            bottom_left=(0, screen_height()-top-border*2-width-1),
                            color=color, border=border,
                            transparency_enabled=transparency_enabled,
                            density=density, elasticity=elasticity, friction=friction,
                            fixed_object=fixed_object, can_rotate=can_rotate,
                            velocity=velocity, angular_velocity=angular_velocity)
    if bottom is not None:
        actor = create_rect(width=screen_width(), height=width,
                            bottom_left=(0, bottom),
                            color=color, border=border,
                            transparency_enabled=transparency_enabled,
                            density=density, elasticity=elasticity, friction=friction,
                            fixed_object=fixed_object, can_rotate=can_rotate,
                            velocity=velocity, angular_velocity=angular_velocity)


def start(screen_title:str=_screen_props.title,
          screen_width=_screen_props.width,
          screen_height=_screen_props.height,
          screen_color:PyGameColor=_screen_props.color,
          screen_image_path:Optional[str]=_screen_props.image_path,
          screen_fps=_screen_props.fps,
          physics_fps_multiplier:int=4,
          gravity:Optional[Union[float, Vector2]]=None):

    global  _running, screen, draw_options, noone, _physics_fps_multiplier

    set_screen_size(screen_width, screen_height)
    set_screen_color(screen_color)
    set_screen_image(screen_image_path)
    set_screen_fps(screen_fps)
    set_screen_title(screen_title)

    _running = True
    _physics_fps_multiplier = physics_fps_multiplier

    if gravity is not None:
        if not isinstance(gravity, Iterable):
            gravity = (0.0, gravity)
        space.gravity = Vec2d(*gravity)

    space.sleep_time_threshold = 0.3

    assert screen is not None, "screen is None"
    draw_options = pygame_util.DrawOptions(screen)

    # create No One actor to handle global events, put it offscreen
    noone = create_rect(width=1, height=1,
                        color=(0, 0, 0, 0), bottom_left=(-1000,-1000), visible=False)
    # this body doesn't collide with anything
    noone.shape.filter = pymunk.ShapeFilter(categories=0x1, mask=0x0)

def remove(actor:Actor):
    """Remove actor from game"""
    _actors.remove(actor)
    space.remove(actor.shape, actor.shape.body)

def screen_size()->Tuple[int, int]:
    return _screen_props.width, _screen_props.height
def screen_width()->int:
    return _screen_props.width
def screen_height()->int:
    return _screen_props.height
def set_screen_size(width:int, height:int):
    global screen
    screen = pygame.display.set_mode((width, height))
    _screen_props.width = width
    _screen_props.height = height
    _scale_screen_image()

def set_screen_color(color:PyGameColor):
    _screen_props.color = color

def _scale_screen_image():
    if _screen_props.image:
        _screen_props.image_scaled = pygame.transform.scale(_screen_props.image, screen_size())
    else:
        _screen_props.image_scaled = None

def set_screen_image(image_path:Optional[str]):
    if image_path is not None:
        _screen_props.image = common.get_image(image_path)
    else:
        _screen_props.image = None
    _scale_screen_image()
    _screen_props.image_path = image_path

def set_screen_fps(fps:int):
    _screen_props.fps = fps

def set_screen_title(title:str):
    pygame.display.set_caption(title)
    _screen_props.title = title

def on_frame():
    pass

def mouse_button_name(button:int)->str:
    if button == 1:
        return "left"
    elif button == 2:
        return "middle"
    elif button == 3:
        return "right"
    else:
        return str(button)

def update():
    global _running, screen
    assert screen is not None, "screen is None"

    if not _running:
        return

    # first call physics so manual overrides can happen later
    # use fixed fps for dt instead of actual dt
    physics_fps = _screen_props.fps * _physics_fps_multiplier
    for _ in range(_physics_fps_multiplier):
        space.step(1.0 / physics_fps)

    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    # TODO: optimize this by registering actors for events instead of looping through all actors
    # TODO: ability to remove handler
    # TODO: ability to remove actor
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit = True
            for actor in _actors_handlers.get(pygame.QUIT, []):
                quit = quit or actor.on_quit()
            if quit:
                end()
        if event.type == pygame.KEYDOWN:
            key_name = pygame.key.name(event.key)
            down_keys.add(key_name)
            for actor in _actors_handlers.get(pygame.KEYDOWN, []):
                actor.on_keydown(key_name, event.key,
                                 event.mod, event.unicode,
                                 event.scancode, event.window)
        if event.type == pygame.KEYUP:
            key_name = pygame.key.name(event.key)
            for actor in _actors_handlers.get(pygame.KEYUP, []):
                actor.on_keyup(key_name, event.key,
                                 event.mod,
                                 event.scancode, event.window)
        if event.type == pygame.MOUSEBUTTONDOWN:
            button_name = mouse_button_name(event.button)
            pos = pygame_util.from_pygame(Vec2d(*event.pos), screen)
            for actor in _actors_handlers.get(pygame.MOUSEBUTTONDOWN, []):
                actor.on_mousedown(pos, button_name, event.button,
                                   event.touch, event.window)
        if event.type == pygame.MOUSEBUTTONUP:
            button_name = mouse_button_name(event.button)
            down_mousbuttons.remove(button_name)
            pos = pygame_util.from_pygame(Vec2d(*event.pos), screen)
            for actor in _actors_handlers.get(pygame.MOUSEBUTTONUP, []):
                actor.on_mouseup(pos, button_name, event.button,
                                 event.touch, event.window)
        if event.type == pygame.MOUSEMOTION:
            pos = pygame_util.from_pygame(Vec2d(*event.pos), screen)
            for actor in _actors_handlers.get(pygame.MOUSEMOTION, []):
                actor.on_mousemove(pos, event.rel, event.buttons,
                                   event.touch, event.window)
        if event.type == pygame.MOUSEWHEEL:
            for actor in _actors_handlers.get(pygame.MOUSEWHEEL, []):
                actor.on_mousewheel(event.x, event.y, event.flipped,
                                    event.touch, event.window)

        if event.type==pygame.KEYUP and down_keys:
            for actor in _actors_handlers.get(pygame.KEYUP, []):
                actor.on_keypress(down_keys)
            down_keys.clear()
        if event.type==pygame.MOUSEBUTTONUP and down_mousbuttons:
            for actor in _actors_handlers.get(pygame.MOUSEBUTTONUP, []):
                actor.on_mousebutton(down_mousbuttons)
            down_mousbuttons.clear()

    # call on_frame() to update your game state
    on_frame()

    assert screen is not None, "screen is None"

    if _screen_props.color:
        screen.fill(_screen_props.color)
    if _screen_props.image_scaled:
        screen.blit(_screen_props.image_scaled, (0, 0))

    for actor in _actors:
        actor.update()
    for actor in _actors:
        actor.draw(screen)

    # draw texts from noone
    common.draw_texts(screen, noone.texts)

    if show_mouse_coordinates:
        common.print_to(screen, f'{mouse_xy()}')

    # flip() the display to put your work on screen
    pygame.display.flip()

    # This will pause the game loop until 1/60 seconds have passed
    # since the last tick. This limits the loop to _running at 60 FPS.
    clock.tick(_screen_props.fps)

def too_left(actor:Actor)->bool:
    return actor.left() < 0
def too_right(actor:Actor)->bool:
    return actor.right() > screen_width()
def too_top(actor:Actor)->bool:
    return actor.top() > screen_height()
def too_bottom(actor:Actor)->bool:
    return actor.bottom() < 0

def mouse_xy()->Tuple[int, int]:
    assert screen is not None, "screen is None"
    return pygame_util.from_pygame(pygame.mouse.get_pos(), screen)

def play_sound(file_path:str, loops:int=0, volume:float=1., max_time=0, fade_ms=0)->pygame.mixer.Sound:
    global _sounds

    if file_path not in _sounds:
        sound = pygame.mixer.Sound(utils.full_path_abs(file_path))
        sound.set_volume(volume)
        _sounds[file_path] = sound
    sound = _sounds[file_path]

    sound.play(loops, max_time, fade_ms)
    return sound

def stop_sound(file_path:str)->None:
    global _sounds

    if file_path in _sounds:
        _sounds[file_path].stop()

def end():
    global _running

    if _running:
        pygame.quit()
        pygame.display.quit()
        pygame.mixer.quit()
        _running = False
        exit(0)
