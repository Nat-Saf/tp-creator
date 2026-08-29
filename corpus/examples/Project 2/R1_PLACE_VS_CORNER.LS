/PROG R1_PLACE_VS_CORNER
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Place VS Scanner - Corner tilted W/P/R. Gripper open with timeout confirm.";
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
   1:  !--- PLACE VS SCANNER - CORNER (TILTED W/P/R) --- ;
   2:  ! PR[42] = nest approach / retract waypoint (shared by all place programs). ;
   3:  ! CNT50 = blended motion through the approach point. ;
   4:  J PR[42] 80% CNT50    ;
   5:  ! Descend at controlled 100mm/sec to Corner VS exact place position PR[45]. ;
   6:  ! IMPORTANT: PR[45] has non-zero W/P/R (tool is tilted in the nest). ;
   7:  ! This approach path must be verified carefully during commissioning - ;
   8:  ! the tilted orientation changes the TCP path vs SR/LR. ;
   9:  ! SR uses PR[40], LR uses PR[46]. ;
  10:  L PR[45] 100mm/sec FINE    ;
  11:  ! Shared actuate DO[536] (29/07 map): OFF = release. Jaws open ;
  12:  ! VS gripper is parallel-jaw type; opening releases the VS scanner ;
  13:  ! into the tilted Corner nest pocket. ;
  14:  LBL[3]    ;
  15:  DO[536]=OFF    ;
  16:  ! Wait up to 5 sec (R[90]<50 x 0.1s) for gripper to confirm open. ;
  17:  ! DI[533]=OFF = gripper released/open. ;
  18:  ! Fault if gripper jams and never opens - part is not released and ;
  19:  ! robot cannot retract safely; resume re-commands the open (LBL[3]). ;
  20:  R[90]=0    ;
  21:  LBL[1]    ;
  22:  IF DI[533]=OFF, JMP LBL[2]    ;
  23:  WAIT .1(sec)    ;
  24:  R[90]=R[90]+1    ;
  25:  IF R[90]<50, JMP LBL[1]    ;
  26:  CALL SET_STR('VS RELEASE TIMEOUT',1)    ;
  27:  CALL R1_TOWER(1,3)    ;
  28:  PAUSE    ;
  29:  CALL R1_TOWER(3,0)    ;
  30:  JMP LBL[3]    ;
  31:  LBL[2]    ;
  32:  ! DO[535] = compensator off. Shuts off the Z-compliance float so part ;
  33:  ! gravity-seats into the tilted Corner nest locators. ;
  34:  DO[535]=OFF    ;
  35:  ! Retract back to approach height. Robot retraces the tilted descent ;
  36:  ! path in reverse - PR[45]->PR[42] is a linear move to keep XY/orientation fixed. ;
  37:  L PR[42] 100mm/sec FINE    ;
/END
