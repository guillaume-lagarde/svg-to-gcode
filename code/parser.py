import sys
from xml.dom import minidom
import math
import re

parameters = sys.argv
filename = parameters[1]
output = parameters[2]


#-------------------------------
# Set of parameters
SPEED = 3000 # Speed in millimeter/minute
PAUSE_start = 200 # Pause after putting down the printhead
PAUSE_end = 400 # Pause after pulling up the printhead
dl_min = 1 # Discretization: ~size of each step; the smaller the more accurate
dl2 = 0.4 # merge two paths whose distance(end1, start2) < dl2
dT = 0.0001 # Discretization: "delta T"
accuracy = 0.1
X = 1 #normal x-axis
Y = 1 #reverse y-axis
#-------------------------------

doc = minidom.parse(filename)

PI = 3.14159265359

def distance(x1,y1,x2,y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def approx(f):
    return int(f/accuracy)*accuracy

#-------------------------------
# Parametrization of usual curve

def circle(C,T, shift = 0):
    cx, cy, r = [float(p) for p in C]
    x = cx+r*math.cos(shift+T*2*PI)
    y = cy+r*math.sin(shift+T*2*PI)
    return (x,y)

def ellipse(E,T):
    cx, cy, rx, ry = [float(p) for p in E]
    x = cx+rx*math.cos(T*2*PI)
    y = cy+ry*math.sin(T*2*PI)
    return (x,y)

# Cubic bezier
def bezier(b, t):
    sx, sy, x1, y1, x2, y2, ex, ey = [float(p) for p in b]
    xt = sx *(1-t)**3 + 3* x1*t*(1-t)**2 + 3*x2*t**2*(1-t) + ex*t**3
    yt = sy *(1-t)**3 + 3* y1*t*(1-t)**2 + 3*y2*t**2*(1-t) + ey*t**3    
    return (xt,yt)
    
def line(l, T):
    x1, y1, x2, y2 = [float(p) for p in l]
    if T < 1:
        return (x1, y2)
    else:
        return (x2,y2)
#-------------------------------

# F = parametrization function; I = instance of the object
def draw_object(F, I, start = 0, end = 1, DOWN = True, UP = True):
    T = start
    x, y = F(I,T)
    gcode = ""
    # gcode = 'G1 X{} Y{}\n'.format(x,Y*y)
    if DOWN:
        gcode += 'M3 S1000\n'
        gcode += 'G4 P0.{}\n'.format(PAUSE_start)
    T+=dT
    while T < end:
        x2, y2 = F(I,T)
        if distance(x,y,x2,y2) < dl_min:
            T+=dT
        else:
            gcode += 'G1 X{} Y{}\n'.format(X*approx(x2),Y*approx(y2))
            T+=dT
            x, y = x2, y2
    x2,y2 = F(I,end)
    if distance(x,y,x2,y2) > dl2:
        gcode += 'G1 X{} Y{}\n'.format(X*approx(x2),Y*approx(y2))
    if UP:
        gcode += 'M5\n'
        gcode += 'G4 P0.{}\n'.format(PAUSE_end)
    return gcode


def path_to_gcode(p):
    i = 0
    gcode = ""
    cx = 0
    cy = 0
    while i < len(p):
        print(i)
        if p[i] == 'M':
            x, y = float(p[i+1]),float(p[i+2])
            gcode += 'G1 X{} Y{}\n'.format(X*approx(x),Y*approx(y))
            gcode += 'M3 S1000\n'
            gcode += 'G4 P0.{}\n'.format(PAUSE_start)
            cx = float(p[i+1])
            cy = float(p[i+2])
            i+=3
        elif p[i] == 'L':
            x, y = float(p[i][1:]),float(p[i+1])
            gcode += 'G1 X{} Y{}\n'.format(X*approx(x),Y*approx(y))
            cx = float(p[i][1:])
            cy = float(p[i+1])
            i+=2
        elif p[i] == 'Z':
            x, y = float(p[1]),float(p[2])
            gcode += 'G1 X{} Y{}\n'.format(X*approx(x),Y*approx(y))
            cx = float(p[1])
            cy = float(p[2])
            i+=1
        elif p[i] == 'C':
            gcode += draw_object(bezier, [cx,cy,float(p[i+1]),float(p[i+2]),float(p[i+3]),float(p[i+4]), float(p[i+5]), float(p[i+6])], start = 0, end = 1, DOWN = False, UP = False)
            cx, cy = p[i+5],p[i+6]
            i+=7
        else:
            gcode += draw_object(bezier, [cx,cy,float(p[i]),float(p[i+1]),float(p[i+2]),float(p[i+3]), float(p[i+4]), float(p[i+5])], start = 0, end = 1, DOWN = False, UP = False)
            cx, cy = p[i+4],p[i+5]
            i+=6

        # elif p[i][0] == 'Q': # quadratic bezier curve; simulated with the cubic one
        #     x1, y1 = float(p[i][1:]), float(p[i+1])
        #     x, y = float(p[i+2]), float(p[i+3])
        #     gcode += draw_object(bezier, [cx,cy,1/3*(cx+2*x1),1/3*(cy+2*y1),1/3*(x1+2*x), 1/3*(y1+2*y) x,y], start = 0, end = 1, DOWN = False, UP = False)
        #     cx, cy = x, y
        #     i+=4
        # elif p[i][0] == 'A':
        #     rx, ry = float(p[i][1:]), float(p[i+1])
        #     x_axis_rotation = float(p[i+2])
        #     large_arc_flag = float(p[i+3])
        #     sweep_flag  = float(p[i+4])
        #     x, y = float(p[i+5]), float(p[i+6])
    gcode += 'M5\n'
    gcode += 'G4 P0.{}\n'.format(PAUSE_end)
    return gcode

def delete_Z(p):
    if p[-1] == 'z' or p[-1] == 'Z':
        return p[:-1] + ['L{}'.format(p[0][1:])] + [p[1]]
    else:
        return p
    
class SVG_info:

    def __init__(self,doc, output):
        self.circles = [(l.getAttribute('cx'),l.getAttribute('cy'),l.getAttribute('r')) for l in doc.getElementsByTagName('circle')]
        self.ellipses = [(l.getAttribute('cx'),l.getAttribute('cy'),l.getAttribute('rx'),l.getAttribute('ry')) for l in doc.getElementsByTagName('ellipse')]
        self.lines = [(l.getAttribute('x1'),l.getAttribute('y1'),l.getAttribute('x2'),l.getAttribute('y2')) for l in doc.getElementsByTagName('line')]
        self.paths = [(l.getAttribute('d')) for l in doc.getElementsByTagName('path')]
        self.paths_parameterized = []
        self.output = output
        self.clean_it()

    def clean_it(self):
        self.paths = [delete_Z(list(filter(None,re.split('([M|C|L])|,| ',d)))) for d in self.paths]
        
    def merge(self):
        b = True
        L = len(self.paths)
        P = {(index, self.paths[index]) for i in range(len(self.paths))}
        while b:
            b = False
            for d1 in P:
                for d2 in P:
                    if d1 != d2:
                        if distance(*end(P[d1]), *start(P[d2])) < dl2:
                            P[d1] += P.pop(d2)[2:]
                            b = True
                            break
        self.paths = [d for d in P]
                            
            # for i in range(L):
            #     for j in range(L):
            #         if i != j:
            #             if distance(*end(self.paths[i]), *start(self.path[j])):
            #                 self.paths[j]+= self.paths[i][2:]
            #                 self.paths.pop(i)
                                

    def gcode(self):
        f = open(self.output, 'w')
        # Init
        f.write('M5\n') # to get up the printhead
        f.write('G90\n') # Absolute position
        f.write('G21\n') # Unit = millimeters
        f.write('G1 F{}\n'.format(SPEED)) # Speed in millimeter/minute

        for e in self.ellipses:
            f.write(draw_object(ellipse, e))

        for c in self.circles:
            f.write(draw_object(circle, c, UP = False))

        for l in self.lines:
            f.write(draw_object(line,l, UP = False))

        for p in self.paths:
            f.write(path_to_gcode(p))

        # Get back home
        f.write('M5\n') # to get up the printhead
        f.write('G4 P0.{}\n'.format(PAUSE_end))
        f.write('G1 X0 Y0\n') # Get back home
        
        f.close()

S = SVG_info(doc, output)
