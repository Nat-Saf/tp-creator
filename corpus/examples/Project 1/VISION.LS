/PROG  VISION
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Vision";
PROG_SIZE	= 0;
CREATE		= DATE 26-07-05  TIME 18:40:00;
MODIFIED	= DATE 26-07-05  TIME 19:05:00;
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
   1:  ! === VISION === ;
   2:  ! Step-per-scan: ONE pass per call. ;
   3:  ! Inspect PBS orientation via Keyence camera. ;
   4:  ! Frame UT3 / UF0. ;
   5:  ! Trigger DO high, wait fresh result (group ;
   6:  ! counter changes), read pass/fail bit. ;
   7:  ! No image -> retry; 3 total tries -> fault. ;
   8:  ! Result to RUN via R[32:VisResult] 1=pass 2=no-go; ;
   9:  ! status stays 2/1/0. Does NOT touch PR[8]. ;
  10:  ! ;
  11:  ! R[80:BypCam]=1 bypasses the WHOLE camera seq: ;
  12:  ! skip ready-check/trigger/wait/read, move to ;
  13:  ! inspect and back, force pass. Movement only. ;
  14:  ! ;
  15:  ! *** Camera I/O are PLACEHOLDERS from 2000 - ;
  16:  ! *** renumber when real ports known. ;
  17:  ! ;
  18:  ! States (R[34:VisStep]): ;
  19:  !  0 = frame, ready-check, move P[1]->P[2]; ;
  20:  !      if BypCam -> force pass, go to state 4 ;
  21:  !  1 = latch counter, trigger camera, timer ;
  22:  !  2 = wait fresh result / timeout+retry ;
  23:  !  3 = read pass/fail -> R[32:VisResult] ;
  24:  !  4 = exit P[1], report done ;
  25:  ! ;
  26:  ! Registers: ;
  27:  ! R[10:Error Code]    shared fault code (out) ;
  28:  ! R[32:VisResult]     1=pass 2=no-go (out to RUN) ;
  29:  ! R[33:VisStatus]     2=busy 1=ok 0=fault (out) ;
  30:  ! R[34:VisStep]       internal state 0-4 ;
  31:  ! R[35:VisTryCnt]     capture attempt counter ;
  32:  ! R[36:CamTimeout]    per-try image timeout s (def3) ;
  33:  ! R[37:CamResPrev]    pre-trigger result-count latch ;
  34:  ! R[80:BypCam]        1=bypass ALL camera (move only) ;
  35:  ! R[83:BypCamReady]   1=skip camera-ready check ;
  36:  ! R[122:PistElapsed]  timer readback scratch ;
  37:  ! ;
  38:  ! Points (UF0/UT3, taught; no POS comments): ;
  39:  ! P[1] = on-the-way point (in and out) ;
  40:  ! P[2] = inspection pose ;
  41:  ! ;
  42:  ! IO (PLACEHOLDER, renumber later): ;
  43:  ! DO[2000:Cam Trigger]     set HIGH to capture ;
  44:  ! DI[2000:Cam Result]      1=pass 0=fail ;
  45:  ! DI[2001:Cam Ready]       ON=camera on/ready ;
  46:  ! GI[1:Cam Result Count]   image/result number ;
  47:  ! TIMER[2] shared RUN-phase timer. ;
  48:  ! ;
  49:  ! Error codes: ;
  50:  ! 301 = no image after 3 tries ;
  51:  ! 302 = camera not ready (DI[2001] OFF) ;
  52:   ;
  53:  R[33:VisStatus]=2 ;
  54:   ;
  55:  ! --- Dispatch on state --- ;
  56:  SELECT R[34:VisStep]=0,JMP LBL[10] ;
  57:         =1,JMP LBL[20] ;
  58:         =2,JMP LBL[30] ;
  59:         =3,JMP LBL[40] ;
  60:         =4,JMP LBL[50] ;
  61:         ELSE,JMP LBL[10] ;
  62:   ;
  63:   ;
  64:  ! ============================= ;
  65:  ! State 0: frame, ready-check, move to inspect. ;
  66:  ! BypCam -> skip checks, move only, force pass. ;
  67:  ! ============================= ;
  68:  LBL[10] ;
  69:  UTOOL_NUM=3 ;
  70:  UFRAME_NUM=1 ;
  71:  ! Full bypass skips ready-check ;
  72:  IF R[80:BypCam]=1,JMP LBL[11] ;
  73:  ! Camera ready (bypass R[83]) ;
  74:  IF R[83:BypCamReady]=1,JMP LBL[11] ;
  75:  IF DI[2001:Cam Ready]=ON,JMP LBL[11] ;
  76:  R[10:Error Code]=302 ;
  77:  CALL SET_STR('Camera not ready',10) ;
  78:  JMP LBL[88] ;
  79:  LBL[11] ;
  80:  R[35:VisTryCnt]=0 ;
  81:L P[1] R[63:TravelSpd]mm/sec CNT100    ;
  82:L P[2] R[63:TravelSpd]mm/sec FINE    ;
  83:  ! Full bypass: force pass, skip camera ;
  84:  IF R[80:BypCam]=1,JMP LBL[13] ;
  85:  R[34:VisStep]=1 ;
  86:  JMP LBL[99] ;
  87:  LBL[13] ;
  88:  R[32:VisResult]=1 ;
  89:  CALL SET_STR('Vision bypass',10) ;
  90:  R[34:VisStep]=4 ;
  91:  JMP LBL[99] ;
  92:   ;
  93:   ;
  94:  ! ============================= ;
  95:  ! State 1: latch result count, trigger camera ;
  96:  ! ============================= ;
  97:  LBL[20] ;
  98:  R[37:CamResPrev]=GI[1:Cam Result Count] ;
  99:  DO[2000:Cam Trigger]=ON ;
 100:  TIMER[2]=RESET ;
 101:  TIMER[2]=START ;
 102:  R[34:VisStep]=2 ;
 103:  JMP LBL[99] ;
 104:   ;
 105:   ;
 106:  ! ============================= ;
 107:  ! State 2: wait fresh result; timeout -> retry ;
 108:  ! (3 total tries) then fault 301. ;
 109:  ! ============================= ;
 110:  LBL[30] ;
 111:  ! Fresh result = counter changed ;
 112:  IF GI[1:Cam Result Count]<>R[37:CamResPrev],JMP LBL[32] ;
 113:  R[122:PistElapsed]=TIMER[2] ;
 114:  IF R[122:PistElapsed]<R[36:CamTimeout],JMP LBL[99] ;
 115:  ! Timeout, no image: count try ;
 116:  TIMER[2]=STOP ;
 117:  DO[2000:Cam Trigger]=OFF ;
 118:  R[35:VisTryCnt]=(R[35:VisTryCnt]+1) ;
 119:  IF R[35:VisTryCnt]<3,JMP LBL[31] ;
 120:  R[10:Error Code]=301 ;
 121:  CALL SET_STR('No image',10) ;
 122:  JMP LBL[88] ;
 123:  LBL[31] ;
 124:  ! Retry: re-trigger ;
 125:  R[34:VisStep]=1 ;
 126:  JMP LBL[99] ;
 127:  LBL[32] ;
 128:  ! Fresh image captured ;
 129:  TIMER[2]=STOP ;
 130:  DO[2000:Cam Trigger]=OFF ;
 131:  R[34:VisStep]=3 ;
 132:  JMP LBL[99] ;
 133:   ;
 134:   ;
 135:  ! ============================= ;
 136:  ! State 3: read pass/fail -> R[32:VisResult] ;
 137:  ! (bypass handled in state 0) ;
 138:  ! ============================= ;
 139:  LBL[40] ;
 140:  IF DI[2000:Cam Result]=ON,JMP LBL[41] ;
 141:  ! Fail -> no-go ;
 142:  R[32:VisResult]=2 ;
 143:  CALL SET_STR('Vision no-go',10) ;
 144:  JMP LBL[42] ;
 145:  LBL[41] ;
 146:  ! Pass ;
 147:  R[32:VisResult]=1 ;
 148:  CALL SET_STR('Vision pass',10) ;
 149:  LBL[42] ;
 150:  R[34:VisStep]=4 ;
 151:  JMP LBL[99] ;
 152:   ;
 153:   ;
 154:  ! ============================= ;
 155:  ! State 4: exit on-way point, report done ;
 156:  ! ============================= ;
 157:  LBL[50] ;
 158:L P[1] R[63:TravelSpd]mm/sec CNT100    ;
 159:  R[10:Error Code]=0 ;
 160:  R[33:VisStatus]=1 ;
 161:  R[34:VisStep]=0 ;
 162:  JMP LBL[99] ;
 163:   ;
 164:   ;
 165:  ! ============================= ;
 166:  ! Fault: trigger off, status 0, reset step ;
 167:  ! ============================= ;
 168:  LBL[88] ;
 169:  DO[2000:Cam Trigger]=OFF ;
 170:  TIMER[2]=STOP ;
 171:  R[33:VisStatus]=0 ;
 172:  R[34:VisStep]=0 ;
 173:  JMP LBL[99] ;
 174:   ;
 175:  LBL[99] ;
/POS
P[1]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   432.000989  mm,	Y =   415.000932  mm,	Z =  -83.332025  mm,
	W =     -.002920 deg,	P =    -1.495423 deg,	R =      .000134 deg
};
P[2]{
   GP1:
	UF : 1, UT : 3,		CONFIG : 'F U T, 0, 0, 0',
	X =   473.266968  mm,	Y =   415.410251  mm,	Z =   -83.856434  mm,
	W =     -.004188 deg,	P =    -1.496028 deg,	R =     -.000631 deg
};
/END
