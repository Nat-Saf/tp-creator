/PROG R1_NEST_UNLOCK
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "Nest unlock: delegates safe retract order to R1_SAFE_RETRACT_LIN (#16).";
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
   1:  !--- NEST UNLOCK (#16) --- ;
   2:  ! R1_SAFE_RETRACT_LIN enforces the mandatory unlock order: ;
   3:  !   1. Verify flipper at 0 deg (DI[435]=ON) - PAUSE if not. ;
   4:  !   2. Release 4 holding pistons (DO[468]) - wait DI[402/404/406/408] all released. ;
   5:  !   3. Retract linear piston (DO[466]) - wait DI[433] retracted. ;
   6:  ! This order is critical: releasing pistons before flipper is at 0 ;
   7:  ! would allow the nest to rotate under gravity with no control. ;
   8:  ! Retracting linear before pistons release would mechanically bind. ;
   9:  CALL R1_SAFE_RETRACT_LIN    ;
  10:  ! DO[468] = release command. Set OFF after R1_SAFE_RETRACT_LIN to ;
  11:  ! de-energize the release valve once retract is confirmed complete. ;
  12:  ! R1_SAFE_RETRACT_LIN leaves DO[468] ON (valve still energized during ;
  13:  ! the retract wait); this line shuts it off for the idle state. ;
  14:  DO[468]=OFF    ;
/END
