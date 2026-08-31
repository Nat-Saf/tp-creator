# Testing examples

Grader-style prompts with their VERIFIED program outputs.
Each pair was produced by a live run through /api/execute
and saved only after passing its property checks.

| # | Prompt | Output |
|---|---|---|
| 01 | pick a part from the conveyor and put it on fixture A, gently | `01_basic_pick_place.ls` |
| 02 | pick a part from the conveyor and place it on fixture B | `02_pick_place_fixture_b.ls` |
| 03 | write a program called DEMO_CYCLE that moves from home to conveyor approach at 150mm/sec and back home | `03_named_program_speed.ls` |
| 04 | move from home to the camera inspection pose, turn the camera on, wait for a minute, turn the camera off, and return home | `04_camera_minute_wait.ls` |
| 05 | pick from the conveyor and place on fixture A, but before picking wait until part present is on with a 5 second timeout to an error label | `05_wait_part_present_timeout.ls` |
| 06 | pick and place from the conveyor to fixture A and increment the cycle count at the end | `06_cycle_counter.ls` |
| 07 | pick from the conveyor to fixture A and pulse the green lamp for 1 second at the end | `07_lamp_pulse.ls` |
| 08 | pick from the conveyor, verify the gripper closed feedback after closing the gripper, then place on fixture A | `08_gripper_feedback.ls` |
| 09 | pick from the conveyor and place on fixture A, repeat the cycle 3 times | `09_repeat_three_cycles.ls` |
| 10 | write a program that turns the buzzer on for 2 seconds and then off, with no motion at all | `10_io_only_buzzer.ls` |
| 11 | move from home through conveyor approach to fixture A approach without stopping at the middle point, then back home | `11_smooth_through_point.ls` |
| 12 | move the robot from the safe travel point to the purge station and then home | `12_from_to_points.ls` |
| 13 | if the part present input is on, pick from the conveyor and place on fixture A; otherwise just go back to home | `13_conditional_pick.ls` |
| 14 | move from home to conveyor approach, start the conveyor, wait until conveyor running is on with a 10 second timeout to an error label, then stop the conveyor and go home | `14_conveyor_handshake.ls` |
| 15 | move from home to fixture A approach, then move down by 50mm using PR[10] as a scratch register, and return home | `15_relative_down_named_scratch.ls` |
