# frames_offset - own-words syntax notes

## UFRAME_NUM - select active user frame
Syntax: UFRAME_NUM=<i> ;
Semantics: makes user frame i the active frame for subsequent motion and for
positions recorded afterwards. Value 0 means no user frame - world frame acts
as the reference. The line must actually EXECUTE (not merely sit in the
program) before positions taught after it are stored relative to frame i.
Indirection: the right side may be a register-style value, e.g. UFRAME_NUM=AR[3].
Related: $USEUFRAME must be TRUE for teach-time frame stamping to apply.
Example:
    UFRAME_NUM=1 ;
    L P[1:station A] 500mm/sec FINE ;
Manual: HandlingTool V9.40 sec 7.20

## UTOOL_NUM - select active tool frame
Syntax: UTOOL_NUM=<i> ;
Semantics: makes tool frame i the active TCP definition for subsequent motion.
Value 0 means no tool frame - the faceplate coordinates define the TCP.
Indirection: an argument register is accepted, e.g. UTOOL_NUM=AR[4].
Example:
    UTOOL_NUM=2 ;
    J P[1:gripper approach] 50% CNT100 ;
Manual: HandlingTool V9.40 sec 7.20

## UFRAME[i]=PR[j] - define a user frame from a position register
Syntax: UFRAME[<i>]=PR[<j>] ;
Semantics: writes the frame data held in PR[j] into user frame i at runtime.
Defining the frame does not select it - follow with UFRAME_NUM=i to use it.
Typical pattern: a vision or calibration routine fills PR[j], then the program
installs and activates the frame.
Example:
    UFRAME[1]=PR[10:pallet frame] ;
    UFRAME_NUM=1 ;
Manual: HandlingTool V9.40 sec 7.20

## UTOOL[i]=PR[j] - define a tool frame from a position register
Syntax: UTOOL[<i>]=PR[<j>] ;
Semantics: writes the frame data held in PR[j] into tool frame i at runtime.
As with user frames, definition and selection are separate steps - add
UTOOL_NUM=i afterwards to make the new TCP active.
Example:
    UTOOL[1]=PR[11:new tcp] ;
    UTOOL_NUM=1 ;
Manual: HandlingTool V9.40 sec 7.20

## OFFSET CONDITION - set the shift used by bare Offset clauses
Syntax: OFFSET CONDITION PR[<i>] [UFRAME[<j>]] ;
Semantics: names the position register whose contents shift every later motion
line that carries a bare Offset clause. Must execute before the first such
motion line. If UFRAME[j] is given, the shift is interpreted in that user
frame instead of the active one. Once set, every bare Offset clause keeps
using this PR until a new OFFSET CONDITION replaces it.
Example:
    OFFSET CONDITION PR[3:row shift] ;
    L P[2:place] 300mm/sec FINE Offset ;
Manual: HandlingTool V9.40 sec 7.20

## Offset - bare offset motion clause
Syntax: <J|L|C> P[<i>] <speed> <FINE|CNTn> Offset ;
Semantics: moves to P[i] shifted by the PR named in the last executed OFFSET
CONDITION. A Cartesian PR is combined element by element with the target
(pre-multiplied as a frame instead when $OFFSET_CART is TRUE); a JOINT PR is
added joint by joint and no user frame enters the calculation.
Constraints: combined with the Inc option, the position and the offset PR must
share one representation, both Cartesian or both JOINT.
Example:
    OFFSET CONDITION PR[3] ;
    J P[4:stack top] 80% CNT50 Offset ;
Manual: HandlingTool V9.40 sec 7.3.12

## Offset,PR[i] - direct offset motion clause
Syntax: <J|L|C> P[<i>] <speed> <FINE|CNTn> Offset,PR[<j>] ;
Semantics: shifts the target of THIS line only by PR[j]; no OFFSET CONDITION
needed and none is disturbed. The shift is interpreted in the currently
selected user frame when PR[j] is Cartesian; a JOINT-representation PR is
added joint-wise with no frame involved.
Constraints: with the Inc option the position and PR must share representation.
Example:
    L PR[5:pick base] 100mm/sec CNT50 Offset,PR[2:part shift] ;
Manual: HandlingTool V9.40 sec 7.3.13

## TOOL_OFFSET CONDITION - set the shift used by bare Tool_Offset clauses
Syntax: TOOL_OFFSET CONDITION PR[<i>] [UTOOL[<j>]] ;
Semantics: names the PR whose contents shift later motion lines carrying a
bare Tool_Offset clause, with the shift expressed in tool coordinates. Must
execute before the first such motion line; it stays in force until the
program ends or another tool offset condition executes. Omitting the tool
number means the currently selected tool frame is used.
Constraints: a target position stored in joint representation raises an alarm
and pauses the program.
Example:
    TOOL_OFFSET CONDITION PR[6:probe shift] UTOOL[1] ;
    L P[3:touch point] 50mm/sec FINE Tool_Offset ;
Manual: HandlingTool V9.40 sec 7.33

## Tool_Offset - bare tool offset motion clause
Syntax: <J|L|C> P[<i>] <speed> <FINE|CNTn> Tool_Offset ;
Semantics: moves to P[i] shifted along the tool frame axes by the PR named in
the last executed TOOL_OFFSET CONDITION - useful for approach and retreat
along the tool Z axis regardless of part orientation.
Notes: in backward (BWD) execution the robot still goes to the shifted
position, not the raw taught one.
Example:
    TOOL_OFFSET CONDITION PR[6] ;
    L P[7:insert] 30mm/sec FINE Tool_Offset ;
Manual: HandlingTool V9.40 sec 7.3.20

## Tool_Offset,PR[i] - direct tool offset motion clause
Syntax: <J|L|C> P[<i>] <speed> <FINE|CNTn> Tool_Offset,PR[<j>] ;
Semantics: shifts the target of THIS line only by PR[j] expressed in the
currently selected tool frame. Any active TOOL_OFFSET CONDITION is ignored
for this line and left untouched for later bare Tool_Offset clauses.
Example:
    L P[8:nozzle clean] 100mm/sec FINE Tool_Offset,PR[3:z lift] ;
Manual: HandlingTool V9.40 sec 7.3.21

## Offset frame semantics - which frame a shift is applied in
Rule of thumb: Offset and Offset,PR shifts live in a USER frame; Tool_Offset
and Tool_Offset,PR shifts live in a TOOL frame.
Details: a bare Offset uses the UFRAME[j] named in its OFFSET CONDITION when
one was given, otherwise the active user frame; Offset,PR always uses the
active user frame; both tool variants use the active tool frame unless the
condition line named a UTOOL[j]. A JOINT-representation offset PR bypasses
frames entirely - values add joint by joint.
Example:
    UFRAME_NUM=2 ;
    L P[1] 200mm/sec FINE Offset,PR[4] ;  -- PR[4] read in user frame 2
Manual: HandlingTool V9.40 sec 7.3.13
