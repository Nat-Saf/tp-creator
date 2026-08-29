/PROG R1_NEST_FLIP
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Flip nest 0 to 180 degrees. Guards all 4 pistons locked before rotating.";
PROG_SIZE	= 0;
CREATE		= DATE 26-06-01  TIME 00:00:00;
MODIFIED	= DATE 26-06-24  TIME 00:00:00;
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
   1:  !--- FLIP 0 TO 180 --- ;
   2:  ! Safety guard: all 4 holding pistons must be confirmed LOCKED before ;
   3:  ! the rotate command is issued. If any piston is not locked, the part ;
   4:  ! could fall out mid-flip. Each locked sensor maps to one piston: ;
   5:  ! DI[401]=piston 1, DI[403]=piston 2, DI[405]=piston 3, DI[407]=piston 4. ;
   6:  ! Audit 2026-07-27: guard + timeout are retry-on-resume (no fall-through). ;
   7:  LBL[10]    ;
   8:  IF DI[401]=OFF, JMP LBL[9]    ;
   9:  IF DI[403]=OFF, JMP LBL[9]    ;
  10:  IF DI[405]=OFF, JMP LBL[9]    ;
  11:  IF DI[407]=OFF, JMP LBL[9]    ;
  12:  ! All 4 confirmed locked - safe to flip ;
  13:  JMP LBL[1]    ;
  14:  LBL[9]    ;
  15:  ! At least one piston not locked - fault; resume RE-CHECKS (LBL[10]) ;
  16:  CALL SET_STR('FLIP:PISTONS NOT LOCKED',1)    ;
  17:  CALL R1_TOWER(1,3)    ;
  18:  PAUSE    ;
  19:  CALL R1_TOWER(3,0)    ;
  20:  JMP LBL[10]    ;
  21:  LBL[1]    ;
  22:  ! Locker (29/07 map): DO[561]/DO[562] pilot the VFOF check valves on ;
  23:  ! the flip + axis lines. Enable pilots BEFORE commanding rotation; ;
  24:  ! re-lock after arrival and in every fault path (fail-locked policy). ;
  25:  ! >>> BENCH: verify coil roles (561=enable assumed) + closed-centre ;
  26:  ! >>> pilot venting on the pneumatic drawing (safety review item). ;
  27:  DO[562]=OFF    ;
  28:  DO[561]=ON    ;
  29:  ! Ensure CCW valve is OFF before energizing CW (do not double-energize). ;
  30:  ! DO[470] = CCW (unflip direction). DO[469] = CW (flip direction, 0->180). ;
  31:  DO[470]=OFF    ;
  32:  DO[469]=ON    ;
  33:  ! Wait up to 10 sec (R[90]<100 x 0.1s) for nest to reach 180 degrees. ;
  34:  ! DI[436] = at-180-degrees sensor. ;
  35:  R[90]=0    ;
  36:  LBL[2]    ;
  37:  IF DI[436]=ON, JMP LBL[3]    ;
  38:  WAIT .1(sec)    ;
  39:  R[90]=R[90]+1    ;
  40:  IF R[90]<100, JMP LBL[2]    ;
  41:  ! Nest did not reach 180 deg in 10 sec - mechanical jam or sensor fault. ;
  42:  ! De-energize the rotate valve before faulting (safe state); resume ;
  43:  ! re-verifies the piston guard and re-commands the flip (LBL[10]). ;
  44:  DO[469]=OFF    ;
  45:  ! Re-lock the VFOF pilots while faulted (nest held at angle) ;
  46:  DO[561]=OFF    ;
  47:  DO[562]=ON    ;
  48:  CALL SET_STR('FLIP:180 TIMEOUT',1)    ;
  49:  CALL R1_TOWER(1,3)    ;
  50:  PAUSE    ;
  51:  CALL R1_TOWER(3,0)    ;
  52:  JMP LBL[10]    ;
  53:  LBL[3]    ;
  54:  ! De-energize rotate solenoid after arrival confirmed. ;
  55:  ! Nest is held at 180 by the 4 holding pistons, not by the rotate valve. ;
  56:  DO[469]=OFF    ;
  57:  ! Re-lock the VFOF pilots - flipper mechanically held at 180 ;
  58:  DO[561]=OFF    ;
  59:  DO[562]=ON    ;
/END
