/PROG MOVE_HOME_CAMERA_INSPECT
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Move from home to camera inspection pose, enable camera, wait 60s, disable camera, return home ;
   4:  J PR[1:home] 100% FINE ;
   5:  L PR[17:camera inspection pose] 100mm/sec CNT50 ;
   6:  !Uses DO[1] 'camera on' to toggle the camera ;
   7:  DO[1]=ON ;
   8:  WAIT 60.00(sec) ;
   9:  DO[1]=OFF ;
  10:  J PR[1:home] 100% FINE ;
/POS
/END
