/PROG R1_RETURN_REJECT
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "V3 reject: return nest to op";
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
   1:  !--- V3 RETURN REJECT: bring Top Cover back to operator ---    ;
   2:  ! Called by MAIN on Top Cover-level NOK (lidar barcode, height,    ;
   3:  ! O-ring, place verify, reject limit). SR[1]=reason (caller set).    ;
   4:  ! Nest is pre-flip (0 deg); pistons open, linear retracted.    ;
   5:  CALL SET_STR('REJECT RETURN',2)    ;
   6:  ! Robot clear of nest envelope before any nest/axis motion    ;
   7:  J PR[50] 100% FINE    ;
   8:  ! Defensive normalize: flipper@0 verified, pistons up, linear in    ;
   9:  CALL R1_SAFE_RETRACT_LIN    ;
  10:  DO[468]=OFF    ;
  11:  ! Drive nest to operator station    ;
  12:  CALL R1_AXIS_P2    ;
  13:  ! Nest back -> PC pulls up the reject screen (PC owns the verdict)    ;
  14:  DO[21]=ON    ;
  15:  WAIT .5(sec)    ;
  16:  DO[21]=OFF    ;
  17:  ! Robot home. GREEN=ready; HMI tells operator to remove the part.    ;
  18:  J PR[1] 100% FINE    ;
  19:  CALL R1_TOWER(2,0)    ;
/END
