/PROG R1_PLACE_VERIFY_VS
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Verify VS 2pts R7 recipe V3";
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
   1:  !--- PLACE VERIFY VS SCANNER 2-PT (#15) ---    ;
   2:  !  R[7]=1 SR : PR[66], PR[67]    ;
   3:  !  R[7]=2 LR : PR[74], PR[75]    ;
   4:  !  R[7]=3 Corner: PR[78], PR[79]    ;
   5:  !  2 captures (R[50]=21) then verdict (R[50]=7) -> R[51].    ;
   6:  !  V3: NOK sets SR[1] and RETURNS - MAIN checks R[51] and    ;
   7:  !  returns the Top Cover to the operator (no PAUSE here).    ;
   8:  !  Audit 2026-07-27: unknown R[7] faults instead of silently    ;
   9:  !  measuring the SR points with a wrong recipe.    ;
  10:  LBL[11]    ;
  11:  IF R[7]=1, JMP LBL[1]    ;
  12:  IF R[7]=2, JMP LBL[2]    ;
  13:  IF R[7]=3, JMP LBL[3]    ;
  14:  CALL SET_STR('VERIFY:R7 INVALID',1)    ;
  15:  CALL R1_TOWER(1,3)    ;
  16:  PAUSE    ;
  17:  CALL R1_TOWER(3,0)    ;
  18:  JMP LBL[11]    ;
  19:  LBL[1]    ;
  20:  !  SR    ;
  21:  J PR[66] 80% FINE    ;
  22:  R[50]=21    ;
  23:  CALL R1_PC_REQ    ;
  24:  J PR[67] 80% FINE    ;
  25:  R[50]=21    ;
  26:  CALL R1_PC_REQ    ;
  27:  JMP LBL[9]    ;
  28:  LBL[2]    ;
  29:  !  LR    ;
  30:  J PR[74] 80% FINE    ;
  31:  R[50]=21    ;
  32:  CALL R1_PC_REQ    ;
  33:  J PR[75] 80% FINE    ;
  34:  R[50]=21    ;
  35:  CALL R1_PC_REQ    ;
  36:  JMP LBL[9]    ;
  37:  LBL[3]    ;
  38:  !  Corner    ;
  39:  J PR[78] 80% FINE    ;
  40:  R[50]=21    ;
  41:  CALL R1_PC_REQ    ;
  42:  J PR[79] 80% FINE    ;
  43:  R[50]=21    ;
  44:  CALL R1_PC_REQ    ;
  45:  LBL[9]    ;
  46:  !  Verdict: 2 pts captured, PC measures against nominal    ;
  47:  R[50]=7    ;
  48:  CALL R1_PC_REQ    ;
  49:  IF R[51]=1, JMP LBL[10]    ;
  50:  CALL SET_STR('VS PLACE VERIFY NOK',1)    ;
  51:  LBL[10]    ;
/END
