/PROG R1_NEST_LOCK
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Nest lock: linear extend then lock 4 pistons then verify at 0deg.";
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
   1:  !--- NEST LOCK SEQUENCE --- ;
   2:  ! Three-step sequence: (1) extend linear piston to engage nest, ;
   3:  ! (2) lock all 4 holding pistons, (3) confirm rotate is at 0 deg. ;
   4:  ! Must complete before NEST_FLIP is called. ;
   5:  ! Audit 2026-07-27: all faults retry-on-resume (re-command + re-wait); ;
   6:  ! PAUSE never falls through into the next step. ;
   7:   ;
   8:  !  STEP 1: extend linear piston ;
   9:  ! DO[466] = retract linear piston command. De-energize before extending ;
  10:  ! to avoid simultaneous energize of both directions (valve damage). ;
  11:  LBL[10]    ;
  12:  DO[466]=OFF    ;
  13:  ! DO[465] = extend linear piston. Pushes the nest engagement pin into ;
  14:  ! its locking groove, fixing the nest at the current angle. ;
  15:  DO[465]=ON    ;
  16:  ! Wait up to 5 sec (R[90]<50 x 0.1s) for extension to confirm. ;
  17:  ! DI[434] = linear piston fully extended sensor. ;
  18:  R[90]=0    ;
  19:  LBL[1]    ;
  20:  IF DI[434]=ON, JMP LBL[2]    ;
  21:  WAIT .1(sec)    ;
  22:  R[90]=R[90]+1    ;
  23:  IF R[90]<50, JMP LBL[1]    ;
  24:  ! Timeout: fault; resume re-commands the extend (LBL[10]) ;
  25:  CALL SET_STR('LOCK:LINEAR TIMEOUT',1)    ;
  26:  CALL R1_TOWER(1,3)    ;
  27:  PAUSE    ;
  28:  CALL R1_TOWER(3,0)    ;
  29:  JMP LBL[10]    ;
  30:  LBL[2]    ;
  31:   ;
  32:  !  STEP 2: lock 4 holding pistons, verify ALL 4 individually locked ;
  33:  ! DO[468] = release pistons command. De-energize before locking. ;
  34:  LBL[11]    ;
  35:  DO[468]=OFF    ;
  36:  ! DO[467] = lock 4 holding pistons. Clamp the scanner components in place. ;
  37:  DO[467]=ON    ;
  38:  ! Poll all 4 piston sensors simultaneously in a loop. ;
  39:  ! All 4 must be ON before proceeding. Each maps to one piston: ;
  40:  ! DI[401]=piston 1, DI[403]=piston 2, DI[405]=piston 3, DI[407]=piston 4. ;
  41:  ! If any piston is not locked within 5 sec -> fault. ;
  42:  R[90]=0    ;
  43:  LBL[3]    ;
  44:  IF DI[401]=OFF, JMP LBL[6]    ;
  45:  IF DI[403]=OFF, JMP LBL[6]    ;
  46:  IF DI[405]=OFF, JMP LBL[6]    ;
  47:  IF DI[407]=OFF, JMP LBL[6]    ;
  48:  ! All 4 locked - continue ;
  49:  JMP LBL[4]    ;
  50:  LBL[6]    ;
  51:  ! At least one piston not yet confirmed - wait and retry ;
  52:  WAIT .1(sec)    ;
  53:  R[90]=R[90]+1    ;
  54:  IF R[90]<50, JMP LBL[3]    ;
  55:  ! Timeout: a piston did not lock - fault; resume re-commands (LBL[11]) ;
  56:  CALL SET_STR('LOCK:PISTON TIMEOUT',1)    ;
  57:  CALL R1_TOWER(1,3)    ;
  58:  PAUSE    ;
  59:  CALL R1_TOWER(3,0)    ;
  60:  JMP LBL[11]    ;
  61:  LBL[4]    ;
  62:   ;
  63:  !  STEP 3: confirm rotate at 0 deg before flip is allowed ;
  64:  ! DI[435] = at-0-degrees sensor on the rotate actuator. ;
  65:  ! If nest is not at 0 deg (e.g. stuck partway from a prior flip) ;
  66:  ! NEST_FLIP would command another 180 turn from a wrong starting angle. ;
  67:  LBL[12]    ;
  68:  IF DI[435]=ON, JMP LBL[5]    ;
  69:  CALL SET_STR('LOCK:NOT AT 0 DEG',1)    ;
  70:  CALL R1_TOWER(1,3)    ;
  71:  PAUSE    ;
  72:  CALL R1_TOWER(3,0)    ;
  73:  JMP LBL[12]    ;
  74:  LBL[5]    ;
/END
