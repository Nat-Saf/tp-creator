# io - own-words syntax notes

## DO - digital output set
Syntax: DO[i] = <ON|OFF> ;   or   DO[i] = R[j] ;
Sets a user digital output signal. With a register source, 0 switches the
output OFF and any non-zero value switches it ON.
I/O instructions execute as soon as the previous line finishes; they do not
wait for motion in progress unless taught as a motion option.
Example:
    DO[3:gripper close] = ON ;
    DO[4] = R[7] ;
Manual: HandlingTool V9.40 sec 7.13.2

## DO PULSE - timed digital output
Syntax: DO[i] = PULSE [,width] ;
Turns the digital output ON for the given duration, then back OFF. Width is
written in seconds (e.g. ,0.5sec). When the width is omitted the controller
uses system variable $DEFPULSE, which is stored in 100-msec units (0-255).
Program execution continues while the pulse runs.
Example:
    DO[11:cycle done] = PULSE ,0.5sec ;
    DO[12] = PULSE ;
Manual: HandlingTool V9.40 sec 7.13.2

## R = DI - read digital input
Syntax: R[i] = DI[j] ;
Copies the state of a user digital input into a register: ON stores 1, OFF
stores 0. Use this to latch an input value at a known instant instead of
testing the live signal later in the program.
Example:
    R[10:part present] = DI[2:part sensor] ;
Manual: HandlingTool V9.40 sec 7.13.2

## RO - robot digital output
Syntax: RO[i] = <ON|OFF> ;   or   RO[i] = PULSE [,width] ;   or   RO[i] = R[j] ;
Robot outputs are the signals wired through the end-effector (EE) connector
on the robot arm, typically driving gripper valves. Forms mirror DO: direct
ON/OFF, a timed pulse (width in seconds, $DEFPULSE when omitted), or a
register source where 1 means ON and 0 means OFF. The signal count depends
on the robot model.
Example:
    RO[1:vacuum on] = ON ;
    RO[2] = PULSE ,0.3sec ;
Manual: HandlingTool V9.40 sec 7.13.3

## R = RI - read robot input
Syntax: R[i] = RI[j] ;
Stores the state of a robot input (EE connector, e.g. a gripper-open feedback
switch) into a register: ON stores 1, OFF stores 0.
Example:
    R[15:grip feedback] = RI[1] ;
Manual: HandlingTool V9.40 sec 7.13.3

## GO - group output
Syntax: GO[i] = value ;   or   GO[i] = R[j] ;
Writes a decimal value onto a group of digital output lines as its binary
equivalent in one instruction. Handy for sending a part style or station
number to a PLC as one number instead of setting bits individually.
Example:
    GO[1:style code] = 5 ;
    GO[2] = R[11] ;
Manual: HandlingTool V9.40 sec 7.13.5

## R = GI - read group input
Syntax: R[i] = GI[j] ;
Reads the binary pattern present on a group of digital inputs and stores its
decimal value in a register.
Example:
    R[12:plc command] = GI[1] ;
Manual: HandlingTool V9.40 sec 7.13.5

## AO - analog output
Syntax: AO[i] = value ;   or   AO[i] = R[j] ;
Sends a numeric value to an analog output channel; the magnitude represents
a continuous quantity such as a voltage or speed reference.
Example:
    AO[1:flow ref] = 100 ;
    AO[2] = R[20] ;
Manual: HandlingTool V9.40 sec 7.13.4

## R = AI - read analog input
Syntax: R[i] = AI[j] ;
Stores the current value of an analog input channel (for example a
temperature or pressure transducer reading) in a register.
Example:
    R[21:pressure] = AI[3] ;
Manual: HandlingTool V9.40 sec 7.13.4

## I/O in IF conditions
Syntax: IF <DI|DO|RI|RO|SI|SO|UI|UO>[i] <=|<>> <ON|OFF>, <JMP LBL[x]|CALL prog> ;
Digital-type signals compare against ON/OFF; AI/AO and GI/GO compare against
numeric values with =, <>, <, >, <=, >=. Up to 5 conditions may be joined
with AND or OR, but AND and OR cannot be mixed on one line.
Example:
    IF DI[2]=ON AND DI[3]=OFF, JMP LBL[10] ;
    IF GI[1]=5, CALL STYLE5 ;
Manual: HandlingTool V9.40 sec 7.9.4

## I/O in WAIT conditions
Syntax: WAIT <DI|DO|RI|RO|SI|SO|UI|UO>[i] <=|<>> <ON|OFF> [TIMEOUT,LBL[x]] ;
Pauses execution until the signal condition is true. With no timeout clause
the wait lasts forever; with TIMEOUT,LBL[x] the program jumps to the label
after $WAITTMOUT expires ($WAITTMOUT is in 100ths of a second, default
3000 = 30 sec). Conditions can be chained with AND or OR (no mixing).
Example:
    WAIT DI[5:clamp closed]=ON TIMEOUT,LBL[99] ;
Manual: HandlingTool V9.40 sec 7.36

## UO/SO - system status signals (read-only use)
Syntax: read-only in practice: IF UO[i]=ON ...  /  WAIT SO[i]=OFF ...
UO signals are UOP outputs the controller drives to report its own state,
e.g. UO[1] CMDENBL, UO[2] SYSRDY, UO[3] PROGRUN, UO[4] PAUSED, UO[6] FAULT.
SI/SO belong to the standard operator panel; their assignments are fixed and
cannot be changed. Treat UO and SO as status to test in IF/WAIT conditions,
never as outputs your program sets. UI inputs are likewise read in
conditions (e.g. WAIT UI[i]=ON), while the cell controller drives them.
Example:
    WAIT UO[6:fault]=OFF ;
Manual: HandlingTool V9.40 sec 13.9.3
