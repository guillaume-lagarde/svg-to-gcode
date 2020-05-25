import sys
from xml.dom import minidom
import math
import re

parameters = sys.argv

#-------------------------------
# Set of parameters by default
filename = parameters[1]
output = filename.split(".")[0] + ".gcode"
speed = 3000 # Speed in millimeters/minute
pause_start = 200 # Pause in milliseconds after putting down the printhead
pause_end = 400 # Pause in milliseconds after pulling up the printhead
dl_min = 0.5 # Discretization: ~size min of each step in millimeters; the smaller the more accurate
dl_max = 0.9 # Discretization: ~size max of each step in millimeters; the smaller the more accurate
sensitivity = 0.4 # 
dT_min = 0.00001 # Discretization: "delta T minimum"
accuracy = 1 # Discretization: number of decimals (by default everything approximated within 1 decimal)
X = 1 #normal x-axis; -1 to reverse axis
Y = 1 #normal y-axis; -1 to reverse axis
verbose = True
#-------------------------------

# Take into account user's parameters
for p in parameters[2:]:
    name, arg = p.split("=")
    if name == "output":
        vars()[name] = arg
    elif name == "verbose":
        vars()[name] = (lambda x: True if x == "True" else False)(arg)
    else:
        vars()[name] = float(arg)


        
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
        gcode += 'G4 P0.{}\n'.format(pause_start)

    while T < 1:
        if distance(cx,cy, x, y) > dl_min:
            if distance(cx,cy,x,y) < dl_max or dT == 0:
                cx, cy = approx(x), approx(y)
                gcode += 'G1 X{} Y{}\n'.format(cx,cy)
                if dT == 0:
                    dT = dT_min
            else: # we went to far so decrease the step
                T -=dT/2
                dT = dT/4 # next time we increment from previous point by half the step we have made
        T+=dT
        dT*=2
        x, y = F(I,T)
    T = 1
    x, y = F(I,T)
    if distance(cx,cy,x,y) > sensitivity:
        cx, cy = approx(x), approx(y)
        gcode += 'G1 X{} Y{}\n'.format(cx, cy)
    if UP:
        gcode += 'M5\n'
        gcode += 'G4 P0.{}\n'.format(pause_end)
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
            print("SkewX not implemented yet")
            
        elif name == "skewY":
            print("SkewY not implemented yet")
            
    return approx(rx),approx(ry)

def path_to_gcode(p, transformation = ""):
    i = 0
    gcode = ""
    cx, cy = 0, 0 # where the printhead is (with the approx)
    rx, ry = 0, 0 # exact theoretic position (without approx), useful when relative positions to avoid propagating errors
    
    while i < len(p):
        # Move
        if p[i] == 'M':
            cx, cy = transform(float(p[i+1]),float(p[i+2]),transformation)
            gcode += 'G1 X{} Y{}\n'.format(cx,cy)
            gcode += 'M3 S1000\n'
            gcode += 'G4 P0.{}\n'.format(pause_start)
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
    gcode += 'G4 P0.{}\n'.format(pause_end)
    return gcode

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

def relative_to_absolute(d):
    cx,cy = 0,0
    cs = ""
    i = 0
    res = []
    while i < len(d):
        ISF = isfloat(d[i])
        if d[i] == "M" or (ISF and cs == "M"):
            cs = "M"
            if ISF:
                i-=1
            cx, cy = float(d[i+1]),float(d[i+2])
            res+= ["M", str(cx), str(cy)]
            i+=3
        elif d[i] == "m" or (ISF and cs == "m"):
            cs = "M"
            if ISF:
                i-=1
            cx += float(d[i+1])
            cy += float(d[i+2])
            res+= ["M", str(cx), str(cy)]
            i+=3

        elif d[i] == "L" or (ISF and cs == "L"):
            cs = "L"
            if ISF:
                i-=1
            cx, cy = float(d[i+1]),float(d[i+2])
            res+= ["L", str(cx), str(cy)]
            i+=3
            
        elif d[i] == "l" or (ISF and cs == "l"):
            cs = "l"
            if ISF:
                i-=1
            cx += float(d[i+1])
            cy += float(d[i+2])
            res+= ["L", str(cx), str(cy)]
            i+=3

        elif d[i] == "H" or (ISF and cs == "H"):
            cs = "H"
            if ISF:
                i-=1
            cx = float(d[i+1])
            res+= ["L", str(cx), str(cy)]
            i+=2

        elif d[i] == "h" or (ISF and cs == "h"):
            cs = "h"
            if ISF:
                i-=1
            cx += float(d[i+1])
            res+= ["L", str(cx), str(cy)]
            i+=2

        elif d[i] == "V" or (ISF and cs == "V"):
            cs = "V"
            if ISF:
                i-=1
            cy = float(d[i+1])
            res+= ["L", str(cx), str(cy)]
            i+=2

        elif d[i] == "v" or (ISF and cs == "v"):
            cs = "v"
            if ISF:
                i-=1
            cy += float(d[i+1])
            res+= ["L", str(cx), str(cy)]
            i+=2

        elif d[i] == "C" or (ISF and cs == "C"):
            # print(d[i:i+7])
            cs = "C"
            if ISF:
                i-=1
            res+= ["C"] + d[i+1:i+7]
            # print(res)
            cx,cy = float(res[-2]), float(res[-1])
            i+=7

        elif d[i] == "c" or (ISF and cs == "c"):
            cs = "c"
            if ISF:
                i-=1
            # print(d[i:i+7])
            XS = [str(cx + float(d[i+j])) for j in [1,3,5]]
            YS = [str(cy + float(d[i+j])) for j in [2,4,6]]
            res+= ["C",XS[0],YS[0],XS[1],YS[1],XS[2],YS[2]]
            # print(res)
            cx,cy = float(res[-2]), float(res[-1])            
            i+=7
    return res

def delete_Z(p):
    if p[-1] == 'z' or p[-1] == 'Z':
        return p[:-1] + ['L{}'.format(p[0][1:])] + [p[1]]
    else:
        return p



def get_transform(e):
    res = ""
    root = e
    while root != doc:
        add = reversed(root.getAttribute('transform').split())
        for t in add:
            res = res + " " + t
            # res = t + " " + res
        # res = root.getAttribute('transform') + " " + res
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
        self.paths = [(relative_to_absolute(delete_Z(list(filter(None,re.split('([M|C|L|H|V|m|c|l|h|v])|,| ',d))))),t) for (d,t) in self.paths]                                

    def gcode(self):
        f = open(self.output, 'w')
        # Init
        f.write('M5\n') # to get up the printhead
        f.write('G90\n') # Absolute position
        f.write('G21\n') # Unit = millimeters
        f.write('G1 F{}\n'.format(speed)) # Speed in millimeter/minute

        # for e in self.ellipses:
        #     f.write(draw_object(ellipse, e)[0])

        # for c in self.circles:
        #     f.write(draw_object(circle, c, UP = False)[0])

        # for l in self.lines:
        #     f.write(draw_object(line,l, UP = False)[0])

        i = 1
        L = len(self.paths)
        for d,l in self.paths:
            if verbose:
                print("Computing path {} over {}".format(i, L))
            i+=1
            f.write(path_to_gcode(d,l))
            if verbose:
                print("--> DONE")

        # Get back home
        f.write('M5\n') # to get up the printhead
        f.write('G4 P0.{}\n'.format(pause_end))
        f.write('G1 X0 Y0\n') # Get back home
        
        f.close()

S = SVG_info(doc, output)
S.gcode()
