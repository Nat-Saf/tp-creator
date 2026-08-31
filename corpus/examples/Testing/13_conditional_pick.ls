/PROG COND_PICK_PLACE_FIXA
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Conditional: pick only if part present input is true; otherwise return home. ;
   4:  R[4] = DI[3] ;
   5:  IF DI[3]=OFF,JMP LBL[10] ;
   6:  !uses fixture A place and conveyor pick/approach from table. ;
   7:  J PR[1:home] 100% FINE ;
   8:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   9:  L PR[5:conveyor pick] 50mm/sec FINE ;
  10:  RO[1:gripper close]=ON ;
  11:  WAIT 0.50(sec) ;
  12:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  13:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  14:  L PR[8:fixture A place] 50mm/sec FINE ;
  15:  RO[2:gripper open]=ON ;
  16:  WAIT 0.50(sec) ;
  17:  J PR[1:home] 100% FINE ;
  18:  LBL[10] ;
  19:  !No part present: go to home and do not pick. ;
  20:  J PR[1:home] 100% FINE ;
/POS
/END
