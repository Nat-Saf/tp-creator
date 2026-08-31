/PROG PICK_CONVEYOR_TO_FIXTURE_A
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Wait for DI[3] 'part present' up to 5s, branch to ERR_PART_NOT_PRESENT on timeout ;
   4:  WAIT DI[3:part present]=ON TIMEOUT,LBL[100] ;
   5:  !Standard pick/place: approach, slow descend, grip, lift, transfer, place, release, return home ;
   6:  J PR[1:home] 100% FINE ;
   7:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   8:  L PR[5:conveyor pick] 50mm/sec FINE ;
   9:  RO[1:gripper close]=ON ;
  10:  WAIT .50(sec) ;
  11:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  12:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  13:  L PR[8:fixture A place] 50mm/sec FINE ;
  14:  RO[2:gripper open]=ON ;
  15:  WAIT .50(sec) ;
  16:  J PR[1:home] 100% FINE ;
  17:  JMP LBL[101] ;
  18:  LBL[100] ;
  19:  R[3:part counter]=R[3:part counter] ;
  20:  R[3:part counter]=R[3:part counter] ;
  21:  !ERR_PART_NOT_PRESENT ;
  22:  R[3:part counter]=R[3:part counter] ;
  23:  JMP LBL[101] ;
  24:  LBL[101] ;
/POS
/END
