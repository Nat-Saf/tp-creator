/PROG MOVE_TRAVEL_TO_PURGE_AND_HOME
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move from safe travel point to purge station, then return to home ;
   4:  J PR[14:safe travel point] 100% FINE ;
   5:  L PR[16:purge station] 100mm/sec FINE ;
   6:  J PR[1:home] 100% FINE ;
/POS
/END
