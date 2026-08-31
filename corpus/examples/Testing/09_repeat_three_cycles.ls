/PROG PICK_PLACE_FIXA_3X
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick parts from conveyor and place on fixture A ;
   4:  !Repeat cycle 3 times ;
   5:  R[1]=0 ;
   6:  J PR[1:home] 100% FINE ;
   7:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   8:  IF DI[4:conveyor running]=OFF,JMP LBL[90] ;
   9:  LBL[10] ;
  10:  IF R[1]=3,JMP LBL[80] ;
  11:  !Cycle start ;
  12:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  13:  L PR[5:conveyor pick] 50mm/sec FINE ;
  14:  RO[1:gripper close]=ON ;
  15:  WAIT 0.50(sec) ;
  16:  !lift from conveyor ;
  17:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  18:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  19:  L PR[8:fixture A place] 50mm/sec FINE ;
  20:  RO[2:gripper open]=ON ;
  21:  WAIT 0.50(sec) ;
  22:  J PR[1:home] 100% FINE ;
  23:  R[1]=R[1]+1 ;
  24:  JMP LBL[10] ;
  25:  LBL[80] ;
  26:  !Completed 3 cycles ;
  27:  J PR[1:home] 100% FINE ;
  28:  JMP LBL[100] ;
  29:  LBL[90] ;
  30:  R[3]=1 ;
  31:  R[10]=201 ;
  32:  JMP LBL[100] ;
  33:  LBL[100] ;
/POS
/END
