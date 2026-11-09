# Automation directory

The runner's `--automation-dir <dir>` provides a file-based test interface.

```text
<dir>/
  status.txt          written by the runner
  commands/           the runner reads command files here
    stop.txt
    shot.txt
    state.txt
```

Commands are key/value text files. Use any filename; `.txt` is conventional.

```text
command=stop
```

```text
command=pad_frames
port=0
frames=90
main_y=1
```

```text
command=screenshot
path=C:/absolute/path/shot.png
```

```text
command=save_state
path=C:/absolute/path/gameplay.state
```

```text
command=load_state
path=C:/absolute/path/gameplay.state
```

See the runtime's `automation_protocol.cpp` for the full field list
(`pad`, `clear_pad`, `pause`, `resume`, `read_memory`, `write_memory`).

`status.txt` is the evidence file. Its fields are documented in
[status-fields.md](status-fields.md).

Use `--load-state` instead of replaying menus for benchmarks. Stop the process
with `command=stop` so the log/PGO profile flushes.
