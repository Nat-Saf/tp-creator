/PROG R1_READY_SEND
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "V3 pre-send check to operator";
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
   1:  !--- R1 READY TO SEND (V3) ---    ;
   2:  ! Called after nest flip (0->180) confirmed, before AXIS -> P2    ;
   3:  ! (deliver to OPERATOR STATION). Verifies nest hardware state:    ;
   4:  ! linear extended, 4 pistons locked, flipper at 180, axis at P1.    ;
   5:  ! Any miss -> RED+buzzer PAUSE; resume RE-CHECKS the failed condition    ;
   6:  ! (audit 2026-07-27) - this is the last gate before the nest travels    ;
   7:  ! to the operator, a bare CYCLE START must not bypass it.    ;
   8:  ! V2 Part B (R2 ready check) deleted - R2 cancelled in V3.    ;
   9:  ! Linear piston must be extended (DI[434]=ON) before transfer.    ;
  10:  LBL[10]    ;
  11:  IF DI[434]=ON, JMP LBL[1]    ;
  12:  CALL SET_STR('RDY SEND:LINEAR NOT EXT',1)    ;
  13:  CALL R1_TOWER(1,3)    ;
  14:  PAUSE    ;
  15:  CALL R1_TOWER(3,0)    ;
  16:  JMP LBL[10]    ;
  17:  LBL[1]    ;
  18:  ! All 4 holding pistons must be locked.    ;
  19:  LBL[11]    ;
  20:  IF DI[401]=ON, JMP LBL[2]    ;
  21:  CALL SET_STR('RDY SEND:PISTON 1 UNLOCK',1)    ;
  22:  CALL R1_TOWER(1,3)    ;
  23:  PAUSE    ;
  24:  CALL R1_TOWER(3,0)    ;
  25:  JMP LBL[11]    ;
  26:  LBL[2]    ;
  27:  LBL[12]    ;
  28:  IF DI[403]=ON, JMP LBL[3]    ;
  29:  CALL SET_STR('RDY SEND:PISTON 2 UNLOCK',1)    ;
  30:  CALL R1_TOWER(1,3)    ;
  31:  PAUSE    ;
  32:  CALL R1_TOWER(3,0)    ;
  33:  JMP LBL[12]    ;
  34:  LBL[3]    ;
  35:  LBL[13]    ;
  36:  IF DI[405]=ON, JMP LBL[4]    ;
  37:  CALL SET_STR('RDY SEND:PISTON 3 UNLOCK',1)    ;
  38:  CALL R1_TOWER(1,3)    ;
  39:  PAUSE    ;
  40:  CALL R1_TOWER(3,0)    ;
  41:  JMP LBL[13]    ;
  42:  LBL[4]    ;
  43:  LBL[14]    ;
  44:  IF DI[407]=ON, JMP LBL[5]    ;
  45:  CALL SET_STR('RDY SEND:PISTON 4 UNLOCK',1)    ;
  46:  CALL R1_TOWER(1,3)    ;
  47:  PAUSE    ;
  48:  CALL R1_TOWER(3,0)    ;
  49:  JMP LBL[14]    ;
  50:  LBL[5]    ;
  51:  ! Flipper must be at 180 deg (DI[436]=ON).    ;
  52:  LBL[15]    ;
  53:  IF DI[436]=ON, JMP LBL[6]    ;
  54:  CALL SET_STR('RDY SEND:NOT AT 180',1)    ;
  55:  CALL R1_TOWER(1,3)    ;
  56:  PAUSE    ;
  57:  CALL R1_TOWER(3,0)    ;
  58:  JMP LBL[15]    ;
  59:  LBL[6]    ;
  60:  ! Axis must be at P1 (DI[499]=ON) before transfer begins.    ;
  61:  LBL[16]    ;
  62:  IF DI[499]=ON, JMP LBL[7]    ;
  63:  CALL SET_STR('RDY SEND:AXIS NOT AT P1',1)    ;
  64:  CALL R1_TOWER(1,3)    ;
  65:  PAUSE    ;
  66:  CALL R1_TOWER(3,0)    ;
  67:  JMP LBL[16]    ;
  68:  LBL[7]    ;
  69:  ! Nest state confirmed - MAIN proceeds with AXIS -> P2.    ;
  70:  CALL SET_STR('SEND OK',2)    ;
/END
