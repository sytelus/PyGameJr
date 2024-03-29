from typing import Any, Dict, List, Optional, Set, Tuple, Union, Iterable, Callable, Sequence, Sized, Iterator
import math
import timeit

import pygame
import pymunk
from pymunk import pygame_util, Vec2d

from pygamejr.common import PyGameColor, AnimationSpec, TextInfo,  \
                            CostumeSpec, Coordinates, \
                            DrawOptions, ImagePaintMode, Camera, draw_shape, \
                            Grounding
from pygamejr import common


class Actor:
    def __init__(self,
                 shape:pymunk.Shape,
                 color:PyGameColor="green",
                 border=0,
                 image_paths:Optional[Union[str, Iterable[str]]]=None,
                 image_scale_xy:Tuple[float,float]=(1., 1.),
                 image_transparent_color:Optional[PyGameColor]=None,
                 image_transparency_enabled:bool=True,
                 image_paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                 visible:bool=True,
                 draw_options:Optional[DrawOptions]=None):

        self.shape = shape
        self.color = color
        self.border = border
        self.draw_options = draw_options
        self.visible = visible

        self.texts:Dict[str, TextInfo] = {}

        self.costumes:Dict[str, CostumeSpec] = {}
        self.current_costume:Optional[CostumeSpec] = None

        if image_paths:
            self.add_costume("", image_paths=image_paths,
                            scale_xy=image_scale_xy,
                            transparent_color=image_transparent_color,
                            transparency_enabled=image_transparency_enabled,
                            paint_mode=image_paint_mode,
                            change=True)

    def start_animation(self, loop:bool=True, from_index=0, frame_time_s:float=0.2):
        if self.current_costume is not None:
            self.current_costume.animation.start(loop, from_index, frame_time_s)
    def stop_animation(self):
        if self.current_costume is not None:
            self.current_costume.animation.stop()

    def show(self):
        self.visible = True
    def hide(self):
        self.visible = False

    @property
    def velocity(self)->Vec2d:
        return self.shape.body.velocity
    @velocity.setter
    def velocity(self, value:Vec2d):
        self.shape.body.velocity = value
    @property
    def position(self)->Vec2d:
        return self.shape.body.position
    @position.setter
    def position(self, value:Vec2d):
        self.shape.body.position = value
    @property
    def angle(self)->float:
        return math.degrees(self.shape.body.angle)
    @angle.setter
    def angle(self, value:float):
        self.shape.body.angle = math.radians(value)
    @property
    def angular_velocity(self)->float:
        return math.degrees(self.shape.body.angular_velocity)
    @angular_velocity.setter
    def angular_velocity(self, value:float):
        self.shape.body.angular_velocity = math.radians(value)
    @property
    def mass(self)->float:
        return self.shape.body.mass
    @mass.setter
    def mass(self, value:float):
        self.shape.body.mass = value
    @property
    def moment(self)->float:
        return self.shape.body.moment
    @moment.setter
    def moment(self, value:float):
        self.shape.body.moment = value
    @property
    def friction(self)->float:
        return self.shape.friction
    @friction.setter
    def friction(self, value:float):
        self.shape.friction = value
    @property
    def elasticity(self)->float:
        return self.shape.elasticity
    @elasticity.setter
    def elasticity(self, value:float):
        self.shape.elasticity = value
    @property
    def collision_type(self)->int:
        return self.shape.collision_type
    @collision_type.setter
    def collision_type(self, value:int):
        self.shape.collision_type = value
    @property
    def group(self)->int:
        return self.shape.group
    @group.setter
    def group(self, value:int):
        self.shape.group = value

    def apply_force(self, force:Coordinates, local_point:Coordinates=(0,0))->None:
        self.shape.body.apply_force_at_local_point(force, local_point)
    def apply_impulse(self, impulse:Coordinates, local_point:Coordinates=(0,0))->None:
        self.shape.body.apply_impulse_at_local_point(impulse, local_point)
    def apply_torque(self, torque:float)->None:
        self.shape.body.apply_torque(torque)
    def apply_local_force(self, force:Coordinates, local_point:Coordinates=(0,0))->None:
        self.shape.body.apply_force_at_local_point(force, local_point)
    def apply_local_impulse(self, impulse:Coordinates, local_point:Coordinates=(0,0))->None:
        self.shape.body.apply_impulse_at_local_point(impulse, local_point)
    def apply_impulse_torque(self, impulse_torque):
        """
        Apply an impulse torque to a PyMunk body.

        :param body: The PyMunk body to which the impulse torque is applied.
        :param impulse_torque: The amount of impulse torque to apply.
        """
        # Angular impulse is change in angular momentum, which is I * Δω
        # Δω (change in angular velocity) = impulse_torque / moment_of_inertia
        if self.shape.body.moment.iszero():
            return
        angular_velocity_change = impulse_torque / self.shape.body.moment
        self.shape.body.angular_velocity += angular_velocity_change

    def add_costume(self, name:str, image_paths:Union[str, Iterable[str]],
                    scale_xy:Tuple[float,float]=(1., 1.),
                    transparent_color:Optional[PyGameColor]=None,
                    transparency_enabled:bool=False,
                    paint_mode:ImagePaintMode=ImagePaintMode.CENTER,
                    change:bool=False):

        costume = CostumeSpec(name, image_paths,
                        transparent_color=transparent_color,
                        transparency_enabled=transparency_enabled,
                        paint_mode=paint_mode)
        costume.scale_xy = scale_xy
        self.costumes[name] = costume

        costume.add_images(image_paths)

        if change:
            self.current_costume = costume

    def add_text(self, text:str, pos:Coordinates=(0,0),
              font_name:Optional[str]=None, font_size:int=20,
              color:PyGameColor="black",
              background_color:Optional[PyGameColor]=None,
              name:Optional[str]=None)->TextInfo:
        if name is None:
            name = text
        self.texts[name] = TextInfo(text=text, pos=pos,
                                    font_name=font_name, font_size=font_size,
                                    color=color, background_color=background_color)
        return self.texts[name]

    def remove_text(self, text:str, name:Optional[str]=None)->None:
        name = name or text
        if name in self.texts:
            del self.texts[name]

    def set_cosume(self, name:Optional[str])->None:
        if name is None:
            self.current_costume = None
        else:
            self.current_costume = self.costumes[name]

    def glide_to(self, xy:Coordinates, speed:float=1.0)->None:
        """Smoothly move the body to a new position."""
        target_vector = Vec2d(*xy) - self.shape.body.position
        if target_vector.length > 0:
            target_vector = target_vector.normalized() * speed
            self.shape.body.position = self.shape.body.position + target_vector

    def move_by(self, delta:Coordinates)->None:
        """Move the body by a vector."""
        self.shape.body.position = self.shape.body.position + Vec2d(*delta)
    def move_to(self, xy:Coordinates)->None:
        """Move the body to a new position."""
        self.shape.body.position = Vec2d(*xy)

    def turn_by(self, angle:float)->None:
        """Turn the body by an angle."""
        self.shape.body.angle += math.radians(angle)

    def turn_to(self, angle:float)->None:
        """Turn the body to an angle."""
        self.shape.body.angle = math.radians(angle)

    def turn_towards(self, xy:Coordinates)->None:
        """Turn the body towards a point."""
        target_vector = Vec2d(*xy) - self.shape.body.position
        self.shape.body.angle = target_vector.angle

    @property
    def surface_velocity(self)->Vec2d:
        return self.shape.surface_velocity
    @surface_velocity.setter
    def surface_velocity(self, value:Vec2d):
        self.shape.surface_velocity = value

    def touches_at(self, point:Coordinates)->bool:
        query_result = self.shape.point_query(point)
        return query_result.distance <= 0


    def touches(self, other:Optional[Union['Actor', Sequence['Actor']]])->bool:
        if self.shape.space is None:
            return False

        colliding_shapes = self.shape.space.shape_query(self.shape)

        if other  is None:
            other = []
        elif not isinstance(other, Sequence):
            other = [other]

        if len(other) == 0:
            return len(colliding_shapes) > 0
        else:
            other_shapes = {o.shape:o for o in other}
            return any(other_shapes[s.shape] for s in colliding_shapes if s.shape in other_shapes)

    def distance_to(self, xy:Coordinates)->float:
        """Return the distance to another sprite."""
        target_vector = Vec2d(*xy) - self.shape.body.position
        return target_vector.length

    def x(self)->float:
        return self.shape.body.position.x
    def y(self)->float:
        return self.shape.body.position.y
    def center(self)->Vec2d:
        return Vec2d(self.x(), self.y())
    def width(self)->float:
        self.shape.cache_bb()
        return self.shape.bb.right - self.shape.bb.left
    def height(self)->float:
        self.shape.cache_bb()
        return self.shape.bb.top - self.shape.bb.bottom
    def topleft(self)->Vec2d:
        self.shape.cache_bb()
        return Vec2d(self.shape.bb.left, self.shape.bb.top)
    def topright(self)->Vec2d:
        self.shape.cache_bb()
        return Vec2d(self.shape.bb.right, self.shape.bb.top)
    def bottomleft(self)->Vec2d:
        self.shape.cache_bb()
        return Vec2d(self.shape.bb.left, self.shape.bb.bottom)
    def bottomright(self)->Vec2d:
        self.shape.cache_bb()
        return Vec2d(self.shape.bb.right, self.shape.bb.bottom)
    def top(self)->float:
        self.shape.cache_bb()
        return self.shape.bb.top
    def bottom(self)->float:
        self.shape.cache_bb()
        return self.shape.bb.bottom
    def left(self)->float:
        self.shape.cache_bb()
        return self.shape.bb.left
    def right(self)->float:
        self.shape.cache_bb()
        return self.shape.bb.right
    def rect(self)->Tuple[float, float, float, float]:
        self.shape.cache_bb()
        return (self.shape.bb.left, self.shape.bb.top, self.width(), self.height())
    def is_hidden(self)->bool:
        return not self.visible


    def remove_costume(self, name:str)->None:
        if name in self.costumes:
            del self.costumes[name]
            if self.current_costume is not None and self.current_costume.name == name:
                self.set_cosume(None)

    def update(self)->None:
        if self.current_costume is not None:
            self.current_costume.update()

    def _recreate_shape(self, new_width, new_height)->None:
        self.shape.cache_bb()
        width, height = self.width(), self.height()
        body, space, offset = self.shape.body, self.shape.space, self.shape.offset
        assert space is not None
        space.remove(self.shape)
        if isinstance(self.shape, pymunk.Circle):
            self.shape = pymunk.Circle(body, max(new_width, new_height)/2., offset)
        elif isinstance(self.shape, pymunk.Poly):
            vertices, radius = self.shape.get_vertices(), self.shape.radius
            x_scale, y_scale = new_width/width, new_height/height
            vertices = [(v.x*x_scale, v.y*y_scale) for v in vertices]
            self.shape = pymunk.Poly(body, vertices, radius=radius)
        elif isinstance(self.shape, pymunk.Segment):
            a, b, radius = self.shape.a, self.shape.b, self.shape.radius
            a = (a.x*new_width/width, a.y*new_height/height)
            b = (b.x*new_width/width, b.y*new_height/height)
            self.shape = pymunk.Segment(body, a, b, radius)
        else:
            raise ValueError(f"Unknown shape type {self.shape}")
        space.add(self.shape)


    def is_grounded(self)->bool:
        if self.shape.space is None:
            return False

        colliding_shapes = self.shape.space.shape_query(self.shape)

        for s in colliding_shapes:
            if s.shape is not None and s.shape.body is not None and s.shape.body != self.shape.body:
                n = s.contact_point_set.normal
                if n.y > 0:
                    return True
        return False

    def get_grounding(self)->Grounding:
        grounding = Grounding()
        def f(arbitrater):
            n = arbitrater.contact_point_set.normal
            if n.y > grounding.normal.y:
                grounding.normal = n
                grounding.penetration = -arbitrater.contact_point_set.points[0].distance
                grounding.impulse = arbitrater.total_impulse
                grounding.position = arbitrater.contact_point_set.points[0].point_b
                grounding.has_body = arbitrater.shapes[1].body is not None
                if grounding.has_body:
                    grounding.friction = abs(n.x/n.y)
                    grounding.velocity = arbitrater.shapes[1].body.velocity

        self.shape.body.each_arbiter(f)

        return grounding


    def fit_to_image(self)->None:
        if self.current_costume is not None and len(self.current_costume.images):
            new_width, new_height = self.current_costume.images[0].get_size()
            if isinstance(self.shape, pymunk.Circle):
                self.shape.unsafe_set_radius(max(new_width, new_height)/2.)
            elif isinstance(self.shape, pymunk.Poly):
                vertices = self.shape.get_vertices()
                x_scale, y_scale = new_width/self.width(), new_height/self.height()
                vertices = [(v.x*x_scale, v.y*y_scale) for v in vertices]
                self.shape.unsafe_set_vertices(vertices)
            elif isinstance(self.shape, pymunk.Segment):
                a, b = self.shape.a, self.shape.b
                a = (a.x*new_width/self.width(), a.y*new_height/self.height())
                b = (b.x*new_width/self.width(), b.y*new_height/self.height())
                self.shape.unsafe_set_endpoints(a, b)

    def fit_image(self)->None:
        if self.current_costume is not None and len(self.current_costume):
            new_width, new_height = self.width(), self.height()
            old_width, old_height = self.current_costume.get_image().get_size()
            scale_xy = (new_width/old_width, new_height/old_height)
            self.current_costume.scale_xy = scale_xy

    def on_keypress(self, keys:Set[str]):
        pass

    def on_keydown(self, key_name:str, key_code:int, mod:int, scancode:int, window:int, unicode:str):
        pass

    def on_keyup(self, key_name:str, key_code:int, mod:int, scancode:int, window:int):
        pass

    def on_mousebutton(self, buttons:Set[str]):
        pass

    def on_mousedown(self, pos:Tuple[int, int], button:str, button_num:int,
                     is_touch:bool, window_id:int):
        pass

    def on_mouseup(self, pos:Tuple[int, int], button:str, button_num:int,
                   is_touch:bool, window_id:int):
        pass

    def on_mousemove(self, pos:Tuple[int, int], rel:Tuple[int, int], buttons:Sequence[bool],
                     is_touch:bool, window_id:int):
        pass

    def on_mousewheel(self, horizotal_scroll:float, vertical_scroll:float, is_flipped:bool,
                      is_touch:bool, window_id:int):
        pass

    def on_quit(self)->bool:
        return False # continue quiting

    def draw(self, screen:pygame.Surface, camera:Camera)->None:
        if self.visible:
            draw_shape(screen, shape=self.shape,
                                         texts=self.texts,
                                         color=self.color,
                                         border=self.border,
                                         draw_options=self.draw_options,
                                         camera=camera,
                                         costume=self.current_costume)

