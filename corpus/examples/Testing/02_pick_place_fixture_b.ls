/PROG PICK_PLACE_B
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick from conveyor and place on fixture B ;
   4:  !Approach above pick, slow contact descend, close gripper, lift, travel, approach place, slow descend, open gripper, retreat, go home ;
   5:  J PR[1:home] 100% FINE ;
   6:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   7:  L PR[5:conveyor pick] 50mm/sec FINE ;
   8:  RO[1:gripper close]=ON ;
   9:  WAIT .50(sec) ;
  10:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  11:  L PR[13:fixture B approach] 100mm/sec CNT50 ;
  12:  L PR[9:fixture B place] 50mm/sec FINE ;
  13:  RO[2:gripper open]=ON ;
  14:  WAIT .50(sec) ;
  15:  J PR[1:home] 100% FINE ;
/POS
/END
