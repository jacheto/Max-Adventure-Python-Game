import pygame
from pygame.locals import *
import math
import random
import datetime
from operator import itemgetter
from math import atan2
import xlrd
import os.path
import numpy as np
from scipy.spatial import Voronoi
from libs import funcs
from libs.PAdLib import shadow as shadow
from libs.PAdLib import occluder as occluder

class pygame_engine():

    def __init__(self, dimensions):
        pygame.init()
        pygame.joystick.init()
        self.clock = pygame.time.Clock()
        flags = DOUBLEBUF
        # flags = FULLSCREEN | DOUBLEBUF
        self.gameDisplay = pygame.display.set_mode(dimensions, flags, 16)

    def update_display(self):
        pygame.display.update()

    def quit(self):
        pygame.quit()

    def get_mouse(self):
        p = [pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1]]
        r = [pygame.mouse.get_rel()[0], pygame.mouse.get_rel()[1]]
        return [p, r]

    def set_mouse(self, bool):
        pygame.mouse.set_visible(bool)

    def load_img(self, img):
        return pygame.image.load(img).convert_alpha()

    def fill(self, color):
        self.gameDisplay.fill(color)

    def write(self, msg, pos=(30, 120), size=15, color=(255, 255, 255), font='arial'):
        myfont = pygame.font.SysFont(font, size)
        label = myfont.render(msg, 1, color)
        self.gameDisplay.blit(label, pos)

    def draw_line(self, color, p1, p2, t=1):
        pygame.draw.line(self.gameDisplay, color, p1, p2, t)

    def draw_circle(self, color, pos, radius, t=1):
        pos = [int(pos[0]), int(pos[1])]
        pygame.draw.circle(self.gameDisplay, color, pos, radius, t)

    def draw_polygon(self, color, points, t=1):
        pygame.draw.polygon(self.gameDisplay, color, points, t)

    def set_fps(self, fps):
        self.clock.tick(fps)

    def show(self, img, pos):
        self.gameDisplay.blit(img, pos)

    def play_sound(self, sound, loop = 0, max_time = 0, fade_ms = 0):
        pygame.mixer.Sound('game_files/sounds/'+ sound + '.wav').play(loop, max_time, fade_ms)

    def draw_image(self, obj):
        img = obj.image[0]
        pos = obj.pos
        rad_ang = obj.ang
        ang = rad_ang * 180 / math.pi
        img = pygame.transform.rotozoom(img, ang, 1)
        re = img.get_rect()
        position = [pos[0] - re[2] / 2, pos[1] - re[3] / 2]
        self.show(img, position)

    def draw_special_image(self, img, pos, rad_ang, max_dist):
        ang = rad_ang * 180 / math.pi
        img = pygame.transform.rotozoom(img, ang, 0.5)
        re = img.get_rect()
        offset = (re[2] - max_dist)
        position = [pos[0] - re[2] / 2, pos[1] - re[3] / 2]
        self.gameDisplay.blit(img, pos, (0, 0, 200, max_dist+10))

class Object():

    def __init__(self, id, name):
        self.name = name
        self.ID = id
        self.static = False
        self.selected = False
        self.is_player = False
        self.collider = True
        self.figure = False
        self.hits = []
        self.is_voronoi = False
        self.follows = None
        self.allow_gravity = True
        self.allow_rotation = True
        self.visible = False
        self.deletable = False
        self.wait_obj = False
        self.deadly = False
        self.image = False
        self.master = False
        self.thickness = 1
        self.max_life_time = math.inf
        self.life_time = 0
        self.ammo = 0
        self.exclude_list = []
        self.rev_count = 0
        self.pos = [0, 0]
        self.vel = [0, 0]
        self.force = [0, 0]
        self.ang = 0
        self.ang_vel = 0
        self.torque = 0

        self.e = 0
        self.eu = 0.3
        self.du = 0.1

        self.color = funcs.random_color() if not self.static else funcs.colors('light grey')

    def exclude(self, obj):
        for ID in self.exclude_list:
            if ID == obj.ID:
                return False
        return True

    def apply_impulse(self, j, r):
        if not self.static:
            self.vel[0] += j[0] * self.inv_mass
            self.vel[1] += j[1] * self.inv_mass
            if self.allow_rotation:
                self.ang_vel += funcs.cross(j, r) * self.inv_inertia

class Circle(Object):

    def __init__(self, id, name, r):
        Object.__init__(self, id, name)
        self.type = 'circle'
        self.radius = r
        self.set_mass()

    def set_mass(self, density=1):
        self.density = density

        self.mass = self.density * math.pi * self.radius ** 2
        self.inertia = self.mass * self.radius ** 2
        self.set_box()
        if self.static:
            self.inv_mass = 0
            self.inv_inertia = 0
        else:
            self.inv_mass = 1 / self.mass
            self.inv_inertia = 1 / self.inertia

    def update_all(self):
        self.set_box()

    def set_box(self):
        minX = self.pos[0] - self.radius
        maxX = self.pos[0] + self.radius
        minY = self.pos[1] - self.radius
        maxY = self.pos[1] + self.radius
        self.box = [minX, maxX, minY, maxY]

    def set_light_segments(self, pos):
        pc = self.pos
        dx = pc[0] - pos[0]
        dy = pc[1] - pos[1]
        d = funcs.pol(dx, dy)
        R = self.radius
        if d > R:
            a = math.asin(R / d)
            b = math.atan2(dy, dx)
            t = b - a
            p1 = [pc[0] + R * math.sin(t), pc[1] + R * -math.cos(t)]
            t = b + a
            p2 = [pc[0] + R * -math.sin(t), pc[1] + R * math.cos(t)]
            self.light_segments = [p1, p2, pc]
        else:
            self.light_segments = []

    def inside(self, p):
        return funcs.dpp(p, self.pos) < self.radius

class Poly(Object):

    def __init__(self, id, name, v_list):
        Object.__init__(self, id, name)
        self.type = 'poly'
        self.vertex_pos = v_list
        self.radius = max(funcs.pol(v[0], v[1]) for v in v_list)
        self.vertex_count = len(v_list)
        self.set_mass(1)
        self.set_vertex()
        self.set_box()

    def set_vertex(self):
        cos = math.cos(-self.ang)
        sin = math.sin(-self.ang)

        new_v = [0, 0]
        vertex = []

        for v in self.vertex_pos:
            new_v = [v[0] * cos - v[1] * sin + self.pos[0], v[1] * cos + v[0] * sin + self.pos[1]]
            vertex.append(new_v)

        self.light_segments = self.vertex = vertex
        self.set_box()
        if self.is_player:
            self.set_touch_box()
        self.set_mass(1)
        self.set_normals()
        self.set_tangents()

    def update_all(self):
        self.set_vertex()

    def set_box(self):
        minX = min(v[0] for v in self.vertex)
        maxX = max(v[0] for v in self.vertex)
        minY = min(v[1] for v in self.vertex)
        maxY = max(v[1] for v in self.vertex)
        self.box = [minX, maxX, minY, maxY]

    def set_mass(self, d):

        area = 0
        I = 0
        c = [0, 0]

        for i in range(self.vertex_count):
            j = (i + 1) % self.vertex_count
            p1 = self.vertex_pos[i]
            p2 = self.vertex_pos[j]
            triArea = funcs.cross(p1, p2) * 0.5
            area += triArea
            c_aux = triArea / 3
            c[0] += c_aux * (p1[0] + p2[0])
            c[1] += c_aux * (p1[1] + p2[1])

            x2 = p1[0] ** 2 + p2[0] * p1[0] + p2[0] ** 2
            y2 = p1[1] ** 2 + p2[1] * p1[1] + p2[1] ** 2
            I += triArea * (x2 + y2) / 6

        c = [c[0] / area, c[1] / area]
        self.centroid = c

        self.mass = area * d
        self.inertia = I * d

        if self.static:
            self.inv_mass = 0
            self.inv_inertia = 0
        else:
            self.inv_mass = 1 / self.mass
            self.inv_inertia = 1 / self.inertia

    def set_normals(self):
        v = self.vertex
        n = []
        for i in range(self.vertex_count):
            j = (i + 1) % self.vertex_count
            n.append(funcs.norm([v[j][1] - v[i][1], v[i][0] - v[j][0]]))
        self.normals = n
        if self.is_player:
            self.foot = n[-1]

    def set_tangents(self):
        v = self.vertex
        t = []
        for i in range(self.vertex_count):
            j = (i + 1) % self.vertex_count
            t.append(funcs.norm([v[j][0] - v[i][0], v[j][1] - v[i][1]]))
        self.tangents = t

    def inside(self, p):

        v = self.vertex
        n = self.normals
        for i in range(self.vertex_count):
            if funcs.dot(p, n[i]) > funcs.dot(v[i], n[i]):
                return False
        return True

class Player(Poly):

    def __init__(self, id, name, v_list):
        Poly.__init__(self, id, name, v_list)
        self.life = 1
        self.lifes_left = 1
        self.is_player = True
        self.walker = False
        self.jumper = False
        self.has_weapon = False
        self.using_weapon = False
        self.in_air = False
        self.stop = False
        self.in_ground = False
        self.ground = self
        self.ground_momentum = 0
        self.sliding = False
        self.weapon_rate = 10
        self.walking = False
        self.running = False
        self.jumped = False
        self.jump_boost = False
        self.facing_left = True
        self.instant_push = False
        self.shooting = False
        self.punching = False
        self.grabbing = False
        self.grabbed = [False, False]
        self.foot_accumulator = 1
        self.t0 = 0

        self.head = False
        self.larm = False
        self.rarm = False
        self.foot1 = False
        self.foot2 = False

        self.lhand_sprite = [None, None]
        self.rhand_sprite = [None, None]
        self.body_sprite = [None, None]
        self.head_sprite = [None, None]
        self.foot_sprite = [None, None]

        self.e = 0
        self.eu = 1
        self.du = 1

    def set_touch_box(self, side=5):
        b = self.box
        if side == 5:
            b[0] -= 20
            b[1] += 20
        elif not side:
            b[0] -= -10
            b[1] += 20
        else:
            b[0] -= 20
            b[1] += -10
        b[2] += 10
        b[3] -= 20
        self.touch_box = b
        return b

    def change_direction(self, only_sprite = False):

        l = self.larm.image
        r = self.rarm.image
        self.larm.image = r
        self.rarm.image = l
        if self.image:
            self.image[0] = pygame.transform.flip(self.image[0], True, False)
            self.head.image[0] = pygame.transform.flip(self.head.image[0], True, False)
        if not only_sprite:
            self.head.follows[1][0] *= -1
        self.facing_left = not self.facing_left

    def update(self, time, p0, s, g):

        def walk_controls():

            if self.in_ground and not (self.grabbed[0] and self.grabbed[0].ID == self.ground.ID):
                self.ground_momentum = self.ground.vel[0]
            else:
                self.ground_momentum *= 0.98

            T = 0.5
            v = 360 if self.running else 180

            if self.facing_left == self.vel[0] > 0:
                self.change_direction()

            if self.walking > 0:
                tr = funcs.step_response(1, T, time, 'walkingR ' + str(self.ID))
                tl = funcs.step_response(0, T, time, 'walkingL ' + str(self.ID))

            elif self.walking < 0:
                tr = funcs.step_response(0, T, time, 'walkingR ' + str(self.ID))
                tl = funcs.step_response(1, T, time, 'walkingL ' + str(self.ID))

            else:
                tr = funcs.step_response(0, T, time, 'walkingR ' + str(self.ID))
                tl = funcs.step_response(0, T, time, 'walkingL ' + str(self.ID))

            self.ang = -0.03 * math.pi / 180 * v * (tr - tl)

            self.vel[0] = self.ground_momentum + v * (tr - tl)

        def jump_controls():
            jump = 500

            condition = True if g else self.in_ground

            if self.jumped and funcs.delay(condition, 0.5, time, 'c'):
                self.vel[1] = - jump
                if s:
                    r = random.randrange(0, 2)
                    s[r].play()
            if funcs.delay(self.jumped, 0.25, time, 'c') and not self.in_ground and self.jump_boost:
                self.vel[1] -= jump / 3
                self.jump_boost = False
            if self.in_ground:
                self.jump_boost = True

        def random_walk():

            if random.randrange(0, 150) % 49 == 32:
                a = 1 if p0 >= self.pos[0] else -1
                rv = random.randrange(-30, 30) / 15
                rv += a
                self.walking = 0 if rv % 3 == 0 else funcs.signal(rv)
                v = rv * self.walking

            g = self.ground.vel[0] if self.in_ground else 0
            T = 0.5

            if self.walking > 0:
                tr = funcs.step_response(1, T, time, 'walkingR ' + str(self.ID))
                tl = funcs.step_response(0, T, time, 'walkingL ' + str(self.ID))

            elif self.walking < 0:
                tr = funcs.step_response(0, T, time, 'walkingR ' + str(self.ID))
                tl = funcs.step_response(1, T, time, 'walkingL ' + str(self.ID))

            else:
                tr = funcs.step_response(0, T, time, 'walkingR ' + str(self.ID))
                tl = funcs.step_response(0, T, time, 'walkingL ' + str(self.ID))
            if 'v' in locals():
                self.ang = -0.5 * math.pi / 180 * v * (tr - tl)
                self.vel[0] = g + v * (tr - tl)

        def random_jump():
            if int(time * 60 + self.ID * 190) % 200 == 0:
                self.jumped = True
            jump = 600
            if self.jumped and funcs.delay(self.in_ground, 0.2, time, 'c' + str(self.ID)):
                self.vel[1] -= jump
                self.jumped = False

        if self.name == 'main':
            walk_controls()
            jump_controls()
        elif not self.stop:
            if self.walker:
                random_walk()
            if self.jumper:
                random_jump()

    def apply_impulse(self, j, r):
        if not self.static:
            self.vel[0] += j[0] * self.inv_mass
            self.vel[1] += j[1] * self.inv_mass
            if self.stop:
                self.ang_vel += funcs.cross(j, r) * self.inv_inertia

class Button():

    def __init__(self, name, x, y, double_state = True, is_menu = 0, go_menu = 0):
        self.name = name
        self.is_switch = False
        self.pos = [x, y]
        self.increment = [0, 0]
        self.double_state = double_state
        self.is_selected = False
        self.is_menu = is_menu
        self.go_menu = go_menu
        if double_state:
            self.image1 = pygame.image.load('game_files/images/comum/menu/' + name + '1.png').convert_alpha()
            self.image2 = pygame.image.load('game_files/images/comum/menu/' + name + '2.png').convert_alpha()
            self.image = self.image1
        else:
            self.image = pygame.image.load('game_files/images/comum/menu/' + name + '.png').convert_alpha()

    def inside(self):
        size = self.image.get_size()
        [mx, my] = pygame.mouse.get_pos()
        x = self.pos[0]
        y = self.pos[1]
        size = [x, x + size[0], y, y + size[1]]
        return mx > size[0] and mx < size[1] and my > size[2] and my < size[3]

class Switch(Button):

    def __init__(self, boolean, x, y, name = 'switch'):
        self.name = name
        self.is_switch = True
        self.double_state = True
        self.pos = [x, y]
        self.increment = [0, 0]
        self.boolean = boolean
        self.on1 = pygame.image.load('game_files/images/comum/menu/on1.png').convert_alpha()
        self.on2 = pygame.image.load('game_files/images/comum/menu/on2.png').convert_alpha()
        self.off1 = pygame.image.load('game_files/images/comum/menu/off1.png').convert_alpha()
        self.off2 = pygame.image.load('game_files/images/comum/menu/off2.png').convert_alpha()
        self.update()

    def turn(self):
        self.boolean = not self.boolean
        self.update()

    def update(self):
        self.image1 = self.on1 if self.boolean else self.off1
        self.image2 = self.on2 if self.boolean else self.off2
        self.image = self.image1

class Simulation():

    def __init__(self):

        self.screen_w = 1280
        self.screen_h = 720
        pygame.joystick.init()
        self.xbox = pygame.joystick.get_count() != 0
        self.xbox = False
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=256)
        self.graphics = pygame_engine([self.screen_w, self.screen_h])

        #sounds

        self.step_sound = pygame.mixer.Sound('game_files/sounds/step.wav')
        self.jump_sound = []
        for i in range(2):
            self.jump_sound.append(pygame.mixer.Sound('game_files/sounds/jump' + str(i + 1) + '.wav'))
        self.punch_sound = [pygame.mixer.Sound('game_files/sounds/punch missed 1.wav'), pygame.mixer.Sound('game_files/sounds/punch missed 1.wav')]
        self.punch_hit_sound = [pygame.mixer.Sound('game_files/sounds/punch1.wav'), pygame.mixer.Sound('game_files/sounds/punch2.wav'), pygame.mixer.Sound('game_files/sounds/punch3.wav')]
        self.shoot_sound = [pygame.mixer.Sound('game_files/sounds/shoot1.wav'), pygame.mixer.Sound('game_files/sounds/shoot2.wav')]
        self.shoot_wall_hit_sound = []
        for i in range(3):
            self.shoot_wall_hit_sound.append(pygame.mixer.Sound('game_files/sounds/tarmac_0' + str(i+1) + '.wav'))
        self.shoot_glass_hit_sound = []
        for i in range(3):
            self.shoot_glass_hit_sound.append(pygame.mixer.Sound('game_files/sounds/glass_0' + str(i+1) + '.wav'))
        self.shoot_player_hit_sound = pygame.mixer.Sound('game_files/sounds/shoot_player_hit.wav')
        self.reload_sound = pygame.mixer.Sound('game_files/sounds/reload.wav')
        self.noammo_sound = pygame.mixer.Sound('game_files/sounds/noammo.wav')
        self.switch_weapon_sound = pygame.mixer.Sound('game_files/sounds/switch weapon.wav')
        self.wood_crack_sound = pygame.mixer.Sound('game_files/sounds/wood crack.wav')

        #sprites

        self.menu_background = self.graphics.load_img('game_files/images/comum/menu/gamemenu.png')
        self.pause_background = self.graphics.load_img('game_files/images/comum/menu/pausemenu.png')
        self.no_xbox_message = self.graphics.load_img('game_files/images/comum/menu/no_xbox.png')
        self.resettoapply_message = self.graphics.load_img('game_files/images/comum/menu/resettoapply.png')
        self.gamewin_image = self.graphics.load_img('game_files/images/comum/menu/youwin.png')
        self.gamelost_image = self.graphics.load_img('game_files/images/comum/menu/youlost.png')
        self.gameover_image = self.graphics.load_img('game_files/images/comum/menu/yougameover.png')
        self.hit_image = self.graphics.load_img('game_files/images/comum/hit.png')

        self.fps = funcs.fps
        self.dt = 1 / self.fps
        self.grav_ang = -90
        self.grav_scale = 700
        self.frames = 0
        self.gravity = [self.grav_scale * math.cos(self.grav_ang * math.pi / 180), -self.grav_scale * math.sin(self.grav_ang * math.pi / 180)]
        self.GameExit = False
        self.MenuExit = False
        self.GameWin = False
        self.GameLost = False
        self.button_selected_index = 0
        self.music_setting = True
        self.soundeffects_setting = True
        self.godmode_setting = False
        self.game_reseted = False
        self.current_scene = 1
        self.saved_scene = 1
        self.lifes_left = 5
        self.current_music = 0
        self.last_music = 1

        pygame.display.set_caption('Max´s Adventure')
        pygame.display.set_icon(self.graphics.load_img('game_files/images/comum/player/head.png'))

        if os.path.exists('game_files/save_file/save.txt'):
            info = self.load_game()
            if info:
                self.saved_scene = info[0]
                self.lifes_left = info[1]
        self.current_scene = self.saved_scene
        self.save_game()
        self.main_loop()

    def main_loop(self):
        screen = 0
        b = 0
        pygame.mixer.music.load('game_files/sounds/musicmenu.mp3')
        pygame.mixer.music.play(1000)
        if not self.music_setting:
            pygame.mixer.music.pause()
        while not self.MenuExit:
            if b == None:
                b = 0
            if screen == 0:
                b = self.main_menu()
            if screen == 1:
                b = self.continue_menu()
            if screen == 2:
                b = self.selectlevel_menu()
            if screen == 3:
                b = self.settings_menu()
            if screen == 4:
                b = self.credits_menu()
            if screen == 5:
                b = self.quit_menu()
            screen = b
        self.graphics.quit()
        quit()

    def main_menu(self):
        self.graphics.set_mouse(True)
        main_dict = {'back': 0, 'continue': 1, 'selectlevel': 2, 'settings': 3, 'credits': 4, 'quit': 5}
        main_buttons = []
        main_buttons.append(Button('continue', 50, 200))
        main_buttons.append(Button('selectlevel', 50, 300))
        main_buttons.append(Button('settings', 50, 400))
        main_buttons.append(Button('credits', 50, 500))
        main_buttons.append(Button('quit', 50, 600))
        b = self.show_buttons(main_buttons)

        return main_dict[b]

    def continue_menu(self):
        self.game_loop()
        return 0

    def selectlevel_menu(self):

        selectlevel_dict = {'back':0, 'level11':1, 'level12':2, 'level13':3, 'level21':4, 'level22':5, 'level23':6}

        selectlevel_buttons = []
        selectlevel_buttons.append(Button('level11', 235, 208))
        if self.saved_scene >= 2:
            selectlevel_buttons.append(Button('level12', 535, 208))
        if self.saved_scene >= 3:
            selectlevel_buttons.append(Button('level13', 835, 208))
        if self.saved_scene >= 4:
            selectlevel_buttons.append(Button('level21', 235, 408))
        # selectlevel_buttons.append(Button('level22', 535, 408))
        # selectlevel_buttons.append(Button('level23', 835, 408))
        selectlevel_buttons.append(Button('back', 50, 650))

        b = self.show_buttons(selectlevel_buttons)

        if b != 'back' and b != 'level22' and b != 'level23':
            self.game_loop(selectlevel_dict[b])
        elif b == 'back':
            return 0
        else:
            return 2

    def settings_menu(self, pause = False):
        settings_buttons = []
        settings_buttons.append(Button('music', 50, 200, False))
        settings_buttons.append(Button('soundeffects', 50, 300, False))
        settings_buttons.append(Button('xboxcontrol', 50, 400, False))
        settings_buttons.append(Button('godmode', 50, 500, False))
        settings_buttons.append(Button('back', 50, 650))
        if pause != False:
            settings_buttons.append(Button('quit_pause', 300, 650))
        else:
            settings_buttons.append(Button('resetsave', 900, 650))
        settings_buttons.append(Switch(self.music_setting, 500, 200, 'switch music'))
        settings_buttons.append(Switch(self.soundeffects_setting, 500, 300, 'switch soundeffects'))
        settings_buttons.append(Switch(self.xbox, 500, 400, 'switch xbox'))
        settings_buttons.append(Switch(self.godmode_setting, 500, 500, 'switch godmode'))
        b = 0
        while b != 'back' and b != 'quit_pause':
            c = self.show_buttons(settings_buttons, pause)
            b = c[0]
            self.music_setting = c[1][0]
            self.soundeffects_setting = c[1][1]
            self.xbox = c[1][2]
            self.godmode_setting = c[1][3]

        return 0 if b == 'back' else 1

    def credits_menu(self):
        credits_buttons = []
        credits_buttons.append(Button('creditstext', 75, 150, False))
        credits_buttons.append(Button('back', 50, 650))

        b = self.show_buttons(credits_buttons)

        return 0

    def quit_menu(self):
        self.MenuExit = True

    def add_buttons(self):
        ['continue',    50,     200,    1,     2]
        ['selectlevel', 50,     300,    1,     3]
        ['settings',    50,     400,    1,     4]
        ['credits',     50,     500,    1,     5]
        ['quit',        50,     600,    1,     6]
        ['level11',     235,    208,    3,     111]
        ['level12',     535,    208,    3,     112]
        ['level13',     835,    208,    3,     113]
        ['level21',     235,    408,    3,     121]
        ['level22',     535,    408,    3,     122]
        ['level23',     835,    408,    3,     123]
        ['music',       50,     200,    4,     ]

    def show_buttons(self, button_list, pause = False):

        button_press = False
        button_over = button_list[0]
        self.up_selection = [True, True]
        no_xbox_message = False
        while not button_press:

            if funcs.changed(self.music_setting, 'music change'):
                if self.music_setting:
                    pygame.mixer.music.unpause()
                else:
                    pygame.mixer.music.pause()

            self.frames += 0.001
            if funcs.changed(self.xbox, 'xbox change'):
                pygame.joystick.init()
                if pygame.joystick.get_count() == 0:
                    no_xbox_message = True
                    self.xbox = False
            button_press = False
            button_over = False

            if self.xbox:
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
                axis = []
                axes = joystick.get_numaxes()
                for i in range(axes):
                    a = joystick.get_axis(i)
                    axis.append(a)

                hat = []
                hats = joystick.get_numhats()
                for i in range(hats):
                    h = joystick.get_hat(i)
                    hat.append(h)

                if axis[1] >= 0.5 and self.up_selection[0]:
                    self.button_selected_index += 1
                    self.up_selection = [False, True]

                if axis[1] <= -0.5 and self.up_selection[1]:
                    self.button_selected_index -= 1
                    self.up_selection = [True, False]

                if axis[1] > -0.5 and axis[1] < 0.5:
                    self.up_selection = [True, True]

                self.button_selected_index = funcs.clamp(self.button_selected_index, 0, len(button_list) - 1, True)

                while not button_list[self.button_selected_index].double_state:
                    self.button_selected_index += 1
                    self.button_selected_index = funcs.clamp(self.button_selected_index, 0, len(button_list) - 1, True)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT or event.type == pygame.K_ESCAPE:
                        pygame.quit()
                        quit()
                    if event.type == pygame.JOYBUTTONDOWN:
                        button = []
                        buttons = joystick.get_numbuttons()
                        for i in range(buttons):
                            b = joystick.get_button(i)
                            button.append(b)

                        if button[0] == 1:
                            button_press = button_list[self.button_selected_index].name
                        if button[1] == 1 or button[7] == 1:
                            button_press = 'back'

                for b in button_list:
                    b.is_selected = False
                button_list[self.button_selected_index].is_selected = True

            else:
                for button in button_list:
                    if button.inside():
                        button.is_selected = True
                        button_over = button.name
                    else:
                        button.is_selected = False

                for event in pygame.event.get():
                    if event.type == pygame.QUIT or event.type == pygame.K_ESCAPE:
                        pygame.quit()
                        quit()

                    if event.type == pygame.MOUSEBUTTONDOWN:
                        button_press = button_over

                    if event.type == pygame.KEYDOWN:

                        if event.key == pygame.K_ESCAPE:
                            button_press = 'back'

            switch_list = []
            s = False
            for switch in button_list:
                if switch.is_switch:
                    if switch.is_selected and type(button_press) is str:
                        if button_press.startswith('switch'):
                            switch.turn()
                    switch_list.append(switch.boolean)
                    s = True

            for b in button_list:
                if b.double_state:
                    if b.is_selected:
                        b.image = b.image2 if b.is_selected else b.image1
                        b.increment = [3, 3] if b.is_selected else [0, 0]
                    else:
                        b.image = b.image1
                        b.increment = [0, 0]

            if not pause:
                image = self.menu_background
            else:
                image = pause
                self.graphics.show(self.pause_background, [0, 0])

            self.graphics.show(image, [0, 0])
            if pause:
                self.graphics.show(self.pause_background, [0, 0])
            for button in button_list:
                pos = [button.pos[0] + button.increment[0], button.pos[1] + button.increment[1]]
                self.graphics.show(button.image, pos)
            if no_xbox_message and not funcs.wait(0.5, self.frames, 'no xbox message'):
                self.graphics.show(self.no_xbox_message, [700, 400])



            if button_press == 'resetsave':
                self.save_game(True)
                self.game_reseted = True
            if self.game_reseted and not funcs.wait(0.8, self.frames, 'reset save message'):
                self.graphics.show(self.resettoapply_message, [800, 500])

            self.graphics.update_display()

        return [button_press, switch_list] if s else button_press

    def game_loop(self, scene = False):
        pygame.mixer.music.stop()

        self.GameExit = False
        self.current_scene = self.current_scene if not scene else scene

        while not self.GameExit:
            self.GameOver = self.lifes_left == 0
            self.save_game()
            y = self.reset_all()
            self.add_player(100, y)
            self.last_music = self.current_music
            self.generate_scene()
            if self.current_music != self.last_music and self.music_setting:
                pygame.mixer.music.stop()
                pygame.mixer.music.load('game_files/sounds/' + self.current_music + '.mp3')
                pygame.mixer.music.play(1000)
            self.correct_positions(0)
            while not self.GameOver:
                self.update_parameters()
                self.update_keys()

                self.update_wobj()

                self.update_damage()
                self.update_deaths()

                self.update_camera()
                self.update_collisions()
                self.update_joints()
                self.update_dynamics()

                self.update_players()
                self.update_scene()

                self.update_bullets()
                self.update_guns()
                self.update_followers()
                self.update_lights()

                self.render()

                if self.Pause:
                    self.pause()
            self.save_game()
            self.level_end_screen()

        pygame.mixer.music.stop()
        pygame.mixer.music.load('game_files/sounds/musicmenu.mp3')
        pygame.mixer.music.play(1000)
        if not self.music_setting:
            pygame.mixer.music.pause()


    # funções iniciais

    def save_game(self, reset = False):
        file = open('game_files/save_file/save.txt', 'w')
        if not reset:
            file.write(str(self.current_scene) + '\n')
            file.write(str(self.lifes_left) + '\n')
        else:
            file.write('1\n')
            file.write('5\n')
            info = self.load_game()
            self.current_scene = 1
            self.lifes_left = 5
        file.close()

    def load_game(self):
        file = open('game_files/save_file/save.txt', 'r')
        info = file.readlines()
        file.close()
        return [int(info[0]), int(info[1])] if info != [] else False

    def level_end_screen(self):
        pygame.image.save(self.graphics.gameDisplay, 'game_files/images/temp/screenshot.png')
        img = self.graphics.load_img('game_files/images/temp/screenshot.png')
        img1 = False

        if self.GameLost:
            img1 = self.gamelost_image
            self.lifes_left -= 1
            self.GameLost = False

        elif self.GameWin:
            img1 = self.gamewin_image
            self.GameWin = False
            if self.current_scene <= 4:
                self.current_scene += 1
                self.saved_scene += 1

            self.save_game()

        if self.lifes_left == -1:
            img1 = self.gameover_image
            self.GameExit = True
            self.lifes_left = 5
            self.current_scene = 1

        if img1:
            self.graphics.show(img, [0, 0])
            self.graphics.show(img1, [0, 0])
            self.graphics.update_display()
            not_pressed = True
            while not_pressed:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.graphics.quit()
                        quit()
                    if (event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYHATMOTION) and self.xbox:
                        not_pressed = False

                    if (event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN) and not self.xbox:
                        not_pressed = False

    def reset_all(self):
        self.keys = [None]
        self.graphics.set_mouse(False)
        self.fps_now = self.fps
        self.GameOver = False
        self.Pause = False
        self.player = False
        self.camera = False
        self.ID = 0
        self.end_door = [0,0,0,0]
        self.obj_list = []
        self.wobj_list = []
        self.bullet_list = []
        self.rev_joint_list = []
        self.dist_joint_list = []
        self.light_list = []
        self.stick_list = []
        self.arm_list = []
        self.lever_list = []
        self.guns_list = []
        self.hits = []
        self.bullet_hit = False
        y_dict = {1:500, 2:50, 3: 300, 4:350}
        self.voronoi = []
        self.bridge_index = 0
        self.mouse_pos = self.graphics.get_mouse()[0]
        self.t = 0
        self.current_time = datetime.datetime.now().time().microsecond
        self.p0 = [0, 0]
        self.sprites = []
        funcs.oneup_list = []
        funcs.act_list = []
        funcs.wait_list = []
        funcs.delay_list = []
        funcs.step_list = []
        funcs.registered = []
        return y_dict[self.current_scene]

    def generate_voronoi(self, name, number=False, r=False):

        def voronoi_generator(vor, radius=1):
            new_regions = []
            new_vertices = vor.vertices.tolist()
            center = vor.points.mean(axis=0)
            if radius is None:
                radius = vor.points.ptp().max()
            all_ridges = {}
            for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
                all_ridges.setdefault(p1, []).append((p2, v1, v2))
                all_ridges.setdefault(p2, []).append((p1, v1, v2))
            for p1, region in enumerate(vor.point_region):
                vertices = vor.regions[region]
                if all(v >= 0 for v in vertices):
                    new_regions.append(vertices)
                    continue
                ridges = all_ridges[p1]
                new_region = [v for v in vertices if v >= 0]
                for p2, v1, v2 in ridges:
                    if v2 < 0:
                        v1, v2 = v2, v1
                    if v1 >= 0:
                        continue
                    t = vor.points[p2] - vor.points[p1]
                    t /= np.linalg.norm(t)
                    n = np.array([-t[1], t[0]])
                    midpoint = vor.points[[p1, p2]].mean(axis=0)
                    direction = np.sign(np.dot(midpoint - center, n)) * n
                    far_point = vor.vertices[v2] + direction * radius
                    new_region.append(len(new_vertices))
                    new_vertices.append(far_point.tolist())
                vs = np.asarray([new_vertices[v] for v in new_region])
                c = vs.mean(axis=0)
                angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
                new_region = np.array(new_region)[np.argsort(angles)]
                new_regions.append(new_region.tolist())
            return new_regions, np.asarray(new_vertices)

        def intersect(v1, v2):
            p1 = v1[0]
            p2 = v1[1]
            pa = v2[0]
            pb = v2[1]
            r = [p2[0] - p1[0], p2[1] - p1[1]]
            s = [pb[0] - pa[0], pb[1] - pa[1]]
            g = [pa[0] - p1[0], pa[1] - p1[1]]
            t = funcs.cross(g, s) / funcs.cross(r, s) if funcs.cross(r, s) != 0 else 1
            if t > 0 and t < 1:
                return [p1[0] + t * r[0], p1[1] + t * r[1]]
            else:
                return False

        def fora(p, index=-1, margin=0):
            xmin = limits[0]
            ymin = limits[1]
            xmax = limits[2]
            ymax = limits[3]
            if index == 0:
                return p[0] < xmin - margin
            elif index == 1:
                return p[0] > xmax + margin
            elif index == 2:
                return p[1] < ymin - margin
            elif index == 3:
                return p[1] > ymax + margin
            elif index == -1:
                return (p[0] < xmin or p[0] > xmax or p[1] < ymin or p[1] > ymax)

        def inside(vertices, point):
            RIGHT = "RIGHT"
            LEFT = "LEFT"

            def get_side(a, b):
                x = x_product(a, b)
                if x < 0:
                    return LEFT
                elif x > 0:
                    return RIGHT
                else:
                    return None

            def v_sub(a, b):
                return (a[0] - b[0], a[1] - b[1])

            def x_product(a, b):
                return a[0] * b[1] - a[1] * b[0]

            previous_side = None
            n_vertices = len(vertices)
            for n in range(n_vertices):
                a, b = vertices[n], vertices[(n + 1) % n_vertices]
                affine_segment = v_sub(b, a)
                affine_point = v_sub(point, a)
                current_side = get_side(affine_segment, affine_point)
                if current_side is None:
                    return False  # outside or over an edge
                elif previous_side is None:  # first segment
                    previous_side = current_side
                elif previous_side != current_side:
                    return False
            return True

        def order(a):

            b = []
            for x in a:
                if x not in b:
                    b.append(x)
            a = b


            arctangents = []
            arctangentsandpoints = []
            arctangentsoriginalsandpoints = []
            arctangentoriginals = []
            centerx = 0
            centery = 0
            sortedlist = []
            firstpoint = []
            k = len(a)
            for i in a:
                x, y = i[0], i[1]
                centerx += float(x) / float(k)
                centery += float(y) / float(k)
            for i in a:
                x, y = i[0], i[1]
                arctangentsandpoints += [[i, atan2(y - centery, x - centerx)]]
                arctangents += [atan2(y - centery, x - centerx)]
                arctangentsoriginalsandpoints += [[i, atan2(y, x)]]
                arctangentoriginals += [atan2(y, x)]
            arctangents = sorted(arctangents)
            arctangentoriginals = sorted(arctangentoriginals)
            for i in arctangents:
                for c in arctangentsandpoints:
                    if i == c[1]:
                        sortedlist += [c[0]]
            for i in arctangentsoriginalsandpoints:
                if arctangentoriginals[0] == i[1]:
                    firstpoint = i[0]
            z = sortedlist.index(firstpoint)
            m = sortedlist[:z]
            sortedlist = sortedlist[z:]
            sortedlist.extend(m)
            return sortedlist

        rect = self.find_obj(name)
        rect.figure = False
        pos = rect.pos
        ID = rect.ID
        ver = []
        polygons = []
        edges_list = []
        right = []
        centers = []
        b = rect.box
        hmin = b[0]
        hmax = b[1]
        vmin = b[2]
        vmax = b[3]
        prop = (hmax - hmin) / (vmax - vmin)
        area = (hmax - hmin) * (vmax - vmin)
        if not number:
            number = area / 500

        if prop < 1:
            prop = 1 / prop
        if not r:
            r = random.randrange(1000, 5000)

        np.random.seed(r)

        points = np.random.rand(int(number * prop), 2)
        vor = Voronoi(points)
        regions, vertices = voronoi_generator(vor)

        limits = (hmin, vmin, hmax, vmax)
        margin = [[[hmin, vmin], [hmax, vmin]],
                  [[hmax, vmin], [hmax, vmax]],
                  [[hmax, vmax], [hmin, vmax]],
                  [[hmin, vmax], [hmin, vmin]]]
        edges = [[hmin, vmin],
                 [hmax, vmin],
                 [hmax, vmax],
                 [hmin, vmax]]

        for v in vertices:
            prop = max((hmax - hmin), (vmax - vmin))
            x = hmin + v[0] * prop
            y = vmin + v[1] * prop
            if False:
                x = funcs.clamp(x, hmin, hmax)
                y = funcs.clamp(y, vmin, vmax)
            ver.append([x, y])
        for r in regions:
            poly = []
            for p in r:
                poly.append(ver[p])
            polygons.append(poly)
        for e in edges:
            for poly in polygons:
                if inside(poly, e):
                    edges_list.append([poly, e])
        for poly in polygons:
            p = 0
            while p < len(poly):
                p1 = poly[p]
                p2 = poly[(p + 1) % len(poly)]
                t = [p1, p2]
                for m in margin:
                    intersection = intersect(t, m)
                    if intersection and not fora(intersection):
                        poly.insert(p + 1, intersection)
                        ph = [int(intersection[0]), int(intersection[1])]
                p += 1
        for poly in polygons:
            p = 0
            while p < len(poly):
                if fora(poly[p]):
                    del poly[p]
                else:
                    p += 1
        for edg in edges_list:
            edg[0].insert(0, edg[1])
        for poly in polygons:
            if len(poly) > 2:
                right.append(order(poly))
        for poly in right:
            x = 0
            y = 0
            for p in poly:
                x += p[0]
                y += p[1]
            x /= len(poly)
            y /= len(poly)
            centers.append([x, y])
        vlist = []
        for i in range(len(right)):
            c = centers[i]
            points = []
            for p in right[i]:
                pt = [p[0] - c[0], p[1] - c[1]]
                points.append(pt)
            self.add_poly(c[0], c[1], points, True, False, 'voronoi')
            self.obj_list[-1].figure = False
            self.obj_list[-1].visible = True
            self.obj_list[-1].wait_obj = True
            self.obj_list[-1].thickness = 0
            self.obj_list[-1].is_voronoi = ID
            self.obj_list[-1].color = funcs.colors('light blue')
            vlist.append(self.obj_list[-1])
        self.voronoi.append([ID, vlist])

    def generate_scene(self):

        def level_1():
            self.current_music = 'music123'
            self.find_obj('p20').ang = -3.5 * math.pi / 180
            self.light_list.append([[4430, 10], funcs.colors('white'), 80, 1000, 3, False])

        def level_2():
            self.current_music = 'music123'
            self.add_button([3940, 200], 'hor')
            self.add_button([4860, 540], 'ver')
            self.add_button([4860, 200], 'rot')
            self.add_button([7690, 500], 'wall')

        def level_3():
            self.current_music = 'music123'
            self.light_list.append([[8000, 150], funcs.colors('white'), 80, 1000, 4, False])

        def level_4():
            self.current_music = 'music45'
            bridge = self.graphics.load_img('game_files/images/level' + str(self.current_scene) + '/objetos/ponte.png')
            self.add_bridge([1760, 260], [2340, 260], 4, bridge, 0)
            pass

        def level_5():
            pass

        def level_6():
            pass

        workbook = xlrd.open_workbook("game_files/level_data/levels.xlsx")
        sheet = workbook.sheet_by_index(self.current_scene - 1)

        objlist = []
        distlist = []
        revlist = []
        scelist = []
        sprites_dict = {}

        for i in range(1, sheet.nrows):
            if sheet.cell_value(i, 0) != '':
                obj = []
                for j in range(10):
                    obj.append(sheet.cell_value(i, j))
                objlist.append(obj)

            if sheet.cell_value(i, 11) != '':
                dist = []
                for j in range(8):
                    dist.append(sheet.cell_value(i, 11 + j))
                distlist.append(dist)

            if sheet.cell_value(i, 19) != '':
                rev = []
                for j in range(5):
                    rev.append(sheet.cell_value(i, 19 + j))
                revlist.append(rev)

            if sheet.cell_value(i, 25) != '':
                sce = []
                for j in range(2):
                    sce.append(sheet.cell_value(i, 25 + j))
                scelist.append(sce)
        for obj in objlist:
            type = obj[0]
            if type == 'rect':
                name = obj[1]
                x = obj[2]
                y = obj[3]
                w = obj[4]
                h = obj[5]
                if name.startswith('p'):
                    static = True
                    collider = True
                    figure = False
                    wait_obj = True
                elif name.startswith('s'):
                    static = False
                    collider = True
                    figure = False
                    wait_obj = True
                elif name.startswith('m'):
                    static = False
                    collider = True
                    figure = False
                    wait_obj = False
                elif name.startswith('i'):
                    static = True
                    collider = False
                    figure = True
                    wait_obj = False
                elif name.startswith('a'):
                    static = True
                    collider = True
                    figure = False
                    wait_obj = False
                self.add_rect(x, y, w, h, 0, static, collider, name)
                self.obj_list[-1].figure = figure
                self.obj_list[-1].wait_obj = wait_obj

            elif type == 'ramp':
                name = obj[1]
                x = obj[2]
                y = obj[3]
                w = obj[4]
                ha = obj[5]
                hb = obj[6]
                side = obj[7] if len(obj) > 6 else 0

                self.add_ramp(x, y, w, ha, hb, side, name)
                self.obj_list[-1].wait_obj = True

            elif type == 'circle':
                name = obj[1]
                x = obj[2]
                y = obj[3]
                r = obj[4]
                if name.startswith('p'):
                    static = True
                    collider = True
                    figure = False
                elif name.startswith('s'):
                    static = False
                    collider = True
                    figure = False
                elif name.startswith('m'):
                    static = False
                    collider = True
                    figure = False
                elif name.startswith('i'):
                    static = True
                    collider = False
                    figure = True
                elif name.startswith('a'):
                    static = True
                    collider = False
                    figure = True
                self.add_circle(x, y, r, 0, static, collider, name)
                self.obj_list[-1].figure = figure

            elif type == 'triangule':
                name = obj[1]
                x = obj[2]
                y = obj[3]
                w = obj[4]
                h = obj[5]
                side = obj[6]
                if name.startswith('p'):
                    static = True
                    collider = True
                    figure = False
                elif name.startswith('sp'):
                    static = False
                    collider = True
                    figure = False
                elif name.startswith('mp'):
                    static = True
                    collider = False
                    figure = False
                elif name.startswith('ip'):
                    static = True
                    collider = True
                    figure = True
                self.add_triangle_ramp(x, y, w, h, side, name)

            elif type == 'voronoi':
                name = obj[1]
                x = obj[2]
                y = obj[3]
                w = obj[4]
                h = obj[5]
                n = obj[6]
                if n == 0:
                    n = False
                seed = int(obj[7])
                self.add_rect(x, y, w, h, 0, True, True, name)
                self.generate_voronoi(name, n, seed)

            elif type == 'enemy':
                name = obj[1]
                x = obj[2]
                y = obj[3]
                weapon = obj[4]
                jump = obj[5]
                walk = obj[6]
                self.add_guy(x, y, weapon, jump, walk, name)

            if obj[8] != '':
                name = obj[1]
                img = obj[8]
                z = obj[9]
                image = self.graphics.load_img('game_files/images/level' + str(self.current_scene) + '/objetos/' + img + '.png')
                sprites_dict.update({name:[image, z]})

        for dist in distlist:
            name1 = dist[0]
            pos1_x = dist[1]
            pos1_y = dist[2]
            name2 = dist[3]
            pos2_x = dist[4]
            pos2_y = dist[5]
            d =  dist[6]
            sprite = dist[7]
            self.dist_joint(name1, [pos1_x, pos1_y], name2, [pos2_x, pos2_y], d, sprite)

        for rev in revlist:
            name1 = rev[0]
            pos_x = rev[1]
            pos_y = rev[2]
            name2 = rev[3]
            k = rev[4]
            self.rev_joint(name1, [pos_x, pos_y], name2, k)

        for sce in scelist:
            name = sce[0]
            z = sce[1]
            self.sprites.append([self.graphics.load_img('game_files/images/level' + str(self.current_scene) + '/cenario/'+ name +'.png'), z])

        for obj in self.obj_list:
            if obj.name in sprites_dict:
                obj.image = sprites_dict[obj.name]

        if self.current_scene == 1:
            level_1()
        if self.current_scene == 2:
            level_2()
        if self.current_scene == 3:
            level_3()
        if self.current_scene == 4:
            level_4()
        if self.current_scene == 5:
            level_5()
        if self.current_scene == 6:
            level_6()

    def correct_positions(self, start_pos=0):
        for obj in self.obj_list + self.wobj_list:
            if not obj.name == 'main':
                obj.pos[0] -= start_pos
        self.p0[0] -= start_pos

    # adicionar items

    def rev_joint(self, nameA, rpA, nameB, K=0):
        objA = self.find_obj(nameA)
        objB = self.find_obj(nameB)
        if objB and objA:
            rpB = [objA.pos[0] + rpA[0] - objB.pos[0], objA.pos[1] + rpA[1] - objB.pos[1]]
            objA.exclude_list.append(objB.ID)
            self.rev_joint_list.append([nameA, rpA, nameB, rpB, K])

    def dist_joint(self, nameA, rpA, nameB, rpB, max_dist, sprite = ''):
        self.dist_joint_list.append([nameA, rpA, nameB, rpB, max_dist, sprite])

    def add_lever(self, pos, name):
        self.add_rect(pos[0], pos[1] - 5, 50, 10, 0, True, False)
        self.add_circle(pos[0] - 25, pos[1] - 50, 10, 0, False, True, name)
        self.obj_list[-1].allow_gravity = False
        self.obj_list[-1].exclude_list.append(self.player.ID)

    def add_button(self, pos, name, dist=70):
        self.add_rect(pos[0], pos[1] - 10, dist + 20, 20, 0, True, True)
        image1 = self.graphics.load_img('game_files/images/comum/button_1.png')
        image2 = self.graphics.load_img('game_files/images/comum/button_2.png')
        self.obj_list[-1].image = [image2, 0.2]
        self.add_rect(pos[0], pos[1] - 20, dist, 26, 0, True, True, name)
        self.obj_list[-1].image = [image1, 0.1]
        self.obj_list[-1].e = 0
        self.obj_list[-1].color = funcs.colors('red')
        self.obj_list[-1].allow_gravity = False

    def add_bridge(self, p1, p2, q, img, dl=10):
        d = funcs.dpp(p1, p2)
        n = funcs.norm([p2[0] - p1[0], p2[1] - p1[1]])
        ang = math.atan2(n[1], n[0])
        w = (d - (q + 1) * dl) / q
        h = 20
        self.bridge_index += 1
        bi = str(self.bridge_index)
        begin_name = 'bridge'+ bi +' begin'
        end_name = 'bridge'+ bi +' end'

        self.add_circle(p1[0], p1[1], 5, ang, True, True, begin_name)

        for i in range(q):
            d1 = [0, 0] if i == 0 else [w / 2, 0]
            d2 = [-w / 2, 0]
            p = dl + w / 2 + i * (dl + w)
            pi = [p1[0] + n[0] * p, p1[1] + n[1] * p]
            name1 = 'bridge ' + str(i) + bi if i != 0 else begin_name
            name2 = 'bridge ' + str(i + 1) + bi
            self.add_rect(pi[0], pi[1], w, h, -ang, False, True, name2, 1)
            self.obj_list[-1].image = [img, 0, 1]
            self.dist_joint(name1, d1, name2, d2, dl)

        self.add_circle(p2[0], p2[1], 5, ang, True, True, end_name)
        self.dist_joint('bridge ' + str(q) + bi, d1, end_name, [0, 0], dl)

    def add_guy(self, x, y, weapon = -1, jump = -1, walk = -1, name = False):
        w2 = 44 / 2
        h2 = 64 / 2
        p1 = [-w2, h2]
        p2 = [-w2 * 0.6, -h2]
        p3 = [w2 * 0.6, -h2]
        p4 = [w2, h2]

        v_list = [p1, p2, p3, p4]
        wait_obj = False
        if not name:
            name = 'enemy' + str(self.ID)
        player = Player(self.ID, name, v_list)
        player.static = False
        player.collider = True
        player.visible = True
        player.pos = [x, y]
        player.thickness = 0
        player.color = funcs.colors('light blue')
        player.wait_obj = wait_obj
        self.obj_list.append(player)
        self.ID += 1
        player.set_vertex()
        if weapon == -1:
            player.using_weapon = random.random() > 0.5
        else:
            player.using_weapon = weapon

        if player.using_weapon:
            player.ammo = 30
            player.has_weapon = True
            player.using_weapon = True
            player.weapon_rate = weapon

        if jump == -1:
            player.jumper = random.random() > 0.5
        elif jump:
            player.jumper = True
        elif not jump:
            player.jumper = False

        if walk == -1:
            player.walker = random.random() > 0.5
        elif walk:
            player.walker = True
        elif not walk:
            player.walker = False

        head = Circle(self.ID, 'head', 30)
        head.pos = [0, 0]
        head.exclude_list.append(player.ID)
        head.color = funcs.colors('light red')
        head.static = True
        head.collider = True
        head.visible = True
        head.thickness = 0
        head.wait_obj = wait_obj
        self.obj_list.append(head)
        self.ID += 1

        larm = Circle(self.ID, 'l_arm', 10)
        larm.set_mass(10)
        larm.color = funcs.colors('light green')
        larm.exclude_list.append(player.ID)
        larm.wait_obj = wait_obj
        self.arm_list.append(self.ID)
        self.obj_list.append(larm)
        self.ID += 1

        rarm = Circle(self.ID, 'r_arm', 10)
        rarm.set_mass(10)
        rarm.color = funcs.colors('light green')
        rarm.exclude_list.append(player.ID)
        rarm.wait_obj = wait_obj
        self.arm_list.append(self.ID)
        self.obj_list.append(rarm)
        self.ID += 1

        wf = 10
        hf = 4
        p1 = [-wf, hf]
        p2 = [-wf, -hf]
        p3 = [wf, -hf]
        p4 = [wf, hf]
        v_list = [p1, p2, p3, p4]

        foot1 = Poly(self.ID, 'foot1', v_list)
        foot1.color = funcs.colors('blue')
        foot1.wait_obj = wait_obj
        self.obj_list.append(foot1)
        self.ID += 1

        foot2 = Poly(self.ID, 'foot2', v_list)
        foot2.color = funcs.colors('blue')
        foot2.wait_obj = wait_obj
        self.obj_list.append(foot2)
        self.ID += 1

        for i in range(4):
            self.obj_list[-(i + 1)].static = True
            self.obj_list[-(i + 1)].collider = False
            self.obj_list[-(i + 1)].figure = True
            self.obj_list[-(i + 1)].visible = True
            self.obj_list[-(i + 1)].pos = [0, 0]
            self.obj_list[-(i + 1)].thickness = 0

        self.add_follower('head', name, [-w2 * 0.2, -h2 * 1.7])
        self.add_follower('l_arm', name, [-w2, 0])
        self.add_follower('r_arm', name, [w2, 0])
        self.add_follower('foot1', name, [0, h2 - 4])
        self.add_follower('foot2', name, [0, h2 - 4])

        player.head = head
        player.larm = larm
        player.rarm = rarm
        player.foot1 = foot1
        player.foot2 = foot2

        n = random.randrange(1, 4)

        sprites_dict = {
            name: [self.graphics.load_img('game_files/images/comum/inimigos/body'+ str(n) + '.png'), 1],
            'head': [self.graphics.load_img('game_files/images/comum/inimigos/head'+ str(n) + '.png'), 1],
            'l_arm': [self.graphics.load_img('game_files/images/comum/inimigos/back_hand'+ str(n) + '.png'), -0.5],
            'r_arm': [self.graphics.load_img('game_files/images/comum/inimigos/front_hand'+ str(n) + '.png'), 1],
            'foot1': [self.graphics.load_img('game_files/images/comum/inimigos/foot'+ str(n) + '.png'), 1],
            'foot2': [self.graphics.load_img('game_files/images/comum/inimigos/foot'+ str(n) + '.png'), 1]
        }

        player.lhand_sprite[0] = [self.graphics.load_img('game_files/images/comum/inimigos/back_hand' + str(n) + '.png'), -0.5]
        player.lhand_sprite[1] = [self.graphics.load_img('game_files/images/comum/inimigos/back_hand' + str(n) + '_gun.png'), -0.5]
        player.rhand_sprite[0] = [self.graphics.load_img('game_files/images/comum/inimigos/front_hand' + str(n) + '.png'), 1]
        player.rhand_sprite[1] = [self.graphics.load_img('game_files/images/comum/inimigos/front_hand' + str(n) + '_gun.png'), 1]

        for i in range(6):
            obj = self.obj_list[-(i + 1)]
            obj.visible = False
            obj.image = sprites_dict[obj.name]

    def add_player(self, x, y):
        w2 = 44 / 2
        h2 = 64 / 2
        p1 = [-w2, h2]
        p2 = [-w2 * 0.6, -h2]
        p3 = [w2 * 0.6, -h2]
        p4 = [w2, h2]

        v_list = [p1, p2, p3, p4]
        name = 'main'

        player = Player(self.ID, name, v_list)
        player.static = False
        player.collider = True
        player.pos = [x, y]
        self.obj_list.append(player)
        self.ID += 1
        player.set_vertex()
        player.thickness = 0
        player.visible = True
        player.color = funcs.colors('orange')
        self.player = player

        head = Circle(self.ID, 'main_head', 25)
        head.pos = [0, 0]
        head.exclude_list.append(player.ID)
        head.color = funcs.colors('light red')
        head.static = True
        head.collider = True
        self.obj_list.append(head)
        self.ID += 1

        larm = Circle(self.ID, 'l_arm', 10)
        larm.pos = [0, 0]
        larm.set_mass(10)
        larm.exclude_list.append(player.ID)
        larm.color = funcs.colors('light green')
        self.arm_list.append(self.ID)
        self.obj_list.append(larm)
        self.ID += 1

        rarm = Circle(self.ID, 'r_arm', 10)
        rarm.set_mass(10)
        rarm.exclude_list.append(player.ID)
        rarm.color = funcs.colors('light green')
        self.arm_list.append(self.ID)
        self.obj_list.append(rarm)
        self.ID += 1

        wf = 10
        hf = 4
        p1 = [-wf, hf]
        p2 = [-wf, -hf]
        p3 = [wf, -hf]
        p4 = [wf, hf]
        v_list = [p1, p2, p3, p4]

        foot1 = Poly(self.ID, 'foot1', v_list)
        foot1.color = funcs.colors('blue')
        self.obj_list.append(foot1)
        self.ID += 1

        foot2 = Poly(self.ID, 'foot2', v_list)
        foot2.color = funcs.colors('blue')
        self.obj_list.append(foot2)
        self.ID += 1

        for i in range(4):
            self.obj_list[-(i + 1)].static = True
            self.obj_list[-(i + 1)].collider = False
            self.obj_list[-(i + 1)].figure = True
            self.obj_list[-(i + 1)].visible = True
            self.obj_list[-(i + 1)].pos = [0, 0]
            self.obj_list[-(i + 1)].thickness = 0

        self.add_follower('main_head', name, [-w2 * 0.2, -h2 * 1.8])
        self.add_follower('l_arm', name, [-w2, 0])
        self.add_follower('r_arm', name, [w2, 0])
        self.add_follower('foot1', name, [0, h2 - 4])
        self.add_follower('foot2', name, [0, h2 - 4])

        player.head = head
        player.larm = larm
        player.rarm = rarm
        player.foot1 = foot1
        player.foot2 = foot2

        player.lhand_sprite[0] = [self.graphics.load_img('game_files/images/comum/player/back_hand.png'), -0.5]
        player.lhand_sprite[1] = [self.graphics.load_img('game_files/images/comum/player/back_hand_gun.png'), -0.5]
        player.rhand_sprite[0] = [self.graphics.load_img('game_files/images/comum/player/front_hand.png'), 1]
        player.rhand_sprite[1] = [self.graphics.load_img('game_files/images/comum/player/front_hand_gun.png'), 1]
        player.body_sprite[0] = [self.graphics.load_img('game_files/images/comum/player/body.png'), 1]
        player.body_sprite[1] = [self.graphics.load_img('game_files/images/comum/player/body_god.png'), 1]
        player.head_sprite[0] = [self.graphics.load_img('game_files/images/comum/player/head.png'), 1]
        player.head_sprite[1] = [self.graphics.load_img('game_files/images/comum/player/head_god.png'), 1]
        player.foot_sprite[0] = [self.graphics.load_img('game_files/images/comum/player/foot.png'), 1]
        player.foot_sprite[1] = [self.graphics.load_img('game_files/images/comum/player/foot_god.png'), 1]

        for i in range(6):
            obj = self.obj_list[-(i + 1)]
            obj.visible = False

    def add_follower(self, nameA, nameB, p=False):
        for obj in self.obj_list:
            if nameA == obj.name:
                a = obj
            if nameB == obj.name:
                b = obj
        if p:
            rel_pos = p
        else:
            rel_pos = [b.pos[0] - a.pos[0], b.pos[1] - a.pos[1]]
        a.follows = [nameB, rel_pos]

    def add_circle(self, x, y, r, ang=0, static=False, collider=True, name='', d=1, list=1):
        if list == 1:
            list = self.obj_list
        if list == 2:
            list = self.wobj_list
        if list == 3:
            list = self.bullet_list
        new_obj = Circle(self.ID, name, r)
        new_obj.pos = [x, y]
        new_obj.ang = ang
        new_obj.static = static
        new_obj.collider = collider
        new_obj.set_mass(d)
        new_obj.color = funcs.random_color() if not static else funcs.colors('light grey')
        self.obj_list.append(new_obj)
        self.ID += 1
        return new_obj.ID

    def add_gun(self, pos, ammo = 30):
        v_list = [[-13, 23], [-14, 10], [4, -20], [14, -22], [14, 18]]
        self.add_poly(pos[0], pos[1], v_list, False, True, 'gun')
        gun = self.obj_list[-1]
        gun.image = [self.graphics.load_img('game_files/images/comum/gun.png'), 1]
        gun.ammo = ammo
        gun.vel[1] = 0
        gun.ang_vel = 0
        for obj in self.obj_list:
            if obj.is_player:
                gun.exclude_list.append(obj.ID)
        self.guns_list.append(gun)

    def add_poly(self, x, y, v_list, static=False, collider=True, name='', d=1):

        new_obj = Poly(self.ID, name, v_list)
        new_obj.static = static
        new_obj.collider = collider
        new_obj.pos = [x, y]
        new_obj.ang = 0
        new_obj.color = funcs.random_color() if not static else funcs.colors('light grey')
        self.obj_list.append(new_obj)
        self.ID += 1
        new_obj.set_vertex()

        return new_obj.ID

    def add_rect(self, x, y, w, h, ang=0, static=False, collider=True, name='', d=1):
        w2 = w / 2
        h2 = h / 2
        p1 = [-w2, h2]
        p2 = [-w2, -h2]
        p3 = [w2, -h2]
        p4 = [w2, h2]
        v_list = [p1, p2, p3, p4]

        new_obj = Poly(self.ID, name, v_list)
        new_obj.static = static
        new_obj.collider = collider
        new_obj.pos = [x, y]
        new_obj.ang = ang
        new_obj.color = funcs.random_color() if not static else funcs.colors('light grey')
        self.obj_list.append(new_obj)
        self.ID += 1
        new_obj.set_vertex()

        return new_obj.ID

    def add_ramp(self, x, y, w, ha, hb, side=0, name=''):
        # side: local da rampa 0:cima 1:baixo
        h = max(ha, hb)
        w2 = w / 2
        h2 = h / 2
        if side == 0:
            p1 = [-w2, h2]
            p2 = [-w2, h2 - ha]
            p3 = [w2, h2 - hb]
            p4 = [w2, h2]
        elif side == 1:
            p1 = [-w2, -h2 + ha]
            p2 = [-w2, -h2]
            p3 = [w2, -h2]
            p4 = [w2, -h2 + hb]
        v_list = [p1, p2, p3, p4]

        static = True
        collider = True

        new_obj = Poly(self.ID, name, v_list)
        new_obj.static = static
        new_obj.collider = collider
        new_obj.pos = [x, y]
        new_obj.ang = 0
        new_obj.color = funcs.random_color() if not static else funcs.colors('light grey')
        self.obj_list.append(new_obj)
        self.ID += 1
        new_obj.set_vertex()

        return new_obj.ID

    def add_triangle_ramp(self, x, y, w, h, side=0, name=''):
        # side: local da ponta 0:direita 1:esquerda 2:cima 3:baixo
        w2 = w / 2
        h2 = h / 2
        if side == 0:
            p1 = [-w2, h2]
            p2 = [-w2, -h2]
            p3 = [w2, 0]
        elif side == 1:
            p1 = [-w2, 0]
            p2 = [w2, -h2]
            p3 = [w2, h2]
        elif side == 2:
            p1 = [-w2, h2]
            p2 = [0, -h2]
            p3 = [w2, h2]
        elif side == 3:
            p1 = [0, h2]
            p2 = [-w2, -h2]
            p3 = [w2, -h2]

        v_list = [p1, p2, p3]

        static = True
        collider = True

        new_obj = Poly(self.ID, name, v_list)
        new_obj.static = static
        new_obj.collider = collider
        new_obj.pos = [x, y]
        new_obj.ang = 0
        new_obj.color = funcs.random_color() if not static else funcs.colors('light grey')
        self.obj_list.append(new_obj)
        self.ID += 1
        new_obj.set_vertex()

        return new_obj.ID

    def add_triangule(self, x, y, l, ang=0, static=False, collider=True, name='', d=1):

        h = l / math.sqrt(3)
        p1 = [-0.5 * l, 0.5 * h]
        p2 = [0, -h]
        p3 = [0.5 * l, 0.5 * h]

        v_list = [p1, p2, p3]

        new_obj = Poly(self.ID, name, v_list)
        new_obj.static = static
        new_obj.collider = collider
        new_obj.pos = [x, y]
        new_obj.ang = ang
        new_obj.color = funcs.random_color() if not static else funcs.colors('light grey')
        self.obj_list.append(new_obj)
        self.ID += 1
        new_obj.set_vertex()

    # atualizar items

    def update_parameters(self):

        self.draw_line = []
        self.draw_circle = []
        self.draw_polygon = []
        self.draw_lights = []
        self.special_sprites = []
        self.hits_sprites = []
        self.player_axis_vel = 0

        for obj in self.obj_list:
            obj.hits = []
            obj.life_time += self.dt
            if obj.type == 'poly':
                obj.set_vertex()
            if obj.inside(self.mouse_pos):
                obj.selected = True
            else:
                obj.selected = False
        for wobj in self.wobj_list:
            wobj.life_time += self.dt
        self.t += self.dt

        if funcs.changed(self.music_setting, 'music set'):
            if self.music_setting:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()

        if self.godmode_setting:
            self.player.life = 1

        ct2 = datetime.datetime.now().time().microsecond
        n = 1 / (ct2 - self.current_time) * 1000000
        self.fps_now = funcs.clamp(n, 30, 60)
        self.dt = 1 / self.fps_now
        self.frames += 0.001
        self.current_time = datetime.datetime.now().time().microsecond

    def update_wobj(self):
        limit = 1
        for wobj in self.wobj_list:
            wobj.update_all()
            if wobj.box[0] < self.screen_w * limit and wobj.box[1] > self.screen_w * (1 - limit):
                self.obj_list.append(wobj)
                self.destroy_obj(wobj.ID, True)

        for obj in self.obj_list:
            obj.update_all()
            if obj.wait_obj and (obj.box[0] > self.screen_w * limit or obj.box[1] < self.screen_w * (1 - limit)):
                self.wobj_list.append(obj)
                self.destroy_obj(obj.ID, False)

    def update_scene(self):

        def level_1():
            self.end_door = [self.p0[0] + 6720, self.p0[0] + 6780, self.p0[1] + 560, self.p0[1] + 660]
            pass

        def level_2():

            self.end_door = [self.p0[0] + 7880, self.p0[0] + 7940, self.p0[1] + 240, self.p0[1] + 340]

            def circulate(obj, time, center, max_ang, follow_ang=True):
                first_ang = funcs.register('circulate' + str(obj.ID), 0, obj.ang)[0]
                if funcs.signal(first_ang - max_ang) == funcs.signal(obj.ang - max_ang):
                    ang_vel = max_ang * self.dt / time

                    x1 = obj.pos[0] - center[0]
                    y1 = obj.pos[1] - center[1]

                    x2 = x1 * math.cos(ang_vel) - y1 * math.sin(ang_vel)
                    y2 = y1 * math.cos(ang_vel) + x1 * math.sin(ang_vel)

                    ang = math.atan2(y2, x2)
                    obj.pos[0] += x2 - x1
                    obj.pos[1] += y2 - y1
                    obj.vel[0] = x2 - x1
                    obj.vel[1] = y2 - y1
                    if follow_ang:
                        obj.ang -= ang_vel

            t1 = 0.1
            t = 5
            hor = self.get_button('hor', 5, t1)
            ver = self.get_button('ver', 3, t1)
            rot = self.get_button('rot', 7, t1)
            wall = self.get_button('wall', 0, 0)

            ap_obj = [False]
            for i in range(18):
                ap_obj.append(self.find_obj('ap' + str(i + 1)))

            ac_obj = [False]
            for i in range(2):
                ac_obj.append(self.find_obj('ac' + str(i + 1)))

            at_obj = self.find_obj('at1')

            ac_obj[1].ang_vel = -40 * math.pi / 180
            ac_obj[2].ang_vel = 40 * math.pi / 180

            e2 = self.find_obj('e2')
            e3 = self.find_obj('e3')
            e4 = self.find_obj('e4')
            e5 = self.find_obj('e5')
            e6 = self.find_obj('e6')
            e7 = self.find_obj('e7')
            e8 = self.find_obj('e8')
            e9 = self.find_obj('e9')
            e10 = self.find_obj('e10')

            e = not (not e2 and not e3 and not e4)

            self.translade(ap_obj[1].ID, e, 50, 470, 590, 1)

            self.translade(ap_obj[2].ID, hor, 300, 3560, 4320, 0)
            self.translade(ap_obj[3].ID, hor, 300, 3560, 4320, 0)
            self.translade(ap_obj[4].ID, hor, 120, 3840, 4040, 0)
            self.translade(ap_obj[5].ID, ver, -300, 340, 700, 1)
            self.translade(ap_obj[6].ID, ver, -300, 340, 700, 1)
            self.translade(ap_obj[9].ID, hor, -300, 5380, 5740, 0)

            if rot and ap_obj[7].ang <= - math.pi / 2:
                ap_obj[7].pos = [self.p0[0] + 4520, 220]
                ap_obj[7].ang = -math.pi / 2
                ap_obj[8].pos = [self.p0[0] + 5200, 220]
                ap_obj[8].ang = math.pi / 2

            elif not rot and ap_obj[7].ang >= 0:
                ap_obj[7].pos = [self.p0[0] + 4420, 120]
                ap_obj[7].ang = 0
                ap_obj[8].pos = [self.p0[0] + 5300, 120]
                ap_obj[8].ang = 0
            else:
                s = -1 if rot else 1
                circulate(ap_obj[7], -1, [self.p0[0] + 4420, self.p0[1] + 220], s * math.pi / 2, True)
                circulate(ap_obj[8], -1, [self.p0[0] + 5300, self.p0[1] + 220], -s * math.pi / 2, True)


            act1 = [False, False]
            act2 = [True, False]
            act3 = [False, False]
            act4 = [True, False]
            act =[act1, act2, act3, act4]

            if funcs.check_once(self.player.pos[0] > self.p0[0] + 6520, 'act1'):
                act[0][1] = True
                act[0][0] = not act[0][0]
            if funcs.check_once(self.player.pos[0] > self.p0[0] + 6800 and not e5, 'act2'):
                act[1][1] = True
                act[0][0] = not act[0][0]
                act[1][0] = not act[1][0]
            if funcs.check_once(self.player.pos[0] > self.p0[0] + 7080 and not (e6 or e7), 'act3'):
                act[2][1] = True
                act[0][0] = not act[0][0]
                act[1][0] = not act[1][0]
                act[2][0] = not act[2][0]
            if funcs.check_once(self.player.pos[0] > self.p0[0] + 7360 and not (e8 or e9 or e10), 'act4'):
                act[3][1] = True
                act[0][0] = not act[0][0]
                act[1][0] = not act[1][0]
                act[2][0] = not act[2][0]
                act[3][0] = not act[3][0]

            self.translade(ap_obj[10].ID, act[0][0], 200, -60, 240, 1)
            self.translade(ap_obj[11].ID, act[0][0], 200, 580, 880, 1)
            self.translade(ap_obj[12].ID, act[1][0], 200, -60, 240, 1)
            self.translade(ap_obj[13].ID, act[1][0], 200, 580, 880, 1)
            self.translade(ap_obj[14].ID, act[2][0], 200, -60, 240, 1)
            self.translade(ap_obj[15].ID, act[2][0], 200, 580, 880, 1)
            self.translade(ap_obj[16].ID, act[3][0], 200, -60, 240, 1)
            self.translade(ap_obj[17].ID, act[3][0], 200, 580, 880, 1)

            if self.player.pos[0] < self.p0[0] + 6760 and act[3][1]:
                self.translade(at_obj.ID, False, 200, 180, 340, 1)

            self.translade(ap_obj[18].ID, not wall, 800, 100, 240, 1)

        def level_3():

            ac_obj = [False]
            for i in range(3):
                ac_obj.append(self.find_obj('ac' + str(i + 1)))

            ap_obj = [False]
            for i in range(3):
                ap_obj.append(self.find_obj('ap' + str(i + 1)))

            ap_obj[1].vel[1] = 3000 * math.cos(self.t * math.pi) * self.dt
            ap_obj[1].ang_vel = 400 * math.pi / 180 * math.cos(2 * self.t) * self.dt

            ap_obj[2].vel[1] = 3000 * math.cos(self.t * math.pi + math.pi) * self.dt
            ap_obj[2].ang_vel = 300 * math.pi / 180 * math.cos(3 * self.t) * self.dt

            ap_obj[3].vel[1] = 3000 * math.cos(self.t * math.pi) * self.dt
            ap_obj[3].ang_vel = 200 * math.pi / 180 * math.cos(4 * self.t) * self.dt

            ac_obj[1].ang_vel = -60 *  self.dt
            ac_obj[2].ang_vel =  60 * self.dt
            ac_obj[3].ang_vel = -60 * self.dt

            if self.got_hit('main', 'mp1') and funcs.wait(0.3, self.t, 'platform fall 1'):
                self.del_dist_joint(['mp1', [-80, -5], 'ic1', [0, 0], 215, ''])
                if funcs.wait(0.8, self.t, 'platform fall 1.5'):
                    self.del_dist_joint(['mp1', [80, -5], 'ic1', [0, 0], 230, ''])

            if self.got_hit('main', 'mp2') and funcs.wait(0.3, self.t, 'platform fall 2'):
                self.del_dist_joint(['mp2', [-80, -5], 'ic2', [0, 0], 215, ''])
                if funcs.wait(0.7, self.t, 'platform fall 2.5'):
                    self.del_dist_joint(['mp2', [80, -5], 'ic2', [0, 0], 230, ''])

            if self.got_hit('main', 'mp3') and funcs.wait(0.2, self.t, 'platform fall 3'):
                self.del_dist_joint(['mp3', [80, -5], 'ic3', [0, 0], 230, ''])
                if funcs.wait(0.9, self.t, 'platform fall 3.5'):
                    self.del_dist_joint(['mp3', [-80, -5], 'ic3', [0, 0], 215, ''])


            if self.player.pos[0] > self.p0[0] + 8010:
                self.GameOver = True
                self.GameWin = True

        def level_4():

            ap_obj = [False]
            for i in range(3):
                ap_obj.append(self.find_obj('ap' + str(i + 1)))


            a1 = self.player.pos[0] > self.p0[0] + 2120
            if funcs.check_once(a1, 'act40'):
                if self.soundeffects_setting and funcs.one_up('act40'):
                    self.wood_crack_sound.play()
                b = self.find_obj('bridge1 end')
                if ap_obj[2].ang < 5 * math.pi / 180:
                    ap_obj[2].ang += 0.4 * math.pi / 180
                if ap_obj[2].pos[1] < self.p0[1] + 540:
                    ap_obj[2].pos[1] += 4
                    b.pos[1] += 5
                if ap_obj[2].pos[0] > self.p0[0] + 2370:
                    ap_obj[2].pos[0] += -2
                    b.pos[0] += -6

            a2 = self.player.pos[0] > self.p0[0] + 2580
            a3 = self.player.pos[1] > self.p0[1] + 370
            if funcs.check_once(a2 and a3, 'act41'):
                if self.soundeffects_setting and funcs.one_up('act41'):
                    self.wood_crack_sound.play()
                if funcs.wait(0.1, self.t, 'act41 time'):
                    if ap_obj[1].ang > -4 * math.pi / 180:
                        ap_obj[1].ang += -0.4 * math.pi / 180
                    if ap_obj[1].pos[1] < self.p0[1] + 610:
                        ap_obj[1].pos[1] += 4
                    if ap_obj[1].pos[0] > self.p0[0] + 2786:
                        ap_obj[1].pos[0] += -2

            ip_obj = [False]
            for i in range(10):
                ip_obj.append(self.find_obj('ip' + str(i + 1)))

            ic_obj = [False]
            for i in range(2):
                ic_obj.append(self.find_obj('ic' + str(i + 1)))

            ic_obj[1].ang_vel = -4000 * self.dt / 180
            ic_obj[2].ang_vel = -4000 * self.dt / 180

            for i in range(1, 5):
                if ip_obj[i].pos[1] > -50:
                    ip_obj[i].vel[1] = -4000 * self.dt
                else:
                    ip_obj[i].pos[1] = 770

            for i in range(5, 9):
                if ip_obj[i].pos[1] < 770:
                    ip_obj[i].vel[1] = 4000 * self.dt
                else:
                    ip_obj[i].pos[1] = -50

            ps = 60

            if ip_obj[9].pos[1] > 360 - ps:
                ip_obj[9].vel[1] = -4000 * self.dt
            else:
                ip_obj[9].pos[1] = 360

            if ip_obj[10].pos[1] < 360 + ps:
                ip_obj[10].vel[1] = 4000 * self.dt
            else:
                ip_obj[10].pos[1] = 360

            a4 = self.player.pos[0] > self.p0[0] + 5640
            a5 = self.player.pos[1] > self.p0[1] + 360

            if funcs.check_once(a4 and a5, 'act42'):
                if self.soundeffects_setting and funcs.one_up('act42'):
                    self.wood_crack_sound.play()
                if funcs.wait(0.1, self.t, 'act42 time'):
                    if ap_obj[3].ang < 2 * math.pi / 180:
                        ap_obj[3].ang += 0.4 * math.pi / 180
                    if ap_obj[3].pos[1] < self.p0[1] + 600:
                        ap_obj[3].pos[1] += 4
                    if ap_obj[3].pos[0] < self.p0[0] + 5950:
                        ap_obj[3].pos[0] += 2

            self.launch_ball(6276, 327, 800, 180, 70)
            self.launch_ball(6976, 679, 1200, 75, 60, 3)
            self.launch_ball(7605, 678, 1100, 110, 60, 3, 550)

        if self.current_scene == 1:
            level_1()
        elif self.current_scene == 2:
            level_2()
        elif self.current_scene == 3:
            level_3()
        elif self.current_scene == 4:
            level_4()

    def launch_ball(self, x, y, v, ang, freq, life = 1, offset = 0, damage = 2):
        name = 'cannon' + str(x + y)
        s = 1 if ang > 90 and ang < 270 else -1

        if funcs.one_up(name):
            self.add_circle(self.p0[0] + x, self.p0[1] + y, 20, (ang - s * 20) * math.pi / 180, True, False, name)
            cannon = self.obj_list[-1]
            cannon.visible = False
            cannon.image = [self.graphics.load_img('game_files/images/comum/cannon.png'), 1.1]
        else:
            cannon = self.find_obj(name)
            cannon.ang += s * 20 * math.pi / 180 / freq

        if funcs.interval(self.frames, freq, offset):
            self.add_circle(self.p0[0] + x, self.p0[1] + y, 20, 0, False, False, 'bullet_ball', 5)
            circle = self.obj_list[-1]
            dir = funcs.get_dir(ang)
            circle.vel[0] = v * dir[0]
            circle.vel[1] = v * dir[1]
            circle.deadly = damage
            circle.thickness = 0
            circle.max_life_time = life
            circle.image = [self.graphics.load_img('game_files/images/comum/redball.png'), 1]
            cannon.ang = (ang - s * 20) * math.pi / 180

    def update_joints(self):

        for i in range(len(self.rev_joint_list)):
            rev = self.rev_joint_list[ - i - 1]
            objA = self.find_obj(rev[0])
            rpA = rev[1]
            objB = self.find_obj(rev[2])
            rpB = rev[3]
            K = rev[4]

            if objA and objB:

                angA = -objA.ang
                angB = -objB.ang

                rA = [rpA[0] * math.cos(angA) - rpA[1] * math.sin(angA), rpA[1] * math.cos(angA) + rpA[0] * math.sin(angA)]
                rB = [rpB[0] * math.cos(angB) - rpB[1] * math.sin(angB), rpB[1] * math.cos(angB) + rpB[0] * math.sin(angB)]

                pA = [objA.pos[0] + rA[0], objA.pos[1] + rA[1]]
                pB = [objB.pos[0] + rB[0], objB.pos[1] + rB[1]]

                dist = funcs.dpp(pA, pB)
                dn = [pA[0] - pB[0], pA[1] - pB[1]]
                d = funcs.dpp(dn)
                n = funcs.norm(dn)
                s = 0.1
                total_sum = objA.inv_mass + objB.inv_mass + objA.inv_inertia * funcs.cross(rA, n) ** 2 + objB.inv_inertia * funcs.cross(rB, n) ** 2
                if total_sum != 0:

                    impulse = [n[0] * dist / (total_sum * s), n[1] * dist / (total_sum * s)]
                    neg_impulse = [- impulse[0], - impulse[1]]
                    if not objB.static:
                        objB.apply_impulse(impulse, rB)
                        objB.pos[0] = objA.pos[0] + rA[0] - rB[0]
                        objB.pos[1] = objA.pos[1] + rA[1] - rB[1]
                        objB.ang_vel -= objB.ang * K
                    if not objA.static:
                        objA.apply_impulse(neg_impulse, rA)
                        objA.pos[0] = objB.pos[0] + rB[0] - rA[0]
                        objA.pos[1] = objB.pos[1] + rB[1] - rA[1]
                        objA.ang_vel -= objA.ang * K

                    self.update_drag(objB, 0.99)
                    self.update_drag(objA, 0.99)

                    # self.draw_circle.append([funcs.colors('white'), [int(pA[0]), int(pA[1])], 3, 0])
                    # self.draw_circle.append([funcs.colors('red'), [int(pB[0]), int(pB[1])], 3, 0])

        for dist in self.dist_joint_list:
            objA = self.find_obj(dist[0])
            rpA = dist[1]
            objB = self.find_obj(dist[2])
            rpB = dist[3]
            max_dist = dist[4]
            sprite = dist[5]

            if objA and objB:

                angA = -objA.ang
                angB = -objB.ang

                rA = [rpA[0] * math.cos(angA) - rpA[1] * math.sin(angA), rpA[1] * math.cos(angA) + rpA[0] * math.sin(angA)]
                rB = [rpB[0] * math.cos(angB) - rpB[1] * math.sin(angB), rpB[1] * math.cos(angB) + rpB[0] * math.sin(angB)]

                pA = [objA.pos[0] + rA[0], objA.pos[1] + rA[1]]
                pB = [objB.pos[0] + rB[0], objB.pos[1] + rB[1]]

                dn = [pA[0] - pB[0], pA[1] - pB[1]]
                d = funcs.dpp(dn)
                n = funcs.norm(dn)
                s = 0.1
                difference = (d - max_dist)
                total_sum = objA.inv_mass + objB.inv_mass + objA.inv_inertia * funcs.cross(rA, n) ** 2 + objB.inv_inertia * funcs.cross(rB, n) ** 2
                impulse = [n[0] * difference / (total_sum * s), n[1] * difference / (total_sum * s)]
                neg_impulse = [- impulse[0], - impulse[1]]

                if difference > 0:
                    objB.apply_impulse(impulse, rB)
                    objA.apply_impulse(neg_impulse, rA)

                self.update_drag(objB, 0.95)
                self.update_drag(objA, 0.95)

                if sprite == '':
                    self.draw_line.append([funcs.colors('white'), pA, pB, 1])
                else:
                    img = self.graphics.load_img('game_files/images/comum/cordas/' + sprite + '.png')
                    pos = [(pA[0] + pB[0])/2, (pA[1] + pB[1])/2]
                    ang = -math.atan2(pB[1] - pA[1],pB[0] - pA[0]) - math.pi/2
                    self.special_sprites.append([img, pB, ang, max_dist])

    def update_dynamics(self):

        for obj in self.obj_list:
            if obj.allow_gravity and not obj.static:
                obj.vel[0] += (obj.force[0] * obj.inv_mass + self.gravity[0]) * self.dt
                obj.vel[1] += (obj.force[1] * obj.inv_mass + self.gravity[1]) * self.dt
            else:
                obj.vel[0] += obj.force[0] * obj.inv_mass * self.dt
                obj.vel[1] += obj.force[1] * obj.inv_mass * self.dt
            obj.ang_vel += obj.torque * obj.inv_inertia

            self.update_drag(obj, 0.99)

            obj.pos[0] += obj.vel[0] * self.dt
            obj.pos[1] += obj.vel[1] * self.dt
            obj.ang += obj.ang_vel * self.dt

    def update_lights(self):

        for light in self.light_list:
            # [pos, color, alpha, range, time delay, objects]

            shad = shadow.Shadow()

            p = light[0]
            pos = [self.p0[0] + p[0], self.p0[1] + p[1]]
            radius = light[3]
            t = light[4]

            if self.player.pos[0] > (pos[0] - radius) and self.player.pos[0] < (pos[0] + radius):
                f = funcs.step_response(1, t, self.t, 'light ' + str(pos[0]))
            else:
                f = funcs.step_response(0, t, self.t, 'light ' + str(pos[0]))
            if f > 0:
                objects = light[5]
                if objects:
                    obj_list = []
                    for obj_name in objects:
                        obj = self.find_obj(obj_name, True)
                        obj_list.append(obj)
                else:
                    obj_list = self.obj_list
                occluders = []

                for obj in obj_list:
                    if self.in_scene(obj, radius) and not obj.figure and not obj.name.startswith("bullet") and not obj.name.startswith("blood"):
                        if obj.type == 'circle':
                            obj.set_light_segments(pos)
                        limit = 1
                        if obj.box[0] < self.screen_w * limit and obj.box[1] > self.screen_w * (1 - limit):
                            occluders.append(occluder.Occluder(obj.light_segments))

                alpha = light[2] * f
                color = light[1]
                c = [color[0], color[1], color[2], alpha]
                shad.set_occluders(occluders)
                shad.set_radius(1000)
                shad.set_light_position(pos)
                mask, draw_pos = shad.get_mask_and_position(c)
                self.draw_lights.append([mask, draw_pos])

    def update_drag(self, obj, slow):
        if abs(obj.vel[0]) > 0:
            obj.vel[0] *= slow
        if abs(obj.vel[1]) > 0:
            obj.vel[1] *= slow
        if abs(obj.ang_vel) > 0:
            obj.ang_vel *= slow

    def update_guns(self):
        i = 0
        deleted = False
        while i < len(self.guns_list) and not deleted:
            gun = self.guns_list[i]
            for obj in self.obj_list:
                if obj.is_player and not obj.stop and abs(obj.pos[1] - gun.pos[1]) < 90 and abs(obj.pos[0] - gun.pos[0]) < 50:

                    if not obj.has_weapon:
                        obj.using_weapon = True
                    obj.has_weapon = True
                    obj.ammo += gun.ammo
                    if len(self.guns_list) > 0:
                        self.destroy_obj(self.guns_list[i].ID)
                    del self.guns_list[i]
                    deleted = True

                    if obj.ID == self.player.ID and self.soundeffects_setting:
                        self.reload_sound.play()
                if deleted:
                    break
            i += 1

    def update_bullets(self):
        radius = 40
        player = False
        i = 0
        while i < len(self.bullet_list):
            bullet = self.bullet_list[i]
            delete = False
            for target in bullet.hits:
                if not target.figure:
                    if len(bullet.hits) > 0 and target.ID != bullet.master and target.ID != bullet.master + 1:
                        delete = True
                        if target.is_player:
                            target.life -= 0.1
                            player = True
                            if self.soundeffects_setting:
                                self.shoot_player_hit_sound.play()
                        elif target.name == 'head':
                            player = True
                            self.find_obj(target.ID - 1).life -= 0.2
                            if self.soundeffects_setting:
                                self.shoot_player_hit_sound.play()
                        elif target.is_voronoi:
                            if self.soundeffects_setting:
                                r = random.randrange(0, 3)
                                self.shoot_glass_hit_sound[r].play()
                            self.destroy_obj(target.is_voronoi)
                            for vor in self.voronoi:
                                if vor[0] == target.is_voronoi:
                                    for obj in vor[1]:
                                        dist = funcs.dpp(bullet.pos, obj.pos)
                                        obj.figure = False
                                        obj.collider = True
                                        if dist < radius:
                                            obj.static = False
                                            obj.allow_gravity = True
                                            obj.vel[0] = -(bullet.pos[0] - obj.pos[0])
                                            obj.vel[1] = -(bullet.pos[1] - obj.pos[1])
                                            obj.max_life_time = obj.life_time + 1
                        else:
                            if self.soundeffects_setting:
                                r = random.randrange(0,3)
                                self.shoot_wall_hit_sound[r].play()
            if delete:
                if player:
                    for j in range(7):
                        dx = random.randrange(-20, 20)
                        dy = random.randrange(-20, 20)
                        size = random.randrange(1, 5)
                        [x, y] = [bullet.pos[0] + dx, bullet.pos[1] + dy]
                        self.add_circle(x, y, size, 0, False, True, 'blood')
                        circle = self.obj_list[-1]
                        circle.max_life_time = abs(dx / 10)
                        circle.vel[0] = dx * 5
                        circle.vel[1] = dy * 5
                        circle.color = funcs.colors('red')
                        circle.visible = True
                        circle.thickness = 0
                        circle.exclude_list.append(target.ID)
                self.hits_sprites.append([self.hit_image, bullet.pos])
                self.destroy_obj(bullet.ID)
                del self.bullet_list[i]
            else:
                i += 1

    def update_players(self):

        def foots():

            foot1.ang = player.ang
            foot2.ang = player.ang
            step = 40 # maxima distância entre os pés
            if player.in_ground and not player.stop:
                p = funcs.step_response(0, 0.2, self.t, 'foot jump ' + str(player.ID))
                if abs(player.vel[0] - player.ground.vel[0]) > 0.5:
                    player.foot_accumulator += (player.vel[0] - player.ground.vel[0]) * self.dt if player.in_ground else player.vel[0] * self.dt
                    f = funcs.step_response(1, 0.2, self.t, 'foot ' + str(player.ID))
                else:
                    f = funcs.step_response(0, 0.2, self.t, 'foot ' + str(player.ID))
                foot1.pos[1] = 0
                foot2.pos[1] = - step / 5 * math.sin(player.foot_accumulator % step * math.pi / step) * f
                foot1.pos[0] = - player.foot_accumulator % step - step / 2
                foot2.pos[0] = + player.foot_accumulator % step - step / 2
                foot1.ang += 20 * math.pi / 180 * p * funcs.signal(-player.vel[0])
                foot2.ang += 20 * math.pi / 180 * p * funcs.signal(-player.vel[0])
            else:
                p = funcs.step_response(1, 0.8, self.t, 'foot jump ' + str(player.ID))
                f = funcs.step_response(0, 0.2, self.t, 'foot ' + str(player.ID))

            x1 = - player.foot_accumulator % step - step / 2
            y1 = 0
            x2 = + player.foot_accumulator % step - step / 2
            y2 = - step / 5 * math.sin(player.foot_accumulator % step * math.pi / step) * f
            ang = - player.ang
            foot1.pos[1] = y1 * math.cos(ang) + x1 * math.sin(ang)
            foot2.pos[1] = y2 * math.cos(ang) + x2 * math.sin(ang)
            foot1.pos[0] = x1 * math.cos(ang) - y1 * math.sin(ang)
            foot2.pos[0] = x2 * math.cos(ang) - y2 * math.sin(ang)
            foot1.ang += 20 * math.pi / 180 * p * funcs.signal(-player.vel[0])
            foot2.ang += 20 * math.pi / 180 * p * funcs.signal(-player.vel[0])
            if is_main and player.walking and player.in_ground and self.soundeffects_setting:
                f = 10 if not player.running else 6
                if funcs.interval(self.frames, f):
                    self.step_sound.play()

        def shoot():

            reload = 0.1 if is_main else 0.2
            dist = 20

            if left:
                pL = funcs.step_response(0, t2, self.t, 'shoot Lhand ' + str(player.ID))
                pR = funcs.step_response(1, t2, self.t, 'shoot Rhand ' + str(player.ID))

                rarm.pos = [dist * dir[0], (dist * dir[1] + 3 * math.cos(self.t * math.pi)) * pR]
                rarm.ang = ang * pR
                larm.pos = [0, dist * dir[1] * pL + 3 * math.sin(self.t * math.pi) * pR]
                larm.ang = ang * pL - math.pi / 2 * pR
            else:
                pL = funcs.step_response(1, t2, self.t, 'shoot Lhand ' + str(player.ID))
                pR = funcs.step_response(0, t2, self.t, 'shoot Rhand ' + str(player.ID))

                larm.pos = [dist * dir[0], (dist * dir[1] + 3 * math.sin(self.t * math.pi)) * pL]
                larm.ang = ang * pL
                rarm.pos = [0, dist * dir[1] * pR + 3 * math.cos(self.t * math.pi) * pL]
                rarm.ang = ang * pR + math.pi / 2 * pL

            if funcs.delay(player.shooting, reload, self.t, 'bullet' + str(player.ID), False) and not player.stop:
                dt = 20
                arm = rarm if left else larm
                r = random.randrange(1500, 3000)
                r = 1000
                if self.soundeffects_setting:
                    self.shoot_sound[0].play()
                speed = r if is_main else r / 2
                vel = [speed * dir[0], speed * dir[1]]
                l = funcs.dpp(vel) * self.dt * 0.8
                self.add_circle(arm.pos[0] + arm.follows[1][0] + player.pos[0] + dir[0] * 20, arm.pos[1] + arm.follows[1][1] + player.pos[1] + dir[1] * 20 - 10, 2, ang, False, True, 'bullet', 10)
                if not is_main or not self.godmode_setting:
                    player.ammo -= 1
                if player.ammo == 0 and not self.godmode_setting:
                    player.using_weapon = False
                    player.has_weapon = False
                    if self.soundeffects_setting:
                        self.noammo_sound.play()

                if left:
                    rarm.ang += 20 * math.pi / 180
                else:
                    larm.ang -= 20 * math.pi / 180
                bullet = self.obj_list[-1]
                bullet.vel = vel
                for i in range(5):
                    bullet.exclude_list.append(head.ID + i)
                bullet.allow_gravity = False
                bullet.allow_rotation = False
                bullet.eu = bullet.du = 0
                bullet.e = 1
                bullet.master = player.ID
                bullet.visible = True
                bullet.thickness = 0
                bullet.color = funcs.colors('yellow')
                bullet.max_life_time = 2
                self.bullet_list.append(bullet)

        def punch():

            def punched(dir):
                for obj in self.obj_list:
                    if abs(obj.pos[0] - player.pos[0]) < 150:
                        [xp, yp] = player.pos
                        [xo, yo] = obj.pos
                        rel = [xo - xp, yo - yp]
                        if funcs.dpp(player.pos, obj.pos) < 150 and funcs.dot(dir, rel) > 0 and not obj.static and not obj.figure:
                            f = 2 if is_main else 1
                            magnitude = random.randrange(4000, 5000) / self.dt
                            if self.soundeffects_setting:
                                r = random.randrange(0, 2)
                                self.punch_hit_sound[r].play()
                            obj.vel[0] += dir[0] * magnitude * obj.inv_mass * f
                            obj.vel[1] += dir[1] * magnitude * obj.inv_mass * f
                            if obj.is_player:
                                obj.life -= 0.3

            larm.ang = player.ang + ang
            rarm.ang = player.ang + ang
            if player.punching and not player.stop:
                p = 1 if left else 0
                s = 'l' if left else 'r'
                pL = funcs.step_response(p, t1, self.t, 'punch Lhand ' + str(player.ID))
                pR = funcs.step_response((1 - p), t1, self.t, 'punch Rhand ' + str(player.ID))
                larm.figure = False
                if funcs.wait(t1, self.t, s + ' punch' + str(player.ID)):
                    punched(dir)
                    player.punching = False
                    larm.figure = True
            else:
                pL = funcs.step_response(0, t2, self.t, 'punch Lhand ' + str(player.ID))
                pR = funcs.step_response(0, t2, self.t, 'punch Rhand ' + str(player.ID))
            if funcs.delay(player.punching, 0.5, self.t, 'punch bug', False):
                player.punching = False
            larm.pos[0] = 100 * dir[0] * pL
            larm.pos[1] = 100 * dir[1] * pL + 3 * math.sin(self.t * math.pi)
            rarm.pos[0] = 100 * dir[0] * pR
            rarm.pos[1] = 100 * dir[1] * pR + 3 * math.cos(self.t * math.pi)

        def grab():

            ID1 = player.ID + 1
            ID2 = player.ID + 2
            found = False
            if not player.grabbed[0]:
                for obj in self.obj_list:
                    obj_left = 1 if obj.pos[0] > player.pos[0] else -1
                    if obj.ID != 0 and not obj.figure and self.inside_box(obj, player.touch_box) and not obj.static:
                        player.grabbed = [obj, obj_left]
                        found = True
                        break
            else:
                found = True
                obj_left = player.grabbed[1]
            if not found:
                player.grabbing = False
                player.grabbed[0] = False
                p = funcs.step_response(0, t2, self.t, 'grab L' + str(player.ID))
                R = 0
                L = 0
            else:
                if obj_left == 1:
                    p = funcs.step_response(1, t2, self.t, 'grab L' + str(player.ID))
                    funcs.step_response(0, t2, self.t, 'grab R' + str(player.ID))
                    R = 10
                    L = 40
                elif obj_left == -1:
                    p = funcs.step_response(-1, t2, self.t, 'grab R' + str(player.ID))
                    funcs.step_response(0, t2, self.t, 'grab L' + str(player.ID))
                    R = 40
                    L = 10

            larm.pos = [p * L, 3 * math.sin(self.t * math.pi)]
            rarm.pos = [p * R, 3 * math.cos(self.t * math.pi)]

            if player.grabbed[0]:
                multiplier = 1 + player.grabbed[0].du if funcs.signal(player.vel[0]) == funcs.signal(player.pos[0] - player.grabbed[0].pos[0]) else 1
                player.grabbed[0].vel[0] = player.vel[0] * multiplier

            if player.grabbing and not self.inside_box(player.grabbed[0], player.touch_box):
                player.grabbed = [False, False]

        def heads():
            head.pos[1] = 2 * math.sin(self.t * math.pi / 1.5 + player.ID)
            head.pos[0] = 0

        def face():
            dir = funcs.signal(self.player.pos[0] - player.pos[0])
            if funcs.signal(player.vel[0]) != funcs.signal(dir):
                player.vel[0] = dir * 0.001

        def sprites():


            w = 1 if player.using_weapon else 0
            l = 1 if left else 0
            player.larm.image = player.lhand_sprite[w * (1 - l)]
            player.rarm.image = player.rhand_sprite[w * l]

            g = 1 if self.godmode_setting else 0

            if is_main:
                player.image = player.body_sprite[g]
                player.head.image = player.head_sprite[g]
                player.foot1.image = player.foot_sprite[g]
                player.foot2.image = player.foot_sprite[g]
                if funcs.changed(self.godmode_setting, 'godmode' + str(player.ID)) and not player.facing_left:
                    player.change_direction(True)
            if player.vel[0] !=0 and funcs.changed(player.vel[0] > 0, 'facing left' + str(player.ID)):
                player.change_direction()

        def set_random_stats():
            t = 3 if funcs.dpp(self.player.pos, player.pos) < 100 else 1
            if int(self.t * 60 + self.ID * 45) % (150 / t) == 0:
                player.punching = True
            if int(self.t * 60 + self.ID * 45) % player.weapon_rate == 0:
                player.shooting = True
            if int(self.t * 60 + self.ID * 10) % 30 == 0:
                player.shooting = False

        for obj in self.obj_list:
            if obj.is_player:
                s = self.jump_sound if self.soundeffects_setting else False
                obj.update(self.t, self.player.pos[0], s, self.godmode_setting)

                is_main = obj.name == 'main'
                player = obj
                head = player.head
                larm = player.larm
                rarm = player.rarm
                foot1 = player.foot1
                foot2 = player.foot2
                left = self.mouse_pos[0] >= player.pos[0] if is_main else player.vel[0] > 0
                t1 = 0.05
                t2 = 0.2
                head.ang = player.ang

                if is_main:
                    dir = funcs.get_dir(player.pos, self.mouse_pos)
                    ang = - math.atan2(dir[1], dir[0]) - math.pi / 2
                    if self.godmode_setting:
                        player.has_weapon = True
                else:
                    conditions = self.player.pos[0] > player.pos[0] and player.vel[0] > 0 or self.player.pos[0] < player.pos[0] and player.vel[0] < 0
                    dir = funcs.get_dir(player.pos, self.player.pos) if conditions else [funcs.signal(player.vel[0]), 0]
                    ang = - math.atan2(dir[1], dir[0]) - math.pi / 2 if conditions else (-math.pi / 2 if player.vel[0] > 0 else math.pi / 2)
                    set_random_stats()
                    if player.pos[0] < -30 or player.pos[0] > self.screen_w +30:
                        player.shooting = False
                        player.punching = False
                        player.static = True
                        player.allow_gravity = False
                        player.vel = [0, 0]
                    else:
                        player.static = False
                        player.allow_gravity = True
                        if funcs.one_up('player first' + str(player.ID)):
                            player.vel = [0, 0]
                if player.grabbing:
                    grab()
                elif abs(self.player.pos[0] - player.pos[0]) < 1000:
                    player.grabbed = [False, False]
                    funcs.step_response(0, t2, self.t, 'grab L' + str(player.ID))
                    funcs.step_response(0, t2, self.t, 'grab R' + str(player.ID))

                    if player.using_weapon:
                        shoot()
                    else:
                        punch()

                heads()
                foots()
                sprites()
                if not player.walker and not is_main:
                    face()

    def update_followers(self):
        for obj in self.obj_list:
            if obj.follows:
                t = False
                for obj1 in self.obj_list:
                    if obj.follows[0] == obj1.name:
                        fobj = obj1
                        rel_pos = obj.follows[1]
                        t = True
                if t:
                    obj.pos[0] += fobj.pos[0] + rel_pos[0] * math.cos(-fobj.ang) - rel_pos[1] * math.sin(-fobj.ang)
                    obj.pos[1] += fobj.pos[1] + rel_pos[1] * math.cos(-fobj.ang) + rel_pos[0] * math.sin(-fobj.ang)

    def update_camera(self):
        margin = self.screen_w * 0.35

        level_limits = self.p0[0] <= 0 and self.player.vel[0] < 0 or self.p0[0] + 8000 >= self.screen_w and self.player.vel[0] > 0
        screen_limits = self.player.pos[0] < margin and self.player.vel[0] < 0 or self.player.pos[0] > self.screen_w - margin and self.player.vel[0] > 0

        if level_limits and screen_limits:
            self.camera = True
            for obj in self.obj_list + self.wobj_list:
                obj.pos[0] -= self.player.vel[0] * self.dt
            self.p0[0] -= self.player.vel[0] * self.dt
        else:
            self.camera = False

    def update_keys(self):

        self.axis_vel = [0, 0]

        if self.xbox:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

            axis = []
            axes = joystick.get_numaxes()
            for i in range(axes):
                a = joystick.get_axis(i)
                axis.append(a)


            if axis[2] < -0.5:
                if 'g' not in self.keys:
                    self.keys.append('g')
                    if self.player.using_weapon == False:
                        self.player.punching = True
                        if self.soundeffects_setting:
                            r = random.randrange(0, 2)
                            self.punch_sound[r].play()
            else:
                funcs.delete(self.keys, 'g')

            d = 20
            e = 0.2

            if abs(axis[3]) > e:
                self.axis_vel[1] = d * (axis[3] - e)

            if abs(axis[4]) > e:
                self.axis_vel[0] = d * (axis[4] - e)

            if abs(axis[0]) > 0.5:
                self.player_axis_vel = axis[0]


        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self.graphics.quit()
                quit()
            
            if self.xbox:

                button = []
                buttons = joystick.get_numbuttons()
                for i in range(buttons):
                    b = joystick.get_button(i)
                    button.append(b)

                if event.type == pygame.JOYBUTTONDOWN:

                    if button[0] == 1:
                        self.keys.append('w')

                    if button[5] == 1:
                        self.player.grabbing = True

                    if button[2] == 1:
                        self.keys.append('shift')

                    if button[3] == 1:
                        if self.inside_box(self.player, self.end_door):
                            self.GameOver = True
                            self.GameWin = True

                    if button[4] == 1:
                        if self.player.has_weapon:
                            self.player.using_weapon = not self.player.using_weapon
                            if self.soundeffects_setting:
                                self.switch_weapon_sound.play()

                    if button[6] == 1:
                        self.GameOver = True
                        self.GameExit = True

                    if button[7] == 1:
                        self.Pause = True

                    if button[8] == 1:
                        if self.godmode_setting:
                            self.add_guy(self.mouse_pos[0], self.mouse_pos[1])

                    if button[9] == 1:
                        if self.godmode_setting:
                            self.add_rect(self.mouse_pos[0], self.mouse_pos[1], 50, 50, 30)
                            self.obj_list[-1].image = [self.graphics.load_img('game_files/images/comum/box.png'), 1]
                            self.obj_list[-1].deletable = True


                if button[0] == 0:
                    funcs.delete(self.keys, 'w')

                if button[5] == 0:
                    self.player.grabbing = False

                if button[2] == 0:
                    funcs.delete(self.keys, 'shift')

            else:
                self.mouse_pos = self.graphics.get_mouse()[0]

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if pygame.mouse.get_pressed()[0]:
                        removed = False
                        if self.godmode_setting:
                            for obj in self.obj_list:
                                if obj.selected and not obj.static and not obj.is_player and obj.deletable:
                                    self.destroy_obj(obj.ID)
                                    removed = True

                        if not removed:
                            self.keys.append('g')
                            if self.player.using_weapon == False:
                                self.player.punching = True
                                if self.soundeffects_setting:
                                    r = random.randrange(0, 2)
                                    self.punch_sound[r].play()

                    elif pygame.mouse.get_pressed()[1]:
                        if self.godmode_setting:
                            self.add_guy(self.mouse_pos[0], self.mouse_pos[1])

                    elif pygame.mouse.get_pressed()[2]:
                        if self.godmode_setting:
                            self.add_rect(self.mouse_pos[0], self.mouse_pos[1], 50, 50, 30)
                            self.obj_list[-1].image = [self.graphics.load_img('game_files/images/comum/box.png'), 1]
                            self.obj_list[-1].deletable = True

                if event.type == pygame.MOUSEBUTTONUP:
                    funcs.delete(self.keys, 'g')

                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_r:
                        self.GameOver = True
                        self.GameExit = True
                        # self.MenuExit = True

                    if self.player != False:

                        if event.key == pygame.K_ESCAPE:
                            self.Pause = True

                        if event.key == pygame.K_LSHIFT:
                            self.keys.append('shift')

                        if event.key == pygame.K_a:
                            self.keys.append('a')
                            self.player.t0 = self.t

                        if event.key == pygame.K_d:
                            self.keys.append('d')
                            self.player.t0 = self.t

                        if event.key == pygame.K_w:
                            self.keys.append('w')

                        if event.key == pygame.K_s:
                            if self.inside_box(self.player, self.end_door):
                                self.GameOver = True
                                self.GameWin = True

                        if event.key == pygame.K_SPACE:
                            self.player.grabbing = True

                        if event.key == pygame.K_x:
                            self.player.life -= 0.1

                        if event.key == pygame.K_c:
                            self.player.life += 0.1

                        if event.key == pygame.K_f:
                            if self.player.has_weapon:
                                self.player.using_weapon = not self.player.using_weapon
                                if self.soundeffects_setting:
                                    self.switch_weapon_sound.play()

                if event.type == pygame.KEYUP:

                    if self.player != False:

                        if event.key == pygame.K_LSHIFT:
                            funcs.delete(self.keys, 'shift')

                        if event.key == pygame.K_a:
                            funcs.delete(self.keys, 'a')

                        if event.key == pygame.K_d:
                            funcs.delete(self.keys, 'd')

                        if event.key == pygame.K_w:
                            funcs.delete(self.keys, 'w')

                        if event.key == pygame.K_SPACE:
                            self.player.grabbing = False
        if self.xbox:
            v = self.player_axis_vel
        else:
            v = False
        r = True
        self.player.shooting = False
        self.player.jumped = False
        self.player.running = False

        self.mouse_pos[0] += self.axis_vel[0]
        self.mouse_pos[1] += self.axis_vel[1]

        self.mouse_pos[0] = funcs.clamp(self.mouse_pos[0], 0, self.screen_w)
        self.mouse_pos[1] = funcs.clamp(self.mouse_pos[1], 0, self.screen_h)

        for key in self.keys:
            if key == 'a':
                v -= 1
                r = False
            if key == 'd':
                v += 1
                r = False
            if key == 'w':
                self.player.jumped = True
            if key == 'shift':
                self.player.running = True
            if key == 'g':
                if self.player.using_weapon:
                    self.player.shooting = True
                    self.player.punching = False
        if not self.xbox:
            self.player.walking = v
        else:
            self.player.walking = v

    def update_deaths(self):
        for obj in self.obj_list + self.wobj_list:

            time_death = obj.life_time > obj.max_life_time
            fall_death = obj.pos[1] > self.screen_h * 1.5 and not obj.figure and not obj.static

            if time_death or fall_death:
                if obj.name != 'main':
                    self.destroy_obj(obj.ID)
                else:
                    self.GameOver = True
                    self.GameLost = True

    def update_collisions(self):

        def collision_Circle_Circle(a, b):
            if funcs.dpp(a.pos, b.pos) > (a.radius + b.radius):
                return False
            else:
                points = []
                pd = a.radius + b.radius - funcs.dpp(a.pos, b.pos)
                normal = funcs.norm([b.pos[0] - a.pos[0], b.pos[1] - a.pos[1]])

                point = [a.pos[0] + a.radius * normal[0], a.pos[1] + a.radius * normal[1]]

                points.append(point)

                self.hits.append([a.ID, b.ID, normal, abs(pd), points])
                return True

        def collision_Poly_Circle(a, b):
            n1 = [math.cos(a.ang), -math.sin(a.ang)]
            n2 = [math.sin(a.ang), math.cos(a.ang)]

            an = a.normals
            at = a.tangents
            av = a.vertex

            m = math.inf
            points = []
            point = [0, 0]
            is_inside = False

            for i in range(a.vertex_count):
                j = (i + 1) % a.vertex_count
                ti = funcs.dot(at[i], av[i])
                tj = funcs.dot(at[i], av[j])
                tb = funcs.dot(at[i], b.pos)
                m = (funcs.dot(an[i], b.pos) - funcs.dot(an[i], av[i]))
                if funcs.inside(tb, ti, tj) and m > 0:
                    if m < b.radius:
                        pd = m - b.radius
                        normal = an[i]
                        point = [b.pos[0] - normal[0] * m, b.pos[1] - normal[1] * m]
                        is_inside = True
                    else:
                        return False

            if not is_inside:
                if a.inside(b.pos):
                    m = math.inf
                    for i in range(a.vertex_count):
                        m_t = funcs.dot(an[i], av[i]) - funcs.dot(an[i], b.pos)
                        if m_t < m:
                            m = m_t
                            best_i = i
                    pd = - (m + b.radius)
                    normal = an[best_i]
                    point = [b.pos[0] + normal[0] * m, b.pos[1] + normal[1] * m]

                else:
                    m = math.inf
                    for v in av:

                        if funcs.dpp(b.pos, v) < m:
                            m = funcs.dpp(b.pos, v)
                            ext_p = v
                    if m < b.radius:
                        normal = funcs.norm([b.pos[0] - ext_p[0], b.pos[1] - ext_p[1]])
                        pd = m - b.radius
                        point = ext_p
                    else:
                        return False

            if a.is_player:
                if point[1] == a.vertex[0][1] and (b.radius > 10 or b.static) and b.collider:
                    a.in_ground = True
                    a.ground = b

            points.append(point)

            self.hits.append([a.ID, b.ID, normal, abs(pd), points])
            return True

        def collision_Poly_Poly(a, b):

            def min_distance(p, r):
                min_d = math.inf
                for i in range(r.vertex_count):
                    j = (i + 1) % r.vertex_count
                    p1 = r.vertex[i]
                    p2 = r.vertex[j]
                    if funcs.dpl(p1, p2, p) < min_d:
                        min_d = funcs.dpl(p1, p2, p)
                return min_d

            normal = [0, 0]
            pd = 0
            point = [0, 0]
            m = math.inf
            points = []
            av = a.vertex
            bv = b.vertex
            for nv in a.normals + b.normals:
                minA = min(funcs.dot(nv, p) for p in av)
                maxA = max(funcs.dot(nv, p) for p in av)
                minB = min(funcs.dot(nv, p) for p in bv)
                maxB = max(funcs.dot(nv, p) for p in bv)
                if (minB > maxA) != (minA > maxB):
                    return False
                if min(abs(maxA - minB), abs(maxB - minA)) < m:
                    m = min(abs(maxA - minB), abs(maxB - minA))
                    normal = nv

            for p in av:
                d = math.inf
                if b.inside(p):
                    dm = min_distance(p, b)
                    if dm < d:
                        d = dm
                        points.append(p)

            for p in bv:
                d = math.inf
                if a.inside(p):
                    dm = min_distance(p, a)
                    if dm < d:
                        d = dm
                        points.append(p)

            rp = [b.pos[0] - a.pos[0], b.pos[1] - a.pos[1]]

            if funcs.dot(normal, rp) < 0:
                normal = [-normal[0], -normal[1]]
            pd = m

            if a.is_player and b.collider:
                if len(points) == 2:
                    if funcs.dot(normal, a.normals[-1]) > 0.95:
                        a.in_ground = True
                        a.ground = b
                if len(points) == 1:
                    if abs(points[0][1] - a.vertex[0][1]) < 20 or abs(points[0][1] - a.vertex[-1][1]) < 20:
                        a.in_ground = True
                        a.ground = b
            if b.is_player and a.collider:
                if len(points) == 2:
                    if funcs.dot(normal, b.normals[-1]) < - 0.95:
                        b.in_ground = True
                        b.ground = a
                if len(points) == 1:
                    if abs(points[0][1] - b.vertex[0][1]) < 10 or abs(points[0][1] - b.vertex[-1][1]) < 10:
                        b.in_ground = True
                        b.ground = a

            self.hits.append([a.ID, b.ID, normal, abs(pd), points])
            return True

        def detection(A, B):
            if A.type == 'poly' and B.type == 'poly':
                collision_Poly_Poly(A, B)

            elif A.type == 'poly' and B.type == 'circle':
                collision_Poly_Circle(A, B)

            elif A.type == 'circle' and B.type == 'poly':
                collision_Poly_Circle(B, A)

            elif A.type == 'circle' and B.type == 'circle':
                collision_Circle_Circle(B, A)

        def collision_response():

            for hit in self.hits:

                [IDA, IDB, n, pd, points] = hit

                A = self.find_obj(IDA)
                B = self.find_obj(IDB)

                if not (A.name == 'bullet' and B.name == 'bullet'):
                    A.hits.append(B)
                    B.hits.append(A)

                if A.collider and B.collider and A.exclude(B) and B.exclude(A):

                    for p in points:

                        rA = [p[0] - A.pos[0], p[1] - A.pos[1]]
                        rB = [p[0] - B.pos[0], p[1] - B.pos[1]]
                        rv = [B.vel[0] + funcs.cross(B.ang_vel, rB)[0] - A.vel[0] - funcs.cross(A.ang_vel, rA)[0],
                              B.vel[1] + funcs.cross(B.ang_vel, rB)[1] - A.vel[1] - funcs.cross(A.ang_vel, rA)[1]]

                        vn = funcs.dot(rv, n)

                        if A.is_player or B.is_player:
                            e = eu = du = 0
                        else:
                            e = min(A.e, B.e)
                            eu = (A.eu + B.eu) / 2
                            du = (A.du + B.du) / 2

                        total_sum = A.inv_mass + B.inv_mass + A.inv_inertia * funcs.cross(rA, n) ** 2 + B.inv_inertia * funcs.cross(rB, n) ** 2
                        total_mass = A.inv_mass + B.inv_mass

                        if total_sum == 0:
                            total_sum = math.inf
                        if total_mass == 0:
                            total_mass = math.inf

                        # impulse

                        j = -(e + 1) * vn / (total_sum * len(points))
                        impulse = [j * n[0], j * n[1]]
                        neg_impulse = [-impulse[0], -impulse[1]]

                        if vn < 0:
                            A.apply_impulse(neg_impulse, rA)
                            B.apply_impulse(impulse, rB)

                        # friction

                        t = funcs.norm([rv[0] - funcs.dot(rv, n) * n[0], rv[1] - funcs.dot(rv, n) * n[1]])

                        jt = -funcs.dot(rv, t) / total_sum / len(points)

                        if abs(jt) < j * eu:
                            friction = [jt * t[0], jt * t[1]]
                        else:
                            friction = [-j * du * t[0], -j * du * t[1]]

                        neg_friction = [-friction[0], -friction[1]]

                        if vn < 0:
                            A.apply_impulse(neg_friction, rA)
                            B.apply_impulse(friction, rB)

                        # position correction

                        percent = 0.4
                        slop = 0.1
                        cr = percent * max(pd - slop, 0) / total_mass
                        correction = [cr * n[0], cr * n[1]]

                        A.pos[0] -= correction[0] * A.inv_mass
                        A.pos[1] -= correction[1] * A.inv_mass
                        B.pos[0] += correction[0] * B.inv_mass
                        B.pos[1] += correction[1] * B.inv_mass

        def verify():

            self.hits = []
            i = 0
            for obj in self.obj_list:
                obj.set_box()
                if obj.is_player:
                    obj.in_ground = False

            while i < len(self.obj_list):
                j = i + 1
                while j < len(self.obj_list):
                    A = self.obj_list[i]
                    B = self.obj_list[j]

                    if self.inside_box(A, B.box) and (not A.static or not B.static) and (not A.figure and not B.figure):
                        detection(A, B)
                    j += 1
                i += 1

            collision_response()

        verify()

    def update_damage(self):
        for obj in self.obj_list:
            if obj.deadly:
                for h in self.hits:
                    p = False
                    if h[0] == self.player.ID and h[1] == obj.ID:
                        p = True
                    if funcs.delay(p, 1, self.t, 'col time'):
                        self.player.vel[0] -= h[2][0] * obj.deadly
                        self.player.vel[1] -= h[2][1] * obj.deadly
                        self.player.life -= obj.deadly / 10
                        self.destroy_obj(obj.ID)
            if obj.is_player and obj.life <= 0.01:
                if obj.name == 'main':
                    self.GameOver = True
                    self.GameLost = True
                else:
                    self.destroy_enemy(obj)

                        # deletar items

    def del_dist_joint(self, params):
        for i in range(len(self.dist_joint_list)):
            if self.dist_joint_list[i] == params:
                del self.dist_joint_list[i]
                break

    def del_rev_joint(self, params):
        for i in range(len(self.rev_joint_list)):
            if self.rev_joint_list[i] == params:
                del self.rev_joint_list[i]

    def destroy_enemy(self, player):
        d = 1 if self.player.pos[0] < player.pos[0] else -1
        if not player.stop:
            j = [d * 300, -250]
            player.vel[0] += j[0]
            player.vel[1] += j[1]
            player.ang_vel -= 200 * math.pi / 180 * d
            player.stop = True
            if player.has_weapon:
                player.has_weapon = False
                player.using_weapon = False
                self.add_gun(player.pos, player.ammo)
            player.max_life_time = player.life_time + 1

    def destroy_obj(self, ID, wait=False):
        if wait:
            list = self.wobj_list
        else:
            list = self.obj_list
        i = 0
        while i < len(list):
            if list[i].ID == ID:
                if list[i].is_player:
                    del list[i]
                    del list[i]
                    del list[i]
                    del list[i]
                    del list[i]
                    del list[i]
                else:
                    del list[i]
                return
            i += 1

    def get_lever(self, name):
        lever = self.find_obj(name)

        pos = self.find_obj(lever.ID - 1).pos
        x = lever.pos[0] - pos[0]

        lever.vel[1] = 0
        if lever.pos[0] >= pos[0] + 25:
            lever.pos[0] = pos[0] + 25
            lever.vel[0] = 0
        elif lever.pos[0] <= pos[0] - 25:
            lever.pos[0] = pos[0] - 25
            lever.vel[0] = 0
        else:
            lever.pos[1] = pos[1] - 50 - 5.9 * math.cos(x * math.pi / 50)
            lever.vel[0] += funcs.signal(x) * 18

        self.draw_line.append([funcs.colors('white'), lever.pos, pos, 5])

        return x > 0

    def get_button(self, name, wait_time=0, time_to_wait=0.1):
        button = self.find_obj(name)
        pos = self.find_obj(button.ID - 1).pos
        v = 1 / self.dt
        pressing = False
        for h in self.hits:
            if h[0] == button.ID:
                obj = self.find_obj(h[1])
                if obj:
                    if obj.box[3] < button.pos[1]:
                        pressing = True
                        v = 1 / self.dt
                        break
            elif h[1] == button.ID:
                obj = self.find_obj(h[0])
                if obj:
                    if obj.box[3] < button.pos[1]:
                        pressing = True
                        v = 3 / self.dt if obj.is_player else 2 / self.dt
                        break
        if not pressing:
            pressing = not funcs.wait(0.1, self.t, 'button delay' + name)
        button.vel[1] = 0

        go = funcs.register('pressing delay' + name, 0, True)[0]

        if pressing and button.pos[1] < pos[1]-5:
            button.vel[1] += v

        if pressing and funcs.wait(time_to_wait, self.t, 'pressing delay2' + name):
            funcs.register('pressing delay' + name, 1, False)

        if not pressing and button.pos[1] >= pos[1] - 20:
            if funcs.wait(wait_time, self.t, 'pressing delay' + name) or go:
                button.vel[1] -= v

        return button.pos[1] > pos[1] - 10

    # funções úteis

    def find_obj(self, key, w=False):

        if w:
            list = self.obj_list + self.wobj_list
        else:
            list = self.obj_list

        if type(key) is int:
            for obj in self.obj_list + self.wobj_list:
                if obj.ID == key:
                    return obj
        if type(key) is str:
            for obj in self.obj_list + self.wobj_list:
                if obj.name == key:
                    return obj
        return False

    def translade(self, ID, bool, vel, posA, posB, d):
        # bool: variavel que controla a direçao
        # vel: vel do movimento
        # posA e pos B: pos max e min do movimento
        # d: 0 para movimento horizontal e 1 para movimento vertical

        obj = self.find_obj(ID)
        posA += self.p0[d]
        posB += self.p0[d]

        maxd = max(posA, posB)
        mind = min(posA, posB)

        if obj.pos[d] > maxd:
            obj.pos[d] = maxd
        elif obj.pos[d] < mind:
            obj.pos[d] = mind

        obj.vel[d] = vel if bool else -vel

        if (obj.pos[d] <= mind and obj.vel[d] < 0) or (obj.pos[d] >= maxd and obj.vel[d] > 0):
            obj.vel[d] = 0

    # Funções que retornam True ou False

    def inside_box(self, objA, B):
        if objA.box[1] < B[0] or objA.box[0] > B[1]:
            return False
        if objA.box[3] < B[2] or objA.box[2] > B[3]:
            return False
        return True

    def in_scene(self, obj, w_margin=0, h_margin=0):
        if obj:
            if obj.box[1] < - w_margin or obj.box[0] > self.screen_w + w_margin:
                return False

            if obj.box[3] < - h_margin or obj.box[2] > self.screen_h + h_margin:
                return False
            return True

    def got_hit(self, name0, name1):

        obj0 = self.find_obj(name0)
        obj1 = self.find_obj(name1)
        if obj1:
            if funcs.register('hit' + str(obj1.ID), 0)[0]:
                return True
            else:
                for h in self.hits:
                    if h[0] == obj0.ID and h[1] == obj1.ID or h[1] == obj0.ID and h[0] == obj1.ID:
                        funcs.register('hit' + str(obj1.ID), 1, True)
                        return True
                return False

    # renderizar items

    def render(self):

        def draw_surfaces():
            for f in self.draw_line:
                self.graphics.draw_line(f[0], f[1], f[2], f[3])

            for f in self.draw_circle:
                self.graphics.draw_circle(f[0], f[1], f[2], f[3])

            for f in self.draw_polygon:
                self.graphics.draw_polygon(f[0], f[1], f[2])

        def draw_back_sprites():
            add = []
            for spt in self.sprites:
                if spt[1] >= 0:
                    add.append(spt)
            add = sorted(add, key=itemgetter(1))
            for a in add[::-1]:
                p0 = [self.p0[0]/a[1], self.p0[1]/a[1]]
                self.graphics.show(a[0], p0)

        def draw_objects():
            for obj in self.obj_list:
                if obj.type == 'poly' and obj.visible:
                    self.graphics.draw_polygon(obj.color, obj.vertex, obj.thickness)
                if obj.type == 'circle' and obj.visible:
                    cos = math.cos(-obj.ang - math.pi / 2)
                    sin = math.sin(-obj.ang - math.pi / 2)
                    r = obj.radius
                    p = obj.pos
                    self.graphics.draw_circle(obj.color, [int(p[0]), int(p[1])], r, obj.thickness)
                    self.graphics.draw_line(obj.color, [int(p[0]), int(p[1])], [int(p[0]) + r * cos, int(p[1] + r * sin)], obj.thickness)

        def draw_special_sprites():
            for s in self.special_sprites:
                img = s[0]
                pos = s[1]
                ang = s[2]
                max_dist = s[3]

                pos = (pos[0] + max_dist*math.sin(ang), pos[1])

                self.graphics.draw_special_image(img, pos, ang, max_dist)

        def draw_objects_images_back():
            add = []
            for obj in self.obj_list:
                if obj.image:
                    limit = 1
                    if obj.box[0] < self.screen_w * limit and obj.box[1] > self.screen_w * (1 - limit):
                        add.append([obj, obj.image[1]])
            add = sorted(add, key=itemgetter(1))
            front = []
            for a in add:
                if a[1] < 0:
                    self.graphics.draw_image(a[0])
                else:
                    front.append(a)
            return front

        def draw_objects_images_front(f):
            for a in f:
                self.graphics.draw_image(a[0])

        def draw_front_sprites():
            for spt in self.sprites:
                sprite = spt[0]
                z = spt[1]
                if z < 0:
                    self.graphics.show(sprite, self.p0)

        def draw_hits_sprites():
            for sprite in self.hits_sprites:
                img = sprite[0]
                pos = sprite[1]
                re = img.get_rect()
                pos = [pos[0] - re[2] / 2, pos[1] - re[3] / 2]
                self.graphics.show(img, pos)

        def draw_hud():
            for obj in self.obj_list:
                if obj.is_player:
                    is_main = obj.name == 'main'
                    h = 20 if is_main else 1
                    w = 200  if is_main else 80
                    x = 20 if is_main else obj.pos[0]
                    y = 20 if is_main else obj.pos[1] - 100
                    if obj.life > 1:
                        obj.life = 1
                    elif obj.life < 0:
                        obj.life = 0
                    life = funcs.step_response(w * obj.life, 0.5, self.t, 'life' + str(obj.ID))

                    if obj.life >= 0.41:
                        color = funcs.colors('green')
                    elif obj.life >= 0.11:
                        color = funcs.colors('yellow')
                    else:
                        color = funcs.colors('red')

                    if is_main:
                        self.graphics.draw_polygon(color, [[x, y + h], [x, y], [x + life, y], [x + life, y + h]], 0)
                        self.graphics.draw_polygon(funcs.colors('white'), [[x, y + h], [x, y], [x + w, y], [x + w, y + h]], 2)
                    elif not obj.stop:
                        self.graphics.draw_polygon(color, [[x - life/2, y + h], [x - life/2, y], [x + life/2, y], [x + life/2, y + h]], 0)

            color = funcs.colors('light red') if self.player.shooting or self.player.punching else funcs.colors('white')
            positions = funcs.history(self.mouse_pos, 5, 'mouse pos')
            a = 5
            for p in positions:

                self.graphics.draw_circle(color, p, int(a), 0)
                a -= 0.5

            xi = 20
            yi = 20
            hi = 20
            wi = 200
            if self.godmode_setting:
                self.graphics.write('Lifes: ' + str(int(self.lifes_left)), (xi, yi + hi + 10))
                self.graphics.write('Ammo: infinite', (xi, yi + hi + 30))
                self.graphics.write('itens: ' + str(len(self.obj_list)), (xi, yi + hi + 50))
                self.graphics.write('FPS: ' + str(int(self.fps_now)), (xi, yi + hi + 70))
                self.graphics.draw_line(funcs.colors('white'), (xi, yi + hi + 100), (xi + funcs.meter, yi + hi + 100), 1)
                self.graphics.draw_line(funcs.colors('white'), (xi + self.t * funcs.meter % funcs.meter, yi + hi + 110), (xi + self.t * funcs.meter % funcs.meter, yi + hi + 90), 1)
            else:
                self.graphics.write('Lifes: ' + str(int(self.lifes_left)), (xi, yi + hi + 10))
                self.graphics.write('Ammo: ' + str(int(self.player.ammo)), (xi, yi + hi + 30))

        def draw_lights():
           for light in self.draw_lights:
                mask = light[0]
                draw_pos = light[1]
                self.graphics.gameDisplay.blit(mask, draw_pos)

        def change(dir):
            for obj in self.obj_list:
                if obj.is_player:
                    obj.pos[1] -= 5 * dir
                    obj.set_vertex()

        self.graphics.fill(funcs.colors('black'))
        draw_back_sprites()
        draw_lights()
        f = draw_objects_images_back()
        change(1)
        draw_special_sprites()
        draw_objects()
        draw_objects_images_front(f)
        draw_front_sprites()
        draw_hits_sprites()
        change(-1)
        draw_surfaces()
        draw_hud()
        self.graphics.set_fps(self.fps)
        self.graphics.update_display()

    def pause(self):
        pygame.mixer.music.pause()
        self.graphics.set_mouse(True)
        pygame.image.save(self.graphics.gameDisplay, 'game_files/images/temp/screenshot.png')
        img = self.graphics.load_img('game_files/images/temp/screenshot.png')
        b = self.settings_menu(img)
        if b == 0:
            self.Pause = False
            self.graphics.set_mouse(False)
        elif b == 1:
            self.Pause = False
            self.GameOver = True
            self.GameExit = True

        pygame.mixer.music.unpause()


if __name__ == '__main__':
    Simulation()
