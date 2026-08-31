/PROG PICK_CONVEYOR_TO_FIXTURE_A
/ATTR
OWNER = MNEDITOR;
COMMENT = "auto";
/MN
   1:  UFRAME_NUM=1 ;
   2:  UTOOL_NUM=1 ;
   3:  !Pick from conveyor, confirm gripper feedback, place on fixture A ;
   4:  !Uses R[8] 'retry limit' for feedback retries; operator must ensure R[8] is set ;
   5:  !Speeds and termination from defaults ;
   6:  J PR[1:home] 100% FINE ;
   7:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
   8:  L PR[5:conveyor pick] 50mm/sec FINE ;
   9:  RO[1:gripper close]=ON ;
  10:  WAIT .50(sec) ;
  11:  R[8:retry limit]=R[8:retry limit] ;
  12:  IF RI[1:gripper closed feedback]=ON,JMP LBL[20] ;
  13:  !retry loop for gripper feedback ;
  14:  LBL[10] ;
  15:  IF R[8:retry limit]=0,JMP LBL[99] ;
  16:  R[8:retry limit]=R[8:retry limit]-1 ;
  17:  RO[1]=OFF ;
  18:  WAIT .20(sec) ;
  19:  RO[1]=ON ;
  20:  WAIT .50(sec) ;
  21:  IF RI[1]=ON,JMP LBL[20] ;
  22:  JMP LBL[10] ;
  23:  LBL[20] ;
  24:  ! grip confirmed ;
  25:  L PR[6:conveyor approach] 100mm/sec CNT50 ;
  26:  L PR[7:fixture A approach] 100mm/sec CNT50 ;
  27:  L PR[8:fixture A place] 50mm/sec FINE ;
  28:  RO[1]=OFF ;
  29:  WAIT .50(sec) ;
  30:  J PR[1:home] 100% FINE ;
  31:  LBL[99] ;
  32:  R[3:part counter]=R[3:part counter] ;
  33:  R[8:retry limit]=R[8:retry limit] ;
/POS
/END
