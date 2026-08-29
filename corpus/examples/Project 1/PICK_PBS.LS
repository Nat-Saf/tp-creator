/PROG  PICK_PBS
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Pick PBS";
PROG_SIZE	= 0;
CREATE		= DATE 26-07-05  TIME 18:05:00;
MODIFIED	= DATE 26-07-05  TIME 18:05:00;
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
   1:  ! === PICK_PBS === ;
   2:  ! Step-per-scan: ONE pass per call. ;
   3:  ! Picks one PBS from the 5x5 tray. ;
   4:  ! Frame UT3 / UF0 (UF unchanged all program). ;
   5:  ! Two sections: ;
   6:  !  (1) station entry/exit  P[2]<->P[3] (once) ;
   7:  !  (2) slot handling  PR[8] + Z offset (loop) ;
   8:  ! Grid 0-based, raster Y then X; index advances ;
   9:  ! after EACH attempt (state 3), pass or no-part. ;
  10:  ! No part -> blow, lift, next slot (no error). ;
  11:  ! Only no-tray / tray-empty faults. ;
  12:  ! Grip check sensor-first (no full wait). ;
  13:   ;
  14:  ! States (R[26:PickStep]): ;
  15:  !  0 = gate + enter P[2]->P[3] ;
  16:  !  1 = compute PR[8] + approach above slot ;
  17:  !  2 = descend to slot, vacuum ON, timer ;
  18:  !  3 = check grip; advance index; ok->4 no->5 ;
  19:  !  4 = success: lift, exit P[3]->P[2], report OK ;
  20:  !  5 = no part: vacuum OFF, blow ON, timer ;
  21:  !  6 = blow done: blow OFF, lift, back to 1 ;
  22:   ;
  23:  ! Registers: ;
  24:  ! R[10:Error Code]    shared fault code (out) ;
  25:  ! R[25:PickStatus]    2=busy 1=ok 0=fault(out) ;
  26:  ! R[26:PickStep]      internal state 0-6 ;
  27:  ! R[29:GripVacTime]   vacuum settle timeout s ;
  28:  ! R[30:GripBlowTime]  air-blow pulse sec ;
  29:  ! R[31:PickTmp]       grid math scratch ;
  30:  ! R[122:PistElapsed]  timer readback scratch ;
  31:  ! R[153:TrayFull]     1=PBS remaining ;
  32:  ! R[156:PBSPickX]     current X index (0-4) ;
  33:  ! R[157:PBSPickY]     current Y index (0-4) ;
  34:  ! R[158:PBSPitchX]    X pitch mm ;
  35:  ! R[159:PBSPitchY]    Y pitch mm ;
  36:  ! R[161:PBSCntX]      X count (=5) ;
  37:  ! R[162:PBSCntY]      Y count (=5) ;
  38:   ;
  39:  ! Position registers: ;
  40:  ! PR[8:PBSPickLoc]    computed pick pose (out) ;
  41:  ! PR[9:ZOffset]       Z clearance offset (preset) ;
  42:   ;
  43:  ! Points (UF0/UT3, taught; no POS comments): ;
  44:  ! P[1] = first PBS slot (0,0), incl pick Z ;
  45:  ! P[2] = safe above tray ;
  46:  ! P[3] = intermediate waypoint (anti-collision) ;
  47:   ;
  48:  ! IO: ;
  49:  ! DI[592:X8.0 PBS tray in] ;
  50:  ! DI[370:X1.2 GripperVacuumReache] grip OK ;
  51:  ! DO[374:X1.6Gripper.VaccuumACT] ;
  52:  ! DO[375:X1.7Gripper.AirBlowACT] ;
  53:  ! TIMER[2] shared RUN-phase timer. ;
  54:   ;
  55:  ! Error codes: ;
  56:  ! 201 = no PBS tray (DI[592] OFF) ;
  57:  ! 202 = tray empty (R[153]=0) ;
  58:  ! R[27:PickTmrRun] unused (timer at transitions). ;
  59:   ;
  60:  R[25:PickStatus]=2 ;
  61:   ;
  62:  ! Sub owns tool; UF stays 0 all program ;
  63:  UTOOL_NUM=3 ;
  64:  UFRAME_NUM=1 ;
  65:   ;
  66:  ! --- Dispatch on state --- ;
  67:  SELECT R[26:PickStep]=0,JMP LBL[10] ;
  68:         =1,JMP LBL[20] ;
  69:         =2,JMP LBL[30] ;
  70:         =3,JMP LBL[40] ;
  71:         =4,JMP LBL[50] ;
  72:         =5,JMP LBL[60] ;
  73:         =6,JMP LBL[70] ;
  74:         ELSE,JMP LBL[10] ;
  75:   ;
  76:  ! ============================= ;
  77:  ! State 0: gate, enter station ;
  78:  !          (Section 1 in: P[2] -> P[3]) ;
  79:  ! ============================= ;
  80:  LBL[10] ;
  81:  ! Gate: tray present ;
  82:  IF DI[592:X8.0 PBS tray in]=ON,JMP LBL[11] ;
  83:  R[10:Error Code]=201 ;
  84:  CALL SET_STR('No PBS tray',10) ;
  85:  JMP LBL[88] ;
  86:  LBL[11] ;
  87:  ! Gate: tray not empty ;
  88:  IF R[153:TrayFull]=1,JMP LBL[12] ;
  89:  R[10:Error Code]=202 ;
  90:  CALL SET_STR('Tray empty',10) ;
  91:  JMP LBL[88] ;
  92:  LBL[12] ;
  93:   ;
  94:  ! Section 1: enter station P[2] -> P[3] ;
  95:L P[2:SafeAbove] R[63:TravelSpd]mm/sec CNT100    ;
  96:L P[3:Waypt] R[63:TravelSpd]mm/sec CNT100    ;
  97:  R[26:PickStep]=1 ;
  98:  JMP LBL[99] ;
  99:   ;
 100:  ! ============================= ;
 101:  ! State 1: compute PR[8], approach above slot ;
 102:  !          (Section 2 - stays in tray region) ;
 103:  ! ============================= ;
 104:  LBL[20] ;
 105:  ! Tray emptied via skips? retreat + fault ;
 106:  IF R[153:TrayFull]=1,JMP LBL[21] ;
 107:L P[3:Waypt] R[63:TravelSpd]mm/sec CNT100    ;
 108:L P[2:SafeAbove] R[63:TravelSpd]mm/sec CNT100    ;
 109:  R[10:Error Code]=202 ;
 110:  CALL SET_STR('Tray empty',10) ;
 111:  JMP LBL[88] ;
 112:  LBL[21] ;
 113:  ! Compute pick pose from grid (Z from P[1]) ;
 114:  PR[8:PBSPickLoc]=P[1] ;
 115:  R[31:PickTmp]=(R[156:PBSPickX]*R[158:PBSPitchX]) ;
 116:  PR[8,1]=(PR[8,1]+R[31:PickTmp]) ;
 117:  R[31:PickTmp]=(R[157:PBSPickY]*R[159:PBSPitchY]) ;
 118:  PR[8,2]=(PR[8,2]+R[31:PickTmp]) ;
 119:  ! Approach above slot at Z clearance ;
 120:L PR[8:PBSPickLoc] R[63:TravelSpd]mm/sec CNT10 Offset,PR[9]    ;
 121:  R[26:PickStep]=2 ;
 122:  JMP LBL[99] ;
 123:   ;
 124:  ! ============================= ;
 125:  ! State 2: descend, vacuum ON, start timer ;
 126:  ! ============================= ;
 127:  LBL[30] ;
 128:L PR[8:PBSPickLoc] R[64:PrecSpd]mm/sec FINE    ;
 129:  DO[374:X1.6Gripper.VaccuumACT]=ON ;
 130:  TIMER[2]=RESET ;
 131:  TIMER[2]=START ;
 132:  R[26:PickStep]=3 ;
 133:  JMP LBL[99] ;
 134:   ;
 135:  ! ============================= ;
 136:  ! State 3: check grip (sensor-first), then ;
 137:  ! advance index (both outcomes) at LBL[45]. ;
 138:  ! ============================= ;
 139:  LBL[40] ;
 140:  IF DI[370:X1.2 GripperVacuumReache]=ON,JMP LBL[41] ;
 141:  R[122:PistElapsed]=TIMER[2] ;
 142:  IF R[122:PistElapsed]<R[29:GripVacTime],JMP LBL[99] ;
 143:  ! Timeout, no part ;
 144:  TIMER[2]=STOP ;
 145:  R[26:PickStep]=5 ;
 146:  JMP LBL[45] ;
 147:  LBL[41] ;
 148:  ! Grip confirmed ;
 149:  TIMER[2]=STOP ;
 150:  R[26:PickStep]=4 ;
 151:  LBL[45] ;
 152:  ! --- Advance grid index (raster Y then X) --- ;
 153:  R[31:PickTmp]=(R[162:PBSCntY]-1) ;
 154:  IF R[157:PBSPickY]<R[31:PickTmp],JMP LBL[47] ;
 155:  R[31:PickTmp]=(R[161:PBSCntX]-1) ;
 156:  IF R[156:PBSPickX]<R[31:PickTmp],JMP LBL[46] ;
 157:  ! Both axes maxed: tray now empty ;
 158:  R[153:TrayFull]=0 ;
 159:  JMP LBL[99] ;
 160:  LBL[46] ;
 161:  R[156:PBSPickX]=(R[156:PBSPickX]+1) ;
 162:  R[157:PBSPickY]=0 ;
 163:  JMP LBL[99] ;
 164:  LBL[47] ;
 165:  R[157:PBSPickY]=(R[157:PBSPickY]+1) ;
 166:  JMP LBL[99] ;
 167:   ;
 168:  ! ============================= ;
 169:  ! State 4: success -> lift, exit P[3]->P[2], OK ;
 170:  ! ============================= ;
 171:  LBL[50] ;
 172:L PR[8:PBSPickLoc] R[64:PrecSpd]mm/sec FINE Offset,PR[9]    ;
 173:L P[3:Waypt] R[63:TravelSpd]mm/sec CNT100    ;
 174:L P[2:SafeAbove] R[63:TravelSpd]mm/sec CNT100    ;
 175:  R[10:Error Code]=0 ;
 176:  CALL SET_STR('Pick OK',10) ;
 177:  R[25:PickStatus]=1 ;
 178:  R[26:PickStep]=0 ;
 179:  JMP LBL[99] ;
 180:   ;
 181:  ! ============================= ;
 182:  ! State 5: no part -> vacuum OFF, blow ON, timer ;
 183:  ! ============================= ;
 184:  LBL[60] ;
 185:  DO[374:X1.6Gripper.VaccuumACT]=OFF ;
 186:  DO[375:X1.7Gripper.AirBlowACT]=ON ;
 187:  TIMER[2]=RESET ;
 188:  TIMER[2]=START ;
 189:  R[26:PickStep]=6 ;
 190:  JMP LBL[99] ;
 191:   ;
 192:  ! ============================= ;
 193:  ! State 6: blow done -> blow OFF, lift, back to 1 ;
 194:  !          (stay in tray region, next slot) ;
 195:  ! ============================= ;
 196:  LBL[70] ;
 197:  R[122:PistElapsed]=TIMER[2] ;
 198:  IF R[122:PistElapsed]<R[30:GripBlowTime],JMP LBL[99] ;
 199:  TIMER[2]=STOP ;
 200:  DO[375:X1.7Gripper.AirBlowACT]=OFF ;
 201:L PR[8:PBSPickLoc] R[64:PrecSpd]mm/sec FINE Offset,PR[9]    ;
 202:  R[26:PickStep]=1 ;
 203:  JMP LBL[99] ;
 204:   ;
 205:  ! ============================= ;
 206:  ! Fault: blow off, status 0, reset step ;
 207:  ! ============================= ;
 208:  LBL[88] ;
 209:  DO[375:X1.7Gripper.AirBlowACT]=OFF ;
 210:  TIMER[2]=STOP ;
 211:  R[25:PickStatus]=0 ;
 212:  R[26:PickStep]=0 ;
 213:  JMP LBL[99] ;
 214:   ;
 215:  LBL[99] ;
/POS
P[1]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   259.575989  mm,	Y =   562.567932  mm,	Z =  -319.240025  mm,
	W =     -.002920 deg,	P =    -1.495423 deg,	R =      .000134 deg
};
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
