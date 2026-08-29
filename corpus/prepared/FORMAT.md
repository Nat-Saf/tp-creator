# prepared/ extraction format (what the indexer reads)

One file per instruction family (motion.md, registers.md, io.md, branching.md,
wait_skip.md, frames_offset.md, program_control.md, misc.md, position_format.md).

One `##` section per instruction = one chunk. Section template:

## L - linear motion
Syntax: L <P[i]|PR[i]> <speed><unit> <FINE|CNTn> [options] ;
Units: mm/sec, cm/min, inch/min, deg/sec, sec, msec (NOT % - joint only)
Constraints: CNT value 0-100; options order per manual 7.2
Example:
    L PR[5:conveyor pick] 100mm/sec CNT50 Offset,PR[2] ;
Manual: HandlingTool V9.40 sec 7.2.2

Rules: plain ASCII, no tables, one example minimum per section, keep the
manual section reference. corpus/raw/ PDFs are provenance only - never indexed.
