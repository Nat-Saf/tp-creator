/PROG R1_PLACE_POLY_LR
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Place Polygon - Long Range. Approach PR[42], descend to PR[43], release vacuum, retract.";
PROG_SIZE	= 0;
CREATE		= DATE 26-06-01  TIME 00:00:00;
MODIFIED	= DATE 26-06-24  TIME 00:00:00;
FILE_NAME	= ;
VERSION		= 0;
LINE_COUNT	= 0;
MEMORY_SIZE	= 0;
PROTECT		= READ_WRITE;
TCD:  STACK_SIZE	= 0,
      TASK_PRIORITY	= 50,
      TIME_SLICE	= 0,
      BUSY_LAMP_OFF	= 0,
      ABORT_REQUEST	= 0,
      PAUSE_REQUEST	= 0;
DEFAULT_GROUP	= 1,*,*,*,*;
CONTROL_CODE	= 00000000 00000000;
/MN
   1:  !--- PLACE POLYGON - LONG RANGE --- ;
   2:  ! PR[42] = nest approach / retract waypoint (shared by all place programs). ;
   3:  ! CNT50 = continuous motion through PR[42] - robot blends into next move ;
   4:  ! without stopping, reducing tact time on the approach segment. ;
   5:  J PR[42] 80% CNT50    ;
   6:  ! Descend at controlled 100mm/sec to LR polygon exact place position PR[43]. ;
   7:  ! FINE = fully stop and settle before output commands. ;
   8:  ! SR uses PR[41], Corner uses PR[44] - only this line differs per recipe. ;
   9:  L PR[43] 100mm/sec FINE    ;
  10:  ! DO[536] = polygon-tool vacuum off. Part releases from suction cup. ;
  11:  DO[536]=OFF    ;
  12:  ! DO[535] = compliance compensator off. Removes any Z float so part sits ;
  13:  ! firmly on the nest seat under gravity (not held up by tool). ;
  14:  DO[535]=OFF    ;
  15:  ! Audit 2026-07-27: release is DI[533]-CONFIRMED (parity with the VS ;
  16:  ! places) - a part stuck to the cup must not be carried away and get ;
  17:  ! misdiagnosed later as a place-verify NOK. Confirms vacuum decay at ;
  18:  ! the shared holding sensor; operator intervenes on timeout, resume ;
  19:  ! re-checks (LBL[1]). ;
  20:  LBL[1]    ;
  21:  R[90]=0    ;
  22:  LBL[2]    ;
  23:  IF DI[533]=OFF, JMP LBL[3]    ;
  24:  WAIT .1(sec)    ;
  25:  R[90]=R[90]+1    ;
  26:  IF R[90]<50, JMP LBL[2]    ;
  27:  CALL SET_STR('POLY RELEASE TIMEOUT',1)    ;
  28:  CALL R1_TOWER(1,3)    ;
  29:  PAUSE    ;
  30:  CALL R1_TOWER(3,0)    ;
  31:  JMP LBL[1]    ;
  32:  LBL[3]    ;
  33:  ! Retract back to approach height. Linear move keeps XY fixed ;
  34:  ! so robot lifts straight up away from the placed part. ;
  35:  L PR[42] 100mm/sec FINE    ;
/END
