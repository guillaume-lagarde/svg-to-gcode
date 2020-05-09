import sys
from xml.dom import minidom
import math

parameters = sys.argv
filename = parameters[1]

doc = minidom.parse(filename)

PI = 3.14159265359

SPEED = 5500
output = 'test.gcode'
PAUSE_end = 400
PAUSE_start = 200

dl_min = 1
dT = 0.01

def distance(x1,y1,x2,y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def circle(C,T):
    cx, cy, r = [float(p) for p in C]
    x = cx+r*math.cos(T*2*PI)
    y = cy+r*math.sin(T*2*PI)
    return (x,y)

def ellipse(E,T):
    cx, cy, rx, ry = [float(p) for p in E]
    x = cx+rx*math.cos(T*2*PI)
    y = cy+ry*math.sin(T*2*PI)
    return (x,y)

# F = parametrization function; I = instance of the object
def draw_object(F, I, start = 0, end = 1, DOWN = True, UP = True):
    T = start
    x, y = F(I,T)
    gcode = 'G1 X{} Y{}\n'.format(x,y)
    if DOWN:
        gcode += 'M3 S1000\n'
        gcode += 'G4 P0.{}\n'.format(PAUSE_start)
    T+=dT
    while T < end:
        x2, y2 = F(I,T)
        if distance(x,y,x2,y2) < dl_min:
            T+=dT
        else:
            gcode += 'G1 X{} Y{}\n'.format(x2,y2)
            T+=dT
            x, y = x2, y2
    x2,y2 = F(I,end)
    gcode += 'G1 X{} Y{}\n'.format(x2,y2)
    if UP:
        gcode += 'M5\n'
        gcode += 'G4 P0.{}\n'.format(PAUSE_end)
    return gcode

# dl = discretisation length
# def circle_to_path(C):
#     cx, cy, r = [float(p) for p in C]
#     r = r
#     sx1 = cx+r
#     sy1 = cy
#     T = 0
#     gcode = 'G1 X{} Y{}\nM3 S1000\nG4 P0.{}\n'.format(sx1,sy1,PAUSE_start)
#     T+=dT
#     while T < 2*PI:
#         sx2 = cx+r*math.cos(T)
#         sy2 = cy+r*math.sin(T)
#         if distance(sx1,sy1,sx2,sy2) < dl_min:
#             T+=dT
#         else:
#             gcode += 'G1 X{} Y{}\n'.format(sx2,sy2)
#             T+=dT
#             sx1, sy1 = sx2, sy2

#     sx2 = cx+r*math.cos(2*PI)
#     sy2 = cy+r*math.sin(2*PI)
#     gcode += 'G1 X{} Y{}\n'.format(sx2,sy2)
#     gcode += 'M5\n'
#     gcode += 'G4 P0.{}\n'.format(PAUSE_end)
#     return gcode

# def ellipse_to_path(E):
#     cx, cy, rx, ry = [float(p) for p in E]
#     rx= rx
#     ry = ry
#     sx1 = cx+rx
#     sy1 = cy
#     T = 0
#     gcode = 'G1 X{} Y{}\nM3 S1000\nG4 P0.{}\n'.format(sx1,sy1,PAUSE_start)
#     T+=dT
#     while T< 2*PI:
#         sx2 = cx+rx*math.cos(T)
#         sy2 = cy+ry*math.sin(T)
#         if distance(sx1,sy1,sx2,sy2) < dl_min:
#             T+=dT
#         else:
#             gcode += 'G1 X{} Y{}\n'.format(sx2,sy2)
#             T+=dT
#             sx1, sy1 = sx2, sy2

#     sx2 = cx+rx*math.cos(2*PI)
#     sy2 = cy+ry*math.sin(2*PI)
#     gcode += 'G1 X{} Y{}\n'.format(sx2,sy2)
#     gcode += 'M5\n'
#     gcode += 'G4 P0.{}\n'.format(PAUSE_end)
#     return gcode


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
    
# def line_to_path(line):
#     sx1, sy1, sx2, sy2 = line
#     gcode = 'G1 X{} Y{}\nM3 S1000\nG4 P0.{}\n'.format(sx1,sy1,PAUSE_start)
#     gcode += 'G1 X{} Y{}\n'.format(sx2,sy2)
#     gcode += 'M5\n'
#     gcode += 'G4 P0.{}\n'.format(PAUSE_end)
#     return gcode


def path_to_gcode(d):
    p = d.split()
    i = 0
    gcode = ""
    cx = 0
    cy = 0
    while i < len(p):
        print(i)
        if p[i][0] == 'M':
            gcode += 'G1 X{} Y{}\n'.format(p[i][1:],p[i+1])
            gcode += 'M3 S1000\n'
            gcode += 'G4 P0.{}\n'.format(PAUSE_start)
            cx = float(p[i][1:])
            cy = float(p[i+1])
            i+=2
        elif p[i][0] == 'L':
            gcode += 'G1 X{} Y{}\n'.format(p[i][1:],p[i+1])
            cx = float(p[i][1:])
            cy = float(p[i+1])
            i+=2
        elif p[i][0] == 'Z':
            gcode += 'G1 X{} Y{}\n'.format(p[0][1:],p[1])
            cx = float(p[0][1:])
            cy = float(p[1])
            i+=1
        elif p[i][0] == 'C':            
            gcode += draw_object(bezier, [cx,cy,float(p[i][1:]),float(p[i+1]),float(p[i+2]),float(p[i+3]), float(p[i+4]), float(p[i+5])], start = 0, end = 1, DOWN = False, UP = False)
            cx, cy = p[i+4],p[i+5]
            i+=6

    gcode += 'M5\n'
    gcode += 'G4 P0.{}\n'.format(PAUSE_end)
    return gcode

class SVG_info:

    def __init__(self,doc, output):
        self.circles = [(l.getAttribute('cx'),l.getAttribute('cy'),l.getAttribute('r')) for l in doc.getElementsByTagName('circle')]
        self.ellipses = [(l.getAttribute('cx'),l.getAttribute('cy'),l.getAttribute('rx'),l.getAttribute('ry')) for l in doc.getElementsByTagName('ellipse')]
        self.lines = [(l.getAttribute('x1'),l.getAttribute('y1'),l.getAttribute('x2'),l.getAttribute('y2')) for l in doc.getElementsByTagName('line')]
        self.paths = [(l.getAttribute('d')) for l in doc.getElementsByTagName('path')]
        self.paths_parameterized = []
        self.output = output

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
