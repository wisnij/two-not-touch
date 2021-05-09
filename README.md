A simple image parser for [Two Not Touch](https://krazydad.com/twonottouch/)
puzzle boards.  Outputs the boards' structure as a matrix of ints representing
which bold-bordered regions each cell falls into.

**Not** a puzzle solver, just an easier way to import the puzzle structure into
a spreadsheet or text file for human editing.

Example usage and output:

    $ ./parse-two-not-touch.py examples/double-1.png
    found 2 puzzles

    Puzzle #1:
    found 10 regions
    found 100 grid cells

    0,0,0,0,1,1,2,2,2,2
    0,0,0,0,1,1,2,2,2,2
    0,3,3,0,1,2,2,2,2,4
    0,3,0,0,1,2,2,2,2,4
    5,3,3,0,6,6,2,2,2,4
    5,5,5,5,6,6,7,2,8,4
    5,9,9,9,6,7,7,7,8,4
    5,9,6,6,6,6,6,7,8,8
    5,7,7,7,7,7,7,7,8,8
    7,7,7,7,7,7,7,7,8,8

    Puzzle #2:
    found 10 regions
    found 100 grid cells

    0,0,0,1,1,1,1,2,2,2
    0,0,1,1,1,1,1,2,2,2
    3,0,1,1,1,1,1,2,2,2
    3,3,3,3,3,4,4,2,2,2
    3,5,5,5,3,3,4,4,2,2
    6,6,5,5,5,5,4,4,4,2
    6,6,6,6,6,6,7,7,7,2
    6,6,6,6,7,7,7,8,8,8
    6,6,6,7,7,7,9,8,8,8
    6,6,6,6,6,6,9,9,9,9
