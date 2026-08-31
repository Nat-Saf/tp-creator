/PROG PICK_CONVEYOR_TO_FIXTURE_A
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick from conveyor, verify gripper-closed feedback, place on fixture A ;
   4:  !Uses conveyor approach/pick and fixture A approach/place ;
   5:  J PR[1:home] 100% FINE ;
   6:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   7:  L PR[5:conveyor pick] 50mm/sec FINE ;
   8:  RO[1:gripper close]=ON ;
   9:  WAIT .50(sec) ;
  10:  !verify gripper closed feedback, retry up to R[8] then fault ;
  11:  IF RI[1:gripper closed feedback]=ON,JMP LBL[20] ;
  12:  R[8:retry limit]=R[8:retry limit]-1 ;
  13:  IF R[8:retry limit]=0,JMP LBL[90] ;
  14:  !retry: open and close again ;
  15:  RO[2:gripper open]=ON ;
  16:  WAIT .50(sec) ;
  17:  RO[1:gripper close]=ON ;
  18:  WAIT .50(sec) ;
  19:  IF RI[1]=ON,JMP LBL[20] ;
  20:  LBL[20] ;
  21:  !grip confirmed or retried successfully ;
  22:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  23:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  24:  L PR[8:fixture A place] 50mm/sec FINE ;
  25:  RO[1:gripper close]=OFF ;
  26:  WAIT .50(sec) ;
  27:  J PR[1:home] 100% FINE ;
  28:  JMP LBL[99] ;
  29:  LBL[90] ;
  30:  R[3:part counter]=R[3:part counter]+1 ;
  31:  R[12:reject count]=R[12:reject count]+1 ;
  32:  R[3:part counter]=R[3:part counter] ; 
  33:  R[8:retry limit]=0 ;
  34:  CALL SET_STR('Gripper failed',10) ;
  35:  JMP LBL[99] ;
  36:  LBL[99] ;
/POS
/END
