/PROG R1_SAFE_RETRACT_LIN
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Safe linear retract: rotate@0, 4 pistons up, THEN retract";
PROG_SIZE	= 0;
CREATE		= DATE 26-06-17  TIME 00:00:00;
MODIFIED	= DATE 26-06-17  TIME 00:00:00;
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
   1:  !--- SAFE LINEAR RETRACT (design-review #16) --- ;
   2:  !  Order: rotate piston at 0 -> 4 pistons UP -> retract linear ;
   3:  !  Audit 2026-07-27: all faults retry-on-resume. PAUSE never ;
   4:  !  falls through into an actuator command - releasing pistons ;
   5:  !  with the flipper off 0 deg = uncontrolled gravity rotation. ;
   6:   ;
   7:  !  STEP 1: flipper must be at 0 deg (DI[435]) - re-checked ;
   8:  LBL[10]    ;
   9:  IF DI[435]=ON, JMP LBL[1]    ;
  10:  CALL SET_STR('RETRACT:NOT AT 0 DEG',1)    ;
  11:  CALL R1_TOWER(1,3)    ;
  12:  PAUSE    ;
  13:  CALL R1_TOWER(3,0)    ;
  14:  JMP LBL[10]    ;
  15:  LBL[1]    ;
  16:   ;
  17:  !  STEP 2: all 4 holding pistons released/up (DI[402/404/406/408]) ;
  18:  IF DI[402]=OFF, JMP LBL[2]    ;
  19:  IF DI[404]=OFF, JMP LBL[2]    ;
  20:  IF DI[406]=OFF, JMP LBL[2]    ;
  21:  IF DI[408]=OFF, JMP LBL[2]    ;
  22:  JMP LBL[5]    ;
  23:  LBL[2]    ;
  24:  !  not all up - command release and wait ;
  25:  DO[467]=OFF    ;
  26:  DO[468]=ON    ;
  27:  R[90]=0    ;
  28:  LBL[3]    ;
  29:  IF DI[402]=OFF, JMP LBL[4]    ;
  30:  IF DI[404]=OFF, JMP LBL[4]    ;
  31:  IF DI[406]=OFF, JMP LBL[4]    ;
  32:  IF DI[408]=OFF, JMP LBL[4]    ;
  33:  JMP LBL[5]    ;
  34:  LBL[4]    ;
  35:  WAIT .1(sec)    ;
  36:  R[90]=R[90]+1    ;
  37:  IF R[90]<50, JMP LBL[3]    ;
  38:  !  timeout: fault; resume re-commands + re-waits (LBL[2]) ;
  39:  CALL SET_STR('RETRACT:PISTON TIMEOUT',1)    ;
  40:  CALL R1_TOWER(1,3)    ;
  41:  PAUSE    ;
  42:  CALL R1_TOWER(3,0)    ;
  43:  JMP LBL[2]    ;
  44:  LBL[5]    ;
  45:   ;
  46:  !  STEP 3: now safe to retract linear ;
  47:  LBL[8]    ;
  48:  DO[465]=OFF    ;
  49:  DO[466]=ON    ;
  50:  R[90]=0    ;
  51:  LBL[6]    ;
  52:  IF DI[433]=ON, JMP LBL[7]    ;
  53:  WAIT .1(sec)    ;
  54:  R[90]=R[90]+1    ;
  55:  IF R[90]<50, JMP LBL[6]    ;
  56:  !  timeout: fault; resume re-commands the retract (LBL[8]) ;
  57:  CALL SET_STR('RETRACT:LINEAR TIMEOUT',1)    ;
  58:  CALL R1_TOWER(1,3)    ;
  59:  PAUSE    ;
  60:  CALL R1_TOWER(3,0)    ;
  61:  JMP LBL[8]    ;
  62:  LBL[7]    ;
  63:  DO[466]=OFF    ;
/END
