# Curated program examples (own annotated snippets from our cell programs)

## pick and place - complete minimal program
A one-part pick-and-place cycle: approach above the pick point, descend
slowly, close the gripper, settle, lift, move to the place point, release,
return home. FINE at contact points, CNT for travel.
Example:
    /PROG PICK_PLACE
    /MN
       1:  UFRAME_NUM=1 ;
       2:  UTOOL_NUM=1 ;
       3:  J PR[1:home] 100% FINE ;
       4:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
       5:  L PR[5:conveyor pick] 50mm/sec FINE ;
       6:  RO[1:gripper close]=ON ;
       7:  WAIT   .50(sec) ;
       8:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
       9:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
      10:  L PR[8:fixture A place] 50mm/sec FINE ;
      11:  RO[1:gripper close]=OFF ;
      12:  WAIT   .50(sec) ;
      13:  J PR[1:home] 100% FINE ;
    /POS
    /END
Manual: pattern from our PICK_PBS.LS / PLACE_PBS.LS cell programs

## vacuum gripper handshake with sensor check
Command the actuator, then confirm with the feedback input under a timeout
instead of a blind wait. On timeout, set an error register and bail to a
shared fault label.
Example:
    10:  DO[374:VacuumACT]=ON ;
    11:  WAIT DI[370:VacuumReached]=ON TIMEOUT,LBL[90] ;
    12:  ! grip confirmed ;
    ...
    90:  LBL[90] ;
    91:  R[10:Error Code]=205 ;
Manual: pattern from our PICK_PBS.LS grip-check states

## state-machine dispatch with SELECT
Step-per-scan pattern: a register holds the state, SELECT dispatches to one
label per state, each state does one pass of work, advances the register,
and jumps to a common exit. Callers re-enter until status says done.
Example:
    60:  R[25:Status]=2 ;
    67:  SELECT R[26:Step]=0,JMP LBL[10] ;
    68:         =1,JMP LBL[20] ;
    69:         =2,JMP LBL[30] ;
    70:         ELSE,JMP LBL[10] ;
Manual: pattern from our PICK_PBS.LS state machine

## computed grid position with PR arithmetic
Raster over an X/Y tray by computing the slot pose into a position register:
copy the taught slot-zero point, then add index*pitch to the X and Y
components. Element 1 is X, 2 is Y, 3 is Z.
Example:
    20:  PR[8:PickLoc]=P[1:Slot00] ;
    21:  R[31:Tmp]=R[156:IdxX]*R[158:PitchX] ;
    22:  PR[8,1:PickLoc]=PR[8,1:PickLoc]+R[31:Tmp] ;
    23:  R[31:Tmp]=R[157:IdxY]*R[159:PitchY] ;
    24:  PR[8,2:PickLoc]=PR[8,2:PickLoc]+R[31:Tmp] ;
Manual: pattern from our PICK_PBS.LS slot math

## gate checks with error codes before motion
Verify preconditions (part present, tray in place) with IF gates before any
motion; on failure set a numeric error register, write a message, and jump
to the fault exit - never move blind.
Example:
    82:  IF DI[592:Tray in]=ON,JMP LBL[11] ;
    83:  R[10:Error Code]=201 ;
    84:  CALL SET_STR('No PBS tray',10) ;
    85:  JMP LBL[88] ;
    86:  LBL[11] ;
Manual: pattern from our PICK_PBS.LS entry gates
