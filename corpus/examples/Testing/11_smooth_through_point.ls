/PROG MOVE_HOME_VIA_CONVEYOR_TO_FIXA_AND_BACK
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move sequence: home -> conveyor approach -> fixture A approach -> home ;
   4:  !Do not stop at any middle point; straight transit through via points ;
   5:  J PR[1:home] 100% FINE ;
   6:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   7:  L PR[7:fixture A approach] 100mm/sec FINE ;
   8:  J PR[1:home] 100% FINE ;
/POS
/END
