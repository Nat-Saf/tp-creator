/PROG R1_IV3_PROG
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "IV3 program select AR1=prog num";
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
   1:  !--- IV3 PROGRAM SELECT (EIP direct - ASSUMED sequence) ---    ;
   2:  ! AR[1] = IV3 program number: VS trays = 4 (POC 'Program 004');    ;
   3:  ! POLY trays = 5 (ASSUMED - set when the poly program is taught).    ;
   4:  ! GO[3] = PSEL value (DO[627-630]); DO[626] = select strobe;    ;
   5:  ! GI[1] = current-program echo (DI[638-641]).    ;
   6:  ! >>> BENCH: real select sequence + echo; if no echo exists in the    ;
   7:  ! >>> assembly, replace the verify loop with a fixed settle WAIT.    ;
   8:  ! R[99]=1 (Roboguide): skip - no camera in sim.    ;
   9:  IF R[99]=1, JMP LBL[9]    ;
  10:  GO[3]=AR[1]    ;
  11:  WAIT .1(sec)    ;
  12:  LBL[10]    ;
  13:  DO[626]=ON    ;
  14:  WAIT .2(sec)    ;
  15:  DO[626]=OFF    ;
  16:  !  verify the program echo (R[30]/R[31] = documented scratch)    ;
  17:  R[30]=AR[1]    ;
  18:  R[90]=0    ;
  19:  LBL[1]    ;
  20:  R[31]=GI[1]    ;
  21:  R[31]=R[31]-R[30]    ;
  22:  IF R[31]=0, JMP LBL[9]    ;
  23:  WAIT .1(sec)    ;
  24:  R[90]=R[90]+1    ;
  25:  IF R[90]<30, JMP LBL[1]    ;
  26:  !  echo mismatch 3 s: fault; resume re-strobes (LBL[10])    ;
  27:  CALL SET_STR('IV3:PROG SEL FAIL',1)    ;
  28:  CALL R1_TOWER(1,3)    ;
  29:  PAUSE    ;
  30:  CALL R1_TOWER(3,0)    ;
  31:  JMP LBL[10]    ;
  32:  LBL[9]    ;
/END
