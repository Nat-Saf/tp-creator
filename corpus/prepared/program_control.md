# program_control - own-words syntax notes

## PAUSE - suspend program execution
Syntax: PAUSE ;
Constraints: execution stops at this line but the controller finishes what
is already in flight: a motion segment underway runs to its endpoint,
running timers keep counting, and active PULSE outputs complete.
The current instruction also completes - except a program CALL, which is
held and performed when the operator resumes. Resume continues in place.
Example:
    DO[3:blocked]=ON ;
    PAUSE ;
Manual: HandlingTool V9.40 sec 7.26.2

## ABORT - terminate the program
Syntax: ABORT ;
Constraints: ends the program immediately and cancels any motion that is
in progress or still queued. Unlike PAUSE there is no resume - the
program must be restarted from scratch. Use for unrecoverable states;
prefer PAUSE when an operator should be able to continue.
Example:
    IF R[9:fault count]>3, JMP LBL[99] ;
    LBL[99] ;
    ABORT ;
Manual: HandlingTool V9.40 sec 7.26.3

## OVERRIDE - program speed override
Syntax: OVERRIDE = <value>% ;   value = constant, R[i] or AR[i]
Units: percent of programmed speed
Constraints: value range 1-100; acts like turning the pendant override
from within the program, scaling all subsequent programmed speeds.
It changes the global override, so it persists after the program ends.
Example:
    OVERRIDE = 50% ;
    OVERRIDE = R[8:line speed]% ;
Manual: HandlingTool V9.40 sec 7.16.5

## TIMER - program timer control
Syntax: TIMER[i] = <START|STOP|RESET> ;   also TIMER[i]=(value) to preload
Constraints: up to 20 program timers; a timer started in one program can
be stopped in another. START on an already-running timer is ignored with
warning INTP-685. RESET zeroes the count and clears the overflow flag;
TIMER[i]=(expr) loads a starting value and starts counting.
State is visible in $TIMER[n] and on the STATUS Prg Timer screen.
A local timer belongs to the task that started it - make it global on the
program timer screen if several tasks must touch it.
Example:
    TIMER[1] = RESET ;
    TIMER[1] = START ;
    TIMER[1] = STOP ;
Manual: HandlingTool V9.40 sec 7.16.4

## R[i] = TIMER[i] - read a timer into a register
Syntax: R[i] = TIMER[j] ;   R[i] = TIMER_OVERFLOW[j] ;
Units: seconds (elapsed time)
Constraints: TIMER[j] is a legal right-hand value in register instructions
and in comparisons, so cycle times can be measured and tested in-program.
TIMER_OVERFLOW[j] reads 0 or 1; the flag sets once the timer passes
2147483.647 seconds. RESET clears both the count and the flag.
Example:
    TIMER[2] = STOP ;
    R[10:cycle sec] = TIMER[2] ;
    IF R[10:cycle sec]>30, JMP LBL[20] ;
Manual: HandlingTool V9.40 sec 7.29

## UALM - user alarm
Syntax: UALM[i] ;
Constraints: raises user alarm number i, pauses the program, and prints
the alarm text on the error line as INTP-213 UALM[i] <message> with the
program name and line number. The message text per alarm number is
defined in the user alarm setup ($UALRM_MSG[i]), not in the TP line.
On resume, execution continues at the line after the UALM.
Example:
    IF DI[5:feeder empty]=OFF, JMP LBL[1] ;
    UALM[1] ;
    LBL[1] ;
Manual: HandlingTool V9.40 sec 7.16.3

## ERROR_PROG - register an error-handler program
Syntax: ERROR_PROG = <program_name> ;
Constraints: stores the named TP program into system variable $ERROR_PROG
so the shell task can run it as the error recovery routine when a fault
occurs. Name an existing program; the effect depends on how the cell's
error handling is configured.
Example:
    ERROR_PROG = ERR_RECOVER ;
Manual: HandlingTool V9.40 sec 7.26.4

## RESUME_PROG - register a resume program
Syntax: RESUME_PROG = <program_name> ;
Constraints: stores the named program into system variable $RESUME_PROG
for the error recovery option; the system uses it when resuming after a
fault. Distinct from the Fast Fault Recovery resume function - do not
confuse the two. Requires the error recovery option to have any effect.
Example:
    RESUME_PROG = SAFE_RETURN ;
Manual: HandlingTool V9.40 sec 7.26.5

## CLEAR_RESUME_PROG - clear the resume program
Syntax: CLEAR_RESUME_PROG ;
Constraints: erases the resume-program setting made by RESUME_PROG, so no
resume routine runs afterward. Part of the error recovery option; takes
no arguments. Pair it with RESUME_PROG around the region that needs the
special resume behavior.
Example:
    RESUME_PROG = SAFE_RETURN ;
    ! risky zone here ;
    CLEAR_RESUME_PROG ;
Manual: HandlingTool V9.40 sec 7.26.7
