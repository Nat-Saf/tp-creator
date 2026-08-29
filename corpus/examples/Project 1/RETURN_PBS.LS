/PROG  RETURN_PBS
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Return PBS";
PROG_SIZE	= 0;
CREATE		= DATE 26-07-06  TIME 12:30:00;
MODIFIED	= DATE 26-07-06  TIME 13:00:00;
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
/APPL
/MN
   1:  ! === RETURN_PBS === ;
   2:  ! Step-per-scan: ONE pass per call. ;
   3:  ! Places a no-go PBS back into the SAME tray ;
   4:  ! slot it was picked from. Called by RUN after ;
   5:  ! VISION reports no-go (R[32:VisResult]=2). ;
   6:  ! Frame UT3 / UF1 (UF unchanged all program). ;
   7:  ! ;
   8:  ! Target slot = PR[8:PBSPickLoc], set by PICK ;
   9:  ! and untouched by VISION. Grid index R[156]/ ;
  10:  ! R[157] is NOT used and NOT changed here - PICK ;
  11:  ! already advanced it at pick time, so the ;
  12:  ! returned PBS stays in its slot and is skipped. ;
  13:  ! ;
  14:  ! States (R[62:RetStep]): ;
  15:  !  0 = gate + enter station P[2]->P[3] ;
  16:  !  1 = approach above slot (PR[8] + Z offset) ;
  17:  !  2 = descend to slot, release: vac OFF, blow ON ;
  18:  !  3 = blow/settle done: blow OFF, lift ;
  19:  !  4 = exit P[3]->P[2], report OK ;
  20:  ! ;
  21:  ! Release mirrors PICK no-part path: vacuum OFF + ;
  22:  ! blow pulse R[30:GripBlowTime] (settle) -> lift. ;
  23:  ! ;
  24:  ! Registers: ;
  25:  ! R[10:Error Code]    shared fault code (out) ;
  26:  ! R[30:GripBlowTime]  air-blow/settle pulse sec ;
  27:  ! R[63:TravelSpd]     between-station speed mm/s ;
  28:  ! R[64:PrecSpd]       precision speed mm/s ;
  29:  ! R[61:RetStatus]     2=busy 1=ok 0=fault (out) ;
  30:  ! R[62:RetStep]       internal state 0-4 ;
  31:  ! R[122:PistElapsed]  timer readback scratch ;
  32:  ! ;
  33:  ! Position registers: ;
  34:  ! PR[8:PBSPickLoc]    pick pose to return to (in) ;
  35:  ! PR[9:ZOffset]       Z clearance offset (in) ;
  36:  ! ;
  37:  ! Points (UF1/UT3; SAME numbering as PICK_PBS, ;
  38:  ! pre-filled from PICK P[2]/P[3] - VERIFY): ;
  39:  ! P[2] = safe above tray  (= PICK P[2]) ;
  40:  ! P[3] = intermediate WP  (= PICK P[3]) ;
  41:  ! (P[1] = first slot, unused here - PR[8] used) ;
  42:  ! ;
  43:  ! IO: ;
  44:  ! DI[592:X8.0 PBS tray in] ;
  45:  ! DO[374:X1.6Gripper.VaccuumACT] ;
  46:  ! DO[375:X1.7Gripper.AirBlowACT] ;
  47:  ! TIMER[2] shared RUN-phase timer. ;
  48:  ! ;
  49:  ! Error codes: ;
  50:  ! 220 = no PBS tray (DI[592] OFF) ;
  51:   ;
  52:  R[61:RetStatus]=2 ;
  53:   ;
  54:  ! Sub owns tool; UF stays 1 all program ;
  55:  UTOOL_NUM=3 ;
  56:  UFRAME_NUM=1 ;
  57:   ;
  58:  ! --- Dispatch on state --- ;
  59:  SELECT R[62:RetStep]=0,JMP LBL[10] ;
  60:         =1,JMP LBL[20] ;
  61:         =2,JMP LBL[30] ;
  62:         =3,JMP LBL[40] ;
  63:         =4,JMP LBL[50] ;
  64:         ELSE,JMP LBL[10] ;
  65:   ;
  66:   ;
  67:  ! ============================= ;
  68:  ! State 0: gate, enter station P[2]->P[3] ;
  69:  ! ============================= ;
  70:  LBL[10] ;
  71:  ! Gate: tray present ;
  72:  IF DI[592:X8.0 PBS tray in]=ON,JMP LBL[11] ;
  73:  R[10:Error Code]=220 ;
  74:  CALL SET_STR('No PBS tray',10) ;
  75:  JMP LBL[88] ;
  76:  LBL[11] ;
  77:  ! P[2] = safe above tray ;
  78:L P[2] R[63:TravelSpd]mm/sec CNT100    ;
  79:  ! P[3] = intermediate WP ;
  80:L P[3] R[63:TravelSpd]mm/sec CNT100    ;
  81:  R[62:RetStep]=1 ;
  82:  JMP LBL[99] ;
  83:   ;
  84:   ;
  85:  ! ============================= ;
  86:  ! State 1: approach above slot PR[8] ;
  87:  ! ============================= ;
  88:  LBL[20] ;
  89:L PR[8:PBSPickLoc] R[63:TravelSpd]mm/sec CNT10 Offset,PR[9]    ;
  90:  R[62:RetStep]=2 ;
  91:  JMP LBL[99] ;
  92:   ;
  93:   ;
  94:  ! ============================= ;
  95:  ! State 2: descend to slot, release ;
  96:  ! (vacuum OFF, blow ON, start settle timer) ;
  97:  ! ============================= ;
  98:  LBL[30] ;
  99:L PR[8:PBSPickLoc] R[64:PrecSpd]mm/sec FINE    ;
 100:  DO[374:X1.6Gripper.VaccuumACT]=OFF ;
 101:  DO[375:X1.7Gripper.AirBlowACT]=ON ;
 102:  TIMER[2]=RESET ;
 103:  TIMER[2]=START ;
 104:  R[62:RetStep]=3 ;
 105:  JMP LBL[99] ;
 106:   ;
 107:   ;
 108:  ! ============================= ;
 109:  ! State 3: blow/settle done -> blow OFF, lift ;
 110:  ! ============================= ;
 111:  LBL[40] ;
 112:  R[122:PistElapsed]=TIMER[2] ;
 113:  IF R[122:PistElapsed]<R[30:GripBlowTime],JMP LBL[99] ;
 114:  TIMER[2]=STOP ;
 115:  DO[375:X1.7Gripper.AirBlowACT]=OFF ;
 116:  ! PR[8] = pick pose (lift with Z offset) ;
 117:L PR[8:PBSPickLoc] R[63:TravelSpd]mm/sec CNT10 Offset,PR[9]    ;
 118:  R[62:RetStep]=4 ;
 119:  JMP LBL[99] ;
 120:   ;
 121:   ;
 122:  ! ============================= ;
 123:  ! State 4: exit P[3]->P[2], report OK ;
 124:  ! ============================= ;
 125:  LBL[50] ;
 126:  ! P[3] = intermediate WP ;
 127:L P[3] R[63:TravelSpd]mm/sec CNT100    ;
 128:  ! P[2] = safe above tray ;
 129:L P[2] R[63:TravelSpd]mm/sec CNT100    ;
 130:  R[10:Error Code]=0 ;
 131:  CALL SET_STR('Return OK',10) ;
 132:  R[61:RetStatus]=1 ;
 133:  R[62:RetStep]=0 ;
 134:  JMP LBL[99] ;
 135:   ;
 136:   ;
 137:  ! ============================= ;
 138:  ! Fault: blow off, status 0, reset step ;
 139:  ! ============================= ;
 140:  LBL[88] ;
 141:  DO[375:X1.7Gripper.AirBlowACT]=OFF ;
 142:  TIMER[2]=STOP ;
 143:  R[61:RetStatus]=0 ;
 144:  R[62:RetStep]=0 ;
 145:  JMP LBL[99] ;
 146:   ;
 147:  LBL[99] ;
/POS
P[2]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   208.154968  mm,	Y =   562.557251  mm,	Z =   -84.654434  mm,
	W =     -.004188 deg,	P =    -1.496028 deg,	R =     -.000631 deg
};
P[3]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   259.575989  mm,	Y =   562.567932  mm,	Z =  -213.719025  mm,
	W =     -.002920 deg,	P =    -1.495423 deg,	R =      .000134 deg
};
/END
