# svg-to-gcode

Welcome!

This is a v0.0000001 of a simple tool to transform .svg into .gcode, especially designed for pen plotters.
The DOWN (resp. UP) command is set up to be "M3 S1000" (resp. "M5").

Basic use:

`python3 svg_to_gcode.py namefile.svg`

creates a file `namefile.gcode` that contains the corresponding gcode for the svg.

Several parameters can be added to tune the plot more carefully. For example you can type:

`python3 svg_to_gcode.py namefile.svg speed=4500 output=awesome.gcode`

creates a gcode file named `awesome.gcode` with a plotting speed of 4500 millimeters/minute.

Here is a small list of parameters that can be changed (they all should come after `namefile.svg`):

- `speed`: speed in millimeters/minute (3000 by default)
- `output`: output filename (same as input by default)
- `pause_start`: pause in milliseconds after putting down the printhead (200 by default)
- `pause_end`: pause in milliseconds after pulling up the printhead (400 by default)
- `dl_min`: size min of each small step, in millimeters (0.2 by default)
- `dl_max` size max of each small step, in millimeters (0.7 by default)
- `accuracy`: number of decimals (1 if not specified)
- `verbose`: shoud be True or False. Give some information during the conversion (True by default)

Features implemented:
- nested transformation: everything should work except skewX and skewY (soon to come),
- paths with lines, moveto, cubic Bézier (elliptical arcs and quadratic Bézier soon to come)

If you want to use ellipse, circles or lines, it should work if you don't use any transform on them (but you need to uncomment lines 366 -> 373). I will fix it soon to handle them in full generality.

TODO list (probably soon to come, when I find some free time):
- skewX, skewY
- elliptical arc
- quadratic Bézier
- paths optimization
- etc.