/PROG BUZZER_PULSE
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Turn buzzer DO[5] on for 2.0s then off; no robot motion ;
   4:  DO[5]=ON ;
   5:  WAIT 2.00(sec) ;
   6:  DO[5]=OFF ;
/POS
/END
