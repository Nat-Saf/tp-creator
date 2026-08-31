/PROG BUZZER_PULSE
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Activate buzzer for 2.0 seconds with no robot motion ;
   4:  DO[5:buzzer] = ON ;
   5:  WAIT 2.00(sec) ;
   6:  DO[5] = OFF ;
/POS
/END
