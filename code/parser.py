import sys
from xml.dom import minidom
import math
import re

parameters = sys.argv
filename = parameters[1]
output = parameters[2]


#-------------------------------
# Set of parameters
SPEED = 3000 # Speed in millimeters/minute
PAUSE_start = 200 # Pause in milliseconds after putting down the printhead
PAUSE_end = 400 # Pause in milliseconds after pulling up the printhead
dl_min = 1 # Discretization: ~size min of each step in millimeters; the smaller the more accurate
dl_max = 2 # Discretization: ~size max of each step in millimeters; the smaller the more accurate
sensitivity = 0.4 # 
dT_min = 0.001 # Discretization: "delta T minimum"
accuracy = 2 # Discretization: everything is approximated at 2 decimals
X = 1 #normal x-axis; -1 to reverse axis
Y = 1 #normal y-axis; -1 to reverse axis
#-------------------------------

doc = minidom.parse(filename)

PI = 3.14159265359

def distance(x1,y1,x2,y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def approx(f):
    return round(f,accuracy)
    # return int(f/accuracy)*accuracy

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

# Cubic Bezier
def bezier(b, T):
    sx, sy, x1, y1, x2, y2, ex, ey = [float(p) for p in b]
    xt = sx *(1-T)**3 + 3* x1*T*(1-T)**2 + 3*x2*T**2*(1-T) + ex*T**3
    yt = sy *(1-T)**3 + 3* y1*T*(1-T)**2 + 3*y2*T**2*(1-T) + ey*T**3    
    return (xt,yt)
    
def line(l, T):
    x1, y1, x2, y2 = [float(p) for p in l]
    if T < 1:
        return (x1, y2)
    else:
        return (x2,y2)

#-------------------------------

# F = parameterization function, I = parameters of the object,
# current_position is the position of the printhead at T < 0, If DOWN
# = True, it means the printhead is up before drawing this new object;
# if UP = True, we ask the printhead to go up after printing the object
# Output gcode + new current position of the printhead
def draw_object(F, I, currentx, currenty, DOWN = True, UP = True):
    T = 0
    cx, cy = currentx, currenty
    x, y = F(I,T)
    dT = dT_min
    gcode = ""
    if DOWN:
        gcode += 'G1 X{} Y{}\n'.format(x,y)
        gcode += 'M3 S1000\n'
        gcode += 'G4 P0.{}\n'.format(PAUSE_start)

    while T < 1:
        if distance(cx,cy, x, y) > dl_min:
            cx, cy = approx(x), approx(y)
            gcode += 'G1 X{} Y{}\n'.format(cx,cy)
        T+=dT
        x, y = F(I,T)
    T = 1
    x, y = F(I,T)
    if distance(cx,cy,x,y) > sensitivity:
        cx, cy = approx(x), approx(y)
        gcode += 'G1 X{} Y{}\n'.format(cx, cy)
    if UP:
        gcode += 'M5\n'
        gcode += 'G4 P0.{}\n'.format(PAUSE_end)
    return gcode, cx, cy



# transform a point x,y with the given transformation
# matrix, translate, scale, rotate, skewX, skewY, 
def transform(x,y, transformations):
    rx = x
    ry = y
    list_T = list((filter(lambda x: x!='',re.split(' ', transformations)))) # list of each transformation
    for T in list_T:
        T_split = list(filter(lambda x: x!='',re.split('\(|,|\)',T))) # expand as a list of parameters
        name = T_split[0]
        if name == "matrix":
            a,b,c,d,e,f = [float(g) for g in T_split[1:]]
            x_temp = a*rx+c*ry+e
            y_temp = b*rx+d*ry+f
            rx, ry = x_temp, y_temp
            
        elif name == "translate":
            xshift = float(T_split[1])
            if len(T_split) <= 2:
                yshift = 0
            else:
                yshift = float(T_split[2])
            rx += xshift
            ry += yshift
            
        elif name == "rotate":
            angle = float(T_split[1])*2*PI/360 # degree to radian
            centerx,centery = 0,0
            if len(T_split) >= 3:
                centerx, centery = float(T_split[2]), float(T_split[3])
            X = rx - centerx
            Y = ry-centery
            rx, ry = centerx + X*math.cos(angle) - Y*math.sin(angle), centery + X*math.sin(angle) + Y*math.cos(angle)
            
            
        elif name == "scale":
            xscale = float(T_split[1])
            if len(T_split) <= 2:
                yscale = xscale
            else:
                yscale = float(T_split[2])
            rx*=xscale
            ry*=yscale
            
        elif name == "skewX":
            print("not yet implemented")
            
        elif name == "skewY":
            print("not yet implemented")
            
    return approx(rx),approx(ry)

def path_to_gcode(p, transformation = ""):
    i = 0
    gcode = ""
    cx = 0
    cy = 0
    while i < len(p):
        # Move
        if p[i] == 'M':
            cx, cy = transform(float(p[i+1]),float(p[i+2]),transformation)
            gcode += 'G1 X{} Y{}\n'.format(cx,cy)
            gcode += 'M3 S1000\n'
            gcode += 'G4 P0.{}\n'.format(PAUSE_start)
            i+=3
            
        # Line
        elif p[i] == 'L':
            cx, cy = transform(float(p[i+1]),float(p[i+2]), transformation)
            gcode += 'G1 X{} Y{}\n'.format(cx, cy)
            i+=3
            
        # Goto initial point 
        elif p[i] == 'Z':
            cx, cy = transform(float(p[1]),float(p[2]),transformation)
            gcode += 'G1 X{} Y{}\n'.format(X*approx(x),Y*approx(y))
            i+=1

        # Cubic Bezier
        elif p[i] == 'C':
            P1x, P1y = transform(float(p[i-2]), float(p[i-1]), transformation)
            P2x, P2y = transform(float(p[i+1]), float(p[i+2]), transformation)
            P3x, P3y = transform(float(p[i+3]), float(p[i+4]), transformation)
            P4x, P4y = transform(float(p[i+5]), float(p[i+6]), transformation)
            code, cx, cy = draw_object(bezier, [P1x, P1y, P2x, P2y, P3x, P3y, P4x, P4y], cx, cy, DOWN = False, UP = False)
            gcode+=code
            i+=7

        else:
            P1x, P1y = transform(float(p[i-2]), float(p[i-1]), transformation)
            P2x, P2y = transform(float(p[i]), float(p[i+1]), transformation)
            P3x, P3y = transform(float(p[i+2]), float(p[i+3]), transformation)
            P4x, P4y = transform(float(p[i+4]), float(p[i+5]), transformation)
            code, cx, cy = draw_object(bezier, [P1x, P1y, P2x, P2y, P3x, P3y, P4x, P4y], cx, cy, DOWN = False, UP = False)
            gcode+=code
            i+=6


    gcode += 'M5\n'
    gcode += 'G4 P0.{}\n'.format(PAUSE_end)
    return gcode
            

# # F = parametrization function; I = instance of the object
# def draw_object(F, I, start = 0, end = 1, DOWN = True, UP = True):
#     T = start
#     x, y = F(I,T)
#     gcode = ""
#     # gcode = 'G1 X{} Y{}\n'.format(x,Y*y)
#     if DOWN:
#         gcode += 'M3 S1000\n'
#         gcode += 'G4 P0.{}\n'.format(PAUSE_start)
#     T+=dT
#     while T < end:
#         x2, y2 = F(I,T)
#         if distance(x,y,x2,y2) < dl_min:
#             T+=dT
#         else:
#             gcode += 'G1 X{} Y{}\n'.format(X*approx(x2),Y*approx(y2))
#             T+=dT
#             x, y = x2, y2
#     x2,y2 = F(I,end)
#     if distance(x,y,x2,y2) > dl2:
#         gcode += 'G1 X{} Y{}\n'.format(X*approx(x2),Y*approx(y2))
#     if UP:
#         gcode += 'M5\n'
#         gcode += 'G4 P0.{}\n'.format(PAUSE_end)
#     return gcode, x,y


# def path_to_gcode(p):
#     i = 0
#     gcode = ""
#     cx = 0
#     cy = 0
#     while i < len(p):
#         if p[i] == 'M':
#             x, y = float(p[i+1]),float(p[i+2])
#             gcode += 'G1 X{} Y{}\n'.format(X*approx(x),Y*approx(y))
#             gcode += 'M3 S1000\n'
#             gcode += 'G4 P0.{}\n'.format(PAUSE_start)
#             cx = float(p[i+1])
#             cy = float(p[i+2])
#             i+=3
#         elif p[i] == 'L':
#             x, y = float(p[i][1:]),float(p[i+1])
#             gcode += 'G1 X{} Y{}\n'.format(X*approx(x),Y*approx(y))
#             cx = float(p[i][1:])
#             cy = float(p[i+1])
#             i+=2
#         elif p[i] == 'Z':
#             x, y = float(p[1]),float(p[2])
#             gcode += 'G1 X{} Y{}\n'.format(X*approx(x),Y*approx(y))
#             cx = float(p[1])
#             cy = float(p[2])
#             i+=1
#         elif p[i] == 'C':
#             code, x, y = draw_object(bezier, [cx,cy,float(p[i+1]),float(p[i+2]),float(p[i+3]),float(p[i+4]), float(p[i+5]), float(p[i+6])], start = 0, end = 1, DOWN = False, UP = False)
#             gcode+=code
#             cx = approx(x)
#             cy = approx(y)
#             i+=7
            # OLD VERSION
            # gcode += draw_object(bezier, [cx,cy,float(p[i+1]),float(p[i+2]),float(p[i+3]),float(p[i+4]), float(p[i+5]), float(p[i+6])], start = 0, end = 1, DOWN = False, UP = False)
            # cx, cy = p[i+5],p[i+6]
            # END OLD VERSION
            
        # else:
        #     gcode += draw_object(bezier, [cx,cy,float(p[i]),float(p[i+1]),float(p[i+2]),float(p[i+3]), float(p[i+4]), float(p[i+5])], start = 0, end = 1, DOWN = False, UP = False)
        #     cx, cy = p[i+4],p[i+5]
        #     i+=6

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
    # gcode += 'M5\n'
    # gcode += 'G4 P0.{}\n'.format(PAUSE_end)
    # return gcode

def delete_Z(p):
    if p[-1] == 'z' or p[-1] == 'Z':
        return p[:-1] + ['L{}'.format(p[0][1:])] + [p[1]]
    else:
        return p



def get_transform(e):
    res = ""
    root = e
    while root != doc:
        res = res + " " + root.getAttribute('transform')
        root = root.parentNode
    return res

class SVG_info:

    def __init__(self,doc, output):
        self.circles = [(l.getAttribute('cx'),l.getAttribute('cy'),l.getAttribute('r'),get_transform(l)) for l in doc.getElementsByTagName('circle')]
        self.ellipses = [(l.getAttribute('cx'),l.getAttribute('cy'),l.getAttribute('rx'),l.getAttribute('ry'),get_transform(l)) for l in doc.getElementsByTagName('ellipse')]
        self.lines = [(l.getAttribute('x1'),l.getAttribute('y1'),l.getAttribute('x2'),l.getAttribute('y2'), get_transform(l)) for l in doc.getElementsByTagName('line')]
        self.paths = [(l.getAttribute('d'), get_transform(l)) for l in doc.getElementsByTagName('path')]
        self.paths_parameterized = []
        self.output = output
        self.clean_it()

    def clean_it(self):
        self.paths = [(delete_Z(list(filter(None,re.split('([M|C|L])|,| ',d)))),t) for (d,t) in self.paths]
        
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

        # for e in self.ellipses:
        #     f.write(draw_object(ellipse, e)[0])

        # for c in self.circles:
        #     f.write(draw_object(circle, c, UP = False)[0])

        # for l in self.lines:
        #     f.write(draw_object(line,l, UP = False)[0])

        i = 1
        L = len(self.paths)
        for d,l in self.paths:
            print("path {} over {}".format(i, L))
            i+=1
            f.write(path_to_gcode(d,l))

        # Get back home
        f.write('M5\n') # to get up the printhead
        f.write('G4 P0.{}\n'.format(PAUSE_end))
        f.write('G1 X0 Y0\n') # Get back home
        
        f.close()

S = SVG_info(doc, output)

