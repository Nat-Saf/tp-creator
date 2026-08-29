# position_format - own-words syntax notes

## .LS program file - section skeleton
A TP program saved as ASCII (.LS) has fixed blocks in this order:
/PROG <name>, /ATTR, optional /APPL, /MN (the numbered instruction
lines), /POS (the P[n] records taught in this program), /END.
Constraints: program name 1-36 chars, must start with a letter, only
A-Z 0-9 and _ (no space, @ or *); /POS may be empty when the program
only moves through PR[] registers or has no motion at all.
Example:
    /PROG  PICK_ONE
    /MN
       1:  L P[1] 100mm/sec FINE    ;
    /POS
    /END
Manual: HandlingTool V9.40 sec 12.2.7

## /ATTR - program header attributes
Key = value lines ending in ';' that mirror the pendant DETAIL screen:
OWNER, COMMENT ("..." up to 16 chars), PROG_SIZE, CREATE and MODIFIED
(DATE yy-mm-dd TIME hh:mm:ss), FILE_NAME, VERSION, LINE_COUNT,
MEMORY_SIZE, PROTECT = READ_WRITE (write-protect off), a TCD: task
block (STACK_SIZE, TASK_PRIORITY, ...), DEFAULT_GROUP, CONTROL_CODE.
Constraints: DEFAULT_GROUP is the group mask - one slot per motion
group, digit = group used, * = unused; a one-robot cell is 1,*,*,*,*.
The mask cannot change once motion instructions exist in the program.
Example:
    COMMENT         = "Pick PBS";
    DEFAULT_GROUP   = 1,*,*,*,*;
Manual: HandlingTool V9.40 sec 8.5.1

## /MN - motion line anatomy
Each body line is <lineno>:  <instruction> ; - a motion line stacks
five parts in order: motion type (J/L/C/A/S), position P[i] or PR[i],
speed with unit, termination (FINE or CNT0-100), then motion options.
Constraints: every line ends with ' ;'. Remark lines start with '!'
and take a line number like any instruction. The @ sometimes shown
before P[] on the pendant only means "robot is near this point" - it
is a display flag, not part of the program.
Example:
    1:  L P[1] 100mm/sec FINE    ;
    2:  J P[2:SafeAbove] 50% CNT100    ;
    3:  !approach done    ;
Manual: HandlingTool V9.40 sec 7.2.1

## P[i] and P[i:comment] - position references
P[n] keeps its data inside this program's own /POS block; PR[x] points
into the shared position-register bank and never appears under /POS.
Numbers are handed out in teaching order (first taught point = P[1])
and are kept after deletes until you ask for a renumber. A label of
1-16 chars can be attached to a position: it shows up in the /MN
reference as P[2:SafeAbove], while the /POS record below stays keyed
by the bare number.
Example:
    95:  L P[2:SafeAbove] R[63:TravelSpd]mm/sec CNT100    ;
Manual: HandlingTool V9.40 sec 7.2.6

## /POS Cartesian record - GP1 xyzwpr
Record shape: P[n]{ GP1: <UF/UT>, <CONFIG>, X Y Z, W P R };. X, Y, Z
locate the TCP in mm inside user frame UF; W, P, R are rotations about
X, Y, Z in deg. GP1: is the motion group 1 block - multi-group
programs add GP2: etc., and extended axes append E1-E3 fields.
Example:
    P[1]{
       GP1:
        UF : 1, UT : 3,         CONFIG : 'F U T, 0, 0, 0',
        X =   259.576  mm,      Y =   562.568  mm,      Z =  -319.240  mm,
        W =     -.003 deg,      P =    -1.495 deg,      R =      .000 deg
    };
Manual: HandlingTool V9.40 sec 7.2.6

## UF / UT - frame numbers stored per position
Every taught P[n] pins the frames it was recorded in. UF: 0 = world
frame, 1-10 = that UFRAME number, F = follow the current $MNUFRAMENUM.
UT: 0 = not valid, 1-10 = that UTOOL number, F = follow the current
$MNUTOOLNUM. Position registers always carry F for both. Stepping FWD
or BWD across a line where the frame number changes is governed by
$FRM_CHKTYP (default posts a bookkeeping error on mismatch).
Example:
    UF : 0, UT : 1,         CONFIG : 'N U T, 0, 0, 0',
Manual: HandlingTool V9.40 sec 7.2.9

## CONFIG - arm posture string
Format: '<placement letters>, t, t, t'. The letters pick which of the
possible arm postures reaches the point: F/N = wrist flip or no-flip,
U/D = arm up or down, T/B = arm front or back (SCARA types insert an
extra L/R letter). The three trailing integers are turn numbers for
the wrist axes (mapping per $SCR_GRP[grp].$TURN_AXIS, normally J4 J5
J6): 0 = -179..179 deg, 1 = 180..539 deg, -1 = -539..-180 deg. F3
CONFIG on the Position Detail screen toggles F and N.
Example:
    CONFIG : 'N U T, 0, 0, 0',
Manual: HandlingTool V9.40 sec 11.21.2

## /POS joint record - J1..J6 degrees
A point can be stored in joint representation instead of Cartesian:
one angle per robot axis in deg (J1-J6, plus E1-E3 when extended axes
exist), and no CONFIG string - the angles already fix the posture.
F5 [REPRE] on the Position Detail screen converts a point between the
two forms using the frames active at that moment. Joint form is the
right choice for zero-position moves and positioner-table axes.
Example:
    P[3]{
       GP1:
        UF : 1, UT : 3,
        J1 =    90.000 deg,     J2 =    10.500 deg,     J3 =   -35.250 deg,
        J4 =      .000 deg,     J5 =   -60.000 deg,     J6 =   180.000 deg
    };
Manual: HandlingTool V9.40 sec 11.9
