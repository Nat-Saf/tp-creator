/PROG MOVE_HOME_TO_FIXTUREA_DOWN_UP
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move home -> fixture A approach -> offset down 50mm using PR[10] scratch -> return home ;
   4:  !PR[10] marked as scratch (untaught) — teach before running ;
   5:  J PR[1:home] 100% FINE ;
   6:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
   7:  PR[10]=PR[7] ;
   8:  PR[10,3]=PR[10,3]-50 ;
   9:  L PR[10] 50mm/sec FINE ;
  10:  PR[10,3]=PR[10,3]+50 ;
  11:  J PR[1:home] 100% FINE ;
/POS
/END
