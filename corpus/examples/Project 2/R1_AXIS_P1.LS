/PROG R1_AXIS_P1
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "V3 nest to P1, retry-resume";
PROG_SIZE	= 0;
CREATE		= DATE 26-07-16  TIME 00:00:00;
MODIFIED	= DATE 26-07-16  TIME 00:00:00;
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
   1:  !--- AXIS TO P1 (PnP SIDE) (V3 retry-on-resume, 2026-07-20) ---    ;
   2:  ! Drives the nest to P1 (PnP SIDE). Tolerant to a safety stop mid-travel    ;
   3:  ! (LC crossed before its time / STO): on timeout the drive valve    ;
   4:  ! is DE-COMMANDED first (restart interlock - restoring air/enable    ;
   5:  ! alone cannot move the axis), then RED+PAUSE. Operator Resume    ;
   6:  ! (safety clear + CYCLE START) re-enters LBL[1] and RETRIES.    ;
   7:  ! Locker (29/07): VFOF pilots enabled during travel, re-locked at    ;
   8:  ! target / fault (fail-locked policy; coil roles = bench item).    ;
   9:  LBL[1]    ;
  10:  ! already at target? (repeat calls / resume after arrival)    ;
  11:  IF DI[499]=ON, JMP LBL[9]    ;
  12:  ! at origin or mid-travel: enable locker, (re)command the drive    ;
  13:  DO[562]=OFF    ;
  14:  DO[561]=ON    ;
  15:  DO[498]=OFF    ;
  16:  DO[497]=ON    ;
  17:  R[90]=0    ;
  18:  LBL[2]    ;
  19:  IF DI[499]=ON, JMP LBL[8]    ;
  20:  WAIT .1(sec)    ;
  21:  R[90]=R[90]+1    ;
  22:  IF R[90]<100, JMP LBL[2]    ;
  23:  ! NOT ARRIVED (10 s): de-command valve + re-lock, fault; Resume retries    ;
  24:  DO[497]=OFF    ;
  25:  DO[561]=OFF    ;
  26:  DO[562]=ON    ;
  27:  CALL SET_STR('AXIS P1 NOT ARRIVED',1)    ;
  28:  CALL R1_TOWER(1,3)    ;
  29:  PAUSE    ;
  30:  CALL R1_TOWER(3,0)    ;
  31:  JMP LBL[1]    ;
  32:  LBL[8]    ;
  33:  DO[497]=OFF    ;
  34:  LBL[9]    ;
  35:  ! target reached (or already there): axis mechanically held    ;
  36:  DO[561]=OFF    ;
  37:  DO[562]=ON    ;
/END
