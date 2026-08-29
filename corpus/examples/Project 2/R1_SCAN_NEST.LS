/PROG R1_SCAN_NEST
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "IV3 direct nest-clear check";
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
   1:  !--- NEST-CLEAR CHECK - IV3 DIRECT (2026-08-02, no PC) ---    ;
   2:  ! Replaces PC code 8 (only consumer: R1_REJECT - robot HOLDS the    ;
   3:  ! failed component; nest must be clear before the bin run).    ;
   4:  ! Owns the PR[42] approach move. IV3 program 6 (ASSUMED - nest    ;
   5:  ! view): tool 00 = position adjust = NEST IN VIEW (DI[635]);    ;
   6:  ! tool 01 = occupancy (DI[625]) - ON = OCCUPIED, matching the    ;
   7:  ! tray convention (tools trained on the part being present).    ;
   8:  ! >>> BENCH: program number, tool-01 training/polarity, addresses.    ;
   9:  ! Returns ONLY when the nest is verified clear.    ;
  10:  ! R[99]=1 (Roboguide): skip - no camera in sim.    ;
  11:  IF R[99]=1, JMP LBL[99]    ;
  12:  CALL R1_IV3_PROG(6)    ;
  13:  J PR[42] 80% FINE    ;
  14:  !  trigger; pulse, settle, wait BUSY low = results valid    ;
  15:  LBL[11]    ;
  16:  DO[625]=ON    ;
  17:  WAIT .2(sec)    ;
  18:  DO[625]=OFF    ;
  19:  WAIT .3(sec)    ;
  20:  R[90]=0    ;
  21:  LBL[12]    ;
  22:  IF DI[637]=OFF, JMP LBL[13]    ;
  23:  WAIT .1(sec)    ;
  24:  R[90]=R[90]+1    ;
  25:  IF R[90]<50, JMP LBL[12]    ;
  26:  CALL SET_STR('IV3:BUSY STUCK',1)    ;
  27:  CALL R1_TOWER(1,3)    ;
  28:  PAUSE    ;
  29:  CALL R1_TOWER(3,0)    ;
  30:  JMP LBL[11]    ;
  31:  LBL[13]    ;
  32:  !  nest in view? (position-adjust tool)    ;
  33:  IF DI[635]=ON, JMP LBL[15]    ;
  34:  CALL SET_STR('IV3:NEST NOT IN VIEW',1)    ;
  35:  CALL R1_TOWER(1,3)    ;
  36:  PAUSE    ;
  37:  CALL R1_TOWER(3,0)    ;
  38:  JMP LBL[11]    ;
  39:  LBL[15]    ;
  40:  !  occupied? operator clears the nest, resume re-images -    ;
  41:  !  never falls through into the bin run (audit doctrine)    ;
  42:  IF DI[625]=OFF, JMP LBL[99]    ;
  43:  CALL SET_STR('NEST NOT CLEAR',1)    ;
  44:  CALL R1_TOWER(1,3)    ;
  45:  PAUSE    ;
  46:  CALL R1_TOWER(3,0)    ;
  47:  JMP LBL[11]    ;
  48:  LBL[99]    ;
/END
