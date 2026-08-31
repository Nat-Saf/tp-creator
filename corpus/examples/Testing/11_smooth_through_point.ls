/PROG MOVE_HOME_THROUGH_CONV_TO_FIXA_AND_BACK
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move from home through conveyor approach to fixture A approach, then return home ;
   4:  J PR[1:home] 100% FINE ;
   5:  !Move from home to conveyor approach ;
   6:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   7:  !Do not stop at the conveyor pick (middle) point ;
   8:  !Move from conveyor approach to fixture A approach ;
   9:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  10:  !Move from fixture A approach back to home ;
  11:  J PR[1:home] 100% FINE ;
/POS
/END
