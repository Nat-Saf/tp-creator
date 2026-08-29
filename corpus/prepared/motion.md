# motion - own-words syntax notes

## J - joint motion
Syntax: J <P[i]|PR[i]> <speed>% <FINE|CNTn> [options] ;
Units: % (1-100 of max joint speed) or sec (0.1-3200); a register can supply
the value, e.g. R[1]%. Never mm/sec - distance units belong to L/C/A.
Constraints: all axes start and stop together; the slowest axis sets the real
pace. Taught at the destination point only.
Example:
    J P[1:home] 50% FINE ;
    J PR[3:perch] R[7]% CNT100 ;
Manual: HandlingTool V9.40 sec 7.2.2

## L - linear motion
Syntax: L <P[i]|PR[i]> <speed><unit> <FINE|CNTn> [options] ;
Units: mm/sec (1-2000), cm/min (1-12000), inch/min (0.1-4724.41), sec
(0.1-3200), deg/sec (1-500, for rotating about the TCP in place). NOT %.
Constraints: TCP travels a straight line to the destination; tool orientation
blends gradually along the way. Taught at the destination point.
Example:
    L PR[5:conveyor pick] 100mm/sec CNT50 Offset,PR[2] ;
    L P[8] 90deg/sec FINE ;
Manual: HandlingTool V9.40 sec 7.2.2

## C - circular motion
Syntax: C <P[i]> <P[j]> <speed><unit> <FINE|CNTn> [options] ;
Units: same distance/time units as L (mm/sec, cm/min, inch/min, sec); NOT %.
Constraints: one instruction carries TWO points - the first is the via
(intermediate) point, the second is the destination; the arc runs from the
current position through the via point. The line is taught at the via point
and the destination is recorded afterward with TOUCHUP. A full circle needs
two C instructions. Orientation is blended smoothly through the via point.
Example:
    C P[2] P[3:end of arc] 150mm/sec FINE ;
Manual: HandlingTool V9.40 sec 7.2.2

## A - circular arc type A motion
Syntax: A <P[i]|PR[i]> <speed><unit> <FINE|CNTn> [options] ;
Units: same as L (mm/sec, cm/min, inch/min, sec); NOT %.
Constraints: one point per line; teach at least three consecutive A lines so
the controller can fit a circle. The first A line moves linearly to the arc
start; each later one arcs through the neighboring taught points. Points can
be inserted or deleted without re-teaching pairs. Not allowed: PAL_*[ ]
positions, indirect PR index (PR[R[n]]), INC, Skip. Allowed options include
ACC, Wjnt, PTH, Offset,PR[ ], Tool_Offset,PR[ ], TB/TA.
Example:
    A P[2] 200mm/sec CNT100 ;
Manual: HandlingTool V9.40 sec 7.2.4

## Speed units by motion type
Syntax: <value><unit> right after the position, e.g. 50%, 100mm/sec, 2.0sec
Units: J takes % (1-100) or sec (0.1-3200). L/C/A take mm/sec (1-2000),
cm/min (1-12000), inch/min (0.1-4724.41), sec (0.1-3200), or deg/sec
(1-500) for pure rotation about the TCP.
Constraints: a register may replace the number (R[i]% / R[i]mm/sec); an
out-of-range register value faults at run time. Switching a line from L to J
resets the speed to a % default - recheck it. Pendant override scales the
programmed value from 0.01% to 100%, never above it.
Example:
    L P[4] R[10]mm/sec CNT30 ;
Manual: HandlingTool V9.40 sec 7.2.11

## FINE - fine termination type
Syntax: <motion> <speed><unit> FINE [options] ;
Constraints: the robot fully stops at the taught point before the next line
runs. Use for pick/place points, process start points, and anywhere path
accuracy at the point itself matters more than cycle time.
Example:
    L P[6:place] 50mm/sec FINE ;
Manual: HandlingTool V9.40 sec 7.2.12

## CNT - continuous termination type
Syntax: <motion> <speed><unit> CNTn [options] ;  with n = 0-100
Constraints: the robot decelerates near the taught point but rounds the
corner toward the next point without stopping. CNT0 passes closest to the
point (most deceleration); CNT100 cuts the corner widest (least
deceleration). Some following instructions (e.g. WAIT) still force a stop at
the point before they execute.
Example:
    J P[2] 80% CNT100 ;
    L P[3:approach] 200mm/sec CNT25 ;
Manual: HandlingTool V9.40 sec 7.2.12

## ACC - acceleration override option
Syntax: <motion> <speed><unit> <FINE|CNTn> ACC<value> ;
Constraints: value is a percentage of normal acceleration/deceleration,
documented range 20-100; ACC50 stretches accel/decel to twice as long.
Values above 100 make the move more aggressive but risk vibration, servo
alarms, and false Collision Guard trips - avoid them. Applied at the
destination line it is written on.
Example:
    L P[7:fragile part] 100mm/sec FINE ACC40 ;
Manual: HandlingTool V9.40 sec 7.3.1

## Wjnt - wrist joint option
Syntax: <L|C> <position> <speed><unit> <FINE|CNTn> Wjnt ;
Constraints: linear and circular moves only. The three wrist axes are
joint-interpolated while the major axes keep the TCP on the straight/arc
path, so the wrist does not flip at singularities. Start and end orientation
are honored, but orientation mid-move is not predictable (it is repeatable).
Major-axis behavior can differ a lot from the same move without Wjnt.
Example:
    L P[9] 250mm/sec CNT50 Wjnt ;
Manual: HandlingTool V9.40 sec 7.3.22

## Offset,PR[i] - direct position offset option
Syntax: <motion> <position> <speed><unit> <FINE|CNTn> Offset,PR[i] ;
Constraints: shifts only this line's destination by the contents of PR[i],
in the currently selected user frame. A Cartesian PR is added element by
element (position converted to Cartesian first); a JOINT PR is added
joint by joint and no user frame applies. Combined with INC, the position
and the PR must share the same representation. The bare form "Offset"
(no PR) instead uses the PR named by a prior OFFSET CONDITION PR[x]
instruction and applies wherever it appears (sec 7.3.12).
Example:
    L P[1:pick] 100mm/sec FINE Offset,PR[2:pallet shift] ;
Manual: HandlingTool V9.40 sec 7.3.13

## Tool_Offset,PR[i] - direct tool offset option
Syntax: <motion> <position> <speed><unit> <FINE|CNTn> Tool_Offset,PR[i] ;
Constraints: shifts this line's destination by PR[i] expressed in the
currently selected tool frame, ignoring any TOOL_OFFSET_CONDITION. The bare
form "Tool_offset" needs a prior TOOL_OFFSET_CONDITION PR[x] (UTOOL[i])
line, which stays in effect until the program ends or another condition runs
(sec 7.3.20). When teaching such a line the pendant asks whether to subtract
the offset from the recorded position. Backward execution moves to the
offset-applied position.
Example:
    L P[3:nozzle work] 80mm/sec FINE Tool_Offset,PR[6:tip wear] ;
Manual: HandlingTool V9.40 sec 7.3.21

## PTH - path option for short CNT moves
Syntax: <motion> <position> <speed><unit> CNTn PTH ;
Constraints: makes the planner use the speed actually attainable on a short
CNT (CNT1-100) segment instead of the programmed speed, improving cycle time
and path accuracy. Benefit shrinks (and can reverse) with large CNT values,
long segments, or many consecutive CNT lines - verify the effect. If a PTH
move vibrates or jerks, delete the option.
Example:
    J P[5] 100% CNT10 PTH ;
Manual: HandlingTool V9.40 sec 7.3.14

## TIME BEFORE / TIME AFTER - timed program call option
Syntax: <motion> <speed><unit> <FINE|CNTn> TIME BEFORE <t> sec, CALL <prog> ;
        or ... TIME AFTER <t> sec, CALL <prog> ;
Constraints: runs the named TP program at t seconds before (TIME BEFORE) or
after (TIME AFTER) the motion's completion, instead of waiting for the move
to finish first. Typical use: firing a gripper slightly before arrival. On
the pendant motion-option menu these appear abbreviated as TB/TA. Detailed
behavior lives in the Advanced Functions chapter (sec 14.64).
Example:
    L P[2:place] 300mm/sec CNT80 TIME BEFORE 0.5 sec, CALL OPEN_GRIP ;
Manual: HandlingTool V9.40 sec 7.3.19
