/PROG DEMO_CYCLE
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move from home to conveyor approach at 150mm/sec and return to home ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[6:conveyor approach] 150mm/sec CNT50 ;
   6:  L PR[1:home] 150mm/sec FINE ;
/POS
/END
