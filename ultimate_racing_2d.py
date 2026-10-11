import math
import json
import os
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

import pygame



# Utilities

Vec2 = pygame.math.Vector2

def asset_key(name: str) -> str:
    # "Apex GT" -> "apex_gt"
    return name.lower().replace(" ", "_")


# Weather Effects System


@dataclass
class WeatherEffect:
    name: str
    climate: str
    visibility_factor: float  # 1.0 = clear, 0.5 = foggy
    track_friction_modifier: float  # 1.0 = normal
    max_speed_modifier: float  # 1.0 = normal
    handling_modifier: float  # 1.0 = normal
    particle_count: int  # Number of weather particles
    particle_color: Tuple[int, int, int]
    particle_size_range: Tuple[int, int]
    sound_volume: float = 0.0
    sound_looped: bool = False
    light_level: int = 255  # 255 = full daylight
    fog_color: Tuple[int, int, int] = (200, 220, 240)

# Define different weather types
weather_effects = {
    "clear": WeatherEffect(
        name="Clear",
        climate="dry",
        visibility_factor=1.0,
        track_friction_modifier=1.0,
        max_speed_modifier=1.0,
        handling_modifier=1.0,
        particle_count=0,
        particle_color=(255, 255, 255),
        particle_size_range=(1, 1)
    ),
    "rain": WeatherEffect(
        name="Rain",
        climate="wet",
        visibility_factor=0.7,
        track_friction_modifier=0.85,  # Less friction on wet track
        max_speed_modifier=0.95,  # Slightly slower
        handling_modifier=0.85,  # Harder to control
        particle_count=200,
        particle_color=(150, 180, 220),
        particle_size_range=(2, 5),
        sound_volume=0.3,
        sound_looped=True,
        light_level=180,
        fog_color=(100, 130, 170)
    ),
    "heavy_rain": WeatherEffect(
        name="Heavy Rain",
        climate="wet",
        visibility_factor=0.5,
        track_friction_modifier=0.75,
        max_speed_modifier=0.9,
        handling_modifier=0.75,
        particle_count=400,
        particle_color=(120, 150, 190),
        particle_size_range=(3, 7),
        sound_volume=0.5,
        sound_looped=True,
        light_level=150,
        fog_color=(80, 110, 150)
    ),
    "snow": WeatherEffect(
        name="Snow",
        climate="snow",
        visibility_factor=0.6,
        track_friction_modifier=0.7,  # Very slippery
        max_speed_modifier=0.85,
        handling_modifier=0.65,
        particle_count=150,
        particle_color=(240, 240, 255),
        particle_size_range=(3, 8),
        sound_volume=0.1,
        sound_looped=True,
        light_level=200,
        fog_color=(220, 230, 240)
    ),
    "fog": WeatherEffect(
        name="Fog",
        climate="dry",
        visibility_factor=0.4,
        track_friction_modifier=1.0,
        max_speed_modifier=1.0,
        handling_modifier=0.9,  # Harder to see corners
        particle_count=100,
        particle_color=(200, 210, 220),
        particle_size_range=(10, 30),
        sound_volume=0.0,
        light_level=180,
        fog_color=(180, 190, 210)
    ),
    "sandstorm": WeatherEffect(
        name="Sandstorm",
        climate="dry",
        visibility_factor=0.3,
        track_friction_modifier=0.9,
        max_speed_modifier=0.8,  # Wind resistance
        handling_modifier=0.7,
        particle_count=180,
        particle_color=(210, 190, 150),
        particle_size_range=(4, 9),
        sound_volume=0.4,
        sound_looped=True,
        light_level=160,
        fog_color=(190, 170, 140)
    )
}

# Asset Loader, loads the assets from the packs

class AssetLoader:
    def __init__(self):
        # the use of dictionaries is used to store loaded assets by the name 
        # this can prevent loading the same file multiple times
        self.car_sprites: Dict[str, pygame.Surface] = {}
        self.track_bg:    Dict[str, pygame.Surface] = {}
        self.powerup_sprites: Dict[str, pygame.Surface] = {}
        self.ui_sprites:    Dict[str, pygame.Surface] = {}
        self.sounds:        Dict[str, pygame.mixer.Sound] = {}
        self.music:         Dict[str, str] = {}
        self.obstacle_sprites: Dict[str, pygame.Surface] = {}
        self.sprite: Optional[pygame.Surface] = None

    def load_car(self, name: str, scale: float = 1.0) -> Optional[pygame.Surface]:
        KENNEY_CAR_FILES = {
            "Starter":   "car_red_1.png",
            "Sprinter":  "car_blue_1.png",
            "Gripster":  "car_green_1.png",
            "Bruiser":   "car_yellow_1.png",
            "Apex GT":   "car_black_1.png",
        }

        cache_key = f"{name}@{scale}"
        if cache_key in self.car_sprites:
            return self.car_sprites[cache_key]

        filename = KENNEY_CAR_FILES.get(name, f"{asset_key(name)}.png")

        candidates = [
            os.path.join("images", "kenney", "PNG", "Cars", filename),
            os.path.join("images", "kenny",  "PNG", "Cars", filename),
            os.path.join("assets", "kenney", "PNG", "Cars", filename),
            os.path.join("assets", "kenny",  "PNG", "Cars", filename),
        ]

        path = next((p for p in candidates if os.path.exists(p)), None)
        if not path:
            print(f"[load_car] Missing file for '{name}'. Tried:\n  " + "\n  ".join(candidates))
            return None

        try:
            surf = pygame.image.load(path).convert_alpha()

            if scale != 1.0:
                w = max(1, int(surf.get_width() * scale))
                h = max(1, int(surf.get_height() * scale))
                surf = pygame.transform.smoothscale(surf, (w, h))

            self.car_sprites[cache_key] = surf
            print(f"[load_car] Loaded '{name}' from: {path}")
            return surf

        except Exception as e:
            print(f"[load_car] Failed to load '{name}' from {path}: {e}")
            return None

    def load_track_bg(self, name: str) -> Optional[pygame.Surface]:
        """Load full track background image"""
        if name in self.track_bg:
            return self.track_bg[name]

        candidates = [
            os.path.join("assets", "tracks", f"{asset_key(name)}.png"),
            os.path.join("assets", "tracks", f"{name}.png"),
        ]
        path = next((p for p in candidates if os.path.exists(p)), None)
        if not path:
            return None

        try:
            surf = pygame.image.load(path).convert()
            self.track_bg[name] = surf
            return surf
        except Exception as e:
            print(f"Failed to load track {name}: {e}")
            return None

    def load_powerup(self, kind: str) -> Optional[pygame.Surface]:
        """Load powerup sprite"""
        if kind in self.powerup_sprites:
            return self.powerup_sprites[kind]

        try:
            # Try to load from assets first
            path = f"assets/powerups/{kind}.png"
            if os.path.exists(path):
                surf = pygame.image.load(path).convert_alpha()
            else:
                # Create a colored circle for the powerup
                surf = pygame.Surface((36, 36), pygame.SRCALPHA)
                colors = {
                    "nitro": (110, 190, 255),
                    "repair": (120, 255, 140),
                    "shield": (200, 180, 255),
                    "speed": (255, 220, 100),
                    "magnet": (255, 150, 150)
                }
                color = colors.get(kind, (200, 200, 200))
                pygame.draw.circle(surf, color, (18, 18), 16)
                pygame.draw.circle(surf, (255, 255, 255), (18, 18), 16, 2)
                
                # Add symbol
                font = pygame.font.Font(None, 24)
                symbols = {
                    "nitro": "N",
                    "repair": "+",
                    "shield": "S",
                    "speed": "Sp",
                    "magnet": "M"
                }
                symbol = symbols.get(kind, "?")
                text = font.render(symbol, True, (0, 0, 0))
                surf.blit(text, (18 - text.get_width() // 2, 18 - text.get_height() // 2))
            
            surf = pygame.transform.smoothscale(surf, (36, 36))
            self.powerup_sprites[kind] = surf
            return surf
        except Exception as e:
            print(f"Failed to load powerup {kind}: {e}")
            return None

    def load_obstacle(self, kind: str) -> Optional[pygame.Surface]:
        """Load obstacle sprite"""
        if kind in self.obstacle_sprites:
            return self.obstacle_sprites[kind]

        try:
            path = f"assets/obstacles/{kind}.png"
            if not os.path.exists(path):
                surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                if kind == "barrel":
                    pygame.draw.circle(surf, (139, 69, 19), (20, 20), 18)
                    pygame.draw.circle(surf, (160, 82, 45), (20, 20), 15)
                    pygame.draw.circle(surf, (205, 133, 63), (20, 20), 12)
                    pygame.draw.line(surf, (160, 82, 45), (8, 20), (32, 20), 3)
                    pygame.draw.line(surf, (160, 82, 45), (20, 8), (20, 32), 3)
                elif kind == "cone":
                    points = [(20, 5), (5, 40), (35, 40)]
                    pygame.draw.polygon(surf, (255, 140, 0), points)
                    pygame.draw.polygon(surf, (255, 165, 0), points, 3)
                    for i in range(3):
                        y = 15 + i * 8
                        pygame.draw.line(surf, (255, 255, 255), (10, y), (30, y), 3)
                elif kind == "crate":
                    pygame.draw.rect(surf, (160, 120, 60), (5, 5, 30, 30))
                    pygame.draw.rect(surf, (140, 100, 40), (5, 5, 30, 30), 3)
                    for i in range(1, 4):
                        pygame.draw.line(surf, (120, 80, 30), (5, 5 + i*7), (35, 5 + i*7), 2)
                        pygame.draw.line(surf, (120, 80, 30), (5 + i*7, 5), (5 + i*7, 35), 2)
                elif kind == "rock":
                    pygame.draw.circle(surf, (100, 100, 100), (20, 20), 18)
                    pygame.draw.circle(surf, (120, 120, 120), (15, 15), 5)
                    pygame.draw.circle(surf, (120, 120, 120), (25, 25), 4)
                    pygame.draw.circle(surf, (80, 80, 80), (20, 25), 3)
                elif kind == "spike":
                    pygame.draw.rect(surf, (150, 150, 150), (10, 15, 20, 10))
                    for i in range(4):
                        x = 12 + i * 6
                        points = [(x, 25), (x + 3, 15), (x + 6, 25)]
                        pygame.draw.polygon(surf, (200, 50, 50), points)
                else:
                    pygame.draw.rect(surf, (220, 80, 80), (0, 0, 40, 40), border_radius=6)
                    pygame.draw.rect(surf, (255, 100, 100), (5, 5, 30, 30), border_radius=4)
                    font = pygame.font.Font(None, 24)
                    text = font.render("!", True, (255, 255, 255))
                    surf.blit(text, (15, 12))
            else:
                surf = pygame.image.load(path).convert_alpha()
                surf = pygame.transform.smoothscale(surf, (40, 40))

            self.obstacle_sprites[kind] = surf
            return surf
        except Exception as e:
            print(f"Failed to load obstacle {kind}: {e}")
            return None



# Helper functions

def clamp(x: float, a: float, b: float) -> float:   # the clamp function will prevent values from exceeding the limit, keeping the speed at a limit
    return a if x < a else b if x > b else x


def lerp(a: float, b: float, t: float) -> float:      # the lerp function will enable smooth acceleration of the racing cars and camera movement
    return a + (b - a) * t


def wrap_angle_rad(a: float) -> float:     # This will prevent any glitches when the user steers their racing car 
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def circle_rect_collision(center: Vec2, radius: float, rect: pygame.Rect) -> Tuple[bool, Vec2, float]:
    #create a docstring to make the function purpose more understandable
    """
    Docstring for circle_rect_collision
    
    :param center: Description
    :type center: Vec2
    :param radius: Description
    :type radius: float
    :param rect: Description
    :type rect: pygame.Rect
    :return: Description
    :rtype: Tuple[bool, Vec2, float]
    """
    # Find the closest point on rectangle to circle center  
    closest_x = clamp(center.x, rect.left, rect.right)
    closest_y = clamp(center.y, rect.top, rect.bottom)
    closest = Vec2(closest_x, closest_y)
    # Calculate the distance vector from closest point to circle center
    delta = center - closest
    dist2 = delta.length_squared() # distance squared for efficiency 
    if dist2 > radius * radius:  # No collision if distance > radius
        return False, Vec2(0, 0), 0.0
    dist = math.sqrt(dist2) if dist2 > 1e-9 else 0.0 # Calculate actual distance
    if dist > 1e-6: # Normal collision case
        normal = delta / dist  # Normalized collision direction
        penetration = radius - dist # How much the objects overlap
        return True, normal, penetration
    
     # circle center inside rectangle
    left_d  = abs(center.x - rect.left)
    right_d = abs(rect.right - center.x)
    top_d   = abs(center.y - rect.top)
    bot_d   = abs(rect.bottom - center.y)
    m = min(left_d, right_d, top_d, bot_d)

    # Return normal pointing to closest edge
    if m == left_d:
        return True, Vec2(-1, 0), radius
    if m == right_d:
        return True, Vec2(1, 0), radius
    if m == top_d:
        return True, Vec2(0, -1), radius
    return True, Vec2(0, 1), radius


def draw_text(surf: pygame.Surface, text: str, pos: Tuple[int, int], font: pygame.font.Font,
              color=(240, 240, 240), shadow=True):
    x, y = pos
    if shadow:
        img = font.render(text, True, (0, 0, 0))
        surf.blit(img, (x + 2, y + 2))
    img = font.render(text, True, color)
    surf.blit(img, (x, y))



# Dynamic Obstacle Types

@dataclass
class DynamicObstacle:
    pos: Vec2
    radius: float = 20
    active: bool = True
    obstacle_type: str = "generic"
    health: float = 100.0
    damage: float = 8.0
    respawn_time: float = 8.0
    respawn_timer: float = 0.0
    track: Optional['Track'] = None
    last_update_time: float = 0.0

    def update(self, dt: float, current_time: float):
        if not self.active:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.respawn_timer = 0.0
                self.active = True
                self.health = 100.0

    def hit(self, damage: float = 100.0):
        self.health -= damage
        if self.health <= 0:
            self.active = False
            self.respawn_timer = self.respawn_time
            return True
        return False

    def get_collision_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.pos.x - self.radius),
                          int(self.pos.y - self.radius),
                          int(self.radius * 2),
                          int(self.radius * 2))

    def draw(self, screen: pygame.Surface, camera: Vec2, assets: AssetLoader):
        if not self.active: # if they are not active (dynamic)
            return
        p = self.pos - camera # active when cars are nearby
        sprite = assets.load_obstacle(self.obstacle_type) # loads the assets onto the obstacles
        if sprite:
            rect = sprite.get_rect(center=(int(p.x), int(p.y)))
            screen.blit(sprite, rect)

    def keep_on_track(self):
        if self.track and not self.track.on_track(self.pos):
            nearest = self.find_nearest_track_point()
            if nearest:
                self.pos = nearest

    def adjust_to_track_bounds(self, dt: float = 0.0): # allows the obstacles to travel backwards to stay within the track
        self.keep_on_track()



    def find_nearest_track_point(self) -> Optional[Vec2]:
        if not self.track or not self.track.centerline:
            return None

        pts = self.track.centerline
        nearest_i = 0
        min_dist = float("inf")

        for i, point in enumerate(pts):
            d = (point - self.pos).length_squared()
            if d < min_dist:
                min_dist = d
                nearest_i = i

        # compute tangent and perpendicular to push obstacle away from centerline
        n = len(pts)
        p_prev = pts[(nearest_i - 1) % n]
        p_next = pts[(nearest_i + 1) % n]
        tan = (p_next - p_prev)
        if tan.length_squared() > 1e-6:
            tan = tan.normalize()
        else:
            tan = Vec2(1, 0)

        perp = Vec2(-tan.y, tan.x)

        # try several offsets so it lands on-track but NOT on the center racing line
        base = pts[nearest_i]
        side = random.choice([-1, 1])
        offsets = [0.35, 0.25, 0.15, 0.0, -0.15, -0.25, -0.35]

        for off in offsets:
            cand = base + perp * (side * off * self.track.width * 0.45)
            if self.track.on_track(cand):
                return Vec2(cand.x, cand.y)

        return Vec2(base.x, base.y)



@dataclass
class MovingObstacle(DynamicObstacle):
    path: List[Vec2] = None
    speed: float = 80.0
    current_target_idx: int = 0
    pause_time: float = 1.0
    pause_timer: float = 0.0
    move_direction: int = 1
    original_path: List[Vec2] = None

    def __post_init__(self): # initlise the position to a current path
        if self.path is None:
            self.path = [self.pos]
        self.current_target_idx = 0
        self.original_path = self.path.copy()

    def update(self, dt: float, current_time: float): 
        super().update(dt, current_time) # calls the function of the parent class
        if not self.active or len(self.path) < 2:
            return

        #handles pausing the game
        if self.pause_timer > 0:
            self.pause_timer -= dt
            return

        target = self.path[self.current_target_idx] # the obstacles should be at the current path
        direction = target - self.pos # the direction vector to the target position


        # objects has reached the target point
        if direction.length() < 5:
            self.current_target_idx += self.move_direction # move to next point
            if self.current_target_idx >= len(self.path): # it reverses the direction if the path is reached
                if self.move_direction == 1:
                    self.move_direction = -1
                    self.current_target_idx = len(self.path) - 2
                else:
                    self.current_target_idx = 0
            if self.current_target_idx < 0: # ensures it stays within the valid boundaries
                self.current_target_idx = 1
                self.move_direction = 1

            self.pause_timer = self.pause_time
            return

        if direction.length() > 0: # ensures constant speed by normalising the direction of the vector
            direction = direction.normalize() 
        self.pos += direction * self.speed * dt

        self.adjust_to_track_bounds(dt) #stays within the track boundaries

        if self.track and not self.track.on_track(target):
            nearest = self.find_nearest_track_point()
            if nearest:
                self.path[self.current_target_idx] = nearest


@dataclass
class RotatingObstacle(DynamicObstacle): # rotates the obstacle within a circular path
    center: Vec2 = None
    rotation_speed: float = 1.0
    rotation_radius: float = 100.0
    current_angle: float = 0.0
    original_center: Vec2 = None

    def __post_init__(self):
        #rotates around the starting position if no centre coordinate given
        if self.center is None:
            self.center = self.pos
        self.original_center = Vec2(self.center) # store a copy of the orginal centre
        self.update_position()

    def update_position(self): # use trigonometry to calculate obstacle's position
        self.pos.x = self.center.x + math.cos(self.current_angle) * self.rotation_radius # horizontal movement
        self.pos.y = self.center.y + math.sin(self.current_angle) * self.rotation_radius # vertical movement

    def update(self, dt: float, current_time: float):
        super().update(dt, current_time) # calls the parent class to update reuse logic
        if not self.active:
            return

        self.current_angle += self.rotation_speed * dt
        self.current_angle = wrap_angle_rad(self.current_angle)
        self.update_position()

        self.adjust_to_track_bounds(dt)

    def adjust_to_track_bounds(self, dt: float = 0.0):
        if not self.track:
            return
        dt = dt or (1/60)

        # keep rotation radius reasonable for track width
        self.rotation_radius = min(self.rotation_radius, self.track.width * 0.35)

        if not self.track.on_track(self.pos):
            nearest = self.find_nearest_track_point()
            if nearest:
                delta = nearest - self.pos
                self.pos = Vec2(nearest)
                # IMPORTANT: move the center too, so orbit stays consistent
                self.center = Vec2(self.center) + delta
                self.update_position()


        if self.track and not self.track.on_track(self.pos):
            nearest = self.find_nearest_track_point()
            if nearest:
                delta = (nearest - self.center)
                if delta.length() > 0:
                    self.center += delta.normalize() * 50 * dt
                    self.update_position()


@dataclass
class PulsingObstacle(DynamicObstacle):
    min_radius: float = 15.0
    max_radius: float = 25.0
    pulse_speed: float = 2.0
    pulse_timer: float = 0.0
    damage_multiplier: float = 1.3

    def update(self, dt: float, current_time: float): # update obstacle size over time
        super().update(dt, current_time) # parent class called to reuse shared logic
        if not self.active:
            return
        self.pulse_timer += dt * self.pulse_speed * 2 * math.pi # increases based on time, creates a full sine wave
        self.pulse_timer = self.pulse_timer % (2 * math.pi) # keeps timer within valid boundaries
        t = (math.sin(self.pulse_timer) + 1) / 2
        self.radius = self.min_radius + (self.max_radius - self.min_radius) * t # range is from 0 to 1
        # when t is 0 radius is minimum
        # when t is 1 radius at maximum

    def get_current_damage(self) -> float:
        t = (math.sin(self.pulse_timer) + 1) / 2 # damages by matching the vehicle's size
        return self.damage * (1.0 + (self.damage_multiplier - 1.0) * t) # returns the damage done


@dataclass
class PatrolObstacle(DynamicObstacle):
    start_pos: Vec2 = None
    end_pos: Vec2 = None
    speed: float = 100.0
    current_t: float = 0.0
    direction: int = 1

    def __post_init__(self):
        if self.start_pos is None:
            self.start_pos = Vec2(self.pos.x - 100, self.pos.y)
        if self.end_pos is None:
            self.end_pos = Vec2(self.pos.x + 100, self.pos.y)

    def update(self, dt: float, current_time: float):
        super().update(dt, current_time)
        if not self.active:
            return

        total_dist = (self.end_pos - self.start_pos).length()
        if total_dist < 1:
            return

        dist_this_frame = self.speed * dt / total_dist
        self.current_t += dist_this_frame * self.direction

        if self.current_t >= 1.0:
            self.current_t = 1.0
            self.direction = -1
        elif self.current_t <= 0.0:
            self.current_t = 0.0
            self.direction = 1

        self.pos = self.start_pos + (self.end_pos - self.start_pos) * self.current_t

        self.adjust_to_track_bounds(dt)

        if self.track:
            if not self.track.on_track(self.start_pos):
                nearest = self.find_nearest_track_point()
                if nearest:
                    self.start_pos = nearest
            if not self.track.on_track(self.end_pos):
                nearest = self.find_nearest_track_point()
                if nearest:
                    self.end_pos = nearest



# Simple audio

class Audio:
    def __init__(self):
        self.ok = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.engine_channel: Optional[pygame.mixer.Channel] = None
        self.engine_sound:   Optional[pygame.mixer.Sound]   = None

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self.ok = True
        except Exception:
            self.ok = False

        if self.ok:
            self.sounds["boost"] = self._tone(660, 0.12, 0.4)
            self.sounds["pickup"] = self._tone(880, 0.08, 0.35)
            self.sounds["repair"] = self._tone(520, 0.12, 0.35)
            self.sounds["hit"] = self._tone(120, 0.10, 0.55)
            self.sounds["lap"] = self._tone(740, 0.14, 0.35)
            self.sounds["coin"] = self._tone(660, 0.08, 0.3)
            self.sounds["obstacle_hit"] = self._tone(220, 0.15, 0.4)
            self.sounds["obstacle_destroy"] = self._tone(440, 0.20, 0.5)
            self.sounds["death"] = self._tone(180, 0.25, 0.6)
            

            self.engine_sound = self._tone(110, 0.35, 0.18, fade=True)
            self.engine_channel = pygame.mixer.Channel(0)
            self.engine_channel.play(self.engine_sound, loops=-1)
        # Add weather sounds
            self.sounds["rain"] = self._rain_sound(0.3)
            self.sounds["heavy_rain"] = self._rain_sound(0.6)
            self.sounds["snow"] = self._wind_sound(0.2)
            self.sounds["sandstorm"] = self._wind_sound(0.5)
            
            self.current_weather_sound = None

    def set_weather_volume(self, volume: float):
        """Set volume for current weather sound"""
        if self.ok and self.current_weather_sound:
            self.current_weather_sound.set_volume(volume)
            
    def _rain_sound(self, intensity: float) -> pygame.mixer.Sound:
        sr = 44100
        duration = 1.0
        n = int(sr * duration)
        buf = bytearray()
        for i in range(n):
            t = i / sr
            # Rain is random noise with some pattern
            s = random.uniform(-1, 1) * intensity
            if i % 441 < 220:  # Create droplet pattern
                s *= 0.3
            v = int(clamp(s * 32767, -32767, 32767))
            buf += int(v).to_bytes(2, byteorder="little", signed=True)
        return pygame.mixer.Sound(buffer=bytes(buf))
        
    def _wind_sound(self, intensity: float) -> pygame.mixer.Sound:
        sr = 44100
        duration = 1.5
        n = int(sr * duration)
        buf = bytearray()
        for i in range(n):
            t = i / sr
            # Wind is low frequency noise
            freq = 80 + 40 * math.sin(t * 0.5)
            s = math.sin(2.0 * math.pi * freq * t) * intensity
            # Add some noise
            s += random.uniform(-0.2, 0.2) * intensity
            v = int(clamp(s * 32767, -32767, 32767))
            buf += int(v).to_bytes(2, byteorder="little", signed=True)
        return pygame.mixer.Sound(buffer=bytes(buf))
        
    def play_weather(self, weather_type: str):
        """Play appropriate weather sound"""
        if not self.ok:
            return
            
        # Stop current weather sound
        if self.current_weather_sound:
            self.current_weather_sound.stop()
            
        # Play new weather sound if applicable
        if weather_type in ["rain", "heavy_rain", "snow", "sandstorm"]:
            self.current_weather_sound = self.sounds[weather_type]
            self.current_weather_sound.play(loops=-1)
            self.current_weather_sound.set_volume(
                weather_effects[weather_type].sound_volume
            )
    def _tone(self, freq: float, duration: float, volume: float, fade: bool = False) -> pygame.mixer.Sound:
        sr = 44100
        n = max(1, int(sr * duration))
        buf = bytearray()
        for i in range(n):
            t = i / sr
            s = math.sin(2.0 * math.pi * freq * t)
            if fade:
                f = 1.0
                edge = int(0.06 * n)
                if edge > 1:
                    if i < edge:
                        f = i / edge
                    elif i > n - edge:
                        f = (n - i) / edge
                s *= f
            v = int(clamp(s * 32767 * volume, -32767, 32767))
            buf += int(v).to_bytes(2, byteorder="little", signed=True)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def play(self, name: str):
        if self.ok and name in self.sounds:
            self.sounds[name].play()

    def set_engine_volume(self, v: float):
        if self.ok and self.engine_channel:
            self.engine_channel.set_volume(clamp(v, 0.0, 1.0))





# saves the progress for each user independently

SAVE_DIR = "saves"

def default_save() -> dict:
    return {
        "coins": 0,
        "owned": ["Starter"],
        "upgrades": {},
        "track_progress": 1,
        "best_times": {},
    }

def _ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)

def save_path_for_user(username: str) -> str:
    safe = "".join(c for c in username if c.isalnum() or c in ("_", "-"))
    if not safe:
        safe = "player"
    _ensure_save_dir()
    return os.path.join(SAVE_DIR, f"save_{safe}.json")

def load_save(username: str) -> dict: # Loads the save data for a specific user from their personal save file
    path = save_path_for_user(username) # Get the file path for this specific user's save file
    dflt = default_save() # Get default save structure in case user has no save file
    # Check if this user's save file exists
    if not os.path.exists(path): 
        return dflt # returns default data
    try:
        #Try to read and parse the user's save file
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Backward/forward compatibility
        data.setdefault("coins", 0)
        data.setdefault("owned", ["Starter"])
        data.setdefault("upgrades", {})
        data.setdefault("track_progress", 1)
        data.setdefault("best_times", {})
        return data
    except Exception:
        return dflt

def write_save(username: str, data: dict): # identifies the username which is saved in the database
    path = save_path_for_user(username) # generates the file path for the user's personal file
    try:
        with open(path, "w", encoding="utf-8") as f: # it opens a file assuming it hasn't existed before
            json.dump(data, f, indent=2) # writes game data to the file using json format
    except Exception:
        pass



# Data structures

@dataclass
class CarSpec:
    name: str
    max_speed: float
    accel: float
    handling: float
    max_hp: float
    cost: int

CAR_SPECS = [
    CarSpec("Starter", max_speed=360, accel=520, handling=1.00, max_hp=100, cost=0),
    CarSpec("Sprinter", max_speed=420, accel=600, handling=0.92, max_hp=90, cost=450),
    CarSpec("Gripster", max_speed=390, accel=560, handling=1.18, max_hp=95, cost=500),
    CarSpec("Bruiser", max_speed=370, accel=520, handling=0.95, max_hp=130, cost=750),
    CarSpec("Apex GT", max_speed=460, accel=640, handling=1.10, max_hp=105, cost=950),
]
SPEC_BY_NAME = {s.name: s for s in CAR_SPECS}

@dataclass
class Checkpoint: #creates checkpoints where the centre is calculated with use of vectors
    center: Vec2
    radius: float

@dataclass
class PowerUp:
    kind: str
    pos: Vec2
    radius: float = 18
    active: bool = True
    respawn_timer: float = 0.0
    effect_duration: float = 0.0
    effect_active: bool = False

    def update(self, dt: float):
        if not self.active:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.active = True
                self.respawn_timer = 0.0

@dataclass
class Coin:
    pos: Vec2
    value: int = 10
    radius: float = 10
    active: bool = True
    respawn_timer: float = 0.0

    def update(self, dt: float):
        if not self.active:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.active = True
                self.respawn_timer = 0.0



# creating the tracks for the race

class Track:
    def __init__(
        self,
        name: str,
        world_size: Tuple[int, int],
        centerline: List[Vec2],
        width: int,
        climate: str,
        on_friction: float,
        off_friction: float,
        walls: List[pygame.Rect],
        power_spawns: List[Tuple[str, Vec2]],
        checkpoint_count: int = 10,
        coin_spawns: List[Vec2] = None,
        dynamic_obstacles: List[DynamicObstacle] = None,
        weather_type: str = "clear",  
        unlock_time_limit: float = 90.0,  # Time limit to unlock next track (seconds)
    ):
        self.name = name
        self.world_w, self.world_h = world_size
        self.centerline = centerline
        self.width = width
        self.climate = climate
        self.on_friction = on_friction
        self.off_friction = off_friction
        self.walls = walls[:]
        self.unlock_time_limit = unlock_time_limit  # Time to beat to unlock next track

        self.weather_type = weather_type
        self.weather_effect = weather_effects.get(weather_type, weather_effects["clear"])

        # Weather particles for visual effects
        self.weather_particles: List[Dict] = []
        self._init_weather_particles()

        self.powerups: List[PowerUp] = [PowerUp(kind=k, pos=p) for (k, p) in power_spawns]
        self.coins: List[Coin] = [Coin(pos=p) for p in (coin_spawns or [])]

        # drawing the surfaces
        self.track_surface = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)  # overlay lines + walls
        self.mask_surface  = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)  # mask source
        self.bg_surface: Optional[pygame.Surface] = None  # full background (optional)

        self.start_finish_line = self._create_start_finish_line()  # new attribute

        # building visuals and mask 
        self._draw_track()
        self.track_mask = pygame.mask.from_surface(self.mask_surface)

        # obstacles after the mask exists
        self.dynamic_obstacles: List[DynamicObstacle] = (dynamic_obstacles or [])[:6]
        for obstacle in self.dynamic_obstacles:
            obstacle.track = self
            obstacle.adjust_to_track_bounds()

        # checkpoints / start / minimap / start-stop finish line
        self.checkpoints: List[Checkpoint] = self._make_checkpoints(checkpoint_count)
        self.start_pos, self.start_angle = self._make_start_pose()
        self.minimap = self._make_minimap()

    

    def _create_start_finish_line(self):
        """Create start/finish line positions using a robust tangent at centerline[0]."""
        if len(self.centerline) < 3: # Need at least 3 points: previous point, current point (start), and next point
            return Vec2(0, 0), Vec2(0, 0) # returns useless values if not enough points 

        p0 = self.centerline[0] # the first point in the centerline
        p_prev = self.centerline[-1] # last point in the centerline
        p_next = self.centerline[1] # second point in the centerline (point after the start)

        tangent = (p_next - p_prev) # The tangent is the average direction from previous point to next point
        if tangent.length() < 1e-6: # If points are essentially the same
            tangent = (p_next - p0) # Fallback to simple forward direction

        direction = tangent.normalize() if tangent.length() > 0 else Vec2(1, 0) # This represents the forward direction of travel at the start point
        perpendicular = Vec2(-direction.y, direction.x)

        start = p0 - perpendicular * (self.width * 0.5)
        end   = p0 + perpendicular * (self.width * 0.5)
        return start, end


    def _init_weather_particles(self):
        """Initialize weather particles based on weather type"""
        self.weather_particles = [] # of all the weather effects 
        effect = self.weather_effect
        
        
        for _ in range(effect.particle_count): #requires a number of particles 
            self.weather_particles.append({
                'pos': Vec2(random.randint(0, self.world_w), random.randint(0, self.world_h)),
                'vel': Vec2(0, random.randint(100, 300)),  # initial velocity of the particles falling vertically
                'size': random.randint(effect.particle_size_range[0], effect.particle_size_range[1]), # random particle size
                'alpha': random.randint(100, 200)
            })
            
    def update_weather(self, dt: float):
        """Update weather particles"""
        effect = self.weather_effect
        
        for p in self.weather_particles:
            # Move particles along a time-based movement
            p['pos'].x += p['vel'].x * dt
            p['pos'].y += p['vel'].y * dt
            
            # Reset if out of bounds (goes beyond the bottom of the screen)
            if p['pos'].y > self.world_h:
                p['pos'].y = random.randint(-50, -10)
                p['pos'].x = random.randint(0, self.world_w)
                
            # For horizontal movement (sandstorm)
            if self.weather_type == "sandstorm":
                #add sideways velocity to elaborate strong winds
                p['vel'].x = random.randint(100, 200)
                if p['pos'].x > self.world_w:
                    p['pos'].x = random.randint(-50, -10)
                    p['pos'].y = random.randint(0, self.world_h)
                    
    def get_modified_friction(self, base_friction: float) -> float:
        """Apply weather effects to friction"""
        return base_friction * self.weather_effect.track_friction_modifier
        
    def get_modified_handling(self, base_handling: float) -> float:
        """Apply weather effects to handling"""
        return base_handling * self.weather_effect.handling_modifier

    def _draw_track(self):
        # track overlay (asphalt/edges) and mask
        self.track_surface.fill((0, 0, 0, 0))
        self.mask_surface.fill((0, 0, 0, 0))

        asphalt = (55, 58, 62)
        edge    = (210, 210, 210)
        inner   = (35, 38, 42)

        pts = [(int(p.x), int(p.y)) for p in self.centerline]
        if len(pts) >= 3:
            pygame.draw.lines(self.track_surface, asphalt, True, pts, self.width)
            pygame.draw.lines(self.mask_surface, (255, 255, 255, 255), True, pts, self.width)

            pygame.draw.lines(self.track_surface, inner, True, pts, max(1, self.width // 3))
            pygame.draw.lines(self.track_surface, edge, True, pts, max(1, self.width // 10))

        for r in self.walls:
            pygame.draw.rect(self.track_surface, (140, 70, 70), r)

 
    # Draw start and finish line (black and white stripes)
        if hasattr(self, "start_finish_line") and self.start_finish_line: # checks whether the user has passed through the start/finish line
            start_line_start, start_line_end = self.start_finish_line

            for i in range(10):
                t1 = i / 10
                t2 = (i + 1) / 10
                point1 = start_line_start * (1 - t1) + start_line_end * t1
                point2 = start_line_start * (1 - t2) + start_line_end * t2

                color = (255, 255, 255) if i % 2 == 0 else (0, 0, 0)
                pygame.draw.line(
                    self.track_surface, color,
                    (int(point1.x), int(point1.y)),
                    (int(point2.x), int(point2.y)), 8
                )

            pygame.draw.line(
                self.track_surface, (255, 0, 0),
                (int(start_line_start.x), int(start_line_start.y)),
                (int(start_line_end.x), int(start_line_end.y)), 2
            )


    def _make_start_pose(self) -> Tuple[Vec2, float]:
        p0 = self.centerline[0]
        p1 = self.centerline[1]
        v = (p1 - p0)
        angle = math.atan2(v.y, v.x)
        return Vec2(p0.x, p0.y), angle

    def _make_checkpoints(self, count: int) -> List[Checkpoint]:
        pts = self.centerline
        if not pts or len(pts) < 2 or count <= 0:
            return [Checkpoint(center=self.centerline[0], radius=self.width * 0.55)] if pts else []

        n = len(pts)

        # cumulative distance around the FULL loop
        seg_len = []
        cum = [0.0]
        total = 0.0
        for i in range(n):
            a = pts[i]
            b = pts[(i + 1) % n]
            d = (b - a).length()
            seg_len.append(d)
            total += d
            cum.append(total)

        if total <= 1e-6:
            return [Checkpoint(center=self.centerline[0], radius=self.width * 0.55)]

        radius = max(18.0, self.width * 0.45)

        def blocked_by_wall(p: Vec2) -> bool:
            x, y = int(p.x), int(p.y)
            for w in self.walls:
                if w.inflate(40, 40).collidepoint(x, y):
                    return True
            return False

        def valid(p: Vec2) -> bool:
            return self.on_track(p) and not blocked_by_wall(p)

        def nudge_to_valid(p: Vec2, base_idx: int) -> Vec2:
            for r in range(0, 26):
                for s in (-1, 1):
                    j = (base_idx + s * r) % n
                    cand = pts[j]
                    if valid(cand):
                        return Vec2(cand.x, cand.y)
            return p

        cps: List[Checkpoint] = []
        step = total / count

        for k in range(count):
            dtarget = k * step

            # find segment on the loop
            i = 0
            while i < n and cum[i + 1] < dtarget:
                i += 1

            a = pts[i]
            b = pts[(i + 1) % n]
            segd = max(1e-6, seg_len[i])
            t = (dtarget - cum[i]) / segd
            p = a.lerp(b, t)
            p = nudge_to_valid(p, i)

            cps.append(Checkpoint(center=p, radius=radius))

        cps[0] = Checkpoint(center=Vec2(pts[0].x, pts[0].y), radius=self.width * 0.55)
        return cps


    def on_track(self, p: Vec2) -> bool:
        x, y = int(p.x), int(p.y)
        if x < 0 or y < 0 or x >= self.world_w or y >= self.world_h:
            return False
        return bool(self.track_mask.get_at((x, y)))

    def get_track_point_with_offset(self, idx: int, offset: float = 0.0) -> Vec2:
        if not self.centerline or idx < 0 or idx >= len(self.centerline):
            return Vec2(0, 0)

        point = self.centerline[idx]
        if idx + 1 < len(self.centerline):
            next_point = self.centerline[idx + 1]
            direction = (next_point - point).normalize() if (next_point - point).length() > 0 else Vec2(1, 0)
        else:
            direction = Vec2(1, 0)

        perpendicular = Vec2(-direction.y, direction.x)
        offset_point = point + perpendicular * (offset * self.width * 0.4)

        if not self.on_track(offset_point):
            offset_point = point - perpendicular * (offset * self.width * 0.4)
        return offset_point

    def _make_minimap(self, size: Tuple[int, int] = (220, 160)) -> pygame.Surface:
        mm = pygame.Surface(size, pygame.SRCALPHA)
        mm.fill((0, 0, 0, 70))
        scaled = pygame.transform.smoothscale(self.mask_surface, size)
        tint = pygame.Surface(size, pygame.SRCALPHA)
        tint.fill((230, 230, 230, 220))
        scaled.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        mm.blit(scaled, (0, 0))
        pygame.draw.rect(mm, (255, 255, 255, 110), mm.get_rect(), 2)
        return mm
    

    def update_powerups(self, dt: float):
        for pu in self.powerups:
            pu.update(dt)
        for coin in self.coins:
            coin.update(dt)

        current_time = pygame.time.get_ticks() / 1000.0
        for obstacle in self.dynamic_obstacles:
            if current_time - obstacle.last_update_time > 0.05:
                obstacle.update(dt, current_time)
                obstacle.last_update_time = current_time

    def check_start_finish_line(self, car):
        #Check if the car has crossed the start/finish line (robustness)
        if not hasattr(self, 'start_finish_line') or not self.start_finish_line:
            return False

        start, end = self.start_finish_line
        start = Vec2(start)
        end = Vec2(end)

        line_vec = end - start
        line_len = line_vec.length()
        if line_len < 1e-6:
            return False

        line_dir = line_vec / line_len                 # direction along the line (across track)
        line_normal = Vec2(-line_dir.y, line_dir.x)    # normal of the line (along track)

        car_pos = Vec2(car.pos)

        # must be within the segment
        rel = car_pos - start
        proj = rel.dot(line_dir)
        if proj < 0 or proj > line_len:
            return False

        # signed distance to the line
        signed = rel.dot(line_normal)

        # initialize last signed
        if not hasattr(car, "last_sf_signed"):
            car.last_sf_signed = signed
            return False

        
        crossed = (car.last_sf_signed <= 0 < signed) or (car.last_sf_signed >= 0 > signed)

        # 4) must be moving in the "forward" direction (through the line normal)
        car_forward = car.forward_vec()
        moving_forward = car_forward.dot(line_normal) > 0.2

        if crossed and moving_forward:
            if car.can_finish:
                car.laps += 1
                car.can_finish = False

                if hasattr(car, "game") and car.game is not None:
                    g = car.game
                    lap_time = g.race_time - g.current_lap_start
                    g.lap_times.append(lap_time)
                    g.last_lap_time = g.race_time
                    g.current_lap_start = g.race_time
                    if hasattr(g, "audio") and g.audio:
                        g.audio.play("lap")

                car.current_lap_start = pygame.time.get_ticks() / 1000.0

        car.last_sf_signed = signed
        return False



# Cars, for the user and for the AI cars

class Car:
    def __init__(self, spec: CarSpec, color: Tuple[int, int, int], pos: Vec2, angle: float, is_player: bool):
        self.spec = spec
        self.color = color
        self.pos = Vec2(pos)
        self.vel = Vec2(0, 0)
        self.angle = angle

        self.is_player = is_player
        self.sprite: Optional[pygame.Surface] = None
        self.radius = 12

        self.hp = float(spec.max_hp)
        self.laps = 0

        self.next_cp = 1
        self.can_finish = False

        self.nitro_active = False
        self.nitro_timer = 0.0
        self.nitro_cooldown = 0.0
        
        # Power-up effects
        self.shield_active = False
        self.shield_timer = 0.0
        self.speed_boost_active = False
        self.speed_boost_timer = 0.0
        self.magnet_active = False
        self.magnet_timer = 0.0

        self.repair_flash = 0.0
        self.obstacle_hit_flash = 0.0

        self.finished = False
        self.finish_time = None

        self.ai_react_timer = 0.0
        self.ai_cached_inputs = (0.0, 0.0, 0.0)

        self.is_dead = False
        self.death_timer = 0.0
        self.death_flash = 0.0
        self.respawn_pos: Optional[Vec2] = None
        self.respawn_angle: Optional[float] = None

        self.collision_cooldown = 0.0
        self.coin_collection_range = 0.0  # For magnet power-up

        self.crossed_start_line = False
        self.last_checkpoint_time = 0.0

        self.laps = 0 
        self.current_lap_start = 0.0    
        self.ai_lane = random.uniform(-0.35, 0.35) if not is_player else 0.0


        

    def current_performance_factor(self) -> float: # shows each invdividual performance for each racing vehicle
        hp_factor = clamp(self.hp / self.spec.max_hp, 0.0, 1.0)
        return 0.60 + 0.40 * hp_factor

    def max_speed_now(self) -> float: # maximum speed of each individual car
        f = self.current_performance_factor()
        base = self.spec.max_speed * f
        if self.nitro_active:
            base *= 1.22
        if self.speed_boost_active:
            base *= 1.15
        return base

    def accel_now(self) -> float:
        f = self.current_performance_factor()
        base = self.spec.accel * f
        if self.nitro_active:
            base *= 1.25
        if self.speed_boost_active:
            base *= 1.20
        return base

    def handling_now(self) -> float:
        f = 0.75 + 0.25 * (clamp(self.hp / self.spec.max_hp, 0.0, 1.0))
        handling = self.spec.handling * f
        if self.speed_boost_active:
            handling *= 0.9  # Speed boost makes handling slightly harder
        return handling

    def apply_damage(self, amount: float):
        if amount <= 0 or self.is_dead: 
            return

        # Shield reduces the damage
        if self.shield_active:
            amount *= 0.3

        if self.collision_cooldown > 0:
            amount *= 0.3

        self.hp = max(0.0, self.hp - amount)
        self.obstacle_hit_flash = 0.3
        self.collision_cooldown = 0.5

        if self.hp <= 0 and self.is_player:
            self.die()

    def heal(self, amount: float):
        if amount <= 0 or self.is_dead:
            return
        self.hp = min(self.spec.max_hp, self.hp + amount)
        self.repair_flash = 0.35

    def die(self):
        if not self.is_player or self.is_dead:
            return

        self.is_dead = True
        self.death_timer = 3.0
        self.death_flash = 1.0
        self.vel = Vec2(0, 0)

        self.respawn_pos = Vec2(self.pos)
        self.respawn_angle = self.angle

        print(f" Player died! Respawning in {self.death_timer:.1f} seconds")

    def respawn(self):
        if not self.is_player or not self.is_dead:
            return

        if self.respawn_pos:
            self.pos = self.respawn_pos
        if self.respawn_angle is not None:
            self.angle = self.respawn_angle

        self.hp = self.spec.max_hp * 0.5
        self.vel = Vec2(0, 0)
        self.is_dead = False
        self.death_timer = 0.0

        print(f" Player respawned with {self.hp:.0f} HP")

    def try_activate_nitro(self):
        if self.nitro_cooldown <= 0.0 and not self.nitro_active and not self.is_dead:
            self.nitro_active = True
            self.nitro_timer = 1.6
            self.nitro_cooldown = 4.5

    def activate_powerup(self, kind: str):
        """Activate a power-up effect"""
        if kind == "shield":
            self.shield_active = True
            self.shield_timer = 5.0
        elif kind == "speed":
            self.speed_boost_active = True
            self.speed_boost_timer = 4.0
        elif kind == "magnet":
            self.magnet_active = True
            self.magnet_timer = 6.0
            self.coin_collection_range = 50.0  # Increased range for coin collection

    def update_timers(self, dt: float):
        if self.nitro_cooldown > 0:
            self.nitro_cooldown -= dt
        if self.nitro_active:
            self.nitro_timer -= dt
            if self.nitro_timer <= 0:
                self.nitro_active = False
                self.nitro_timer = 0.0
        if self.repair_flash > 0:
            self.repair_flash -= dt
        if self.obstacle_hit_flash > 0:
            self.obstacle_hit_flash -= dt
        if self.collision_cooldown > 0:
            self.collision_cooldown -= dt
            
        # Update power-up timers
        if self.shield_active:
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shield_active = False
                
        if self.speed_boost_active:
            self.speed_boost_timer -= dt
            if self.speed_boost_timer <= 0:
                self.speed_boost_active = False
                
        if self.magnet_active:
            self.magnet_timer -= dt
            if self.magnet_timer <= 0:
                self.magnet_active = False
                self.coin_collection_range = 0.0

        if self.is_dead and self.death_timer > 0:
            self.death_timer -= dt
            self.death_flash -= dt * 2
            if self.death_flash < 0:
                self.death_flash = 1.0
            if self.death_timer <= 0:
                self.respawn()

    def forward_vec(self) -> Vec2:
        return Vec2(math.cos(self.angle), math.sin(self.angle))

    def update_physics(
        self,
        dt: float,
        throttle: float,
        brake: float,
        steer: float,
        track: 'Track',
        audio: Optional[Audio],
    ):
        if self.is_dead:
            return
        
        on = track.on_track(self.pos)

        # Apply weather effects to friction
        # checks whether the car is on the track or not
        base_friction = track.on_friction if on else track.off_friction
        friction = track.get_modified_friction(base_friction)

        # speed = magnitude of the velocity vector (speed is a scalar quantity)
        speed = self.vel.length()
        speed_norm = clamp(speed / max(1.0, self.spec.max_speed), 0.0, 1.0)

        # Apply weather effects to handling
        base_handling = self.handling_now()
        weather_handling = track.get_modified_handling(base_handling)
        turn_rate = (2.4 + 2.2 * speed_norm) * weather_handling
        self.angle += steer * turn_rate * dt
        self.angle = wrap_angle_rad(self.angle)

        # Apply weather effects to max speed
        weather_max_speed = self.max_speed_now() * track.weather_effect.max_speed_modifier

        fwd = self.forward_vec()
        accel = self.accel_now()
        self.vel += fwd * (throttle * accel * dt)

        if brake > 0:
            brake_strength = (900.0 + 900.0 * speed_norm) * brake
            if speed > 1e-3:
                self.vel -= self.vel.normalize() * min(brake_strength * dt, speed)

        if speed > 1e-6:
            right = Vec2(-fwd.y, fwd.x)
            v_fwd = fwd * self.vel.dot(fwd)
            v_side = right * self.vel.dot(right)
            side_damp = (3.6 * friction) * (0.7 + 0.3 * self.handling_now())
            v_side *= max(0.0, 1.0 - side_damp * dt)
            self.vel = v_fwd + v_side

        drag = (1.1 * friction) + (0.0022 * speed)
        self.vel *= max(0.0, 1.0 - drag * dt)

        # Update max speed check with weather modifier
        if self.vel.length_squared() > weather_max_speed * weather_max_speed:
            self.vel.scale_to_length(weather_max_speed)

        old_pos = Vec2(self.pos)
        self.pos += self.vel * dt

        # world bounds that prevents the players from escaping the world (not being able to see their car)
        if self.pos.x < self.radius:
            self.pos.x = self.radius
            self.vel.x *= -0.45
            self.apply_damage(3)
            if audio: audio.play("hit")
        if self.pos.y < self.radius:
            self.pos.y = self.radius
            self.vel.y *= -0.45
            self.apply_damage(3)
            if audio: audio.play("hit")
        if self.pos.x > track.world_w - self.radius:
            self.pos.x = track.world_w - self.radius
            self.vel.x *= -0.45
            self.apply_damage(3)
            if audio: audio.play("hit")
        if self.pos.y > track.world_h - self.radius:
            self.pos.y = track.world_h - self.radius
            self.vel.y *= -0.45
            self.apply_damage(3)
            if audio: audio.play("hit")

        # wall collisions when the player hits any obstacle
        car_damage_this_frame = 0.0
        for r in track.walls:
            hit, normal, penetration = circle_rect_collision(self.pos, self.radius, r)
            if hit:
                self.pos += normal * (penetration + 0.5)
                vn = self.vel.dot(normal)
                if vn < 0:
                    self.vel -= (1.55 * vn) * normal
                self.vel *= 0.72
                car_damage_this_frame += 5.0 + 0.02 * speed
        if car_damage_this_frame > 0:
            self.apply_damage(min(18.0, car_damage_this_frame))
            if audio: audio.play("hit")

        # Dynamic obstacle collisions
        obstacle_damage_this_frame = 0.0
        for obstacle in track.dynamic_obstacles:
            if not obstacle.active or self.collision_cooldown > 0:
                continue

            dist = (self.pos - obstacle.pos).length()
            if dist < (self.radius + obstacle.radius):
                if dist > 0:
                    normal = (self.pos - obstacle.pos) / dist
                else:
                    normal = Vec2(1, 0)

                overlap = (self.radius + obstacle.radius) - dist
                self.pos += normal * (overlap + 0.5)

                vn = self.vel.dot(normal)
                if vn < 0:
                    self.vel -= (1.8 * vn) * normal
                self.vel *= 0.65

                current_damage = obstacle.damage # Default damage value
                if hasattr(obstacle, 'get_current_damage'): # Check if obstacle has dynamic damage
                    current_damage = obstacle.get_current_damage()  # gets damaged

                speed_damage = speed * 0.02 # speed_damage = additional damage based on collision speed
                total_damage = current_damage + min(speed_damage, 15.0) # Calculate total damage from this collision
                obstacle_damage_this_frame += total_damage # Sees the total damage from all obstacles hit this frame 

                if speed > 200 and random.random() < 0.3: # high speed obstacle destruction chance  
                    if obstacle.hit(50 + speed * 0.1): # Calculate destruction damage, the base damage is 50
                        if audio and self.is_player:
                            audio.play("obstacle_destroy")
                        if self.is_player and hasattr(self, 'game'):
                            self.game.obstacles_destroyed += 1

                self.obstacle_hit_flash = 0.4 

        if obstacle_damage_this_frame > 0:
            self.apply_damage(min(25.0, obstacle_damage_this_frame))
            if audio and self.is_player:
                audio.play("obstacle_hit")

        if not on:
            self.vel *= max(0.0, 1.0 - (0.95 * dt))

        if self.is_player and audio and not self.is_dead:
            audio.set_engine_volume(0.10 + 0.45 * clamp(self.vel.length() / max(1.0, self.spec.max_speed), 0, 1))

        if self.hp <= 0 and not self.is_dead and self.is_player:
            self.die()
            if audio:
                audio.play("death")

        if (self.pos - old_pos).length_squared() > (self.max_speed_now() * dt * 4) ** 2:
            self.pos = old_pos

    def update_checkpoints(self, track: 'Track', audio: Optional['Audio'], game: Optional['Game'] = None):
        if self.is_dead:
            return

        cps = track.checkpoints
        if not cps:
            return

        n = len(cps)

        
        # finish and lap logic
        # If we already completed all checkpoints
        # then entering checkpoint 0 increments the lap immediately
        
        if self.can_finish:
            finish_cp = cps[0]
            if (self.pos - finish_cp.center).length() <= finish_cp.radius:
                self.laps += 1
                self.can_finish = False
                self.next_cp = 1 % n  # start next lap from checkpoint 1

                # Lap timing and sound 
                if self.is_player and game is not None:
                    lap_time = game.race_time - game.current_lap_start
                    game.lap_times.append(lap_time)
                    game.last_lap_time = game.race_time
                    game.current_lap_start = game.race_time
                    if getattr(game, "audio", None):
                        game.audio.play("lap")

                self.current_lap_start = pygame.time.get_ticks() / 1000.0
                return  # don't also process checkpoint stepping this frame

        
        # normal checkpoint stepping
        
        self.next_cp %= n
        target = cps[self.next_cp]

        if (self.pos - target.center).length() <= target.radius:
            self.next_cp += 1
            if self.next_cp >= n:
                self.next_cp = 0
                self.can_finish = True



    def progress_value(self, track: Track) -> float: # shows how many checkpoint the player has crossed over
        cps = track.checkpoints
        if not cps:
            return float(self.laps)
        n = len(cps)
        reached = (self.next_cp - 1) % n
        base = self.laps + reached / n
        nxt = cps[self.next_cp].center
        d = (self.pos - nxt).length()
        return base + (1.0 / n) * (1.0 - clamp(d / (track.width * 4.0), 0.0, 1.0))



# AI, used to race against the user

class AIController:
    def __init__(self, difficulty: int):
        self.difficulty = difficulty
        self.react_interval = [0.16, 0.11, 0.07][difficulty]
        self.corner_brake = [0.55, 0.45, 0.35][difficulty]
        self.target_speed_mul = [0.86, 0.93, 1.00][difficulty]
        self.lookahead = [90, 120, 150][difficulty]
        self.aggressiveness = [0.3, 0.5, 0.7][difficulty]

        self.use_nitro_chance = [0.1, 0.2, 0.3][difficulty]
        self.seek_powerups = [False, True, True][difficulty]
        self.avoid_walls = [False, True, True][difficulty]
        self.avoid_obstacles = [False, True, True][difficulty]
        self.overtake_attempt = [False, True, True][difficulty]

        self.last_powerup_check = 0.0
        self.target_powerup = None
        self.obstacle_avoidance = Vec2(0, 0)
        self.overtake_timer = 0.0
        self.overtake_target = None

    def get_inputs(self, car: Car, track: Track, dt: float, other_cars: List[Car]) -> Tuple[float, float, float]:
        # Shows the reaction time of the AI cars responding to external environment
        car.ai_react_timer -= dt
        if car.ai_react_timer > 0:
            return car.ai_cached_inputs
        car.ai_react_timer = self.react_interval

        self.last_powerup_check -= dt
        if self.seek_powerups and self.last_powerup_check <= 0:
            self.last_powerup_check = 1.5
            self.target_powerup = self.find_best_powerup(car, track)

        if car.nitro_cooldown <= 0 and not car.nitro_active:
            if random.random() < self.use_nitro_chance:
                vel_angle = math.atan2(car.vel.y, car.vel.x) if car.vel.length() > 0.1 else car.angle
                angle_diff = abs(wrap_angle_rad(vel_angle - car.angle))
                if angle_diff < 0.3:
                    car.try_activate_nitro()

        # progress base targeting (prevents circling in the center)
        cps = track.checkpoints
        p = car.pos

        if cps and len(cps) >= 2:
            # Get the current target checkpoint 
            target_cp = cps[car.next_cp % len(cps)].center
            # Get the checkpoint after that for better corner prediction
            next_cp   = cps[(car.next_cp + 1) % len(cps)].center

            target = Vec2(target_cp)

             # This creates smoother turns by pulling the target point ahead
            to_next = Vec2(next_cp) - target
            if to_next.length_squared() > 1e-6: # Check if vector has meaningful length
            # Move target slightly towards next checkpoint (55 pixels ahead)
            # This helps AI take better racing lines through corners
                target += to_next.normalize() * 55

            ahead2 = Vec2(next_cp)
        else:
            # Fallback if no checkpoints
            pts = track.centerline
            if not pts:
                return (0.0, 0.0, 0.0)
            target = Vec2(pts[0])
            ahead2 = Vec2(pts[1 % len(pts)])


        # Avoiding the obstacles
        self.obstacle_avoidance = Vec2(0, 0)
        if self.avoid_obstacles: 
            for obstacle in track.dynamic_obstacles:
                if not obstacle.active: # Skip inactive obstacles (destroyed or respawning)
                    continue
                dist_to_obstacle = (car.pos - obstacle.pos).length()
                if dist_to_obstacle < 150:
                    obstacle_vec = obstacle.pos - car.pos
                    if obstacle_vec.length() > 0:  # Ensure vector is valid
                    # Calculate avoidance strength: closer = stronger avoidance
                        strength = 1.0 - clamp(dist_to_obstacle / 150, 0, 1)
                        fwd = car.forward_vec()
                        right = Vec2(-fwd.y, fwd.x)
                        side = 1 if obstacle_vec.dot(right) > 0 else -1
                        avoid_dir = right * side
                        self.obstacle_avoidance += avoid_dir * strength * 2.0

        if self.obstacle_avoidance.length() > 0:
            target += self.obstacle_avoidance.normalize() * 50

        # Overtaking behavior
        self.overtake_timer -= dt
        if self.overtake_attempt and self.overtake_timer <= 0:
            self.overtake_timer = random.uniform(2.0, 4.0)
            self.overtake_target = self.find_overtake_target(car, other_cars)

        if self.overtake_target and (car.pos - self.overtake_target.pos).length() < 100:
            target = self.overtake_target.pos
            if (car.pos - self.overtake_target.pos).length() < 30:
                self.overtake_target = None  # Overtake complete

        detour_target = None
        if self.target_powerup and self.target_powerup.active:
            line_to_target = target - car.pos
            line_to_powerup = self.target_powerup.pos - car.pos

            if line_to_target.length() > 0 and line_to_powerup.length() > 0:
                tproj = line_to_target.dot(line_to_powerup) / line_to_target.length_squared()
                closest_point = car.pos + line_to_target * clamp(tproj, 0, 1)
                dist_from_path = (self.target_powerup.pos - closest_point).length()

                need_repair = (self.target_powerup.kind == "repair" and car.hp < car.spec.max_hp * 0.4)
                need_nitro = (self.target_powerup.kind == "nitro" and car.nitro_cooldown > 3.0 and not car.nitro_active)

                if (need_repair or need_nitro) and dist_from_path < 50 and (car.pos - self.target_powerup.pos).length() < 150:
                    detour_target = self.target_powerup.pos

        desired = math.atan2((detour_target - p).y, (detour_target - p).x) if detour_target else \
                  math.atan2((target - p).y, (target - p).x)

        ang_err = wrap_angle_rad(desired - car.angle)
        steer = clamp(ang_err * 1.3, -1.0, 1.0)

        spd = car.vel.length()
        base_target = car.spec.max_speed * self.target_speed_mul

        if not track.on_track(car.pos):
            base_target *= 0.7
        if self.avoid_obstacles and self.obstacle_avoidance.length() > 0.5:
            base_target *= 0.8

        
        if not (cps and len(cps) >= 2):
            ahead2 = pts[1 % len(pts)]

        dir1 = (target - car.pos)
        dir2 = (ahead2 - target)
        corner = 0.0
        if dir1.length_squared() > 1e-6 and dir2.length_squared() > 1e-6:
            a1 = math.atan2(dir1.y, dir1.x)
            a2 = math.atan2(dir2.y, dir2.x)
            corner = abs(wrap_angle_rad(a2 - a1))
            corner_slow = lerp(1.0, self.corner_brake, clamp(corner / 1.2, 0.0, 1.0))
            base_target *= corner_slow

        throttle = 0.0
        brake = 0.0
        if spd < base_target * 0.98:
            throttle = 1.0
        elif spd > base_target * 1.03:
            throttle = 0.0
            brake = 0.6 + 0.4 * clamp((spd - base_target) / 200.0, 0.0, 1.0)

        if self.avoid_walls:
            for wall in track.walls:
                if car.pos.distance_to(Vec2(wall.centerx, wall.centery)) < 100:
                    wall_vec = Vec2(wall.centerx, wall.centery) - car.pos
                    if wall_vec.length() > 0:
                        wall_angle = math.atan2(wall_vec.y, wall_vec.x)
                        angle_diff = wrap_angle_rad(car.angle - wall_angle)
                        if abs(angle_diff) < math.pi / 2:
                            steer_dir = 1.0 if angle_diff > 0 else -1.0
                            steer = clamp(steer + steer_dir * 0.5, -1.0, 1.0)
                            brake = max(brake, 0.3)

        car.ai_cached_inputs = (throttle, brake, steer)
        return car.ai_cached_inputs

    def find_best_powerup(self, car: Car, track: Track) -> Optional[PowerUp]:
        if not track.powerups:
            return None

        best_pu = None
        best_score = -float('inf')

        for pu in track.powerups:
            if not pu.active:
                continue

            dist = (car.pos - pu.pos).length()
            if dist > 200:
                continue

            score = 0
            if pu.kind == "nitro":
                if not car.nitro_active and car.nitro_cooldown > 2.0:
                    score = 150 / (dist + 1)
            elif pu.kind == "repair":
                hp_percent = car.hp / car.spec.max_hp
                if hp_percent < 0.6:
                    score = (200 * (1.0 - hp_percent)) / (dist + 1)
            elif pu.kind == "shield":
                if not car.shield_active:
                    score = 120 / (dist + 1)
            elif pu.kind == "speed":
                if not car.speed_boost_active:
                    score = 100 / (dist + 1)

            if score > best_score:
                best_score = score
                best_pu = pu

        return best_pu

    def find_overtake_target(self, car: Car, other_cars: List[Car]) -> Optional[Car]:
        """Find a car to overtake"""
        targets = []
        for other in other_cars:
            if other is car or other.is_player:
                continue
            
            # Only consider cars ahead
            pos_diff = other.pos - car.pos
            if pos_diff.dot(car.forward_vec()) < 0:
                continue
            
            distance = (car.pos - other.pos).length()
            if distance < 80:  # Only consider close cars
                targets.append((distance, other))
        
        if targets:
            targets.sort(key=lambda x: x[0])
            return targets[0][1]
        return None



# Track builders (builds the formation of the tracks)

def build_ellipse(center: Vec2, rx: float, ry: float, steps: int) -> List[Vec2]:
    pts = []
    for i in range(steps):
        t = (i / steps) * 2 * math.pi
        pts.append(Vec2(center.x + math.cos(t) * rx, center.y + math.sin(t) * ry))
    return pts

def build_figure8(center: Vec2, r: float, steps: int) -> List[Vec2]:
    pts = []
    for i in range(steps):
        t = (i / steps) * 2 * math.pi
        x = math.sin(t) * r
        y = math.sin(2 * t) * r * 0.70
        pts.append(Vec2(center.x + x, center.y + y))
    return pts

def build_hairpin_loop(origin: Vec2) -> List[Vec2]:
    pts = []
    x0, y0 = origin.x, origin.y
    for i in range(14):
        pts.append(Vec2(x0 + i * 85, y0))
    center = Vec2(x0 + 13 * 85, y0 + 210)
    for i in range(20):
        t = math.pi * (i / 19)
        pts.append(Vec2(center.x + math.cos(t) * 210, center.y + math.sin(t) * 210))
    for i in range(14):
        pts.append(Vec2(x0 + (13 - i) * 85, y0 + 420))
    for i in range(18):
        t = (i / 17) * math.pi
        pts.append(Vec2(x0 + math.cos(t) * 180, y0 + 210 + math.sin(t) * 210))
    return pts

def build_sprint_loop(center: Vec2) -> List[Vec2]:
    pts = []
    w = 1250
    h = 820
    x0 = center.x - w / 2
    y0 = center.y - h / 2

    pts += [Vec2(x0 + 120, y0 + 120), Vec2(x0 + w - 120, y0 + 120)]
    pts += [Vec2(x0 + w - 200, y0 + 250), Vec2(x0 + w - 90, y0 + 410), Vec2(x0 + w - 200, y0 + 570)]
    pts += [Vec2(x0 + w - 120, y0 + h - 120), Vec2(x0 + 120, y0 + h - 120)]
    pts += [Vec2(x0 + 240, y0 + h - 300), Vec2(x0 + 120, y0 + h - 460), Vec2(x0 + 120, y0 + 120)]
    return pts


def build_maze_loop(center: Vec2) -> Tuple[List[Vec2], List[pygame.Rect]]:
    pts = []
    cx, cy = center.x, center.y
    pts += [
        Vec2(cx - 520, cy - 300),
        Vec2(cx + 520, cy - 300),
        Vec2(cx + 520, cy - 80),
        Vec2(cx - 220, cy - 80),
        Vec2(cx - 220, cy + 80),
        Vec2(cx + 280, cy + 80),
        Vec2(cx + 280, cy + 300),
        Vec2(cx - 520, cy + 300),
        Vec2(cx - 520, cy + 100),
        Vec2(cx + 80, cy + 100),
        Vec2(cx + 80, cy - 100),
        Vec2(cx - 520, cy - 100),
    ]
    walls = []
    for i in range(3):
        x = int(cx - 420 + i * 160)
        walls.append(pygame.Rect(x, int(cy - 220), 22, 180))
        walls.append(pygame.Rect(x, int(cy + 40), 22, 180))
    for i in range(5):
        y = int(cy - 160 + i * 80)
        walls.append(pygame.Rect(int(cx - 120), y, 260, 18))
    return pts, walls

def build_mixed(center: Vec2) -> List[Vec2]:
    pts = []
    cx, cy = center.x, center.y
    pts += build_ellipse(Vec2(cx - 240, cy), 260, 170, 48)
    pts += [
        Vec2(cx + 40, cy - 40),
        Vec2(cx + 280, cy - 200),
        Vec2(cx + 480, cy),
        Vec2(cx + 280, cy + 200),
        Vec2(cx + 40, cy + 40),
    ]
    return pts

def generate_coins_along_track(centerline: List[Vec2], count: int, offset: float = 0.5) -> List[Vec2]:
    if len(centerline) < 2:
        return []

    coins = []
    n = len(centerline)
    step = max(1, n // count)

    for i in range(0, n, step):
        if i + 1 >= n:
            break

        p1 = centerline[i]
        p2 = centerline[(i + 1) % n]

        direction = (p2 - p1).normalize() if (p2 - p1).length() > 0 else Vec2(1, 0)
        perpendicular = Vec2(-direction.y, direction.x)

        side = 1 if (i // step) % 2 == 0 else -1
        coin_pos = p1 + perpendicular * (offset * side * 40)

        coins.append(coin_pos)

    return coins[:count]


def make_tracks(asset_loader: AssetLoader) -> List[Track]:
    tracks: List[Track] = []

    def boundary(world_w: int, world_h: int, thickness: int = 26) -> List[pygame.Rect]:
        return [
            pygame.Rect(0, 0, world_w, thickness),
            pygame.Rect(0, world_h - thickness, world_w, thickness),
            pygame.Rect(0, 0, thickness, world_h),
            pygame.Rect(world_w - thickness, 0, thickness, world_h),
        ]

    # First track is oval dunes
    ww, wh = 2200, 1500
    oval = build_ellipse(Vec2(ww / 2, wh / 2), 640, 360, 72)
    walls = boundary(ww, wh)
    walls += [
        pygame.Rect(ww // 2 - 40, wh // 2 - 520, 80, 40),
        pygame.Rect(ww // 2 - 40, wh // 2 + 480, 80, 40),
    ]
    power = [
        ("nitro", Vec2(ww / 2 + 520, wh / 2)),
        ("repair", Vec2(ww / 2 - 520, wh / 2)),
        ("shield", Vec2(ww / 2, wh / 2 + 280)),
        ("speed", Vec2(ww / 2, wh / 2 - 280)),
    ]
    coin_spawns = generate_coins_along_track(oval, 15, 0.6)

    dynamic_obstacles = []
    if len(oval) >= 24:
        path_points = []
        for i in range(0, 72, 18):
            idx = i % len(oval)
            path_points.append(oval[idx])

        dynamic_obstacles.append(MovingObstacle(pos=path_points[0], path=path_points, speed=60, pause_time=0.5, obstacle_type="barrel", damage=8))
        dynamic_obstacles.append(RotatingObstacle(pos=oval[18], center=oval[18], rotation_speed=1.2, rotation_radius=50, obstacle_type="cone", damage=7))
        dynamic_obstacles.append(PatrolObstacle(pos=oval[36], start_pos=oval[36], end_pos=oval[40], speed=70, obstacle_type="crate", damage=6))
        dynamic_obstacles.append(PulsingObstacle(pos=oval[54], obstacle_type="rock", damage=5, pulse_speed=1.5, min_radius=12, max_radius=20))

    track = Track(
        "Oval Dunes", (ww, wh), oval,
        width=120, climate="dry",
        on_friction=1.05, off_friction=1.85,
        walls=walls, power_spawns=power,
        checkpoint_count=16,
        coin_spawns=coin_spawns,
        dynamic_obstacles=dynamic_obstacles,
        weather_type="clear",
        unlock_time_limit=55.0,  # Time to beat to unlock next track
    )

    bg = asset_loader.load_track_bg("oval_dunes")
    if bg:
        track.bg_surface = bg

    tracks.append(track)

    # Second track is figure-8 rainway
    ww, wh = 1800, 1200
    fig8 = build_figure8(Vec2(ww / 2, wh / 2), 520, 96)
    walls = boundary(ww, wh)
    # walls += [pygame.Rect(ww // 2 - 18, wh // 2 - 18, 36, 36)]
    power = [
        ("nitro", Vec2(ww / 2, wh / 2 - 280)),
        ("repair", Vec2(ww / 2, wh / 2 + 280)),
        ("shield", Vec2(ww / 2 - 200, wh / 2)),
        ("speed", Vec2(ww / 2 + 200, wh / 2)),
    ]
    coin_spawns = generate_coins_along_track(fig8, 18, 0.55)

    dynamic_obstacles = []
    if len(fig8) >= 24:
        left_path = []
        for i in range(0, 24, 6):
            left_path.append(fig8[i % len(fig8)])
        dynamic_obstacles.append(MovingObstacle(pos=left_path[0], path=left_path, speed=55, pause_time=0.3, obstacle_type="barrel", damage=8))

        right_path = []
        for i in range(48, 72, 6):
            right_path.append(fig8[i % len(fig8)])
        dynamic_obstacles.append(MovingObstacle(pos=right_path[0], path=right_path, speed=65, pause_time=0.4, obstacle_type="cone", damage=7))

        dynamic_obstacles.append(RotatingObstacle(pos=fig8[0], center=fig8[0], rotation_speed=-1.5, rotation_radius=40, obstacle_type="crate", damage=6))
        dynamic_obstacles.append(RotatingObstacle(pos=fig8[24], center=fig8[24], rotation_speed=1.2, rotation_radius=35, obstacle_type="rock", damage=5))

    track = Track(
        "Figure-8 Rainway", (ww, wh), fig8,
        width=110, climate="wet",
        on_friction=0.82, off_friction=1.75,
        walls=walls, power_spawns=power,
        checkpoint_count=12,
        coin_spawns=coin_spawns,
        dynamic_obstacles=dynamic_obstacles,
        weather_type="rain",
        unlock_time_limit=70.0,
    )
    bg = asset_loader.load_track_bg("figure_8_rainway")
    if bg:
        track.bg_surface = bg
    tracks.append(track)

    # Third track is hairpin glacier
    ww, wh = 2200, 1400
    hairpin = build_hairpin_loop(Vec2(420, 420))
    walls = boundary(ww, wh)
    # walls += [
    #     pygame.Rect(1400, 520, 70, 240),
    #     pygame.Rect(1650, 520, 70, 240),
    #     pygame.Rect(1520, 690, 160, 60),
    # ]
    power = [
        ("nitro", Vec2(1200, 420)),
        ("repair", Vec2(920, 840)),
        ("shield", Vec2(600, 420)),
        ("speed", Vec2(1800, 840)),
    ]
    coin_spawns = generate_coins_along_track(hairpin, 22, 0.5)

    dynamic_obstacles = []
    if len(hairpin) >= 20:
        hairpin1_path = []
        for i in range(14, 20, 2):
            if i < len(hairpin):
                hairpin1_path.append(hairpin[i])
        if len(hairpin1_path) >= 2:
            dynamic_obstacles.append(MovingObstacle(pos=hairpin1_path[0], path=hairpin1_path, speed=60, pause_time=0.5, obstacle_type="barrel", damage=9))

        if len(hairpin) >= 10:
            dynamic_obstacles.append(PatrolObstacle(pos=hairpin[5], start_pos=hairpin[5], end_pos=hairpin[7], speed=70, obstacle_type="cone", damage=8))

        dynamic_obstacles.append(RotatingObstacle(pos=hairpin[30], center=hairpin[30], rotation_speed=1.0, rotation_radius=40, obstacle_type="crate", damage=7))
        dynamic_obstacles.append(PulsingObstacle(pos=hairpin[40], obstacle_type="rock", damage=6, pulse_speed=1.8, min_radius=10, max_radius=22))

    track = Track(
        "Hairpin Glacier", (ww, wh), hairpin,
        width=110, climate="snow",
        on_friction=0.68, off_friction=1.65,
        walls=walls, power_spawns=power,
        checkpoint_count=12,
        coin_spawns=coin_spawns,
        dynamic_obstacles=dynamic_obstacles,
        weather_type="snow",
        unlock_time_limit=80.0,
    )
    bg = asset_loader.load_track_bg("hairpin_glacier")
    if bg:
        track.bg_surface = bg
    tracks.append(track)

    # Fourth track is sprint circuit
    ww, wh = 2300, 1600
    sprint = build_sprint_loop(Vec2(ww / 2, wh / 2))
    walls = boundary(ww, wh)
    # walls += [
    #     pygame.Rect(int(ww/2 + 420), int(wh/2 - 70), 18, 140),
    #     pygame.Rect(int(ww/2 + 360), int(wh/2 + 90), 18, 140),
    # ]
    power = [
        ("nitro", Vec2(ww / 2 - 180, wh / 2 - 360)),
        ("repair", Vec2(ww / 2 + 180, wh / 2 + 360)),
        ("shield", Vec2(ww / 2 - 360, wh / 2)),
        ("speed", Vec2(ww / 2 + 360, wh / 2)),
    ]
    coin_spawns = generate_coins_along_track(sprint, 16, 0.55)

    dynamic_obstacles = []
    if len(sprint) >= 8:
        center_x = sum(p.x for p in sprint) / len(sprint)
        center_y = sum(p.y for p in sprint) / len(sprint)
        center_point = Vec2(center_x, center_y)

        dynamic_obstacles.append(RotatingObstacle(pos=center_point, center=center_point, rotation_speed=1.8, rotation_radius=60, obstacle_type="barrel", damage=8))
        dynamic_obstacles.append(MovingObstacle(pos=sprint[1], path=[sprint[1], sprint[3]], speed=85, pause_time=0.2, obstacle_type="cone", damage=7))
        dynamic_obstacles.append(PatrolObstacle(pos=sprint[4], start_pos=sprint[4], end_pos=sprint[5], speed=65, obstacle_type="crate", damage=6))
        dynamic_obstacles.append(PulsingObstacle(pos=sprint[6], obstacle_type="rock", damage=5, pulse_speed=2.0, min_radius=10, max_radius=20))

    track = Track(
        "Sprint Circuit", (ww, wh), sprint,
        width=115, climate="dry",
        on_friction=1.02, off_friction=1.80,
        walls=walls, power_spawns=power,
        checkpoint_count=16,
        coin_spawns=coin_spawns,
        dynamic_obstacles=dynamic_obstacles,
        weather_type="fog",
        unlock_time_limit=85.0,
    )
    bg = asset_loader.load_track_bg("sprint_circuit")
    if bg:
        track.bg_surface = bg
    tracks.append(track)

    # Fifth track is maze harbor
    ww, wh = 1900, 1300
    maze_pts, maze_walls = build_maze_loop(Vec2(ww / 2, wh / 2))
    walls = boundary(ww, wh)
    power = [
        ("nitro", Vec2(ww / 2 + 500, wh / 2 - 260)),
        ("nitro", Vec2(ww / 2 - 500, wh / 2 + 260)),
        ("repair", Vec2(ww / 2, wh / 2)),
        ("shield", Vec2(ww / 2 + 300, wh / 2 + 200)),
        ("speed", Vec2(ww / 2 - 300, wh / 2 - 200)),
    ]
    coin_spawns = generate_coins_along_track(maze_pts, 20, 0.45)

    dynamic_obstacles = []
    if len(maze_pts) >= 12:
        safe_points = []
        for i in range(0, len(maze_pts), 3):
            point = maze_pts[i]
            too_close = False
            for wall in maze_walls:
                if point.distance_to(Vec2(wall.centerx, wall.centery)) < 100:
                    too_close = True
                    break
            if not too_close and len(safe_points) < 4:
                safe_points.append(point)

        if len(safe_points) >= 2:
            dynamic_obstacles.append(PatrolObstacle(pos=safe_points[0], start_pos=safe_points[0], end_pos=safe_points[1], speed=50, obstacle_type="barrel", damage=8))

        if len(safe_points) >= 4:
            dynamic_obstacles.append(MovingObstacle(pos=safe_points[2], path=[safe_points[2], safe_points[3]], speed=45, pause_time=0.4, obstacle_type="cone", damage=7))
            dynamic_obstacles.append(RotatingObstacle(pos=safe_points[1], center=safe_points[1], rotation_speed=1.0, rotation_radius=30, obstacle_type="crate", damage=6))
            dynamic_obstacles.append(RotatingObstacle(pos=safe_points[3], center=safe_points[3], rotation_speed=-1.2, rotation_radius=25, obstacle_type="rock", damage=5))

    track = Track(
        "Maze Harbor", (ww, wh), maze_pts,
        width=110, climate="wet",
        on_friction=0.80, off_friction=1.75,
        walls=walls, power_spawns=power,
        checkpoint_count=14,
        coin_spawns=coin_spawns,
        dynamic_obstacles=dynamic_obstacles,
        weather_type="heavy_rain",
        unlock_time_limit=95.0,
    )
    bg = asset_loader.load_track_bg("maze_harbor")
    if bg:
        track.bg_surface = bg
    tracks.append(track)

    # Sixth track is mixed mayham 
    ww, wh = 1900, 1300
    mixed = build_mixed(Vec2(ww / 2, wh / 2))
    walls = boundary(ww, wh)
    # walls += [
    #     pygame.Rect(int(ww/2 + 300), int(wh/2 - 40), 80, 80),
    #     pygame.Rect(int(ww/2 + 120), int(wh/2 + 260), 260, 22),
    # ]
    power = [
        ("nitro", Vec2(ww / 2 - 420, wh / 2)),
        ("repair", Vec2(ww / 2 + 420, wh / 2)),
        ("shield", Vec2(ww / 2 - 200, wh / 2 + 200)),
        ("speed", Vec2(ww / 2 + 200, wh / 2 - 200)),
        ("magnet", Vec2(ww / 2, wh / 2)),
    ]
    coin_spawns = generate_coins_along_track(mixed, 18, 0.5)

    dynamic_obstacles = []
    if len(mixed) >= 20:
        ellipse_points = mixed[:24]
        if len(ellipse_points) >= 8:
            center_idx = 12
            dynamic_obstacles.append(RotatingObstacle(pos=ellipse_points[center_idx], center=ellipse_points[center_idx], rotation_speed=1.5, rotation_radius=50, obstacle_type="barrel", damage=8))

        straight_points = mixed[24:]
        if len(straight_points) >= 4:
            dynamic_obstacles.append(MovingObstacle(pos=straight_points[0], path=[straight_points[0], straight_points[2]], speed=75, pause_time=0.3, obstacle_type="cone", damage=7))
            dynamic_obstacles.append(PatrolObstacle(pos=straight_points[1], start_pos=straight_points[1], end_pos=straight_points[3], speed=60, obstacle_type="crate", damage=6))
            if len(straight_points) >= 5:
                dynamic_obstacles.append(PulsingObstacle(pos=straight_points[4], obstacle_type="rock", damage=6, pulse_speed=2.5, min_radius=7, max_radius=20, damage_multiplier=1.3))

    track = Track(
        "Mixed Mayhem", (ww, wh), mixed,
        width=112, climate="dry",
        on_friction=1.00, off_friction=1.85,
        walls=walls, power_spawns=power,
        checkpoint_count=12,
        coin_spawns=coin_spawns,
        dynamic_obstacles=dynamic_obstacles,
        weather_type="sandstorm",
        unlock_time_limit=110.0,
    )
    bg = asset_loader.load_track_bg("mixed_mayhem")
    if bg:
        track.bg_surface = bg
    tracks.append(track)

    return tracks



# Game UI helpers

def draw_bar(surf: pygame.Surface, rect: pygame.Rect, frac: float, fg: Tuple[int, int, int], bg=(40, 40, 40)):
    pygame.draw.rect(surf, bg, rect, border_radius=6)
    inner = rect.inflate(-4, -4)
    inner.width = int(inner.width * clamp(frac, 0.0, 1.0))
    pygame.draw.rect(surf, fg, inner, border_radius=6)
    pygame.draw.rect(surf, (255, 255, 255, 80), rect, 2, border_radius=6)



# Main class for the game

class Game:
    def __init__(self,username:str):
        pygame.init()
        pygame.display.set_caption("Top-Down Racer")
        self.username = (username or "player").strip()

        #loads all the assets onto the main game
        self.assets = AssetLoader()
        self.screen = pygame.display.set_mode((1280, 720))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.Font(None, 28)
        self.font_big = pygame.font.Font(None, 56)
        self.font_small = pygame.font.Font(None, 22)

        self.audio = Audio()
        self.countdown_timer = 0.0
        self.countdown_phase = 0
 
        

        self.save = load_save(self.username) # saves the user's details independently
        self.race_started = False

        self.tracks = make_tracks(self.assets)
        self.track_index = 0
        self.difficulty = 1
        self.total_laps = 3

        self.selected_car_name = "Starter"

        self.state = "MAIN"
        self.menu_index = 0
        self.submenu_index = 0
        self.race_over_options = ["Play Again", "Exit"]
        self.race_over_index = 0
        self.can_go_next_track = False
        self.best_time_for_track = None

        self.race_time = 0.0
        self.race_over = False
        self.result_text = ""
        self.unlocked_this_race = False
        self.coins_earned = 0
        self.coins_collected = 0
        self.coins_lost_on_death = 0

        self.lap_times = []
        self.last_lap_time = 0.0
        self.current_lap_start = 0.0

        self.track: Optional[Track] = None
        self.cars: List[Car] = []
        self.ai_controllers: List[AIController] = []
        self.camera = Vec2(0, 0)

        self.player_died = False
        self.death_message_timer = 0.0
        self.death_message = ""

        self.obstacles_destroyed = 0

        self.weather: Optional[WeatherEffect] = None

    def render_weather_hud(self):
        """Display current weather in HUD"""
        if not self.track:
            return
            
        effect = self.track.weather_effect
        
        # Weather icon and text in top right
        weather_text = f"Weather: {effect.name}"
        weather_color = {
            "Clear": (200, 255, 200),
            "Rain": (150, 200, 255),
            "Heavy Rain": (100, 150, 255),
            "Snow": (240, 240, 255),
            "Fog": (200, 210, 220),
            "Sandstorm": (210, 190, 150)
        }.get(effect.name, (255, 255, 255))
        
        # Weather effects indicators
        x_pos = self.screen.get_width() - 200
        draw_text(self.screen, weather_text, (x_pos, 14), self.font, weather_color)
        
        # Drawing the icons effects
        y = 44
        if effect.visibility_factor < 1.0:
            draw_text(self.screen, f"Visibility: {int(effect.visibility_factor * 100)}%", 
                    (x_pos, y), self.font_small, (255, 255, 200))
            y += 20
        
        if effect.track_friction_modifier != 1.0:
            grip_text = "Low Grip" if effect.track_friction_modifier < 1.0 else "High Grip"
            grip_color = (255, 100, 100) if effect.track_friction_modifier < 1.0 else (100, 255, 100)
            draw_text(self.screen, grip_text, (x_pos, y), self.font_small, grip_color)
            y += 20
        
        if effect.handling_modifier < 1.0:
            draw_text(self.screen, "Poor Handling", (x_pos, y), self.font_small, (255, 150, 100))
            y += 20

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 1 / 30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.race_started and not self.race_over:
                        self.apply_quit_penalty()
                    running = False
                self.handle_event(event)

            self.update(dt)
            self.render()

        write_save(self.username,self.save)
        pygame.quit()

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN: # when the user presses the esc button
            return

        # escape key handling, it acts as a back or a quit button
        if event.key == pygame.K_ESCAPE:
            if self.state == "MAIN":
                # From main menu, Escape quits the game
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif self.state in ["CAR_SELECT", "TRACK_SELECT", "DIFFICULTY_SELECT", "SHOP"]:
                # From any submenu, Escape goes back to previous menu
                if self.state == "CAR_SELECT" or self.state == "TRACK_SELECT" or self.state == "DIFFICULTY_SELECT":
                    self.state = "MAIN"
                    self.menu_index = 0  # Reset to first option
                elif self.state == "SHOP":
                    self.state = "MAIN"
                    self.menu_index = 1  # Reset to Shop option since that's where they came from
            elif self.state == "PAUSE":
                # From pause menu, Escape resumes the race
                self.state = "RACE"
            elif self.state == "RACE_OVER":
                # From race over, Escape button pressed goes to main menu
                self.state = "MAIN"
                self.menu_index = 0
                self.race_started = False
            elif self.state == "RACE":
                self.state = "PAUSE" # pauses the game while in a race
            # Don't handle Escape in "RACE" state - that's already handled separately
            return

        
        
        if self.state == "RACE":
            if event.key == pygame.K_ESCAPE:
                self.state = "PAUSE"
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                player = self.player()
                if not player.is_dead:
                    player.try_activate_nitro()
                    self.audio.play("boost")
            return

        if self.state == "PAUSE":
            if event.key == pygame.K_ESCAPE:
                self.state = "RACE"
            if event.key == pygame.K_RETURN:
                self.state = "RACE"
            if event.key == pygame.K_BACKSPACE:
                if self.race_started and not self.race_over:
                    self.apply_quit_penalty()
                self.state = "MAIN"
                self.menu_index = 0
                self.race_started = False
            return

        if self.state == "RACE_OVER":
            # ESC already handled above, it goes to main menu
            if event.key == pygame.K_UP:
                self.race_over_index = (self.race_over_index - 1) % len(self.race_over_options)
                return
            if event.key == pygame.K_DOWN:
                self.race_over_index = (self.race_over_index + 1) % len(self.race_over_options)
                return
            if event.key == pygame.K_RETURN:
                choice = self.race_over_options[self.race_over_index]

                if choice == "Next Track":
                    num_unlocked = self.save.get("track_progress", 1)
                    next_idx = min(self.track_index + 1, num_unlocked - 1)
                    self.track_index = next_idx
                    self.state = "DIFFICULTY_SELECT"
                    self.submenu_index = self.difficulty
                    return

                if choice == "Play Again":
                    self.start_race()
                    return

                if choice == "Exit":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                    return
            return

        if self.state == "MAIN":
            items = ["Race", "Shop", "Quit"]
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(items)
            if event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(items)
            if event.key == pygame.K_RETURN:
                if self.menu_index == 0:
                    self.state = "CAR_SELECT"
                    self.submenu_index = 0
                elif self.menu_index == 1:
                    self.state = "SHOP"
                    self.submenu_index = 0
                else:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        if self.state == "CAR_SELECT":
            owned = self.save.get("owned", ["Starter"])
            cars = [s.name for s in CAR_SPECS if s.name in owned]
            if event.key == pygame.K_UP:
                self.submenu_index = (self.submenu_index - 1) % len(cars)
            if event.key == pygame.K_DOWN:
                self.submenu_index = (self.submenu_index + 1) % len(cars)
            if event.key == pygame.K_RETURN:
                self.selected_car_name = cars[self.submenu_index]
                self.state = "TRACK_SELECT"
                self.submenu_index = 0
            return

        if self.state == "TRACK_SELECT":
            num_unlocked = self.save.get("track_progress", 1)
            if event.key == pygame.K_UP:
                self.submenu_index = (self.submenu_index - 1) % num_unlocked
            if event.key == pygame.K_DOWN:
                self.submenu_index = (self.submenu_index + 1) % num_unlocked
            if event.key == pygame.K_RETURN:
                self.track_index = self.submenu_index
                self.state = "DIFFICULTY_SELECT"
                self.submenu_index = self.difficulty
            return

        if self.state == "DIFFICULTY_SELECT":
            diffs = ["Easy", "Normal", "Hard"]
            if event.key == pygame.K_UP:
                self.submenu_index = (self.submenu_index - 1) % len(diffs)
            if event.key == pygame.K_DOWN:
                self.submenu_index = (self.submenu_index + 1) % len(diffs)
            if event.key == pygame.K_RETURN:
                self.difficulty = self.submenu_index
                self.start_race()
            return

        if self.state == "SHOP":
            if event.key == pygame.K_UP:
                self.submenu_index = (self.submenu_index - 1) % (len(CAR_SPECS) + 1)
            if event.key == pygame.K_DOWN:
                self.submenu_index = (self.submenu_index + 1) % (len(CAR_SPECS) + 1)
            if event.key == pygame.K_RETURN:
                self.shop_action(self.submenu_index)
            return

    def apply_quit_penalty(self): # if the user quits they will lose all their coins earned within the race
        if not self.race_started or self.race_over:
            return

        coins_before = self.save.get("coins", 0)
        self.save["coins"] = 0

        penalty_text = f"QUIT PENALTY: Lost ALL {coins_before} coins for quitting!"
        write_save(self.username,self.save)

        print("=" * 50)
        print("HARSH PENALTY APPLIED!")
        print(penalty_text)
        print(f"Coins before: {coins_before}")
        print(f"Coins after: 0")
        print("=" * 50)

        self.race_started = False
        self.coins_collected = 0
        self.coins_earned = 0
        self.obstacles_destroyed = 0

    def shop_action(self, idx: int):
        coins = int(self.save.get("coins", 0))
        owned = set(self.save.get("owned", ["Starter"]))
        upgrades = self.save.get("upgrades", {})

        if idx == len(CAR_SPECS):
            name = self.selected_car_name
            if name not in owned:
                return
            lvl = int(upgrades.get(name, 0))
            cost = 220 + lvl * 180
            if coins >= cost:
                coins -= cost
                upgrades[name] = lvl + 1
                self.save["coins"] = coins
                self.save["upgrades"] = upgrades
                write_save(self.username,self.save)
            return

        spec = CAR_SPECS[idx]
        if spec.name in owned:
            self.selected_car_name = spec.name
            return
        if coins >= spec.cost:
            coins -= spec.cost
            owned.add(spec.name)
            self.save["coins"] = coins
            self.save["owned"] = sorted(list(owned), key=lambda n: [s.name for s in CAR_SPECS].index(n))
            write_save(self.username,self.save)

    def apply_upgrades(self, spec: CarSpec) -> CarSpec:
        upgrades = self.save.get("upgrades", {})
        lvl = int(upgrades.get(spec.name, 0))
        if lvl <= 0:
            return spec
        mul_speed = 1.0 + 0.04 * lvl
        mul_accel = 1.0 + 0.05 * lvl
        mul_hand = 1.0 + 0.03 * lvl
        add_hp = 6 * lvl
        return CarSpec(
            spec.name,
            max_speed=spec.max_speed * mul_speed,
            accel=spec.accel * mul_accel,
            handling=spec.handling * mul_hand,
            max_hp=spec.max_hp + add_hp,
            cost=spec.cost,
        )

    def start_race(self):
        self.track = self.tracks[self.track_index]
        t = self.track

        base = SPEC_BY_NAME[self.selected_car_name]
        pspec = self.apply_upgrades(base)

        start = Vec2(t.start_pos)
        ang = t.start_angle

        self.cars = []
        self.ai_controllers = []

        self.weather = t.weather_effect

        player = Car(pspec, (70, 210, 255), start + Vec2(-10, -20), ang, True)
        player.game = self
        self.cars.append(player)
        player.sprite = self.assets.load_car(pspec.name, scale=0.5)

        ai_specs = []
        pool = CAR_SPECS[0:] if self.difficulty < 2 else CAR_SPECS[1:]
        for _ in range(5):
            ai_specs.append(random.choice(pool))

        colors = [(255, 120, 90), (255, 210, 80), (170, 255, 120), (220, 160, 255), (255, 120, 210)]
        for i, s in enumerate(ai_specs):
            ai_spec = s
            if self.difficulty == 1:
                ai_spec = CarSpec(s.name, s.max_speed * 1.02, s.accel * 1.02, s.handling * 1.01, s.max_hp, s.cost)
            if self.difficulty == 2:
                ai_spec = CarSpec(s.name, s.max_speed * 1.05, s.accel * 1.06, s.handling * 1.03, s.max_hp, s.cost)
            c = Car(ai_spec, colors[i % len(colors)], start + Vec2(-40 - 18 * i, 30 + 18 * i), ang, False)
            self.cars.append(c)
            self.ai_controllers.append(AIController(self.difficulty))
            c.sprite = self.assets.load_car(ai_spec.name, scale=0.5)

        self.race_time = 0.0
        self.race_over = False
        self.race_started = True
        self.result_text = ""
        self.coins_earned = 0
        self.coins_collected = 0
        self.coins_lost_on_death = 0
        self.obstacles_destroyed = 0
        self.player_died = False
        self.death_message_timer = 0.0
        self.death_message = ""

        self.lap_times = []
        self.last_lap_time = -999.0
        self.current_lap_start = 0.0

        print("=" * 50)
        print("STARTING RACE!")
        print(f"Current coins: {self.save.get('coins', 0)}")
        print(f"Track: {t.name} - Features {len(t.dynamic_obstacles)} dynamic obstacles")
        print(f"Time to beat for next unlock: {t.unlock_time_limit:.1f} seconds")
        print(" WARNING: Quitting before finish will lose ALL your coins!")
        print(" Death penalty: Lose coins collected on this track")
        print("=" * 50)

        # Starts the weather sound
        self.audio.play_weather(self.track.weather_type)

        self.state = "RACE"

    def player(self) -> Car:
        return self.cars[0]

    def update(self, dt: float):
        if self.state == "RACE":
            self.update_race(dt)

        if self.death_message_timer > 0:
            self.death_message_timer -= dt

    def update_race(self, dt: float):
        assert self.track is not None
        t = self.track
        self.race_time += dt

        # Update track weather particles
        t.update_weather(dt)

        t.update_powerups(dt)

        keys = pygame.key.get_pressed()
        throttle = brake = steer = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            throttle = 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            brake = 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            steer -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            steer += 1.0

        for idx, car in enumerate(self.cars):
            car.update_timers(dt)
            if car.finished:
                continue

            if car.is_player:
                car.update_physics(dt, throttle, brake, steer, t, self.audio)
            else:
                ai = self.ai_controllers[idx - 1]
                th, br, st = ai.get_inputs(car, t, dt, self.cars)
                car.update_physics(dt, th, br, st, t, None)

            # Update checkpoints, this will handle lap counting
            car.update_checkpoints(t, self.audio, self)  
                
            
            # t.check_start_finish_line(car)

            if car.is_player and car.is_dead and not self.player_died:
                self.player_died = True
                self.coins_lost_on_death = self.coins_collected
                self.coins_collected = 0
                self.death_message = f"PLAYER DIED! Lost {self.coins_lost_on_death} coins from this track."
                self.death_message_timer = 3.0
                print(f"Player died! Lost {self.coins_lost_on_death} coins from this track")

            if car.is_player and not car.is_dead and self.player_died:
                self.player_died = False

            if not car.is_dead:
                for pu in t.powerups:
                    if pu.active and (car.pos - pu.pos).length() <= (car.radius + pu.radius):
                        pu.active = False
                        pu.respawn_timer = 6.5
                        if pu.kind == "nitro":
                            car.try_activate_nitro()
                            if car.is_player:
                                self.audio.play("pickup")
                                self.audio.play("boost")
                        elif pu.kind == "repair":
                            car.heal(35.0)
                            if car.is_player:
                                self.audio.play("repair")
                        else:
                            car.activate_powerup(pu.kind)
                            if car.is_player:
                                self.audio.play("pickup")

                if car.is_player:
                    for coin in t.coins:
                        # Check magnet range for player
                        collection_range = coin.radius + car.radius + car.coin_collection_range
                        if coin.active and (car.pos - coin.pos).length() <= collection_range:
                            coin.active = False
                            coin.respawn_timer = 8.0
                            self.coins_collected += coin.value
                            self.coins_earned += coin.value
                            self.audio.play("coin")

          # Check if AI cars finished (based on laps)
            if (not car.is_player) and car.laps >= self.total_laps and not car.finished:
                car.finished = True
                car.finish_time = self.race_time
                print(f"Car {car.spec.name} finished with {car.laps} laps!")

        p = self.player()
        if p.laps >= self.total_laps and not self.race_over:
            if not p.finished:
                p.finished = True
                p.finish_time = self.race_time

            self.race_over = True
            self.result_text = "RACE FINISHED!"
            self.last_lap_time = self.race_time
            self.finish_race()

        # Camera follow player
        p = self.player()
        self.camera.x = clamp(p.pos.x - self.screen.get_width() / 2, 0, t.world_w - self.screen.get_width())
        self.camera.y = clamp(p.pos.y - self.screen.get_height() / 2, 0, t.world_h - self.screen.get_height())

    def finish_race(self):
        assert self.track is not None # only works if the track is loaded
        order = sorted(self.cars, key=lambda c: c.progress_value(self.track), reverse=True) #all cars are stored based on the progress around the track
        pos = order.index(self.player()) + 1 # 
        base = {1: 140, 2: 105, 3: 85, 4: 70, 5: 55, 6: 45}.get(pos, 35) # higher finishing positions = more coins
        diff_mul = [0.85, 1.0, 1.22][self.difficulty] # higher difficulty = higher rewards
        track_mul = 1.0 + (len(self.track.walls) / 80.0) # more walls = higher bonus rewards

        #faster lap timings will mean additional coins
        # rewards efficient driving for the player
        time_bonus = 0
        avg_lap_time = self.race_time / self.total_laps if self.total_laps > 0 else 0
        if avg_lap_time < 60:
            time_bonus = int((60 - avg_lap_time) * 2)

        # Check if beat unlock time = determine if the user unlocks the next track
        beat_unlock_time = self.race_time < self.track.unlock_time_limit
        time_limit_bonus = 50 if beat_unlock_time else 0


        #rewards for destroying obstacles
        obstacle_bonus = self.obstacles_destroyed * 5
        position_bonus = int(base * diff_mul * track_mul) + time_bonus + obstacle_bonus + time_limit_bonus
        total_coins_earned = position_bonus + self.coins_collected

        self.save["coins"] = self.save.get("coins", 0) + total_coins_earned

        unlock_msg = ""
        unlocked_count = self.save.get("track_progress", 1)

        # Check unlock conditions: beat time limit
        if (beat_unlock_time) and self.track_index == unlocked_count - 1 and unlocked_count < len(self.tracks):
            self.unlocked_this_race = True
            self.save["track_progress"] = unlocked_count + 1
            unlock_msg = f" New Track Unlocked! (Beat time limit of {self.track.unlock_time_limit:.1f}s)"

        # Best time per track 
        best_times = self.save.get("best_times", {})
        key = str(self.track_index)
        prev_best = best_times.get(key)

        # update best time if first time or improved
        if (prev_best is None) or (self.race_time < float(prev_best)):
            best_times[key] = float(self.race_time)

        self.save["best_times"] = best_times
        self.best_time_for_track = float(best_times[key])
        self.prev_best_time_for_track = None if prev_best is None else float(prev_best)


        # Build Race Over menu options 
        # You can go to next track if it is unlocked already OR you unlocked it this race
        num_unlocked = self.save.get("track_progress", 1)
        self.can_go_next_track = (self.track_index + 1) < num_unlocked

        if self.can_go_next_track:
            self.race_over_options = ["Next Track", "Play Again", "Exit"]
            self.race_over_index = 0  # Enter goes to next track
        else:
            self.race_over_options = ["Play Again", "Exit"]
            self.race_over_index = 0  # Enter goes to play again
            

        write_save(self.username,self.save) # saves the data into the database remembering the username

        lap_time_text = ""
        if self.lap_times:
            best_lap = min(self.lap_times)
            lap_time_text = f" Best Lap: {best_lap:.1f}s"

        obstacle_text = f" (Destroyed {self.obstacles_destroyed} obstacles)" if self.obstacles_destroyed > 0 else ""
        self.coins_earned = total_coins_earned

        death_penalty_text = ""
        if self.coins_lost_on_death > 0:
            death_penalty_text = f" [Death penalty: -{self.coins_lost_on_death} coins]"

        self.result_text = f"Finished {pos}/{len(self.cars)} in {self.race_time:.1f}s{lap_time_text}{obstacle_text}  +{total_coins_earned} coins{death_penalty_text}{unlock_msg}"
        self.state = "RACE_OVER"
        self.race_started = False

    def render(self): # drawing the titles within the main menu
        self.screen.fill((14, 14, 16))

        if self.state == "MAIN":
            self.render_main()
        elif self.state == "CAR_SELECT":
            self.render_car_select()
        elif self.state == "TRACK_SELECT":
            self.render_track_select()
        elif self.state == "DIFFICULTY_SELECT":
            self.render_difficulty_select()
        elif self.state == "SHOP":
            self.render_shop()
        elif self.state == "RACE":
            self.render_race()
        elif self.state == "PAUSE":
            self.render_race()
            self.render_pause_overlay()
        elif self.state == "RACE_OVER":
            self.render_race()
            self.render_race_over_overlay()

        pygame.display.flip()

    def render_main(self):
        draw_text(self.screen, "RETRO DRIFTERS", (40, 35), self.font_big)
        draw_text(self.screen, "DYNAMIC OBSTACLES & POWER-UPS!", (40, 85), self.font, (100, 200, 255))
        draw_text(self.screen, f"Coins: {self.save.get('coins', 0)}", (40, 115), self.font)
        draw_text(self.screen, f"Tracks Unlocked: {self.save.get('track_progress', 1)}/{len(self.tracks)}", (40, 145), self.font)
        items = ["Race", "Shop", "Quit"]
        for i, it in enumerate(items):
            c = (255, 255, 255) if i == self.menu_index else (180, 180, 180)
            draw_text(self.screen, ("> " if i == self.menu_index else "  ") + it, (60, 180 + 40 * i), self.font, c)
        draw_text(self.screen, "WARNING: Quitting during a race will lose ALL your coins!", (40, 620), self.font_small, (255, 50, 50))
        draw_text(self.screen, " Death penalty: Lose coins collected on current track", (40, 640), self.font_small, (255, 150, 50))
        draw_text(self.screen, "Controls: WASD/Arrows drive, Shift nitro, Esc pause", (40, 660), self.font_small, (210, 210, 210))

    def render_car_select(self):
        owned = self.save.get("owned", ["Starter"])
        cars = [s.name for s in CAR_SPECS if s.name in owned]
        draw_text(self.screen, "Select Car", (40, 35), self.font_big)
        draw_text(self.screen, f"Owned: {len(cars)}   Coins: {self.save.get('coins', 0)}", (40, 95), self.font)
        for i, name in enumerate(cars):
            spec = SPEC_BY_NAME[name]
            c = (255, 255, 255) if i == self.submenu_index else (180, 180, 180)
            draw_text(self.screen, ("> " if i == self.submenu_index else "  ") + name, (60, 160 + 34 * i), self.font, c)
            draw_text(self.screen, f"  Speed {spec.max_speed:.0f}  Accel {spec.accel:.0f}  Handling {spec.handling:.2f}  HP {spec.max_hp:.0f}",
                      (320, 160 + 34 * i), self.font_small, (170, 170, 170))
        draw_text(self.screen, "Enter = confirm   Esc = back", (40, 660), self.font_small, (210, 210, 210))

    def render_track_select(self):
        draw_text(self.screen, "Select Track", (40, 35), self.font_big)
        draw_text(self.screen, f"Car: {self.selected_car_name}", (40, 95), self.font)
        num_unlocked = self.save.get("track_progress", 1)

        for i, tr in enumerate(self.tracks):
            if i < num_unlocked:
                c = (255, 255, 255) if i == self.submenu_index else (180, 180, 180)
                draw_text(self.screen, ("> " if i == self.submenu_index else "  ") + tr.name, (60, 160 + 34 * i), self.font, c)

                # Show weather icon
                weather = tr.weather_effect
                weather_colors = {
                    "Clear": (100, 255, 100),
                    "Rain": (100, 150, 255),
                    "Heavy Rain": (50, 100, 255),
                    "Snow": (200, 230, 255),
                    "Fog": (180, 190, 210),
                    "Sandstorm": (210, 190, 150)
                }
                weather_color = weather_colors.get(weather.name, (255, 255, 255))
                draw_text(self.screen, f"  {weather.name}", 
                        (420, 160 + 34 * i), self.font_small, weather_color)
                
                # Show unlock time
                draw_text(self.screen, f"  Beat: {tr.unlock_time_limit:.1f}s", 
                        (600, 160 + 34 * i), self.font_small, (255, 255, 100))
                
                # Show stats
                obstacle_count = len(tr.dynamic_obstacles)
                coin_count = len(tr.coins)
                powerup_count = len(tr.powerups)
                draw_text(self.screen, f"  {obstacle_count} {coin_count} {powerup_count}", 
                        (750, 160 + 34 * i), self.font_small, (200, 200, 200))
            else:
                draw_text(self.screen, "  [LOCKED] " + tr.name, (60, 160 + 34 * i), self.font, (100, 100, 100))
                draw_text(self.screen, f"  Finish top 3 or beat {tr.unlock_time_limit:.1f}s", 
                        (420, 160 + 34 * i), self.font_small, (150, 150, 150))
        draw_text(self.screen, "Finish top 3 OR beat the time limit to unlock next track.", (40, 600), self.font_small, (210, 210, 210))
        draw_text(self.screen, "Enter = confirm   Esc = back", (40, 680), self.font_small, (210, 210, 210))

    def render_difficulty_select(self):
        draw_text(self.screen, "Select Difficulty", (40, 35), self.font_big)
        diffs = ["Easy", "Normal", "Hard"]
        for i, d in enumerate(diffs):
            c = (255, 255, 255) if i == self.submenu_index else (180, 180, 180)
            draw_text(self.screen, ("> " if i == self.submenu_index else "  ") + d, (60, 170 + 40 * i), self.font, c)
        draw_text(self.screen, f"Track: {self.tracks[self.track_index].name}", (40, 110), self.font)
        draw_text(self.screen, f"Obstacles: {len(self.tracks[self.track_index].dynamic_obstacles)}", (40, 140), self.font_small, (255, 200, 100))
        draw_text(self.screen, f"Coins: {len(self.tracks[self.track_index].coins)}", (40, 160), self.font_small, (255, 215, 0))
        #draw_text(self.screen, f"Power-ups: {len(self.tracks[self.track_index].powerups)}", (40, 180), self.font_small, (100, 200, 255))
        draw_text(self.screen, "Enter = start race   Esc = back", (40, 680), self.font_small, (210, 210, 210))

    def render_shop(self):
        coins = int(self.save.get("coins", 0))
        owned = set(self.save.get("owned", ["Starter"]))
        upgrades = self.save.get("upgrades", {})
        draw_text(self.screen, "Shop", (40, 35), self.font_big)
        draw_text(self.screen, f"Coins: {coins}", (40, 95), self.font)
        y = 160
        for i, s in enumerate(CAR_SPECS):
            sel = (i == self.submenu_index)
            c = (255, 255, 255) if sel else (180, 180, 180)
            status = "OWNED" if s.name in owned else f"{s.cost} coins"
            line = f"{s.name}  [{status}]"
            draw_text(self.screen, ("> " if sel else "  ") + line, (60, y), self.font, c)
            draw_text(self.screen, f"  Speed {s.max_speed:.0f}  Accel {s.accel:.0f}  Handling {s.handling:.2f}  HP {s.max_hp:.0f}",
                      (420, y), self.font_small, (170, 170, 170))
            y += 34
        up_idx = len(CAR_SPECS)
        sel = (up_idx == self.submenu_index)
        c = (255, 255, 255) if sel else (180, 180, 180)
        lvl = int(upgrades.get(self.selected_car_name, 0))
        cost = 220 + lvl * 180
        draw_text(self.screen, ("> " if sel else "  ") + f"Upgrade selected car ({self.selected_car_name})  [Lvl {lvl}]  Cost {cost}",
                  (60, y + 18), self.font, c)
        draw_text(self.screen, "Enter = buy/select/upgrade   Esc = back", (40, 660), self.font_small, (210, 210, 210))

    def render_race(self):
        assert self.track is not None
        t = self.track
        effect = t.weather_effect
        
        # Apply light level (dimmer for bad weather)
        light_multiplier = effect.light_level / 255.0
        bg_col = (int(34 * light_multiplier), int(60 * light_multiplier), int(34 * light_multiplier))
        self.screen.fill(bg_col)
        
        view = pygame.Rect(int(self.camera.x), int(self.camera.y), 
                        self.screen.get_width(), self.screen.get_height())

        # Draw track background
        if t.bg_surface:
            self.screen.blit(t.bg_surface, (0, 0), area=view)
        self.screen.blit(t.track_surface, (0, 0), area=view)
        
        # Draw weather particles
        if effect.particle_count > 0:
            for p in t.weather_particles:
                screen_pos = p['pos'] - self.camera
                if -20 < screen_pos.x < 1300 and -20 < screen_pos.y < 740:  # Check if on screen
                    color = effect.particle_color
                    alpha_color = (*color, p['alpha'])
                    
                    # Draw different particle types
                    if effect.name == "Snow":
                        pygame.draw.circle(self.screen, alpha_color, 
                                        (int(screen_pos.x), int(screen_pos.y)), p['size'])
                    elif effect.name in ["Rain", "Heavy Rain"]:
                        pygame.draw.line(self.screen, alpha_color,
                                    (int(screen_pos.x), int(screen_pos.y)),
                                    (int(screen_pos.x), int(screen_pos.y + p['size'])), 2)
                    else:  # Fog, Sandstorm
                        pygame.draw.circle(self.screen, alpha_color,
                                        (int(screen_pos.x), int(screen_pos.y)), p['size']//2)
        
        # Drawing the fog overlay for low visibility
        if effect.visibility_factor < 0.6:
            fog_alpha = int(100 * (1.0 - effect.visibility_factor))
            fog_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            fog_surf.fill((*effect.fog_color, fog_alpha))
            self.screen.blit(fog_surf, (0, 0))
        
        # Draw weather icon in HUD
        self.render_weather_hud()

        # coins
        for coin in t.coins:
            if not coin.active:
                continue
            p = coin.pos - self.camera
            pygame.draw.circle(self.screen, (255, 215, 0), (int(p.x), int(p.y)), coin.radius)
            pygame.draw.circle(self.screen, (255, 255, 0), (int(p.x), int(p.y)), coin.radius - 2)
            pygame.draw.circle(self.screen, (255, 200, 0), (int(p.x), int(p.y)), coin.radius - 4)
            draw_text(self.screen, "$", (int(p.x) - 4, int(p.y) - 8), self.font_small, (0, 0, 0), shadow=False)

        # powerups
        for pu in t.powerups:
            if not pu.active:
                continue
            p = pu.pos - self.camera
            sprite = self.assets.load_powerup(pu.kind)
            if sprite:
                rect = sprite.get_rect(center=(int(p.x), int(p.y)))
                self.screen.blit(sprite, rect)
            else:
                # Fallback drawing
                colors = {
                    "nitro": (110, 190, 255),
                    "repair": (120, 255, 140),
                    "shield": (200, 180, 255),
                    "speed": (255, 220, 100),
                    "magnet": (255, 150, 150)
                }
                color = colors.get(pu.kind, (200, 200, 200))
                pygame.draw.circle(self.screen, color, (int(p.x), int(p.y)), pu.radius)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(p.x), int(p.y)), pu.radius, 2)

        # obstacles
        for obstacle in t.dynamic_obstacles:
            obstacle.draw(self.screen, self.camera, self.assets)

        # checkpoints - with special highlighting for start/finish
        for i, cp in enumerate(t.checkpoints):
            p = cp.center - self.camera
            # Special coloring for start/finish checkpoint (first checkpoint)
            if i == 0:  # Start/finish line
                col = (255, 255, 0, 150)  # Yellow for start/finish
                # Draw additional highlight
                pygame.draw.circle(self.screen, (255, 255, 0, 80), 
                                 (int(p.x), int(p.y)), int(cp.radius + 5), 4)
                
                # Drawing "start/finish" text
                start_text = self.font.render("START/FINISH", True, (255, 255, 0))
                text_rect = start_text.get_rect(center=(int(p.x), int(p.y) - 50))
                self.screen.blit(start_text, text_rect)
            else:
                col = (255, 255, 255, 60)
            
            pygame.draw.circle(self.screen, col, (int(p.x), int(p.y)), int(cp.radius), 2)

        # cars
        for car in self.cars:
            p = car.pos - self.camera
            if car.is_dead and car.is_player:
                if car.death_flash > 0.5:
                    pygame.draw.circle(self.screen, (255, 50, 50, 180), (int(p.x), int(p.y)), car.radius + 10)
                continue

            # Draw power-up effects
            if car.shield_active:
                pygame.draw.circle(self.screen, (200, 180, 255, 100), (int(p.x), int(p.y)), car.radius + 12)
            if car.speed_boost_active:
                pygame.draw.circle(self.screen, (255, 220, 100, 80), (int(p.x), int(p.y)), car.radius + 10)
            if car.magnet_active:
                pygame.draw.circle(self.screen, (255, 150, 150, 60), (int(p.x), int(p.y)), car.radius + car.coin_collection_range, 2)
            
            if car.nitro_active:
                pygame.draw.circle(self.screen, (110, 190, 255, 60), (int(p.x), int(p.y)), car.radius + 8)
            if car.repair_flash > 0:
                pygame.draw.circle(self.screen, (120, 255, 140, 80), (int(p.x), int(p.y)), car.radius + 7)
            if car.obstacle_hit_flash > 0:
                alpha = int(180 * car.obstacle_hit_flash / 0.4)
                pygame.draw.circle(self.screen, (255, 50, 50, alpha), (int(p.x), int(p.y)), car.radius + 6)

            if car.sprite:
                rot = pygame.transform.rotate(car.sprite, -math.degrees(car.angle) - 90)
                r = rot.get_rect(center=(int(p.x), int(p.y)))
                self.screen.blit(rot, r.topleft)
            else:
                w, h = 28, 16
                body = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.rect(body, car.color, pygame.Rect(0, 0, w, h), border_radius=4)
                rot = pygame.transform.rotate(body, -math.degrees(car.angle))
                r = rot.get_rect(center=(int(p.x), int(p.y)))
                self.screen.blit(rot, r.topleft)

            frac = car.hp / car.spec.max_hp
            bar_w = 34
            bx = int(p.x - bar_w / 2)
            by = int(p.y - 30)
            pygame.draw.rect(self.screen, (30, 30, 30), pygame.Rect(bx, by, bar_w, 6), border_radius=3)
            pygame.draw.rect(self.screen, (240, 70, 70), pygame.Rect(bx + 1, by + 1, int((bar_w - 2) * frac), 4), border_radius=3)

        # lap completion announcement
        if self.race_time - self.last_lap_time < 1.0 and self.player().laps > 0:
            alpha = int(255 * (1.0 - (self.race_time - self.last_lap_time)))
            
            # Create announcement text
            if self.player().laps < self.total_laps:
                lap_text = f"LAP {self.player().laps} COMPLETE!"
                text_color = (100, 200, 255)
            else:
                lap_text = "FINAL LAP COMPLETE!"
                text_color = (255, 215, 0)
            
            # Draw semi-transparent background
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha // 3))
            self.screen.blit(overlay, (0, 0))
            
            # Draw lap text
            font_big = pygame.font.Font(None, 64)
            text_surf = font_big.render(lap_text, True, text_color)
            text_rect = text_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 - 50))
            
            # Shadow
            shadow_surf = font_big.render(lap_text, True, (0, 0, 0))
            self.screen.blit(shadow_surf, (text_rect.x + 4, text_rect.y + 4))
            self.screen.blit(text_surf, text_rect)
            
            # Show lap time if available
            if self.player().laps <= len(self.lap_times):
                lap_time = self.lap_times[self.player().laps - 1]
                time_text = f"Time: {lap_time:.2f}s"
                time_surf = self.font_big.render(time_text, True, (200, 255, 200))
                time_rect = time_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 20))
                time_shadow = self.font_big.render(time_text, True, (0, 0, 0))
                self.screen.blit(time_shadow, (time_rect.x + 2, time_rect.y + 2))
                self.screen.blit(time_surf, time_rect)

                # lap completion flash (simple version)
        if self.race_time - self.last_lap_time < 0.5 and self.player().laps > 0:
            alpha = int(255 * (1.0 - (self.race_time - self.last_lap_time) * 2))
            if alpha > 0:
                flash = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                flash.fill((255, 255, 255, alpha // 4))
                self.screen.blit(flash, (0, 0))

        # death message
        if self.death_message_timer > 0:
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))

            death_text = "PLAYER DIED!"
            text_surf = self.font_big.render(death_text, True, (255, 50, 50))
            text_rect = text_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 - 50))
            shadow_surf = self.font_big.render(death_text, True, (0, 0, 0))
            self.screen.blit(shadow_surf, (text_rect.x + 2, text_rect.y + 2))
            self.screen.blit(text_surf, text_rect)

            respawn_text = f"Respawning in {self.player().death_timer:.1f}s..."
            text_surf = self.font.render(respawn_text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 20))
            self.screen.blit(text_surf, text_rect)

            penalty_text = f"Lost {self.coins_lost_on_death} coins from this track"
            text_surf = self.font_small.render(penalty_text, True, (255, 200, 100))
            text_rect = text_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 60))
            self.screen.blit(text_surf, text_rect)

        self.render_hud()

    def render_hud(self):  
        assert self.track is not None
        t = self.track

        self.render_weather_hud()
        p = self.player()
        order = sorted(self.cars, key=lambda c: c.progress_value(t), reverse=True)
        pos = order.index(p) + 1

        
        # lap counter, it displays the player's current lap during the race 
        current_lap = min(p.laps + 1, self.total_laps)  # +1 because laps starts at 0
        lap_text = f"LAP {current_lap}/{self.total_laps}" # the text shown on the screen
        
        # Different colors based on lap status
        if current_lap == self.total_laps:  # Final lap
            lap_color = (255, 215, 0)  # Gold
            # Add pulsing effect for final lap
            pulse = int(50 + 50 * math.sin(self.race_time * 3))
            bg_color = (255, 215, 0, pulse)
        elif current_lap == self.total_laps - 1:  # Penultimate lap
            lap_color = (255, 150, 50)  # Orange
            bg_color = (255, 150, 50, 30)
        else:
            #normal laps
            lap_color = (255, 255, 255)  # White
            bg_color = (255, 255, 255, 20)
        
        # Draw background with a semi-transparent background so the text can remain readable 
        lap_bg = pygame.Surface((120, 40), pygame.SRCALPHA)
        pygame.draw.rect(lap_bg, bg_color, (0, 0, 120, 40), border_radius=8)
        pygame.draw.rect(lap_bg, (255, 255, 255, 50), (0, 0, 120, 40), 2, border_radius=8)
        self.screen.blit(lap_bg, (18, 14))
        
        # Draw lap text
        lap_font = pygame.font.Font(None, 32)
        draw_text(self.screen, lap_text, (28, 24), lap_font, lap_color)
        
        # Show current lap progress (checkpoints)
        if not p.finished:
            progress = p.next_cp / len(t.checkpoints) if len(t.checkpoints) > 0 else 0
            progress_text = f"Checkpoint: {p.next_cp}/{len(t.checkpoints)}"
            draw_text(self.screen, progress_text, (18, 64), self.font_small, (200, 200, 255))

        
        # original speed and position of the car
        
        draw_text(self.screen, f"Speed: {p.vel.length():6.0f} mph", (18, 84), self.font)
        draw_text(self.screen, f"Position: {pos}/{len(self.cars)}", (18, 114), self.font)

        
        # lap display times
        
        # Show current lap time
        if p.laps > 0:
            current_lap_time = self.race_time - self.current_lap_start
            draw_text(self.screen, f"Lap Time: {current_lap_time:.1f}s", (18, 144), self.font_small, (200, 255, 200))

        # Show best lap time
        if self.lap_times:
            best_lap = min(self.lap_times)
            draw_text(self.screen, f"Best: {best_lap:.1f}s", (18, 164), self.font_small, (255, 255, 100))

        
        # visual lap progress bar
        
        if not p.finished:
            # Calculate progress through current lap
            checkpoints_completed = p.next_cp
            total_checkpoints = len(t.checkpoints)
            
            if total_checkpoints > 0:
                progress = checkpoints_completed / total_checkpoints
                progress_bar_width = 200
                progress_bar_height = 8
                
                # Background
                pygame.draw.rect(self.screen, (40, 40, 40), 
                            (18, 190, progress_bar_width, progress_bar_height), 
                            border_radius=4)
                
                # Fill
                fill_width = int(progress_bar_width * progress)
                if fill_width > 0:
                    fill_color = (100, 200, 255)  # Blue for normal laps
                    if current_lap == self.total_laps:  # Gold for final lap
                        fill_color = (255, 215, 0)
                    elif current_lap == self.total_laps - 1:  # Orange for penultimate
                        fill_color = (255, 150, 50)
                    
                    pygame.draw.rect(self.screen, fill_color, 
                                (18, 190, fill_width, progress_bar_height), 
                                border_radius=4)
                
                # Border
                pygame.draw.rect(self.screen, (255, 255, 255, 100), 
                            (18, 190, progress_bar_width, progress_bar_height), 
                            1, border_radius=4)
                
                # Progress text
                progress_text = f"Lap Progress: {int(progress * 100)}%"
                draw_text(self.screen, progress_text, (18, 204), self.font_small, (200, 230, 255))

        
        # track information 
        
        draw_text(self.screen, f"Track: {t.name}", (18, 230), self.font_small, (220, 220, 220))

        
        # obstacle counter 
        
        active_obstacles = sum(1 for o in t.dynamic_obstacles if o.active)
        draw_text(self.screen, f"Obstacles: {self.obstacles_destroyed}/{len(t.dynamic_obstacles)} destroyed",
                (18, 250), self.font_small, (255, 200, 100))

        
        # health bar for the user's car
        
        hb = pygame.Rect(18, 274, 260, 18)
        draw_bar(self.screen, hb, p.hp / p.spec.max_hp, fg=(240, 70, 70))
        draw_text(self.screen, "HP", (hb.x + hb.w + 10, hb.y - 2), self.font_small, (230, 230, 230))

        
        # nitro bar when the user uses nitros
        
        nb = pygame.Rect(18, 300, 260, 18)
        if p.nitro_active:
            frac = p.nitro_timer / 1.6
            draw_bar(self.screen, nb, frac, fg=(110, 190, 255))
            draw_text(self.screen, "NITRO ACTIVE", (nb.x + nb.w + 10, nb.y - 2), self.font_small, (200, 220, 255))
        else:
            cd = clamp(1.0 - (p.nitro_cooldown / 4.5), 0.0, 1.0)
            draw_bar(self.screen, nb, cd, fg=(80, 110, 140))
            txt = "Nitro READY (Shift)" if p.nitro_cooldown <= 0 else f"Nitro cooldown: {p.nitro_cooldown:0.1f}s"
            draw_text(self.screen, txt, (nb.x + nb.w + 10, nb.y - 2), self.font_small, (210, 210, 210))

        
        # power-up status when activited
        
        y_offset = 326
        if p.shield_active:
            draw_text(self.screen, f"Shield: {p.shield_timer:.1f}s", (18, y_offset), self.font_small, (200, 180, 255))
            y_offset += 20
        if p.speed_boost_active:
            draw_text(self.screen, f"Speed Boost: {p.speed_boost_timer:.1f}s", (18, y_offset), self.font_small, (255, 220, 100))
            y_offset += 20
        if p.magnet_active:
            draw_text(self.screen, f"Magnet: {p.magnet_timer:.1f}s", (18, y_offset), self.font_small, (255, 150, 150))
            y_offset += 20

        
        # coins and stats written in the HUD
        
        draw_text(self.screen, f"Coins collected: {self.coins_collected}", (18, y_offset), self.font_small, (255, 215, 0))
        y_offset += 20
        draw_text(self.screen, f"Obstacles destroyed: {self.obstacles_destroyed} (+{self.obstacles_destroyed * 5} coins)",
                (18, y_offset), self.font_small, (255, 200, 100))
        y_offset += 20


        # time limit display for the next track to be unlocked
        
        draw_text(self.screen, f"Unlock Time: {t.unlock_time_limit:.1f}s", (18, y_offset), self.font_small, (255, 255, 100))
        y_offset += 20

        
        # warnings for the user
        
        if not self.race_over and not p.is_dead:
            draw_text(self.screen, "Death: Lose coins collected on this track", (18, y_offset), self.font_small, (255, 150, 50))
            y_offset += 20
            draw_text(self.screen, "Quit: LOSE ALL COINS!", (18, y_offset), self.font_small, (255, 50, 50))
            y_offset += 20

        
        # death message when the user dies
        
        if p.is_dead:
            draw_text(self.screen, f"RESPAWNING: {p.death_timer:.1f}s", (18, y_offset), self.font, (255, 50, 50))
            y_offset += 30
            draw_text(self.screen, f"Lost {self.coins_lost_on_death} coins", (18, y_offset), self.font_small, (255, 200, 100))

        
        # minimap
        
        mm = t.minimap
        mm_pos = (self.screen.get_width() - mm.get_width() - 14, 14)
        self.screen.blit(mm, mm_pos)

        mw, mh = mm.get_size()
        for car in self.cars:
            x = int(mm_pos[0] + (car.pos.x / t.world_w) * mw)
            y = int(mm_pos[1] + (car.pos.y / t.world_h) * mh)
            col = (70, 210, 255) if car.is_player else (240, 100, 90)
            pygame.draw.circle(self.screen, col, (x, y), 4)
            pygame.draw.circle(self.screen, (0, 0, 0), (x, y), 4, 1)

        for obstacle in t.dynamic_obstacles:
            if obstacle.active:
                x = int(mm_pos[0] + (obstacle.pos.x / t.world_w) * mw)
                y = int(mm_pos[1] + (obstacle.pos.y / t.world_h) * mh)
                col = (255, 100, 100) if obstacle.obstacle_type == "barrel" else \
                    (255, 150, 50) if obstacle.obstacle_type == "cone" else \
                    (200, 150, 50) if obstacle.obstacle_type == "crate" else \
                    (150, 150, 150) if obstacle.obstacle_type == "rock" else \
                    (255, 50, 50)
                pygame.draw.circle(self.screen, col, (x, y), 2)

        
        # Final lap indicator, shows a continuous pulse
        
        if p.laps == self.total_laps - 1 and not p.finished:  # On final lap
            pulse = (math.sin(self.race_time * 3) + 1) * 0.5  # Pulsing effect
            alpha = int(100 + 100 * pulse)
            
            # Draw "FINAL LAP" text
            final_lap_font = pygame.font.Font(None, 48)
            final_text = "FINAL LAP!"
            text_surf = final_lap_font.render(final_text, True, (255, 215, 0, alpha))
            text_rect = text_surf.get_rect(center=(self.screen.get_width()//2, 80))
            
            # Background for better visibility
            bg_width = text_surf.get_width() + 40
            bg_height = text_surf.get_height() + 20
            bg_surf = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 150))
            bg_rect = bg_surf.get_rect(center=(self.screen.get_width()//2, 80))
            self.screen.blit(bg_surf, bg_rect)
            
            self.screen.blit(text_surf, text_rect)

    def render_pause_overlay(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA) # create a semi-transparent overlay
        overlay.fill((0, 0, 0, 140)) # makes the screen darker when the game is paused
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "PAUSED", (self.screen.get_width() // 2 - 90, 260), self.font_big) # draws the PAUSED title in the middle
        draw_text(self.screen, "Esc / Enter = resume", (self.screen.get_width() // 2 - 140, 330), self.font) # Esc/enter = resume
        draw_text(self.screen, "Backspace = quit to main menu (LOSE ALL COINS!)", # backspace button = quit
                 (self.screen.get_width() // 2 - 280, 364), self.font, (255, 50, 50))
        if self.track:
            active_obstacles = sum(1 for o in self.track.dynamic_obstacles if o.active) # provides real-time information about the dynamic obstacles within the track 
            draw_text(self.screen, f"Active obstacles: {active_obstacles}/{len(self.track.dynamic_obstacles)}",
                     (self.screen.get_width() // 2 - 180, 400), self.font_small, (255, 200, 100))

    def render_race_over_overlay(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        cx = self.screen.get_width() // 2
        y = 210

        draw_text(self.screen, "RACE COMPLETED", (cx - 190, y), self.font_big)
        y += 70

        # Time taken + Best time
        best = getattr(self, "best_time_for_track", None)
        time_line = f"Time Taken: {self.race_time:.1f}s"
        best_line = f"Best Time:  {best:.1f}s" if best is not None else "Best Time:  --"

        draw_text(self.screen, time_line, (cx - 160, y), self.font)
        y += 34
        draw_text(self.screen, best_line, (cx - 160, y), self.font)
        y += 46

        # Unlock message / requirement
        if getattr(self, "can_go_next_track", False):
            if getattr(self, "unlocked_this_race", False):
                draw_text(self.screen, " New track unlocked!", (cx - 160, y), self.font)
            else:
                draw_text(self.screen, "Next track is available.", (cx - 160, y), self.font)
        else:
            if self.track:
                draw_text(
                    self.screen,
                    f"Finish under {self.track.unlock_time_limit:.1f}s to unlock the next track.",
                    (cx - 260, y),
                    self.font_small,
                    (255, 220, 60),
                )
        y += 60

        # Menu options
        draw_text(self.screen, "Use Enter to select. ESC = Main Menu", (cx - 240, y), self.font_small)
        y += 40

        opts = getattr(self, "race_over_options", ["Play Again", "Exit"])
        idx = getattr(self, "race_over_index", 0)

        for i, opt in enumerate(opts):
            col = (255, 220, 60) if i == idx else (230, 230, 230)
            draw_text(self.screen, f"{' ' if i == idx else '  '}{opt}", (cx - 90, y + i * 30), self.font, col)




def main():
    from login_system import run_login # it runs the login system 
    username = run_login() # checks whether the username is within the sql database
    if not username: # if the username is not in the database, then the login system will prevent the player to proceed
        return
    Game(username).run() # creates a new game for the player and saves the data into the database

if __name__ == "__main__":
    main()
