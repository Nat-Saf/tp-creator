/PROG  STARTUP
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Startup resets";
PROG_SIZE	= 0;
CREATE		= DATE 26-06-24  TIME 12:00:00;
MODIFIED	= DATE 26-06-24  TIME 12:00:00;
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
LOCAL_REGISTERS	= 0,0,0;
/APPL
/MN
   1:  ! === STARTUP === ;
   2:  ! Called once by MAIN before the main loop. ;
   3:  ! Resets tray and pick counters unconditionally. ;
   4:  ! Station status set from inductive sensors. ;
   5:  ! Does NOT touch vacuums - INIT handles that. ;
   6:   ;
   7:  ! --- Tray and pick counters --- ;
   8:  R[153:TrayFull]=0 ;
   9:  R[152:TraysReady]=0 ;
  10:  R[156:PBSPickX]=0 ;
  11:  R[157:PBSPickY]=0 ;
  12:   ;
   13:  ! --- HMI and error state --- ;
  14:  R[151:Ready]=0 ;
  15:  R[10:Error Code]=0 ;
  16:  CALL SET_STR('Startup OK',10) ;
  17:   ;
  18:  ! --- Station 1 status from inductive --- ;
  19:  ! If OB present on power-up: status=2 (remove) ;
  20:  ! Operator decides what to do with it. ;
  21:  IF DI[402:X2.2 St1 Inductive]=ON,JMP LBL[10] ;
  22:  R[154:St1Status]=0 ;
  23:  JMP LBL[11] ;
  24:  LBL[10] ;
  25:  R[154:St1Status]=2 ;
  26:  LBL[11] ;
  27:   ;
  28:  ! --- Station 2 status from inductive --- ;
  29:  IF DI[434:X3.2 St2 inductive]=ON,JMP LBL[20] ;
  30:  R[155:St2Status]=0 ;
  31:  JMP LBL[21] ;
  32:  LBL[20] ;
  33:  R[155:St2Status]=2 ;
  34:  LBL[21] ;
  35:   ;
  36:  ! --- Edge latch init --- ;
  37:  ! Seed TrayPrev to current state so MONITOR ;
  38:  ! does not trigger a false edge on first scan. ;
  39:  IF DI[592:X8.0 PBS tray in]=ON,JMP LBL[30] ;
  40:  R[160:TrayPrev]=0 ;
  41:  JMP LBL[31] ;
  42:  LBL[30] ;
  43:  R[160:TrayPrev]=1 ;
  44:  LBL[31] ;
  45:   ;
  46:  LBL[99] ;
/POS
/END
