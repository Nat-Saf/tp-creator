/PROG  SYNTAX_PROBE
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Load/accept syntax probe";
PROG_SIZE	= 0;
CREATE		= DATE 26-06-17  TIME 12:00:00;
MODIFIED	= DATE 26-06-17  TIME 12:00:00;
FILE_NAME	= ;
VERSION		= 0;
LINE_COUNT	= 20;
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
   1:  ! SYNTAX PROBE - no motion, safe ;
   2:  ! Verifies frame<->PR + helpers ;
   3:  UTOOL_NUM=1 ;
   4:   ;
   5:  ! Read tool frames into PRs ;
   6:  PR[5]=UTOOL[1] ;
   7:  PR[6]=UTOOL[2] ;
   8:  ! Write a frame back from a PR ;
   9:  UTOOL[1]=PR[5] ;
  10:   ;
  11:  ! Register math + PR element write ;
  12:  R[118]=0 ;
  13:  LBL[1] ;
  14:  R[118]=R[118]+1 ;
  15:  PR[2,3]=R[118] ;
  16:  IF R[118]<3,JMP LBL[1] ;
  17:   ;
  18:  ! Shared error code + string helper ;
  19:  R[10]=801 ;
  20:  CALL SET_STR('Syntax probe OK',10) ;
/POS
/END
