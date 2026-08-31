/PROG MOVE_HOME_TO_CONVEYOR_START
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move from home to conveyor approach, start conveyor, wait up to 10s for DI[4] 'conveyor running', stop conveyor, return home ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   6:  DO[6:conveyor start]=ON ;
   7:  WAIT DI[4:conveyor running]=ON TIMEOUT,LBL[90] ;
   8:  DO[6]=OFF ;
   9:  J PR[1:home] 100% FINE ;
  10:  LBL[90] ;
  11:  DO[6]=OFF ;
  12:  J PR[1:home] 100% FINE ;
/POS
/END
