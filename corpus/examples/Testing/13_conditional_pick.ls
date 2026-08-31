/PROG COND_PICK_CONVEYOR_TO_FIXA
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !If part present input is on, pick from conveyor and place on fixture A; otherwise go home. ;
   4:  !Uses RO[1]/RO[2] for gripper and DI[3] for part-present check. ;
   5:  IF DI[3]=OFF,JMP LBL[10] ;
   6:  J PR[1:home] 100% FINE ;
   7:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   8:  L PR[5:conveyor pick] 50mm/sec FINE ;
   9:  RO[1:gripper close]=ON ;
  10:  WAIT 0.50(sec) ;
  11:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  12:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  13:  L PR[8:fixture A place] 50mm/sec FINE ;
  14:  RO[1]=OFF ;
  15:  RO[2:gripper open]=ON ;
  16:  WAIT 0.50(sec) ;
  17:  J PR[1:home] 100% FINE ;
  18:  LBL[10] ;
  19:  !Part not present - go home. ;
  20:  J PR[1:home] 100% FINE ;
/POS
/END
