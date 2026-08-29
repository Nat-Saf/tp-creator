# wait_skip - own-words syntax notes

## WAIT time - timed wait
Syntax: WAIT <value>(sec) ;   value = constant or R[i]
Units: seconds; finest resolution is 0.01 sec
Constraints: program execution pauses, no motion runs during the wait;
a register operand supplies the delay in seconds at run time.
Avoid timed waits inside line/rail tracking paths.
Example:
    WAIT .50(sec) ;
    WAIT R[3:settle time](sec) ;
Manual: HandlingTool V9.40 sec 7.36

## WAIT condition - wait until true
Syntax: WAIT <item> <op> <value> ;
Items: DI/DO, RI/RO, SI/SO, UI/UO, WI/WO, GI/GO, AI/AO, R[i], $system.var, ERR_NUM
Operators: = and <> for digital signals (values ON/OFF, plus edge forms ON+ / OFF-);
=, <>, <, <=, >, >= for registers and group/analog values.
Combine up to 5 conditions with AND or OR - never both in one line.
With no timeout clause the program blocks forever until the condition holds.
Example:
    WAIT DI[7:part present]=ON ;
    WAIT R[2]>=200 AND DI[1]=ON ;
Manual: HandlingTool V9.40 sec 7.36

## WAIT condition TIMEOUT - bounded wait with branch
Syntax: WAIT <condition>, TIMEOUT LBL[i] ;
Constraints: the wait gives up after the time held in system variable
$WAITTMOUT (units of 0.01 sec; default 3000 = 30 sec) and jumps to LBL[i].
Set the timeout in-program with the parameter name instruction, e.g.
$WAITTMOUT=(value). ERR_NUM waits can also trigger a CALL on match.
Example:
    $WAITTMOUT=500 ;
    WAIT DI[4:clamp closed]=ON, TIMEOUT LBL[10] ;
Manual: HandlingTool V9.40 sec 7.36

## SKIP CONDITION - arm the skip trigger
Syntax: SKIP CONDITION <item> <op> <value> ;
Items: same signal, register, analog, system-variable and ERR_NUM operands
as WAIT condition.
Constraints: stays armed for every following Skip/SkipJump motion until
another SKIP CONDITION replaces it; up to 5 terms joined by AND or OR,
the two operators cannot be mixed in one statement.
Example:
    SKIP CONDITION DI[3:touch probe]=ON ;
Manual: HandlingTool V9.40 sec 7.30

## Skip,LBL - skip motion option (branch when NOT triggered)
Syntax: J|L <P[i]|PR[i]> <speed> <FINE|CNTn> Skip,LBL[i] ;
Constraints: needs a prior SKIP CONDITION. Condition met mid-move: motion
stops early and the NEXT line runs. Condition never met: motion finishes,
then the program jumps to LBL[i] (typically an error/retry handler).
Example:
    SKIP CONDITION DI[3:touch probe]=ON ;
    L P[2:search end] 50mm/sec FINE Skip,LBL[99] ;
Manual: HandlingTool V9.40 sec 7.3.18

## SkipJump,LBL - reversed skip motion option
Syntax: J|L <P[i]|PR[i]> <speed> <FINE|CNTn> SkipJump,LBL[i] ;
Constraints: mirror image of Skip,LBL. Condition met mid-move: motion stops
and the program jumps to LBL[i]. Condition never met: motion completes and
the next line runs. Available to all tools; uses the armed SKIP CONDITION.
Example:
    SKIP CONDITION DI[8:obstacle]=ON ;
    L P[4:approach] 200mm/sec CNT50 SkipJump,LBL[20] ;
Manual: HandlingTool V9.40 sec 7.3.17

## Skip,LBL,PR - quick skip (high-speed skip)
Syntax: J|L <P[i]|PR[i]> <speed> <FINE|CNTn> Skip,LBL[i],PR[j]=LPOS|JPOS ;
Constraints: on trigger the servo stops at max torque and the trigger
position is captured into PR[j] (LPOS Cartesian, JPOS joint); if the
condition is never met, PR[j] is untouched and the program jumps to LBL[i].
Speed is capped at 100 mm/sec (MOTN-560 warns and clamps above that);
capture error grows with speed, about 1.5 mm at 100 mm/sec.
Example:
    SKIP CONDITION SDI[3]=ON ;
    L P[6:probe target] 80mm/sec FINE Skip,LBL[30],PR[9]=LPOS ;
Manual: HandlingTool V9.40 sec 7.28
