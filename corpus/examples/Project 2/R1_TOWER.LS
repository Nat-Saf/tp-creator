/PROG R1_TOWER
/ATTR
OWNER		= MNEDITOR;
COMMENT		= "DV2130 tower color+mode";
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
   1:  !--- SIGNAL TOWER - IFM DV2130 (IO-Link, master port 7) ---    ;
   2:  ! AR[1] = segment color: 0=off 1=red 2=green 3=amber(orange)    ;
   3:  !         4=blue 5=purple 6=cyan 7=white 8=yellow    ;
   4:  ! AR[2] = appearance: 0=continuous 1..3=blink slow/mid/fast    ;
   5:  !         4..6=flash slow/mid/fast    ;
   6:  ! GO[1] = color value  (DO[593-596], 4 bits)    ;
   7:  ! GO[2] = appearance   (DO[597-599], 3 bits)    ;
   8:  ! Buzzer NOT mapped (7-bit decision 29/07) - faults use red+blink    ;
   9:  ! V3 states: (2,0)=GREEN idle  (3,0)=ORANGE working  (1,3)=FAULT    ;
  10:  GO[1]=AR[1]    ;
  11:  GO[2]=AR[2]    ;
/END
