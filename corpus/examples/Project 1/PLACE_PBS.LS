/PROG  PLACE_PBS
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Place PBS";
PROG_SIZE	= 0;
CREATE		= DATE 26-07-08  TIME 15:00:00;
MODIFIED	= DATE 26-07-08  TIME 15:00:00;
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
   1:  ! === PLACE_PBS === ;
   2:  ! Step-per-scan: ONE pass per call. ;
   3:  ! Called by RUN after DISPENSE. Robot arrives ;
   4:  ! holding the squared PBS (vacuum on); glue is ;
   5:  ! already on the OB of the current station. ;
   6:  ! Seats the PBS on the OB, cures while holding, ;
   7:  ! dwell, releases, retracts. One station at a ;
   8:  ! time (R[21:CurStation]). Frame UT3 / UF1. ;
   9:  ! ;
  10:  ! 1st cure only: BOTH UV channels ON together ;
  11:  ! (robot-mounted lamps, level control). 2nd cure ;
  12:  ! left out for now. UV piston DO[373] not used. ;
  13:  ! ;
  14:  ! Offsets (plain Offset = active UF1 = world): ;
  15:  !  PR[16/17] = per-station place delta (final). ;
  16:  !  PR[18:DispZLift] = Z lift (shared w/ DISPENSE). ;
  17:  !  PR[19] = delta with Z lift added, so the ;
  18:  !  descent just-above -> final is a straight line. ;
  19:  ! ;
  20:  ! Motion (station-branched on R[21]): ;
  21:  !  P[1]   above both   CNT ;
  22:  !  P[2/3] above St     CNT ;
  23:  !  P[4/5] just-above   FINE Offset,PR[19] ;
  24:  !  P[4/5] final place  FINE Offset,PR[16/17] ;
  25:  !  ... cure / dwell / release ... ;
  26:  !  retract reversed (up straight, then out). ;
  27:  ! ;
  28:  ! States (R[51:PlaceStep]): ;
  29:  !  0 = gate, build PR[19], move above both ;
  30:  !  1 = above current station ;
  31:  !  2 = just-above final (Offset PR[19]) ;
  32:  !  3 = final place (Offset PR[16/17]) ;
  33:  !  4 = confirm PBS held (DI[370]) ;
  34:  !  5 = UV both channels ON, cure timer ;
  35:  !  6 = cure done -> UV OFF, post-cure timer ;
  36:  !  7 = dwell done -> release (vac OFF, blow) ;
  37:  !  8 = blow done -> retract, report OK ;
  38:  ! ;
  39:  ! Registers: ;
  40:  ! R[10:Error Code]    shared fault code (out) ;
  41:  ! R[21:CurStation]    1=St1 2=St2 (in) ;
  42:  ! R[30:GripBlowTime]  release air-blow pulse sec ;
  43:  ! R[50:PlaceStatus]   2=busy 1=ok 0=fault (out) ;
  44:  ! R[51:PlaceStep]     internal state 0-8 ;
  45:  ! R[53:CureTime]      UV on-time sec ;
  46:  ! R[54:PostCureDly]   dwell after cure, pre-release ;
  47:  ! R[63:TravelSpd]     approach/exit speed mm/sec ;
  48:  ! R[64:PrecSpd]       inside/precision speed mm/sec ;
  49:  ! R[122:PistElapsed]  timer readback scratch ;
  50:  ! R[154:St1Status]    1=St1 active (in) ;
  51:  ! R[155:St2Status]    1=St2 active (in) ;
  52:  ! ;
  53:  ! Position registers: ;
  54:  ! PR[16:PlaceDeltaSt1] St1 place delta (preset) ;
  55:  ! PR[17:PlaceDeltaSt2] St2 place delta (preset) ;
  56:  ! PR[18:DispZLift]     Z lift, shared w/ DISPENSE ;
  57:  ! PR[19:PlaceApp]      scratch = delta + Z lift ;
  58:  ! ;
  59:  ! Points (UF1/UT3, taught): ;
  60:  ! P[1] above both OB   P[2]/P[3] above St1/St2 ;
  61:  ! P[4]/P[5] inside (place) St1/St2 ;
  62:  ! ;
  63:  ! IO: ;
  64:  ! DI[370:X1.2 GripperVacuumReache] PBS held ;
  65:  ! DO[374:X1.6Gripper.VaccuumACT]  gripper vacuum ;
  66:  ! DO[375:X1.7Gripper.AirBlowACT]  release blow ;
  67:  ! DO[464:X4.0 UV Channel 1] 1st cure lamp A ;
  68:  ! DO[465:X4.1 UV Channel 2] 1st cure lamp B ;
  69:  ! TIMER[2] shared RUN-phase timer. ;
  70:  ! ;
  71:  ! Error codes: ;
  72:  ! 601 = no active OB station on entry ;
  73:  ! 602 = PBS not held at place (DI[370] OFF) ;
  74:   ;
  75:  R[50:PlaceStatus]=2 ;
  76:   ;
  77:  ! Sub owns tool; UF stays 1 all program ;
  78:  UTOOL_NUM=3 ;
  79:  UFRAME_NUM=1 ;
  80:   ;
  81:  ! --- Dispatch on state --- ;
  82:  SELECT R[51:PlaceStep]=0,JMP LBL[10] ;
  83:         =1,JMP LBL[20] ;
  84:         =2,JMP LBL[30] ;
  85:         =3,JMP LBL[40] ;
  86:         =4,JMP LBL[50] ;
  87:         =5,JMP LBL[55] ;
  88:         =6,JMP LBL[60] ;
  89:         =7,JMP LBL[65] ;
  90:         =8,JMP LBL[70] ;
  91:         ELSE,JMP LBL[10] ;
  92:   ;
  93:   ;
  94:  ! ============================= ;
  95:  ! State 0: gate, build PR[19], go above both ;
  96:  ! ============================= ;
  97:  LBL[10] ;
  98:  IF R[21:CurStation]=1 AND R[154:St1Status]=1,JMP LBL[11] ;
  99:  IF R[21:CurStation]=2 AND R[155:St2Status]=1,JMP LBL[11] ;
 100:  R[10:Error Code]=601 ;
 101:  CALL SET_STR('No OB station',10) ;
 102:  JMP LBL[88] ;
 103:  LBL[11] ;
 104:  ! PR[19] = station delta; add Z lift into Z so ;
 105:  ! just-above sits straight over the final point ;
 106:  IF R[21:CurStation]=2,JMP LBL[12] ;
 107:  PR[19:PlaceApp]=PR[16:PlaceDeltaSt1] ;
 108:  JMP LBL[13] ;
 109:  LBL[12] ;
 110:  PR[19:PlaceApp]=PR[17:PlaceDeltaSt2] ;
 111:  LBL[13] ;
 112:  PR[19,3]=(PR[19,3]+PR[18,3]) ;
 113:L P[1:Above both OB] R[63:TravelSpd]mm/sec CNT100    ;
 114:  R[51:PlaceStep]=1 ;
 115:  JMP LBL[99] ;
 116:   ;
 117:   ;
 118:  ! ============================= ;
 119:  ! State 1: above current station ;
 120:  ! ============================= ;
 121:  LBL[20] ;
 122:  IF R[21:CurStation]=2,JMP LBL[21] ;
 123:L P[2:Above St1] R[63:TravelSpd]mm/sec CNT100    ;
 124:  JMP LBL[29] ;
 125:  LBL[21] ;
 126:L P[3:Above St2] R[63:TravelSpd]mm/sec CNT100    ;
 127:  LBL[29] ;
 128:  R[51:PlaceStep]=2 ;
 129:  JMP LBL[99] ;
 130:   ;
 131:   ;
 132:  ! ============================= ;
 133:  ! State 2: just-above final (delta + Z lift) ;
 134:  ! ============================= ;
 135:  LBL[30] ;
 136:  IF R[21:CurStation]=2,JMP LBL[31] ;
 137:L P[4:Inside St1] R[64:PrecSpd]mm/sec FINE Offset,PR[19]    ;
 138:  JMP LBL[39] ;
 139:  LBL[31] ;
 140:L P[5:Inside St2] R[64:PrecSpd]mm/sec FINE Offset,PR[19]    ;
 141:  LBL[39] ;
 142:  R[51:PlaceStep]=3 ;
 143:  JMP LBL[99] ;
 144:   ;
 145:   ;
 146:  ! ============================= ;
 147:  ! State 3: final place (delta only) ;
 148:  ! ============================= ;
 149:  LBL[40] ;
 150:  IF R[21:CurStation]=2,JMP LBL[41] ;
 151:L P[4:Inside St1] R[64:PrecSpd]mm/sec FINE Offset,PR[16]    ;
 152:  JMP LBL[49] ;
 153:  LBL[41] ;
 154:L P[5:Inside St2] R[64:PrecSpd]mm/sec FINE Offset,PR[17]    ;
 155:  LBL[49] ;
 156:  R[51:PlaceStep]=4 ;
 157:  JMP LBL[99] ;
 158:   ;
 159:   ;
 160:  ! ============================= ;
 161:  ! State 4: confirm PBS still held (gripper) ;
 162:  ! ============================= ;
 163:  LBL[50] ;
 164:  IF DI[370:X1.2 GripperVacuumReache]=ON,JMP LBL[51] ;
 165:  R[10:Error Code]=602 ;
 166:  CALL SET_STR('PBS not held',10) ;
 167:  JMP LBL[88] ;
 168:  LBL[51] ;
 169:  R[51:PlaceStep]=5 ;
 170:  JMP LBL[99] ;
 171:   ;
 172:   ;
 173:  ! ============================= ;
 174:  ! State 5: UV both channels ON, cure timer ;
 175:  ! ============================= ;
 176:  LBL[55] ;
 177:  DO[464:X4.0 UV Channel 1]=ON ;
 178:  DO[465:X4.1 UV Channel 2]=ON ;
 179:  TIMER[2]=RESET ;
 180:  TIMER[2]=START ;
 181:  R[51:PlaceStep]=6 ;
 182:  JMP LBL[99] ;
 183:   ;
 184:   ;
 185:  ! ============================= ;
 186:  ! State 6: cure done -> UV OFF, post-cure timer ;
 187:  ! ============================= ;
 188:  LBL[60] ;
 189:  R[122:PistElapsed]=TIMER[2] ;
 190:  IF R[122:PistElapsed]<R[53:CureTime],JMP LBL[99] ;
 191:  TIMER[2]=STOP ;
 192:  DO[464:X4.0 UV Channel 1]=OFF ;
 193:  DO[465:X4.1 UV Channel 2]=OFF ;
 194:  TIMER[2]=RESET ;
 195:  TIMER[2]=START ;
 196:  R[51:PlaceStep]=7 ;
 197:  JMP LBL[99] ;
 198:   ;
 199:   ;
 200:  ! ============================= ;
 201:  ! State 7: dwell done -> release (vac OFF, blow) ;
 202:  ! ============================= ;
 203:  LBL[65] ;
 204:  R[122:PistElapsed]=TIMER[2] ;
 205:  IF R[122:PistElapsed]<R[54:PostCureDly],JMP LBL[99] ;
 206:  TIMER[2]=STOP ;
 207:  DO[374:X1.6Gripper.VaccuumACT]=OFF ;
 208:  DO[375:X1.7Gripper.AirBlowACT]=ON ;
 209:  TIMER[2]=RESET ;
 210:  TIMER[2]=START ;
 211:  R[51:PlaceStep]=8 ;
 212:  JMP LBL[99] ;
 213:   ;
 214:   ;
 215:  ! ============================= ;
 216:  ! State 8: blow done -> retract (up straight, ;
 217:  !  then out), report OK ;
 218:  ! ============================= ;
 219:  LBL[70] ;
 220:  R[122:PistElapsed]=TIMER[2] ;
 221:  IF R[122:PistElapsed]<R[30:GripBlowTime],JMP LBL[99] ;
 222:  TIMER[2]=STOP ;
 223:  DO[375:X1.7Gripper.AirBlowACT]=OFF ;
 224:  IF R[21:CurStation]=2,JMP LBL[71] ;
 225:L P[4:Inside St1] R[64:PrecSpd]mm/sec FINE Offset,PR[19]    ;
 226:L P[2:Above St1] R[63:TravelSpd]mm/sec CNT100    ;
 227:  JMP LBL[72] ;
 228:  LBL[71] ;
 229:L P[5:Inside St2] R[64:PrecSpd]mm/sec FINE Offset,PR[19]    ;
 230:L P[3:Above St2] R[63:TravelSpd]mm/sec CNT100    ;
 231:  LBL[72] ;
 232:L P[1:Above both OB] R[63:TravelSpd]mm/sec CNT100    ;
 233:  R[10:Error Code]=0 ;
 234:  CALL SET_STR('Place OK',10) ;
 235:  R[50:PlaceStatus]=1 ;
 236:  R[51:PlaceStep]=0 ;
 237:  JMP LBL[99] ;
 238:   ;
 239:   ;
 240:  ! ============================= ;
 241:  ! Fault: UV OFF, blow OFF. Vacuum left ON ;
 242:  !  (keep holding PBS). Status 0, reset step. ;
 243:  ! ============================= ;
 244:  LBL[88] ;
 245:  DO[464:X4.0 UV Channel 1]=OFF ;
 246:  DO[465:X4.1 UV Channel 2]=OFF ;
 247:  DO[375:X1.7Gripper.AirBlowACT]=OFF ;
 248:  TIMER[2]=STOP ;
 249:  R[50:PlaceStatus]=0 ;
 250:  R[51:PlaceStep]=0 ;
 251:  JMP LBL[99] ;
 252:   ;
 253:  LBL[99] ;
/POS
P[1]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   -133.703989  mm,	Y =   648.246932  mm,	Z =  -56.000025  mm,
	W =     1.328920 deg,	P =    -2.847423 deg,	R =      0.346134 deg
};
P[2]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   -79.434989  mm,	Y =   703.281932  mm,	Z =  -153.594025  mm,
	W =     1.328920 deg,	P =    -2.847423 deg,	R =      0.346134 deg
};
P[3]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   -79.434989  mm,	Y =   703.281932  mm,	Z =  -153.594025  mm,
	W =     1.328920 deg,	P =    -2.847423 deg,	R =      0.346134 deg
};
P[4]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   -56.813989  mm,	Y =   703.123932  mm,	Z =  -186.574025  mm,
	W =     0.745920 deg,	P =    -2.849423 deg,	R =      0.355134 deg
};
P[5]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   -59.659989  mm,	Y =   702.961932  mm,	Z =  -186.288025  mm,
	W =     1.328920 deg,	P =    -2.847423 deg,	R =      0.346134 deg
};

/END
