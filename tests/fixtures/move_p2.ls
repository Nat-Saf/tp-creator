/PROG MOVE_P2
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !move from home to position 2 ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[2:position 2] 100mm/sec FINE ;
/POS
/END
