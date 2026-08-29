# branching - own-words syntax notes

## LBL - label definition
Syntax: LBL[i] ; or LBL[i:comment] ;
A label names a spot in the program that jump instructions can target.
Define it on its own line; the optional comment after the colon is only
documentation and does not affect matching - only the number i does.
A label must be defined before any JMP that references it will resolve
at run time (definition may sit above or below the jump in the listing).
Example:
    22:  LBL[10:retry pick] ;
Manual: HandlingTool V9.40 sec 7.9.2

## JMP LBL - unconditional jump
Syntax: JMP LBL[i] ;
Transfers execution straight to the line holding LBL[i], every time it
runs, forward or backward in the program. Pair it with LBL[i] to build
loops or to skip past a block; use IF ... ,JMP LBL[i] for a guarded jump.
Example:
    15:  JMP LBL[10] ;
    ...
    30:  LBL[10] ;
Manual: HandlingTool V9.40 sec 7.9.3

## IF - conditional branch on a comparison
Syntax: IF <R[i]|I/O|value> <op> <value>, <JMP LBL[i]|CALL prog> ;
Operators: =, <>, <, >, <=, >= for numeric compares (registers, GI/AI,
system variables); discrete signals (DI/DO, RI/RO, SI/SO, UI/UO) compare
with = or <> against ON/OFF. When the comparison is true the action runs;
otherwise execution falls through to the next line. Action is a jump or
a program call.
Example:
    12:  IF R[3:part count]>=8, JMP LBL[20] ;
    13:  IF DI[7:part present]=OFF, CALL FAULT_HANDLER ;
Manual: HandlingTool V9.40 sec 7.9.4

## IF with AND/OR - combined conditions
Syntax: IF <cond1> AND <cond2> AND ..., <action> ;  (or all OR)
Constraints: AND and OR must not be mixed in one statement - the pendant
refuses it by rewriting every operator on the line to the one you last
picked (warnings TPIF-062/TPIF-063). At most 5 conditions may be chained
in a single statement. All conditions must pass (AND) or any one (OR) for
the action to fire.
Example:
    14:  IF R[1]=1 AND R[2]<5 AND DI[2]=ON, JMP LBL[30] ;
    15:  IF DI[10]=ON OR R[7]=R[8], JMP LBL[2] ;
Manual: HandlingTool V9.40 sec 7.9.4

## IF (mixed logic) - parenthesized condition
Syntax: IF (<expression>), <JMP LBL[i]|CALL prog|assignment|Pulse> ;
The parenthesized form takes a full mixed-logic expression: AND and OR
may be nested with parentheses, ! negates, and arithmetic subexpressions
are allowed. The whole expression must evaluate to boolean; when it is
on, the action runs. Only with this form may the action also be a
mixed-logic assignment or a Pulse. A statement holds roughly 20 items
(operands plus operators) at most.
Example:
    16:  IF (DI[1] AND (!DI[2] OR DI[3])), JMP LBL[40] ;
    17:  IF (DI[2]), DO[1]=(ON) ;
Manual: HandlingTool V9.40 sec 7.9.4

## SELECT - multi-way branch on a register
Syntax: SELECT R[i]=<v1>,<action> ; =<v2>,<action> ; ... ELSE,<action> ;
Compares R[i] against each listed value top-down and runs the action of
the first match; the ELSE action runs when nothing matches. Each action
must be a JMP LBL[i] or a CALL - no other instruction types. Classic use
is a state-machine dispatcher keyed on a step register.
Example:
    20:  SELECT R[2:station]=1, JMP LBL[110] ;
    21:         =2, JMP LBL[120] ;
    22:         =3, CALL STATION_3 ;
    23:         ELSE, JMP LBL[999] ;
Manual: HandlingTool V9.40 sec 7.9.4

## CALL - subprogram call
Syntax: CALL <program> ; or CALL <program>(<arg1>,<arg2>,...) ;
Runs another program; when it hits END, execution resumes at the line
after the CALL. Application masks must be compatible: a program masked
for one application cannot call one masked for a different application
(NONE is compatible either way). With the call-parameters option, up to
10 arguments may be passed; each is a constant, a string, R[i], AR[i],
P[i], or PR[i].
Example:
    18:  CALL PICK_PART(2, R[3], 'GRIP') ;
Manual: HandlingTool V9.40 sec 7.9.3

## AR - argument register inside a called program
Syntax: AR[i] where i counts the call arguments left to right (AR[1] is
the first). Read arguments inside a subprogram or macro through AR[i]:
on the right side of an assignment, inside IF/WAIT comparisons, as an
indirect index (DO[AR[1]]=ON), or passed onward to a nested CALL. Data
type must match the use site - checked only at run time, an alarm fires
on mismatch. AR[i] may not serve as the index of an indirect register
(R[R[AR[1]]] is rejected).
Example:
    5:  UFRAME_NUM=AR[1] ;
    6:  IF R[7]=AR[2], JMP LBL[1] ;
Manual: HandlingTool V9.40 sec 7.21.4

## END - program end
Syntax: END (final line, inserted by the editor)
Marks the end of the program body. In a called program it is the return
point: control goes back to the caller at the line after the CALL. In a
top-level program it ends the cycle. It takes no arguments.
Example:
    35:  J PR[1:home] 100% FINE ;
    [End]
Manual: HandlingTool V9.40 sec 7.9.3

## RUN - start a parallel task
Syntax: RUN <program> ;
Multi-tasking launch: the named program starts executing immediately as
its own task while the parent program keeps running past the RUN line -
unlike CALL, there is no wait and no return. The launched subtask is
also stepped when the main task runs in single-step mode. Tasks that run
concurrently must not fight over the same motion group.
Example:
    3:  RUN CONVEYOR_WATCH ;
    4:  J P[1] 50% CNT100 ;
Manual: HandlingTool V9.40 sec 7.18
