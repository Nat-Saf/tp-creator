/PROG PICK_PLACE_A
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto v2";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !pick from conveyor ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 100mm/sec FINE ;
   6:  L PR[5:conveyor pick] 50mm/sec FINE ;
   7:  RO[1:gripper close]=ON ;
   8:  WAIT 1.00(sec) ;
   9:  L PR[6] 100mm/sec FINE ;
  10:  !place on fixture A ;
  11:  L PR[8:fixture A place] 100mm/sec FINE ;
  12:  RO[1]=OFF ;
  13:  WAIT   0.50(sec) ;
  14:  J PR[1:home] 100% FINE ;
/POS
/END
