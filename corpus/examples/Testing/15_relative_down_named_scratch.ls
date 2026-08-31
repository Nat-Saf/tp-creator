/PROG MOVE_HOME_TO_FIXTUREA_DOWN_UP
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Moves: home -> fixture A approach -> descend 50mm (using PR[10] as scratch) -> home ;
   4:  J PR[1:home] 100% FINE ;
   5:  J PR[7:fixture A approach] 100% FINE ;
   6:  !PR[10] is used as a scratch register and will be overwritten; operator must teach PR[10] before first run or allow program to move to it for teaching ;
   7:  PR[10]=PR[7] ;
   8:  PR[10,3]=PR[10,3]-50 ;
   9:  L PR[10] 50mm/sec FINE ;
  10:  J PR[1:home] 100% FINE ;
/POS
/END
