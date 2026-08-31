/PROG PICK_CONVEYOR_TO_FIXA
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick from conveyor and place on fixture A ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   6:  L PR[5:conveyor pick] 50mm/sec FINE ;
   7:  !Use RO[1] to close gripper and RO[2] to open ;
   8:  RO[1:gripper close]=ON ;
   9:  WAIT  .50(sec) ;
  10:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  11:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  12:  L PR[8:fixture A place] 50mm/sec FINE ;
  13:  RO[2:gripper open]=ON ;
  14:  WAIT  .50(sec) ;
  15:  J PR[1:home] 100% FINE ;
  16:  R[1:cycle count]=R[1]+1 ;
/POS
/END
