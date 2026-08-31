/PROG PICK_CONVEYOR_TO_FIXTURE_A
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick part from conveyor and place on fixture A ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   6:  L PR[5:conveyor pick] 50mm/sec FINE ;
   7:  RO[1:gripper close]=ON ;
   8:  WAIT .50(sec) ;
   9:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  10:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  11:  L PR[8:fixture A place] 50mm/sec FINE ;
  12:  RO[2:gripper open]=ON ;
  13:  WAIT .50(sec) ;
  14:  J PR[1:home] 100% FINE ;
  15:  !Pulse green lamp for 1.0s at end ;
  16:  DO[7:green lamp]=ON ;
  17:  WAIT 1.00(sec) ;
  18:  DO[7]=OFF ;
/POS
/END
