# registers - own-words syntax notes

## R[i]= - numeric register assignment
Syntax: R[i] = <value> ;
Value sources: constant, R[j], PR[j,k], AR[j], DI/DO, RI/RO, GI/GO, AI/AO,
SI/SO, UI/UO, TIMER[j], TIMER_OVERFLOW[j]
Constraints: one register holds one number (integer or decimal); default
count is 32 and the pool can be raised to 999 at a controlled start; an
optional comment rides inside the brackets as R[i:comment]
Example:
    R[7:part count]=0 ;
    R[3]=DI[8] ;
Manual: HandlingTool V9.40 sec 7.29

## R[i]=x op y - register arithmetic
Syntax: R[i] = <value> <+|-|*|/|DIV|MOD> <value> [op <value> ...] ;
Operators: + - * / DIV (whole-number quotient) MOD (remainder)
Constraints: at most 5 operators per line; + and - may share a line, and so
may * and /, but the two groups never mix in one instruction; evaluation
runs left to right, not by precedence
Example:
    R[10]=R[10]+1 ;
    R[12]=R[4]*100/R[6] ;
    R[5]=R[9] MOD 4 ;
Manual: HandlingTool V9.40 sec 7.29

## R[R[i]] - indirect register addressing
Syntax: R[R[i]] = <value> ;   (also PR[R[i]], PL[R[i]], DI[R[i]], ...)
Meaning: the inner register's current value selects which outer register or
signal index the instruction touches, so one line can walk a table
Constraints: the inner value must land on an existing register/port number
at run time; works anywhere an index appears, including signal brackets
Example:
    R[1]=6 ;
    R[R[1]]=25 ;    (writes 25 into R[6])
    PR[R[2]]=LPOS ;
Manual: HandlingTool V9.40 sec 7.29

## PR[i]= - position register assignment
Syntax: PR[i] = <PR[j]|P[j]|LPOS|JPOS|UFRAME[j]|UTOOL[j]> ;
Sources: another PR, a taught position P[j], the current Cartesian pose
(LPOS), the current joint pose (JPOS), or a user/tool frame value
Constraints: a PR stores X,Y,Z,W,P,R plus configuration (or joint angles);
default 100 registers, expandable to 2000 on single-group systems at a
controlled start; multi-group systems can prefix a group as PR[GRPn:i]
Example:
    PR[8:home]=JPOS ;
    PR[10]=UFRAME[3] ;
Manual: HandlingTool V9.40 sec 7.24.2

## PR[i] arithmetic - whole-register add and subtract
Syntax: PR[i] = <value> <+|-> <value> [op <value> ...] ;
Operands: PR[j], P[j], LPOS, JPOS as terms after the first
Constraints: only + and - exist for whole position registers (no * / DIV
MOD at this level); at most 5 operators per line; addition is element by
element, handy for applying a stored shift to a pose
Example:
    PR[3]=PR[3]+PR[6:shift] ;
Manual: HandlingTool V9.40 sec 7.24.2

## PR[i,j] - position register element access
Syntax: PR[i,j] = <value> [<+|-|*|/|DIV|MOD> <value> ...] ;
Element j (Cartesian representation): 1=X 2=Y 3=Z 4=W 5=P 6=R
Element j (joint representation): axis number, 1=J1 ... n=Jn
Constraints: scalar sources match R[i]= (constant, R, PR[i,j], I/O, timers);
same mixing rules as register arithmetic, max 5 operators; which mapping of
j applies depends on how the register currently stores its data
Example:
    PR[4,3]=PR[4,3]+50 ;    (raise stored Z by 50 mm)
    PR[2,6]=R[11] ;
Manual: HandlingTool V9.40 sec 7.24.3

## LOCK PREG / UNLOCK PREG - freeze position registers for look-ahead
Syntax: LOCK PREG ;  ...  UNLOCK PREG ;
Purpose: LOCK PREG blocks every write to position registers so the
controller can safely read motion lines ahead of execution; UNLOCK PREG
releases the block
Constraints: bracket PR-writing logic between the pair when nearby motion
lines consume those registers
Example:
    LOCK PREG ;
    PR[5,1]=R[20] ;
    UNLOCK PREG ;
Manual: HandlingTool V9.40 sec 7.25

## PL[i]= - pallet register assignment
Syntax: PL[i] = [row, column, layer] ;
Constraints: a pallet register holds the three palletizing counters in the
order row, column, layer; registers are numbered from 1 (32 by default,
expandable to 127 at a controlled start); arithmetic offers + and - only,
max 5 operators; indirect form PL[R[j]] is allowed; comparisons in IF
lines may wildcard an element with *
Example:
    PL[1]=[1,1,1] ;
    PL[R[6]]=[2,4,1] ;
Manual: HandlingTool V9.40 sec 7.7

## SR[i]= - string register assignment and concatenation
Syntax: SR[i] = <SR[j]|R[j]|AR[j]> [+ <SR|R|AR term> ...] ;  also R[i]=SR[j]
Constraints: each string register holds up to 254 characters; default 25
registers, expandable at a controlled start; numbers are converted to text
automatically (floats rounded to 6 decimal places); text converts back to a
number until the first alphabetic character, so a pure-letter string reads
as 0
Example:
    SR[2]=SR[1] ;
    SR[3]=SR[1]+R[5] ;
Manual: HandlingTool V9.40 sec 7.31

## STRLEN / FINDSTR / SUBSTR - string register functions
Syntax: R[i]=STRLEN SR[j] ;  R[i]=FINDSTR SR[j],SR[k] ;
        SR[i]=SUBSTR SR[j],R[m],R[n] ;
Semantics: STRLEN returns character count; FINDSTR searches target SR[j]
for SR[k] case-insensitively and returns the 1-based index, 0 when absent;
SUBSTR cuts from start position R[m] for length R[n]
Constraints: SUBSTR raises an overflow alarm when start <= 0, length < 0,
or start (or start+length) runs past the target string's end
Example:
    R[14]=STRLEN SR[2] ;
    R[15]=FINDSTR SR[2],SR[6] ;
    SR[4]=SUBSTR SR[2],R[1],R[2] ;
Manual: HandlingTool V9.40 sec 7.31
