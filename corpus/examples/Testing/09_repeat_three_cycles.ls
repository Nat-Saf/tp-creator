/PROG PICK_PLACE_FIXTURE_A
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick parts from conveyor and place on fixture A ;
   4:  !Cycle repeated 3 times ;
   5:  !Uses RO[1] to close gripper and RO[2] to open gripper ;
   6:  R[1]=0 ;
   7:  L PR[1:home] 100mm/sec FINE ;
   8:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   9:  IF DI[4:conveyor running]=OFF,JMP LBL[100] ;
  10:  LBL[1] ;
  11:  IF R[1:cycle count]>=3,JMP LBL[90] ;
  12:  !start cycle ;
  13:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  14:  L PR[5:conveyor pick] 50mm/sec FINE ;
  15:  RO[1:gripper close]=ON ;
  16:  WAIT 0.50(sec) ;
  17:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  18:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  19:  L PR[8:fixture A place] 50mm/sec FINE ;
  20:  RO[2:gripper open]=ON ;
  21:  WAIT 0.50(sec) ;
  22:  R[1:cycle count]=R[1]+1 ;
  23:  JMP LBL[1] ;
  24:  LBL[90] ;
  25:  !all cycles complete, return home ;
  26:  J PR[1:home] 100% FINE ;
  27:  JMP LBL[99] ;
  28:  LBL[100] ;
  29:  R[3:part counter]=0 ;
  30:  R[10:parts per pallet]=0 ;
  31:  !conveyor not running fault ;
  32:  R[1:cycle count]=R[1] ;
  33:  LBL[99] ;
/POS
/END
