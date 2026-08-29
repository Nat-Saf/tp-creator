/PROG R1_PC_REQ
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "PC handshake (no KAREL): caller sets R[50], result in R[51]";
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
   1:  !--- PC HANDSHAKE (design-review #11, replaces KAREL) --- ;
   2:  !  Caller sets R[50] = request code BEFORE calling. ;
   3:  !  Returns R[51]: verdict 1=OK/clear/present, 2=NOK; or slot value (0=empty). ;
   4:  !  PC writes R[51] over EtherNet/IP then sets DI[30]=PC_DONE. ;
   5:  !  R[99]=1 (sim) returns R[51]=1 OK without contacting PC. ;
   6:  !  Audit 2026-07-27: (a) DI[30]=OFF verified BEFORE raising DO[20] - ;
   7:  !  back-to-back calls can never sample the previous transaction's ;
   8:  !  stale PC_DONE (PC must drop DI[30] when it sees DO[20] fall); ;
   9:  !  (b) PC timeout is retry-on-resume: operator fixes the PC, CYCLE ;
  10:  !  START re-issues the SAME request (R[50] intact) - the call NEVER ;
  11:  !  returns R[51]=0, so no more false NOK / false tray-empty. ;
  12:   ;
  13:  R[51]=0    ;
  14:  IF R[99]=1, JMP LBL[9]    ;
  15:   ;
  16:  !  guard: previous transaction fully closed (DI[30] must be low) ;
  17:  LBL[11]    ;
  18:  R[90]=0    ;
  19:  LBL[3]    ;
  20:  IF DI[30]=OFF, JMP LBL[12]    ;
  21:  WAIT .1(sec)    ;
  22:  R[90]=R[90]+1    ;
  23:  IF R[90]<50, JMP LBL[3]    ;
  24:  CALL SET_STR('PC:DI30 STUCK ON',1)    ;
  25:  CALL R1_TOWER(1,3)    ;
  26:  PAUSE    ;
  27:  CALL R1_TOWER(3,0)    ;
  28:  JMP LBL[11]    ;
  29:  LBL[12]    ;
  30:  !  request PC action coded in R[50] ;
  31:  DO[20]=ON    ;
  32:  R[90]=0    ;
  33:  LBL[1]    ;
  34:  IF DI[30]=ON, JMP LBL[2]    ;
  35:  WAIT .1(sec)    ;
  36:  R[90]=R[90]+1    ;
  37:  IF R[90]<300, JMP LBL[1]    ;
  38:  !  timeout - PC did not answer; resume RE-ISSUES the request (LBL[11]) ;
  39:  DO[20]=OFF    ;
  40:  CALL SET_STR('PC:NO ANSWER',1)    ;
  41:  CALL R1_TOWER(1,3)    ;
  42:  PAUSE    ;
  43:  CALL R1_TOWER(3,0)    ;
  44:  JMP LBL[11]    ;
  45:  LBL[2]    ;
  46:  !  PC done; R[51] holds the result ;
  47:  DO[20]=OFF    ;
  48:  JMP LBL[10]    ;
  49:  LBL[9]    ;
  50:  R[51]=1    ;
  51:  LBL[10]    ;
/END
