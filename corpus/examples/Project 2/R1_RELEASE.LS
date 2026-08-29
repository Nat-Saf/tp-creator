/PROG R1_RELEASE
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "PNS4 V3 release unflip+unlock";
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
   1:  !--- V3 RELEASE (PNS 4) ---    ;
   2:  ! Operator finished screwing and pressed READY TO RELEASE. PC    ;
   3:  ! verified safety (muting ended, curtain clear) BEFORE pulsing PNS 4.    ;
   4:  ! Nest: at P2, flipped 180, locked. Unflip -> unlock -> DO[24].    ;
   5:  ! Audit 2026-07-27: every guard is retry-on-resume - a bare CYCLE    ;
   6:  ! START can never fall through into a nest actuator command.    ;
   7:  CALL SET_STR('RELEASE',2)    ;
   8:  ! Guard: axis must be at operator station (DI[500]) - re-checked    ;
   9:  LBL[10]    ;
  10:  IF DI[500]=ON, JMP LBL[1]    ;
  11:  CALL SET_STR('RELEASE:NOT AT P2',1)    ;
  12:  CALL R1_TOWER(1,3)    ;
  13:  PAUSE    ;
  14:  CALL R1_TOWER(3,0)    ;
  15:  JMP LBL[10]    ;
  16:  LBL[1]    ;
  17:  ! Guard: flip state must be KNOWN - flipped (DI[436]) -> unflip;    ;
  18:  ! already at 0 (DI[435]) -> skip. NEITHER sensor = mid-angle /    ;
  19:  ! sensor fault -> operator intervention, then re-check.    ;
  20:  LBL[11]    ;
  21:  IF DI[436]=ON, JMP LBL[3]    ;
  22:  IF DI[435]=ON, JMP LBL[2]    ;
  23:  CALL SET_STR('RELEASE:FLIP STATE BAD',1)    ;
  24:  CALL R1_TOWER(1,3)    ;
  25:  PAUSE    ;
  26:  CALL R1_TOWER(3,0)    ;
  27:  JMP LBL[11]    ;
  28:  LBL[3]    ;
  29:  ! Unflip 180->0    ;
  30:  CALL R1_NEST_UNFLIP    ;
  31:  LBL[2]    ;
  32:  ! Unlock: verifies 0 deg, releases pistons, retracts linear (#16)    ;
  33:  CALL R1_NEST_UNLOCK    ;
  34:  ! Release done -> PC shows 'please take out lidar from nest'    ;
  35:  DO[24]=ON    ;
  36:  WAIT .5(sec)    ;
  37:  DO[24]=OFF    ;
  38:  CALL SET_STR('RELEASE DONE',2)    ;
  39:  ! Unit complete: tower GREEN ready    ;
  40:  CALL R1_TOWER(2,0)    ;
/END
