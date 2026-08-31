/PROG PICK_CONVEYOR_TO_FIXB
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick a part from the conveyor and place it on fixture B ;
   4:  !Approach above pick, slow descend to pick, close gripper, lift, travel, approach place, slow descend, open gripper, retreat, return home ;
   5:  J PR[1:home] 100% FINE ;
   6:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   7:  L PR[5:conveyor pick] 50mm/sec FINE ;
   8:  RO[1:gripper close]=ON ;
   9:  WAIT  .50(sec) ;
  10:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  11:  L PR[13:fixture B approach] 100mm/sec CNT50 ;
  12:  L PR[9:fixture B place] 50mm/sec FINE ;
  13:  RO[2:gripper open]=ON ;
  14:  WAIT  .50(sec) ;
  15:  J PR[1:home] 100% FINE ;
/POS
/END
