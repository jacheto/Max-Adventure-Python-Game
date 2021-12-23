import random
import math

def pol(a, b):
    return (a**2 + b**2)**0.5

def dpp(a, b = False):
    return pol(b[0]-a[0], b[1]-a[1]) if b else pol(a[0], a[1])

def dpl(p1, p2, p):
    if p2[0] != p1[0]:
        a = - (p2[1] - p1[1]) / (p2[0] - p1[0])
        c = - p1[0] * a - p1[1]
        return abs((a * p[0] + p[1] + c) / (a ** 2 + 1) ** 0.5)
    else:
        return abs(p[0]-p1[0])

def dot(a, b):
    return a[0]*b[0]+a[1]*b[1]

def cross(a, b):
    if (type(a) is list or type(a) is tuple) and (type(b) is list or type(b) is tuple):
        return a[0] * b[1] - a[1] * b[0]
    elif not (type(a) is list or type(a) is tuple):
        return [a * b[1], -a * b[0]]
    elif not (type(b) is list or type(b) is tuple):
        return [-b * a[1], b * a[0]]

def norm(vec):
    d = pol(vec[0],vec[1])
    n1 = vec[0]/d if d!=0 else 0
    n2 = vec[1]/d if d!=0 else 0
    return [n1, n2]

def random_color():
    r = random.randrange(50, 255)
    g = random.randrange(50, 255)
    b = random.randrange(50, 255)
    return [r, g, b]

def inside(A, b, c):
    return ((A >= b and A <= c) or (A <= b and A >= c))

def clamp(A, b, c, invert = False):
    maxv = max(b, c)
    minv = min(b, c)

    if A > maxv:
        return maxv if not invert else minv
    elif A < minv:
        return minv if not invert else maxv
    else:
        return A

def colors(color_name):
    colors = {
              'red':        (200, 0, 0),
              'light red':  (255, 100, 100),
              'dark red':   (50, 0, 0),
              'blue':       (0, 0, 200),
              'light blue': (100, 100, 255),
              'dark blue':  (0, 0, 50),
              'green':      (0, 200, 0),
              'light green':(100, 255, 100),
              'dark green': (0, 50, 0),
              'yellow':     (255, 255, 0),
              'orange':     (255, 140, 0),
              'black':      (0, 0, 0),
              'white':      (255, 255, 255),
              'dark grey':  (50, 50, 50),
              'light grey': (100, 100, 100)
              }
    return colors[color_name]

def signal(a):
    return 1 if  a>= 0 else -1

def intersection(l, pa, pb):
    p1 = l[0]
    p2 = l[1]
    r = [p2[0] - p1[0], p2[1] - p1[1]]
    s = [pb[0] - pa[0], pb[1] - pa[1]]
    g = [pa[0] - p1[0], pa[1] - p1[1]]
    t = cross(g, s) / cross(r, s) if cross(r, s) != 0 else 1
    if t > 0 and t < 1:
        return [p1[0] + t * r[0], p1[1] + t * r[1]]
    else:
        return False

def wait(t, time, ID):
    for i in range(len(wait_list)):
        if wait_list[i][0] == ID:
            if time - wait_list[i][2] < 4 / fps:
                wait_list[i][2] = time
                return True if time - wait_list[i][1] > t else False
            else:
                del wait_list[i]
                return False

    wait_list.append([ID, time, time])
    return False

def activate(activate, ID):

    if activate == -1:
        a = -1
    elif activate:
        a = 1
    elif not activate:
        a = 0

    for i in range(len(act_list)):
        if act_list[i][1] == ID:

            if a == 1:
                act_list[i][0] = True
                return True
            elif a == 0:
                return act_list[i][0]
            elif a == -1:
                del act_list[i]
                return False


    act_list.append([False, ID])

def delay(bool, t, time, ID, type = True):
    # retorna True após t segundos depois que bool mudou de False para True
    def d(t, time, ID):
        for i in range(len(delay_list)):
            if delay_list[i][0] == ID:
                if time - delay_list[i][1] > t:
                    del delay_list[i]
                    return type
                else:
                    return False
        delay_list.append([ID, time])
        return True
    if bool:
        bool_d = d(t, time, ID)
    else:
        bool_d = False
    return bool_d

def delay_response(value, T, time, ID):
    for i in range(len(step_list)):
        item = delay_list[i]
        if item[0] == ID:
            if value == item[1]:
                return value
            else:
                if item[2] == False:
                    #primeira vez que o valor muda
                    item[2] = time
                    return item[1]
                else:
                    #transição para o outro valor
                    t = time - item[2]
                    if t < T:
                        return item[1]
                    else:
                        step_list[i] = [ID, value, False]
                        return value

    # primeira vez que a função é chamada (não existe o ID na lista)
    delay_list.append([ID, value, False])
    return value

def step_response(value, T, time, ID):
    for i in range(len(step_list)):
        item = step_list[i]
        if item[0] == ID:
            if item[2] == value and item[2] == item[1]: # se o valor final não mudou
                return value
            else: # se é a primeira vez que o valor muda
                if item[3] == False: # se é o primeiro frame após mudança
                    item[2] = value
                    item[3] = time
                    return item[1]
                else:  #senão, faz a transição para o outro valor
                    t = time - item[3]
                    if t < T:   #se ainta não completou o tempo de transição
                        Vi = item[1]
                        Tc = T / 4
                        Vf = item[2] if item[2] != 0 else 0.0000001
                        A = Vf
                        B = Vi * Tc / Vf
                        t = time - item[3]
                        current_value = math.exp(-t / Tc) * A * (B / Tc - 1) + A
                        if value != item[2]:  # se o valor final mudou
                            item[1] = current_value
                            item[2] = value
                            item[3] = time

                        return current_value
                    else:
                        step_list[i] = [ID, value, value, False]
                        return value

    # primeira vez que a função é chamada (não existe o ID na lista)
    #(ID, V INICIAL, V FINAL, t0)
    step_list.append([ID, value, value, False])
    return value

def delete(list, item):
    deleted = False
    i = 0
    if item in list:
        while i < len(list) and not deleted:
            i += 1
            if list[i] == item:
                del list[i]
                deleted = True
    return list

def register(nameID, action = 0, a = False, b = False, c = False, d = False):
    #action:
    # 0-usar
    # 1-atualizar
    # 2-destroir
    for i in range(len(registered)):
        if registered[i][0] == nameID:
            if action == 0:
                return registered[i][1:]
            elif action == 1:
                registered[i] = [nameID, a, b, c, d]
                return registered[i][1:]
            elif action == 2:
                del registered[i][1:]
                return False
    # se não achou, cadastrar:
    registered.append([nameID, a, b, c, d])
    return registered[-1][1:]

def check_once(bool, ID):
    if bool:
        register(ID, 1, True)
        act = True
    else:
        act = register(ID, 0)[0]

    return act

def get_dir(p1, p2 = False):
    if not p2:
        return [math.cos(p1 * math.pi / 180), -math.sin(p1 * math.pi / 180)]
    else:
        return norm([p2[0] - p1[0], p2[1] - p1[1]])

def neg(vec):
    return [-vec[0], -vec[1]]

def one_up(ID, reset = False):
    if ID in oneup_list:
        if reset:
            for i in range(len(oneup_list)):
                if i == ID:
                    del oneup_list[i]
        else:
            return False
    elif not reset:
        oneup_list.append(ID)
        return True
    else:
        pass

def history(var, quant, ID):
    for i in range(len(registered)):
        item = registered[i]
        if ID == item[0]:
            item[2].append(var)
            if len(item[2]) > quant:
                del item[2][0]
            return item[2][::-1]

    values_list = []
    registered.append([ID, var, values_list])
    return values_list

def changed(value, ID):
    for i in range(len(registered)):
        item = registered[i]
        if ID == item[0]:
            if value == item[1]:
                return False
            else:
                registered[i][1] = value
                return True

    registered.append([ID, value])
    return value

def interval(t, freq, offset = 0):
    return int(t * 1000 + offset) % freq == 0


oneup_list = []
act_list = []
wait_list = []
delay_list = []
step_list = []
registered = []

M = 1  # mass unit / kilogram
L = 100  # pixels / meter
T = 60  # frames / second

meter = L
fps = T
vel = meter / T
acel = vel / T
newton = M * acel