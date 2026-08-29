# misc - own-words syntax notes

## ! - remark (comment) line
Syntax: ! <text> ;
Constraints: text is 1-32 characters (letters, digits, punctuation, spaces);
no effect on execution; the line exists purely for human readers.
Related forms: a line starting with two hyphens (--) is a multi-lng remark
(up to 242 chars, per-language, sec 7.16.7); a // prefix marks a commented-out
instruction created via [EDCMD] Remark, not typed directly (sec 7.16.8).
Example:
    ! pick side A, slow approach ;
Manual: HandlingTool V9.40 sec 7.16.6

## MESSAGE - show text on the USER screen
Syntax: MESSAGE[<text>] ;
Constraints: text is 1-23 characters (letters, digits, punctuation, spaces);
an empty text prints a blank line between messages; executing the
instruction switches the pendant to the USER screen automatically.
Execution continues - MESSAGE does not pause the program by itself.
Example:
    MESSAGE[part not found bin 3] ;
Manual: HandlingTool V9.40 sec 7.16.9

## $... = - system variable (parameter) assignment
Syntax: $<name> = <value> ;   and read form: R[i] = $<name> ; or PR[i] = $<name> ;
Constraints: numeric-typed variables go to/from R[i], position-typed
(Cartesian xyzwpr or joint) go to/from PR[i] - mixing the two errors out.
Boolean variables take 1 for TRUE and 0 for FALSE. Some variables are
read-only and cannot be written from a program.
Example:
    $WAITTMOUT = 200 ;
    R[10] = $TIMER[1] ;
Manual: HandlingTool V9.40 sec 7.16.10

## UALM - raise a user alarm
Syntax: UALM[i] ;
Effect: posts alarm INTP-213 with the user alarm text defined for slot i,
puts the controller in an alarm state and pauses the program; on resume,
execution continues at the next line.
Constraints: the alarm text for slot i must be set up beforehand
(General Setup, user alarm table).
Example:
    UALM[2] ;
Manual: HandlingTool V9.40 sec 7.16.3

## TIMER - program timer control
Syntax: TIMER[i] = <START|STOP|RESET> ;
Constraints: up to 20 program timers; a timer started in one program can
be stopped in another; current value readable through $TIMER[i] and on
the STATUS Prg Timer screen.
Example:
    TIMER[1] = RESET ;
    TIMER[1] = START ;
Manual: HandlingTool V9.40 sec 7.16.4

## OVERRIDE - set speed override
Syntax: OVERRIDE = <value>% ;
Effect: sets the controller speed override to the given percentage, scaling
all programmed speeds, same as pressing the override keys.
Example:
    OVERRIDE = 50% ;
Manual: HandlingTool V9.40 sec 7.16.5

## JOINT_MAX_SPEED / LINEAR_MAX_SPEED - clamp program speed
Syntax: JOINT_MAX_SPEED[...] = <value> ;  LINEAR_MAX_SPEED[...] = <value> ;
Effect: caps joint motion speed (JOINT_) or linear/circular motion speed
(LINEAR_) for the rest of the program; faster programmed speeds are limited
to the cap. The bracketed index appears in multi-group systems only.
Constraints: calling a macro resets the cap to default, and a cap set inside
a macro is dropped on return to the caller.
Example:
    LINEAR_MAX_SPEED = 250 ;
Manual: HandlingTool V9.40 sec 7.16.11

## PAYLOAD - select payload schedule
Syntax: PAYLOAD[GPx:y] ;
Constraints: y is a payload schedule number, up to 10 schedules per group;
the schedule must be set up beforehand (General Setup). Use it whenever the
carried load changes (gripper open/close, tool change) so motion planning
uses the right inertia data.
Example:
    PAYLOAD[GP1:2] ;
    L P[3] 800mm/sec CNT100 ;
Manual: HandlingTool V9.40 sec 7.22

## LOCK PREG / UNLOCK PREG - position register look-ahead
Syntax: LOCK PREG ;  ...  UNLOCK PREG ;
Effect: LOCK PREG freezes all position registers so no write can change
them, which lets the controller look-ahead-execute motion lines that use
PR[i] between the lock and the unlock; UNLOCK PREG releases them.
Note: user/tool frame changes still affect how locked PR data is resolved.
Example:
    LOCK PREG ;
    L PR[4:place] 500mm/sec CNT100 ;
    UNLOCK PREG ;
Manual: HandlingTool V9.40 sec 7.25

## MONITOR / MONITOR END - condition handler control
Syntax: MONITOR <ch_program> ;  ...  MONITOR END <ch_program> ;
Effect: MONITOR starts watching the WHEN conditions taught in the named
condition-handler program (CH sub-type); when one triggers, its CALL runs
and interrupts the current program. MONITOR END stops the watch.
Constraints: the CH program holds only WHEN lines (see WHEN section).
Example:
    MONITOR DROPCHK ;
    L P[2] 1000mm/sec CNT100 ;
    MONITOR END DROPCHK ;
Manual: HandlingTool V9.40 sec 7.11

## WHEN - condition line inside a CH program
Syntax: WHEN <condition> CALL <program> ;
Constraints: only WHEN lines are allowed in a condition-handler (CH)
program; several conditions join with AND or OR, but one WHEN line may not
mix AND with OR. Conditions cover I/O, registers, system variables, and
alarms via ERR_NUM = aaabbb (facility code aaa, error number bbb; 0 = any).
Example:
    WHEN RI[1]=OFF, CALL DROPPED ;
    WHEN ERR_NUM=11006, CALL HANDFIX ;
Manual: HandlingTool V9.40 sec 7.11
