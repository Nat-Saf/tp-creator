/PROG R1_NEST_UNFLIP
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Flip nest 180 back to 0 degrees. Must run before NEST_UNLOCK.";
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
   1:  !--- FLIP 180 TO 0 --- ;
   2:  ! Called after screwing is complete. Returns nest to 0 deg (face up) ;
   3:  ! so the part can be unloaded by the operator. ;
   4:  ! NEST_UNLOCK must follow this - pistons must still be locked during unflip. ;
   5:  ! Audit 2026-07-27: entry guard added (mirror of R1_NEST_FLIP) - all 4 ;
   6:  ! pistons locked + linear extended, else the unit can fall mid-rotation ;
   7:  ! (a curtain-break air dump during screwing could have released one). ;
   8:  ! Guard + timeout are retry-on-resume (no fall-through). ;
   9:  LBL[10]    ;
  10:  IF DI[401]=OFF, JMP LBL[9]    ;
  11:  IF DI[403]=OFF, JMP LBL[9]    ;
  12:  IF DI[405]=OFF, JMP LBL[9]    ;
  13:  IF DI[407]=OFF, JMP LBL[9]    ;
  14:  IF DI[434]=OFF, JMP LBL[9]    ;
  15:  JMP LBL[3]    ;
  16:  LBL[9]    ;
  17:  CALL SET_STR('UNFLIP:NEST NOT LOCKED',1)    ;
  18:  CALL R1_TOWER(1,3)    ;
  19:  PAUSE    ;
  20:  CALL R1_TOWER(3,0)    ;
  21:  JMP LBL[10]    ;
  22:  LBL[3]    ;
  23:  ! Locker (29/07 map): enable the VFOF pilots before rotating; re-lock ;
  24:  ! after arrival and in every fault path (fail-locked policy). ;
  25:  DO[562]=OFF    ;
  26:  DO[561]=ON    ;
  27:  ! Ensure CW valve is OFF before energizing CCW (do not double-energize). ;
  28:  ! DO[469] = CW (flip direction). DO[470] = CCW (unflip direction, 180->0). ;
  29:  DO[469]=OFF    ;
  30:  DO[470]=ON    ;
  31:  ! Wait up to 10 sec (R[90]<100 x 0.1s) for nest to reach 0 degrees. ;
  32:  ! DI[435] = at-0-degrees sensor. ;
  33:  R[90]=0    ;
  34:  LBL[1]    ;
  35:  IF DI[435]=ON, JMP LBL[2]    ;
  36:  WAIT .1(sec)    ;
  37:  R[90]=R[90]+1    ;
  38:  IF R[90]<100, JMP LBL[1]    ;
  39:  ! Nest did not return to 0 deg in 10 sec - mechanical jam or sensor fault. ;
  40:  ! De-energize the rotate valve before faulting (safe state); resume ;
  41:  ! re-verifies the guard and re-commands (LBL[10]) - NEVER returns ;
  42:  ! success with the nest off 0 deg. ;
  43:  DO[470]=OFF    ;
  44:  ! Re-lock the VFOF pilots while faulted (nest held at angle) ;
  45:  DO[561]=OFF    ;
  46:  DO[562]=ON    ;
  47:  CALL SET_STR('UNFLIP:0 DEG TIMEOUT',1)    ;
  48:  CALL R1_TOWER(1,3)    ;
  49:  PAUSE    ;
  50:  CALL R1_TOWER(3,0)    ;
  51:  JMP LBL[10]    ;
  52:  LBL[2]    ;
  53:  ! De-energize CCW solenoid after 0 deg confirmed. ;
  54:  ! Nest is now face-up and the unlock/retract sequence can begin. ;
  55:  DO[470]=OFF    ;
  56:  ! Re-lock the VFOF pilots - flipper mechanically held at 0 ;
  57:  DO[561]=OFF    ;
  58:  DO[562]=ON    ;
/END
