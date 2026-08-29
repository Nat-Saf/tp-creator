/PROG R1_PLACE_VS_LR
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Place VS Scanner - Long Range. Gripper open with timeout confirm.";
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
   1:  !--- PLACE VS SCANNER - LONG RANGE --- ;
   2:  ! PR[42] = nest approach / retract waypoint (shared by all place programs). ;
   3:  ! CNT50 = blended motion through the approach point. ;
   4:  J PR[42] 80% CNT50    ;
   5:  ! Descend at controlled 100mm/sec to LR VS exact place position PR[46]. ;
   6:  ! SR uses PR[40], Corner uses PR[45] (tilted W/P/R). ;
   7:  ! FINE = fully stop before opening gripper. ;
   8:  L PR[46] 100mm/sec FINE    ;
   9:  ! Shared actuate DO[536] (29/07 map): OFF = release. Jaws open ;
  10:  ! VS gripper is parallel-jaw type; opening releases the VS scanner ;
  11:  ! into the nest pocket. ;
  12:  LBL[3]    ;
  13:  DO[536]=OFF    ;
  14:  ! Wait up to 5 sec (R[90]<50 x 0.1s) for gripper to confirm open. ;
  15:  ! DI[533]=OFF = gripper released/open. ;
  16:  ! Fault if gripper jams and never opens - part is not released and ;
  17:  ! robot cannot retract safely; resume re-commands the open (LBL[3]). ;
  18:  R[90]=0    ;
  19:  LBL[1]    ;
  20:  IF DI[533]=OFF, JMP LBL[2]    ;
  21:  WAIT .1(sec)    ;
  22:  R[90]=R[90]+1    ;
  23:  IF R[90]<50, JMP LBL[1]    ;
  24:  CALL SET_STR('VS RELEASE TIMEOUT',1)    ;
  25:  CALL R1_TOWER(1,3)    ;
  26:  PAUSE    ;
  27:  CALL R1_TOWER(3,0)    ;
  28:  JMP LBL[3]    ;
  29:  LBL[2]    ;
  30:  ! DO[535] = compensator off. Shuts off the Z-compliance float so part ;
  31:  ! gravity-seats into the nest locators. ;
  32:  DO[535]=OFF    ;
  33:  ! Retract straight up to approach height with linear move. ;
  34:  L PR[42] 100mm/sec FINE    ;
/END
