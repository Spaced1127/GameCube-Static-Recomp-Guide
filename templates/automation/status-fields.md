# status.txt fields

| Field | Meaning |
|---|---|
| `state` | `running`, `paused`, `stopped`, etc. |
| `booted` | `1` after the core booted |
| `fps` | rendered/presented frames per second |
| `vps` | VI fields per second (should be ~59.94 at full speed) |
| `speed` | emulated speed; `1.0` is full speed |
| `frame_count` | guest frame counter (can carry across a save state) |
| `present_count` | presented frames |
| `title` | window title / game title |
| `game_id` | disc ID, e.g. `GSQE78` |
| `game_name` | game name |
| `navigation_*` | game-specific navigation/memory diagnostics |
| `processed_commands` | number of automation commands handled |
| `last_command` | last command file name |
| `last_error` | last command error |

For a performance claim, record `fps`, `vps`, `speed`, `frame_count`,
`present_count`, `title`, the config, the core (static/JIT), the save state and
the external load. Do not rely on a single instantaneous sample; wait for
shader/JIT warm-up and sample over 20-30 seconds.
