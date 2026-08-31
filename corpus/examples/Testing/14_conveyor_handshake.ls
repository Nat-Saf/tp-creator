/PROG MOVE_HOME_TO_CONVEYOR_AND_TOGGLE
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move from home to conveyor approach ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   6:  !Start conveyor, wait up to 10s for conveyor running DI[4] ;
   7:  DO[6:conveyor start]=ON ;
   8:  WAIT DI[4]=ON TIMEOUT,LBL[90] ;
   9:  !Stop conveyor and return home ;
  10:  DO[6:conveyor start]=OFF ;
  11:  J PR[1:home] 100% FINE ;
  12:  JMP LBL[99] ;
  13:  LBL[90] ;
  14:  !On timeout jump to ERROR_CONVEYOR ;
  15:  R[3:part counter]=1 ;
  16:  JMP LBL[98] ;
  17:  LBL[98] ;
  18:  !ERROR_CONVEYOR ;
  19:  R[3:part counter]=2 ;
  20:  LBL[99] ;
/POS
/END
