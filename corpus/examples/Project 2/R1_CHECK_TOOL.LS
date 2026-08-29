/PROG R1_CHECK_TOOL
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Set R[21] from 2-bit tool indicator DI[529]/DI[530].";
PROG_SIZE	= 0;
CREATE		= DATE 26-06-01  TIME 00:00:00;
MODIFIED	= DATE 26-06-01  TIME 00:00:00;
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
   1:  !--- HARDWARE TOOL IDENTIFICATION ---    ;
   2:  !  Tool on robot from 2-bit indicator on master (Balluff #4 on R1):    ;
   3:  !  DI[529]=bit1 DI[530]=bit2 - (1,0)=VS1 (0,1)=LRpoly2 (1,1)=SRpoly3 (0,0)=none    ;
   4:  !  DI[531]=bearings in (master free). 'Bearings out' sensor dropped 29/07.    ;
   5:  !  Rack occupancy DI[501-503] used by R1_TOOL_CHG. Call at start of MAIN.    ;
   6:  R[21]=0    ;
   7:  IF DI[529]=OFF, JMP LBL[1]    ;
   8:  !  bit1 ON -> (1,0) tool 1 or (1,1) tool 3    ;
   9:  IF DI[530]=ON, JMP LBL[3]    ;
  10:  R[21]=1    ;
  11:  JMP LBL[9]    ;
  12:  LBL[1]    ;
  13:  !  bit1 OFF -> (0,1) tool 2 or (0,0) none    ;
  14:  IF DI[530]=OFF, JMP LBL[9]    ;
  15:  R[21]=2    ;
  16:  JMP LBL[9]    ;
  17:  LBL[3]    ;
  18:  R[21]=3    ;
  19:  LBL[9]    ;
  20:  !  Select matching tool frame (valid even if MAIN skips R1_TOOL_CHG)    ;
  21:  !  Audit 2026-07-27: UTOOL 0 is invalid on R-30iB (INTP error) - skip    ;
  22:  !  the frame select when no tool is identified; previous frame stays.    ;
  23:  IF R[21]=0, JMP LBL[10]    ;
  24:  UTOOL_NUM=R[21]    ;
  25:  LBL[10]    ;
/END
