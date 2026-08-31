/PROG PICK_PLACE_A
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !pick from conveyor ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   6:  L PR[5:conveyor pick] 50mm/sec FINE ;
   7:  RO[1:gripper close]=ON ;
   8:  WAIT 1.00(sec) ;
   9:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  10:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  11:  L PR[8:fixture A place] 50mm/sec FINE ;
  12:  !place on fixture A ;
  13:  !gentle settle at place ;
  14:  RO[2:gripper open]=ON ;
  15:  WAIT 1.00(sec) ;
  16:  J PR[1:home] 100% FINE ;
/POS
/END
