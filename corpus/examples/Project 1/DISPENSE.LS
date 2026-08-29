/PROG  DISPENSE
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Dispense";
PROG_SIZE	= 0;
CREATE		= DATE 26-07-08  TIME 10:00:00;
MODIFIED	= DATE 26-07-08  TIME 10:00:00;
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
   1:  ! === DISPENSE === ;
   2:  ! Step-per-scan: ONE pass per call. ;
   3:  ! Dispenses glue onto the OB of the CURRENT ;
   4:  ! station (R[21:CurStation]), one station at a ;
   5:  ! time. PBS still gripped (vacuum on) - glue ;
   6:  ! goes on the OB; PLACE seats the PBS after. ;
   7:  ! Needle tool UT1 / UF1. ;
   8:  ! ;
   9:  ! Dispense trigger DO[437]: OFF=dispensing, ;
  10:  ! ON=stopped. Dispenser owns the dose time; we ;
  11:  ! pulse OFF then ON, holding R[65:DispTime] so ;
  12:  ! the edge registers + glue settles before the ;
  13:  ! needle moves off the point. Starts/ends ON. ;
  14:  ! ;
  15:  ! Needle down ONCE before the points, stays down ;
  16:  ! across all 3, lifted ONCE on the way out. ;
  17:  ! The 3 dispense points are stationary (FINE); ;
  18:  ! between them retreat to P[4]/P[9] with CNT10. ;
  19:  ! ;
  20:  ! Points (UT1/UF1, taught): ;
  21:  ! P[1] P[2]           shared reach-to-area ;
  22:  ! St1: P[3] enter, P[4] neutral-inside, ;
  23:  !      P[5] P[6] P[7] dispense ;
  24:  ! St2: P[8] enter, P[9] neutral-inside, ;
  25:  !      P[10] P[11] P[12] dispense ;
  26:  ! ;
  27:  ! States (R[67:DispStep]): ;
  28:  !  0 = gate, reach area P[1]->P[2] ;
  29:  !  1 = reach-in (branch on station) ;
  30:  !  2 = needle down ;
  31:  !  3-8 = 3 dispense points (pulse + settle) ;
  32:  !  9 = needle up ;
  33:  ! 10 = exit to P[2], report OK ;
  34:  ! ;
  35:  ! Registers: ;
  36:  ! R[10:Error Code]   shared fault code (out) ;
  37:  ! R[14:PistTimeout]  needle move timeout sec (in) ;
  38:  ! R[21:CurStation]   1=St1 2=St2 (in) ;
  39:  ! R[63:TravelSpd]    between-point speed (in) ;
  40:  ! R[64:PrecSpd]      precision speed (in) ;
  41:  ! R[65:DispTime]     glue pulse+settle sec (in) ;
  42:  ! R[66:DispStatus]   2=busy 1=ok 0=fault (out) ;
  43:  ! R[67:DispStep]     internal state 0-10 ;
  44:  ! PR[18:DispZLift]  tool-frame Z lift, set Z (in) ;
  45:  ! R[122:PistElapsed] timer readback scratch ;
  46:  ! R[154:St1Status]   1=St1 active (in) ;
  47:  ! R[155:St2Status]   1=St2 active (in) ;
  48:  ! ;
  49:  ! IO: ;
  50:  ! DI[368] needle UP   DI[369] needle DOWN ;
  51:  ! DO[372] needle piston ACT (ON=down OFF=up) ;
  52:  ! DO[437:X3.5 DispenseSTOP] OFF=dispense ON=stop ;
  53:  ! (dispenser busy signal = TBD, not used yet) ;
  54:  ! TIMER[2] shared RUN-phase timer. ;
  55:  ! ;
  56:  ! Error codes: ;
  57:  ! 501 = needle down FAIL ;
  58:  ! 502 = needle up FAIL ;
  59:  ! 503 = no OB station active ;
  60:   ;
  61:  R[66:DispStatus]=2 ;
  62:   ;
  63:  ! Sub owns tool; UF stays 1 all program ;
  64:  UTOOL_NUM=1 ;
  65:  UFRAME_NUM=1 ;
  66:   ;
  67:  ! --- Dispatch on state --- ;
  68:  SELECT R[67:DispStep]=0,JMP LBL[10] ;
  69:         =1,JMP LBL[20] ;
  70:         =2,JMP LBL[30] ;
  71:         =3,JMP LBL[31] ;
  72:         =4,JMP LBL[32] ;
  73:         =5,JMP LBL[33] ;
  74:         =6,JMP LBL[34] ;
  75:         =7,JMP LBL[35] ;
  76:         =8,JMP LBL[36] ;
  77:         =9,JMP LBL[40] ;
  78:         =10,JMP LBL[50] ;
  79:         ELSE,JMP LBL[10] ;
  80:   ;
  81:   ;
  82:  ! ============================= ;
  83:  ! State 0: gate + reach the stations area ;
  84:  ! ============================= ;
  85:  LBL[10] ;
  86:  ! Trigger safe (stopped) on entry ;
  87:  DO[437:X3.5 DispenseSTOP]=ON ;
  88:  ! Guard: current station must be active ;
  89:  IF R[21:CurStation]=1 AND R[154:St1Status]=1,JMP LBL[11] ;
  90:  IF R[21:CurStation]=2 AND R[155:St2Status]=1,JMP LBL[11] ;
  91:  R[10:Error Code]=503 ;
  92:  CALL SET_STR('No OB station',10) ;
  93:  JMP LBL[88] ;
  94:  LBL[11] ;
  95:  ! P[1] reach-to-area 1 ;
  96:L P[1] R[63:TravelSpd]mm/sec CNT100    ;
  97:  ! P[2] reach-to-area 2 (PLACE picks up here) ;
  98:L P[2] R[63:TravelSpd]mm/sec CNT100    ;
  99:  R[67:DispStep]=1 ;
 100:  JMP LBL[99] ;
 101:   ;
 102:   ;
 103:  ! ============================= ;
 104:  ! State 1: reach-in for the current station ;
 105:  ! P[3]/P[8] enter -> P[4]/P[9] neutral-inside ;
 106:  ! ============================= ;
 107:  LBL[20] ;
 108:  IF R[21:CurStation]=2,JMP LBL[21] ;
 109:  ! -- Station 1 -- ;
 110:  ! P[3] St1 enter ;
 111:L P[3] R[63:TravelSpd]mm/sec CNT100    ;
 112:  ! P[4] St1 neutral-inside ;
 113:L P[4] R[64:PrecSpd]mm/sec CNT5    ;
 114:  JMP LBL[29] ;
 115:  LBL[21] ;
 116:  ! -- Station 2 -- ;
 117:  ! P[8] St2 enter ;
 118:L P[8] R[63:TravelSpd]mm/sec CNT100    ;
 119:  ! P[9] St2 neutral-inside ;
 120:L P[9] R[64:PrecSpd]mm/sec CNT5    ;
 121:  LBL[29] ;
 122:  R[67:DispStep]=2 ;
 123:  JMP LBL[99] ;
 124:   ;
 125:   ;
 126:  ! ============================= ;
 127:  ! State 2: lower needle (once) ;
 128:  ! ============================= ;
 129:  LBL[30] ;
 130:  DO[372:X1.4Gripper.DisPistonACT]=ON ;
 131:  TIMER[2]=RESET ;
 132:  TIMER[2]=START ;
 133:  R[67:DispStep]=3 ;
 134:  JMP LBL[99] ;
 135:   ;
 136:  ! wait needle DOWN ;
 137:  LBL[31] ;
 138:  IF DI[369:X1.1 DispPistonDown]=ON,JMP LBL[311] ;
 139:  R[122:PistElapsed]=TIMER[2] ;
 140:  IF R[122:PistElapsed]<R[14:PistTimeout],JMP LBL[99] ;
 141:  R[10:Error Code]=501 ;
 142:  CALL SET_STR('Disp needle dn FAIL',10) ;
 143:  JMP LBL[88] ;
 144:  LBL[311] ;
 145:  TIMER[2]=STOP ;
 146:  R[67:DispStep]=4 ;
 147:  JMP LBL[99] ;
 148:   ;
 149:   ;
 150:  ! ============================= ;
 151:  ! Dispense point 1: P[5]/P[10] ;
 152:  ! ============================= ;
 153:  LBL[32] ;
 154:  IF R[21:CurStation]=2,JMP LBL[321] ;
 155:  ! P[5] St1 dispense 1 ;
 156:L P[5] R[64:PrecSpd]mm/sec FINE    ;
 157:  JMP LBL[322] ;
 158:  LBL[321] ;
 159:  ! P[10] St2 dispense 1 ;
 160:L P[10] R[64:PrecSpd]mm/sec FINE    ;
 161:  LBL[322] ;
 162:  ! fire glue: OFF=dispense, hold DispTime ;
 163:  DO[437:X3.5 DispenseSTOP]=OFF ;
 164:  TIMER[2]=RESET ;
 165:  TIMER[2]=START ;
 166:  R[67:DispStep]=5 ;
 167:  JMP LBL[99] ;
 168:   ;
 169:  ! settle done -> stop glue, retreat to P[4]/P[9] ;
 170:  LBL[33] ;
 171:  R[122:PistElapsed]=TIMER[2] ;
 172:  IF R[122:PistElapsed]<R[65:DispTime],JMP LBL[99] ;
 173:  TIMER[2]=STOP ;
 174:  DO[437:X3.5 DispenseSTOP]=ON ;
 175:  IF R[21:CurStation]=2,JMP LBL[331] ;
 176:L P[5] R[64:PrecSpd]mm/sec CNT5 Tool_Offset,PR[18]    ;
 177:L P[4] R[64:PrecSpd]mm/sec CNT5    ;
 178:  JMP LBL[332] ;
 179:  LBL[331] ;
 180:L P[10] R[64:PrecSpd]mm/sec CNT5 Tool_Offset,PR[18]    ;
 181:L P[9] R[64:PrecSpd]mm/sec CNT5    ;
 182:  LBL[332] ;
 183:  R[67:DispStep]=6 ;
 184:  JMP LBL[99] ;
 185:   ;
 186:   ;
 187:  ! ============================= ;
 188:  ! Dispense point 2: P[6]/P[11] ;
 189:  ! ============================= ;
 190:  LBL[34] ;
 191:  IF R[21:CurStation]=2,JMP LBL[341] ;
 192:  ! P[6] St1 dispense 2 ;
 193:L P[6] R[64:PrecSpd]mm/sec FINE    ;
 194:  JMP LBL[342] ;
 195:  LBL[341] ;
 196:  ! P[11] St2 dispense 2 ;
 197:L P[11] R[64:PrecSpd]mm/sec FINE    ;
 198:  LBL[342] ;
 199:  DO[437:X3.5 DispenseSTOP]=OFF ;
 200:  TIMER[2]=RESET ;
 201:  TIMER[2]=START ;
 202:  R[67:DispStep]=7 ;
 203:  JMP LBL[99] ;
 204:   ;
 205:  ! settle done -> stop glue, retreat to P[4]/P[9] ;
 206:  LBL[35] ;
 207:  R[122:PistElapsed]=TIMER[2] ;
 208:  IF R[122:PistElapsed]<R[65:DispTime],JMP LBL[99] ;
 209:  TIMER[2]=STOP ;
 210:  DO[437:X3.5 DispenseSTOP]=ON ;
 211:  IF R[21:CurStation]=2,JMP LBL[351] ;
 212:L P[6] R[64:PrecSpd]mm/sec CNT5 Tool_Offset,PR[18]    ;
 213:L P[4] R[64:PrecSpd]mm/sec CNT5    ;
 214:  JMP LBL[352] ;
 215:  LBL[351] ;
 216:L P[11] R[64:PrecSpd]mm/sec CNT5 Tool_Offset,PR[18]    ;
 217:L P[9] R[64:PrecSpd]mm/sec CNT5    ;
 218:  LBL[352] ;
 219:  R[67:DispStep]=8 ;
 220:  JMP LBL[99] ;
 221:   ;
 222:   ;
 223:  ! ============================= ;
 224:  ! Dispense point 3: P[7]/P[12] ;
 225:  ! ============================= ;
 226:  LBL[36] ;
 227:  IF R[21:CurStation]=2,JMP LBL[361] ;
 228:  ! P[7] St1 dispense 3 ;
 229:L P[7] R[64:PrecSpd]mm/sec FINE    ;
 230:  JMP LBL[362] ;
 231:  LBL[361] ;
 232:  ! P[12] St2 dispense 3 ;
 233:L P[12] R[64:PrecSpd]mm/sec FINE    ;
 234:  LBL[362] ;
 235:  DO[437:X3.5 DispenseSTOP]=OFF ;
 236:  TIMER[2]=RESET ;
 237:  TIMER[2]=START ;
 238:  R[67:DispStep]=9 ;
 239:  JMP LBL[99] ;
 240:   ;
 241:   ;
 242:  ! ============================= ;
 243:  ! State 9: stop glue, lift needle (once) ;
 244:  ! ============================= ;
 245:  LBL[40] ;
 246:  R[122:PistElapsed]=TIMER[2] ;
 247:  IF R[122:PistElapsed]<R[65:DispTime],JMP LBL[99] ;
 248:  TIMER[2]=STOP ;
 249:  DO[437:X3.5 DispenseSTOP]=ON ;
 250:  ! Lift off 3rd point + retreat to neutral ;
 251:  IF R[21:CurStation]=2,JMP LBL[401] ;
 252:L P[7] R[64:PrecSpd]mm/sec CNT5 Tool_Offset,PR[18]    ;
 253:L P[4] R[64:PrecSpd]mm/sec CNT5    ;
 254:  JMP LBL[402] ;
 255:  LBL[401] ;
 256:L P[12] R[64:PrecSpd]mm/sec CNT5 Tool_Offset,PR[18]    ;
 257:L P[9] R[64:PrecSpd]mm/sec CNT5    ;
 258:  LBL[402] ;
 259:  DO[372:X1.4Gripper.DisPistonACT]=OFF ;
 260:  TIMER[2]=RESET ;
 261:  TIMER[2]=START ;
 262:  R[67:DispStep]=10 ;
 263:  JMP LBL[99] ;
 264:   ;
 265:  ! ============================= ;
 266:  ! State 10: wait needle UP, exit to P[2] ;
 267:  ! ============================= ;
 268:  LBL[50] ;
 269:  IF DI[368:X1.0 DispPistonUp]=ON,JMP LBL[51] ;
 270:  R[122:PistElapsed]=TIMER[2] ;
 271:  IF R[122:PistElapsed]<R[14:PistTimeout],JMP LBL[99] ;
 272:  R[10:Error Code]=502 ;
 273:  CALL SET_STR('Disp needle up FAIL',10) ;
 274:  JMP LBL[88] ;
 275:  LBL[51] ;
 276:  TIMER[2]=STOP ;
 277:  ! exit per-station: neutral -> enter -> P[2] ;
 278:  IF R[21:CurStation]=2,JMP LBL[52] ;
 279:L P[4] R[64:PrecSpd]mm/sec CNT5    ;
 280:L P[3] R[63:TravelSpd]mm/sec CNT100    ;
 281:  JMP LBL[53] ;
 282:  LBL[52] ;
 283:L P[9] R[64:PrecSpd]mm/sec CNT5    ;
 284:L P[8] R[63:TravelSpd]mm/sec CNT100    ;
 285:  LBL[53] ;
 286:  ! park at P[2] for PLACE ;
 287:L P[2] R[63:TravelSpd]mm/sec CNT100    ;
 288:  R[10:Error Code]=0 ;
 289:  CALL SET_STR('Dispense OK',10) ;
 290:  R[66:DispStatus]=1 ;
 291:  R[67:DispStep]=0 ;
 292:  JMP LBL[99] ;
 293:   ;
 294:   ;
 295:  ! ============================= ;
 296:  ! Fault: glue OFF(stop), status 0, reset step ;
 297:  ! ============================= ;
 298:  LBL[88] ;
 299:  DO[437:X3.5 DispenseSTOP]=ON ;
 300:  TIMER[2]=STOP ;
 301:  R[66:DispStatus]=0 ;
 302:  R[67:DispStep]=0 ;
 303:  JMP LBL[99] ;
 304:   ;
 305:  LBL[99] ;
/POS
P[1]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -63.238989  mm,	Y =   496.230932  mm,	Z =  -96.00025  mm,
	W =     -.002920 deg,	P =    -1.495423 deg,	R =      .000134 deg
};
P[2]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -144.241968  mm,	Y =   634.419251  mm,	Z =   -110.000434  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[3]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -69.280989  mm,	Y =   705.367932  mm,	Z =  -163.465025  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[4]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -53.000968  mm,	Y =   705.367251  mm,	Z =   -187.037434  mm,
	W =     -.014188 deg,	P =    -18.895028 deg,	R =     -.000631 deg
};
P[5]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -41.892989  mm,	Y =   693.598932  mm,	Z = -191.247025  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[6]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -56.961968  mm,	Y =   693.620251  mm,	Z =   -191.6133434  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[7]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -49.198989  mm,	Y =   718.643932  mm,	Z =  -191.757025  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[8]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -69.280989  mm,	Y =   705.367932  mm,	Z =  -163.465025  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[9]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -53.000968  mm,	Y =   705.367251  mm,	Z =   -187.037434  mm,
	W =     -.014188 deg,	P =    -18.895028 deg,	R =     -.000631 deg
};
P[10]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -46.495989  mm,	Y =   692.175932  mm,	Z = -190.963025  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[11]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -61.556968  mm,	Y =   692.332251  mm,	Z =   -191.003434  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
P[12]{
   GP1:
	UF : 1, UT : 1,		CONFIG : 'F U T, 0, 0, 0',
	X =   -53.910989  mm,	Y =   716.705932  mm,	Z =  -190.968025  mm,
	W =     -.012020 deg,	P =    -18.894423 deg,	R =      .000134 deg
};
/END
