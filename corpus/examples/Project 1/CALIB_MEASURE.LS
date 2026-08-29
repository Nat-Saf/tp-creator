/PROG  CALIB_MEASURE
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Calib measure";
PROG_SIZE	= 0;
CREATE		= DATE 26-06-21  TIME 11:06:36;
MODIFIED	= DATE 26-06-23  TIME 17:00:00;
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
LOCAL_REGISTERS	= 0,0,0;
/APPL
/MN
   1:  ! === CALIB_MEASURE === ;
   2:  ! Step-per-scan; called by CALIB_NEEDLE. ;
   3:  ! 4 CW sweeps: N->E->S->W. ;
   4:  ! Two beam-edge midpoints per beam -> line. ;
   5:  ! Parametric intersection solve -> tip XY. ;
   6:  ! Z supplied by R[116:TipZ] from CALIB_NEEDLE. ;
   7:  ! ;
   8:  ! States: 0=setup  1=N sweep  2=E sweep ;
   9:  !         3=S sweep  4=W sweep  5=solve ;
   10:  !         6=store data, return home ;
   11:  ! ;
   12:  ! Registers: ;
   13:  ! R[10:ErrCode]      shared fault code (out) ;
   14:  ! R[101:MeasStatus]  2=busy 1=ok 0=fault (out) ;
   15:  ! R[110:Mode]        0=set ref 1=calib 2=revert ;
   16:  ! R[111:ProbeSpd]    sweep speed mm/sec ;
   17:  ! R[116:TipZ]        Z where tip broke beam (in) ;
   18:  ! R[120:MeasStep]    internal state 0-6 ;
   19:  ! R[123:TipX]        solved tip X (out) ;
   20:  ! R[124:TipY]        solved tip Y (out) ;
   21:  ! R[125:EdgeTmp]     temp: beam entry coord ;
   22:  ! R[128:ProbeZDrop]  Z below TipZ for sweeps ;
   23:  ! R[129:DetGuard]    min abs(Det) guard value ;
   24:  ! R[130:NmidX]       North sweep midpoint X ;
   25:  ! R[131:NmidY]       North sweep midpoint Y ;
   26:  ! R[132:EmidY]       East sweep midpoint Y ;
   27:  ! R[133:EmidX]       East sweep midpoint X ;
   28:  ! R[134:SmidX]       South sweep midpoint X ;
   29:  ! R[135:SmidY]       South sweep midpoint Y ;
   30:  ! R[136:WmidY]       West sweep midpoint Y ;
   31:  ! R[137:WmidX]       West sweep midpoint X ;
   32:  ! R[140:dxA]         Line A delta X (Y-beam N->S) ;
   33:  ! R[141:dyA]         Line A delta Y ;
   34:  ! R[142:dxB]         Line B delta X (X-beam E->W) ;
   35:  ! R[143:dyB]         Line B delta Y ;
   36:  ! R[144:Det]         determinant ;
   37:  ! R[145:Tmp]         scratch / abs guard ;
   38:  ! R[146:Tmp2]        scratch (Ex-Nx) ;
   39:  ! R[147:Tmp3]        scratch (Ey-Ny) ;
   40:  ! R[148:NumT]        numerator T ;
   41:  ! R[149:t]           parametric t ;
   42:  ! ;
   43:  ! Position registers: ;
   44:  ! PR[3:CalibDelta]   XYZ offset vs reference (out) ;
   45:  ! PR[4:RefTipPos]    reference tip XYZ (mode 0 out) ;
   46:  ! PR[29:ScratchPos]  temp position scratch ;
   47:  ! PR[30:ZdropOfs]    tool offset: Z drop to sweep height ;
   48:  ! ;
   49:  ! Points: ;
   50:  ! P[1] calib home - safe position above beam zone ;
   51:  ! P[2] North sweep start - W end of Y-beam row ;
   52:  ! P[3] North sweep end   - E end of Y-beam row ;
   53:  ! P[4] East sweep start  - N end of X-beam column ;
   54:  ! P[5] East sweep end    - S end of X-beam column ;
   55:  ! P[6] South sweep start - E end of Y-beam row ;
   56:  ! P[7] South sweep end   - W end of Y-beam row ;
   57:  ! P[8] West sweep start  - S end of X-beam column ;
   58:  ! P[9] West sweep end    - N end of X-beam column ;
   59:  ! ;
   60:  ! DI[435] X-beam  (crossed: E and W sweeps) ;
   61:  ! DI[436] Y-beam  (crossed: N and S sweeps) ;
   62:  ! ;
   63:  ! PR[30:ZdropOfs].Z = TipZ - P[2].Z - ProbeZDrop ;
   64:  ! Applied as Tool_Offset on all sweeps. ;
   65:  ! Tip runs at Z = TipZ - ProbeZDrop during sweeps. ;
   66:  ! ;
   67:  ! SKIP logic: fires on beam detect -> fall thru. ;
   68:  ! Motion ends without detect -> jump to fault. ;
   69:  ! ;
   70:  ! NOTE: UTOOL[1] is NOT changed in this program. ;
   71:  ! UTOOL snapshot/update done in CALIB_NEEDLE ;
   72:  ! State 7, after beam verification passes. ;
   73:   ;
   74:  R[101:MeasStatus]=2 ;
   75:   ;
   76:  ! --- Dispatch on state --- ;
   77:  SELECT R[120:MeasStep]=0,JMP LBL[10] ;
   78:         =1,JMP LBL[20] ;
   79:         =2,JMP LBL[30] ;
   80:         =3,JMP LBL[40] ;
   81:         =4,JMP LBL[50] ;
   82:         =5,JMP LBL[60] ;
   83:         =6,JMP LBL[70] ;
   84:         ELSE,JMP LBL[10] ;
   85:   ;
   86:  ! ============================= ;
   87:  ! State 0: build Z-drop offset, move to P[1] ;
   88:  ! Seed PR[29:ScratchPos] from P[2] to read P[2].Z. ;
   89:  ! PR[30:ZdropOfs].Z = TipZ - P[2].Z - ProbeZDrop. ;
   90:  ! Result: all sweeps run at Z = TipZ - ProbeZDrop. ;
   91:  ! ============================= ;
   92:  LBL[10] ;
   93:  ! Measure tool must match CALIB_NEEDLE: UT2 in ;
   94:  ! Mode 1 (fixed ref), UT1 in Mode 0. ;
   95:  UTOOL_NUM=1 ;
   96:  IF R[110:Mode]<>1,JMP LBL[2] ;
   97:  UTOOL_NUM=2 ;
   98:  LBL[2] ;
   99:  UFRAME_NUM=1 ;
   100:  ! Seed scratch from P[2] to get its Z reference ;
   101:  PR[29:ScratchPos]=P[2] ;
   102:  ! Build Z-drop tool offset (XY=0, Z only) ;
   103:  PR[30,1]=0 ;
   104:  PR[30,2]=0 ;
   105:  PR[30,3]=R[116:TipZ]-PR[29,3]-R[128:ProbeZDrop] ;
   106:  PR[30,4]=0 ;
   107:  PR[30,5]=0 ;
   108:  PR[30,6]=0 ;
   109:  ! Move to safe home above beam zone ;
   110:L P[1] 100mm/sec FINE    ;
   111:  R[120:MeasStep]=1 ;
   112:  JMP LBL[99] ;
   113:   ;
   114:   ;
   115:  ! ============================= ;
   116:  ! State 1: NORTH sweep P[2]->P[3] ;
   117:  ! Y-beam DI[436]  direction: W->E (X incr) ;
   118:  ! P[2] = N sweep W start ;
   119:  ! P[3] = N sweep E end ;
   120:  ! Result: R[130:NmidX]  R[131:NmidY] ;
   121:  ! ============================= ;
   122:  LBL[20] ;
   123:  ! Approach N sweep start at sweep Z ;
   124:L P[2] 100mm/sec FINE Tool_Offset,PR[30]    ;
   125:  ! Entry edge: DI[436] ON -> skip -> capture X ;
   126:  SKIP CONDITION DI[436]=ON ;
   127:L P[3] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[24]    ;
   128:  PR[29:ScratchPos]=LPOS ;
   129:  R[125:EdgeTmp]=PR[29,1] ;
   130:  JMP LBL[25] ;
   131:  LBL[24] ;
   132:  ! Entry not found ;
   133:  R[10:ErrCode]=804 ;
   134:  CALL SET_STR('Y-beam N find FAIL',10) ;
   135:  JMP LBL[88] ;
   136:  LBL[25] ;
   137:  ! Exit edge: DI[436] OFF -> skip -> capture X ;
   138:  SKIP CONDITION DI[436]=OFF ;
   139:L P[3] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[26]    ;
   140:  PR[29:ScratchPos]=LPOS ;
   141:  ! NmidX = (entry_X + exit_X) / 2 ;
   142:  R[130:NmidX]=(R[125:EdgeTmp]+PR[29,1]) ;
   143:  R[130:NmidX]=(R[130:NmidX]/2) ;
   144:  ! NmidY = Y of this sweep row ;
   145:  R[131:NmidY]=PR[29,2] ;
   146:  R[120:MeasStep]=2 ;
   147:  JMP LBL[99] ;
   148:  LBL[26] ;
   149:  ! Exit not found ;
   150:  R[10:ErrCode]=804 ;
   151:  CALL SET_STR('Y-beam N find FAIL',10) ;
   152:  JMP LBL[88] ;
   153:   ;
   154:   ;
   155:  ! ============================= ;
   156:  ! State 2: EAST sweep P[4]->P[5] ;
   157:  ! X-beam DI[435]  direction: N->S (Y decr) ;
   158:  ! P[4] = E sweep N start ;
   159:  ! P[5] = E sweep S end ;
   160:  ! Result: R[132:EmidY]  R[133:EmidX] ;
   161:  ! ============================= ;
   162:  LBL[30] ;
   163:  ! Approach E sweep start at sweep Z ;
   164:L P[4] 100mm/sec FINE Tool_Offset,PR[30]    ;
   165:  ! Entry edge: DI[435] ON -> skip -> capture Y ;
   166:  SKIP CONDITION DI[435]=ON ;
   167:L P[5] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[34]    ;
   168:  PR[29:ScratchPos]=LPOS ;
   169:  R[125:EdgeTmp]=PR[29,2] ;
   170:  JMP LBL[35] ;
   171:  LBL[34] ;
   172:  ! Entry not found ;
   173:  R[10:ErrCode]=805 ;
   174:  CALL SET_STR('X-beam E find FAIL',10) ;
   175:  JMP LBL[88] ;
   176:  LBL[35] ;
   177:  ! Exit edge: DI[435] OFF -> skip -> capture Y ;
   178:  SKIP CONDITION DI[435]=OFF ;
   179:L P[5] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[36]    ;
   180:  PR[29:ScratchPos]=LPOS ;
   181:  ! EmidY = (entry_Y + exit_Y) / 2 ;
   182:  R[132:EmidY]=(R[125:EdgeTmp]+PR[29,2]) ;
   183:  R[132:EmidY]=(R[132:EmidY]/2) ;
   184:  ! EmidX = X of this sweep column ;
   185:  R[133:EmidX]=PR[29,1] ;
   186:  R[120:MeasStep]=3 ;
   187:  JMP LBL[99] ;
   188:  LBL[36] ;
   189:  ! Exit not found ;
   190:  R[10:ErrCode]=805 ;
   191:  CALL SET_STR('X-beam E find FAIL',10) ;
   192:  JMP LBL[88] ;
   193:   ;
   194:   ;
   195:  ! ============================= ;
   196:  ! State 3: SOUTH sweep P[6]->P[7] ;
   197:  ! Y-beam DI[436]  direction: E->W (X decr) ;
   198:  ! P[6] = S sweep E start ;
   199:  ! P[7] = S sweep W end ;
   200:  ! Result: R[134:SmidX]  R[135:SmidY] ;
   201:  ! ============================= ;
   202:  LBL[40] ;
   203:  ! Approach S sweep start at sweep Z ;
   204:L P[6] 100mm/sec FINE Tool_Offset,PR[30]    ;
   205:  ! Entry edge: DI[436] ON -> skip -> capture X ;
   206:  SKIP CONDITION DI[436]=ON ;
   207:L P[7] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[44]    ;
   208:  PR[29:ScratchPos]=LPOS ;
   209:  R[125:EdgeTmp]=PR[29,1] ;
   210:  JMP LBL[45] ;
   211:  LBL[44] ;
   212:  ! Entry not found ;
   213:  R[10:ErrCode]=804 ;
   214:  CALL SET_STR('Y-beam S find FAIL',10) ;
   215:  JMP LBL[88] ;
   216:  LBL[45] ;
   217:  ! Exit edge: DI[436] OFF -> skip -> capture X ;
   218:  SKIP CONDITION DI[436]=OFF ;
   219:L P[7] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[46]    ;
   220:  PR[29:ScratchPos]=LPOS ;
   221:  ! SmidX = (entry_X + exit_X) / 2 ;
   222:  R[134:SmidX]=(R[125:EdgeTmp]+PR[29,1]) ;
   223:  R[134:SmidX]=(R[134:SmidX]/2) ;
   224:  ! SmidY = Y of this sweep row ;
   225:  R[135:SmidY]=PR[29,2] ;
   226:  R[120:MeasStep]=4 ;
   227:  JMP LBL[99] ;
   228:  LBL[46] ;
   229:  ! Exit not found ;
   230:  R[10:ErrCode]=804 ;
   231:  CALL SET_STR('Y-beam S find FAIL',10) ;
   232:  JMP LBL[88] ;
   233:   ;
   234:   ;
   235:  ! ============================= ;
   236:  ! State 4: WEST sweep P[8]->P[9] ;
   237:  ! X-beam DI[435]  direction: S->N (Y incr) ;
   238:  ! P[8] = W sweep S start ;
   239:  ! P[9] = W sweep N end ;
   240:  ! Result: R[136:WmidY]  R[137:WmidX] ;
   241:  ! ============================= ;
   242:  LBL[50] ;
   243:  ! Approach W sweep start at sweep Z ;
   244:L P[8] 100mm/sec FINE Tool_Offset,PR[30]    ;
   245:  ! Entry edge: DI[435] ON -> skip -> capture Y ;
   246:  SKIP CONDITION DI[435]=ON ;
   247:L P[9] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[54]    ;
   248:  PR[29:ScratchPos]=LPOS ;
   249:  R[125:EdgeTmp]=PR[29,2] ;
   250:  JMP LBL[55] ;
   251:  LBL[54] ;
   252:  ! Entry not found ;
   253:  R[10:ErrCode]=805 ;
   254:  CALL SET_STR('X-beam W find FAIL',10) ;
   255:  JMP LBL[88] ;
   256:  LBL[55] ;
   257:  ! Exit edge: DI[435] OFF -> skip -> capture Y ;
   258:  SKIP CONDITION DI[435]=OFF ;
   259:L P[9] R[111:ProbeSpd]mm/sec FINE Tool_Offset,PR[30] Skip,LBL[56]    ;
   260:  PR[29:ScratchPos]=LPOS ;
   261:  ! WmidY = (entry_Y + exit_Y) / 2 ;
   262:  R[136:WmidY]=(R[125:EdgeTmp]+PR[29,2]) ;
   263:  R[136:WmidY]=(R[136:WmidY]/2) ;
   264:  ! WmidX = X of this sweep column ;
   265:  R[137:WmidX]=PR[29,1] ;
   266:  R[120:MeasStep]=5 ;
   267:  JMP LBL[99] ;
   268:  LBL[56] ;
   269:  ! Exit not found ;
   270:  R[10:ErrCode]=805 ;
   271:  CALL SET_STR('X-beam W find FAIL',10) ;
   272:  JMP LBL[88] ;
   273:   ;
   274:   ;
   275:  ! ============================= ;
   276:  ! State 5: solve line intersection ;
   277:  ! Line A (Y-beam): N(NmidX,NmidY) -> S(SmidX,SmidY) ;
   278:  ! Line B (X-beam): E(EmidX,EmidY) -> W(WmidX,WmidY) ;
   279:  ! Parametric: P = A + t*(B-A) on Line A ;
   280:  ! t    = NumT / Det ;
   281:  ! Det  = dxA*dyB - dyA*dxB ;
   282:  ! NumT = (EmidX-NmidX)*dyB - (EmidY-NmidY)*dxB ;
   283:  ! TipX = NmidX + t*dxA ;
   284:  ! TipY = NmidY + t*dyA ;
   285:  ! ============================= ;
   286:  LBL[60] ;
   287:  ! Line A deltas: Y-beam direction N to S ;
   288:  R[140:dxA]=(R[134:SmidX]-R[130:NmidX]) ;
   289:  R[141:dyA]=(R[135:SmidY]-R[131:NmidY]) ;
   290:  ! Line B deltas: X-beam direction E to W ;
   291:  R[142:dxB]=(R[137:WmidX]-R[133:EmidX]) ;
   292:  R[143:dyB]=(R[136:WmidY]-R[132:EmidY]) ;
   293:  ! Det = dxA*dyB - dyA*dxB ;
   294:  R[144:Det]=(R[140:dxA]*R[143:dyB]) ;
   295:  R[145:Tmp]=(R[141:dyA]*R[142:dxB]) ;
   296:  R[144:Det]=(R[144:Det]-R[145:Tmp]) ;
   297:  ! Guard: abs(Det) must exceed R[129:DetGuard] ;
   298:  ! (lines must not be parallel) ;
   299:  R[145:Tmp]=R[144:Det] ;
   300:  IF R[145:Tmp]>=0,JMP LBL[62] ;
   301:  R[145:Tmp]=(0-R[145:Tmp]) ;
   302:  LBL[62] ;
   303:  IF R[145:Tmp]>R[129:DetGuard],JMP LBL[63] ;
   304:  R[10:ErrCode]=806 ;
   305:  CALL SET_STR('Lines parallel',10) ;
   306:  JMP LBL[88] ;
   307:  LBL[63] ;
   308:  ! NumT = (EmidX-NmidX)*dyB - (EmidY-NmidY)*dxB ;
   309:  R[146:Tmp2]=(R[133:EmidX]-R[130:NmidX]) ;
   310:  R[147:Tmp3]=(R[132:EmidY]-R[131:NmidY]) ;
   311:  R[148:NumT]=(R[146:Tmp2]*R[143:dyB]) ;
   312:  R[145:Tmp]=(R[147:Tmp3]*R[142:dxB]) ;
   313:  R[148:NumT]=(R[148:NumT]-R[145:Tmp]) ;
   314:  ! t = NumT / Det ;
   315:  R[149:t]=(R[148:NumT]/R[144:Det]) ;
   316:  ! TipXY = N + t*(S-N) ;
   317:  R[123:TipX]=(R[140:dxA]*R[149:t]) ;
   318:  R[123:TipX]=(R[123:TipX]+R[130:NmidX]) ;
   319:  R[124:TipY]=(R[141:dyA]*R[149:t]) ;
   320:  R[124:TipY]=(R[124:TipY]+R[131:NmidY]) ;
   321:  R[120:MeasStep]=6 ;
   322:  JMP LBL[99] ;
   323:   ;
   324:   ;
   325:  ! ============================= ;
   326:  ! State 6: store data, return home ;
   327:  ! UTOOL is NOT modified here. ;
   328:  ! UTOOL snapshot/update is done in CALIB_NEEDLE ;
   329:  ! State 7, after beam verification passes. ;
   330:  ! ;
   331:  ! Mode 0: store reference tip pos in PR[4:RefTipPos] ;
   332:  !         zero PR[3:CalibDelta] ;
   333:  ! Mode 1: compute XYZ delta into PR[3:CalibDelta] ;
   334:  !         (UTOOL update applied later in CALIB_NEEDLE) ;
   335:  ! ============================= ;
   336:  LBL[70] ;
   337:  IF R[110:Mode]=1,JMP LBL[74] ;
   338:   ;
   339:  ! --- Mode 0: store reference tip position --- ;
   340:  ! PR[4,1]=TipX  PR[4,2]=TipY  PR[4,3]=TipZ ;
   341:  PR[4,1]=R[123:TipX] ;
   342:  PR[4,2]=R[124:TipY] ;
   343:  PR[4,3]=R[116:TipZ] ;
   344:  ! Clear delta (no offset vs reference) ;
   345:  PR[3,1]=0 ;
   346:  PR[3,2]=0 ;
   347:  PR[3,3]=0 ;
   348:  JMP LBL[76] ;
   349:   ;
   350:  LBL[74] ;
   351:  ! --- Mode 1: compute delta vs stored reference --- ;
   352:  ! PR[4:RefTipPos] was set during mode 0 run. ;
   353:  ! PR[3,1]=dX  PR[3,2]=dY  PR[3,3]=dZ ;
   354:  PR[3,1]=(R[123:TipX]-PR[4,1]) ;
   355:  PR[3,2]=(R[124:TipY]-PR[4,2]) ;
   356:  PR[3,3]=(R[116:TipZ]-PR[4,3]) ;
   357:  ! UTOOL[1] update is applied in CALIB_NEEDLE State 7 ;
   358:   ;
   359:  LBL[76] ;
   360:  ! Return to calib home ;
   361:L P[1] 100mm/sec FINE    ;
   362:  R[10:ErrCode]=0 ;
   363:  CALL SET_STR('Measure OK',10) ;
   364:  R[101:MeasStatus]=1 ;
   365:  R[120:MeasStep]=0 ;
   366:  JMP LBL[99] ;
   367:   ;
   368:   ;
   369:  ! ============================= ;
   370:  ! Fault: set status 0, reset state ;
   371:  ! ============================= ;
   372:  LBL[88] ;
   373:  R[101:MeasStatus]=0 ;
   374:  R[120:MeasStep]=0 ;
   375:  JMP LBL[99] ;
   376:   ;
   377:  LBL[99] ;
/POS
P[1]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -340.608917  mm,	Y =   340.989685  mm,	Z =  -211.000000  mm,
	W =     -.000991 deg,	P =     -.001491 deg,	R =     -.002565 deg
};
P[2]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -333.960571  mm,	Y =   326.947845  mm,	Z =  -212.000000  mm,
	W =     -.000733 deg,	P =      .000230 deg,	R =     -.003536 deg
};
P[3]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -347.274628  mm,	Y =   326.948517  mm,	Z =  -212.000000  mm,
	W =     -.000718 deg,	P =      .000202 deg,	R =     -.003559 deg
};
P[4]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -355.600006  mm,	Y =   337.500000  mm,	Z =  -212.000000  mm,
	W =     -.000718 deg,	P =      .000202 deg,	R =     -.003559 deg
};
P[5]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -355.600006  mm,	Y =   347.213074  mm,	Z =  -212.710495  mm,
	W =     -.011912 deg,	P =     -.007159 deg,	R =     -.004124 deg
};
P[6]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -343.584961  mm,	Y =   357.791718  mm,	Z =  -212.710495  mm,
	W =     -.011912 deg,	P =     -.007159 deg,	R =     -.004124 deg
};
P[7]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -331.507813  mm,	Y =   357.784058  mm,	Z =  -212.718750  mm,
	W =     -.012958 deg,	P =     -.009050 deg,	R =     -.003704 deg
};
P[8]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -323.604950  mm,	Y =   345.213074  mm,	Z =  -212.674118  mm,
	W =     -.004788 deg,	P =     -.004788 deg,	R =     -.003567 deg
};
P[9]{
   GP1:
	UF : 1, UT : 2,		CONFIG : 'F U T, 0, 0, 0',
	X =  -323.607941  mm,	Y =   338.561157  mm,	Z =  -212.678864  mm,
	W =     -.005614 deg,	P =     -.005506 deg,	R =     -.002409 deg
};
/END
