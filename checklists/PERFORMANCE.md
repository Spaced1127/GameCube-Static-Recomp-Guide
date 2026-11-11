# Performance checklist

- [ ] One deterministic save state; same config/command each run.
- [ ] Record `fps`, `vps`, `speed`, log tail, build hash.
- [ ] Host fixed: physical-core affinity, `Cache\Shaders` exists, cache warm,
      app not muted, background load closed.
- [ ] Low settings (1x/no AA/AF0) measured.
- [ ] High/shipped settings measured.
- [ ] If low ~= high: CPU-bound; stop changing GPU settings.
- [ ] JIT reference measured (`--core jit` / env 0).
- [ ] External GPU/CPU load checked and noted.
- [ ] PGO profile from real gameplay.
- [ ] PGO defines verified in `module-pgo\CMakeCache.txt` (4096/128, not 256/24).
- [ ] `llvm-profdata show --topn` reviewed.
- [ ] `STATICRECOMP_DISPATCH_SAMPLES=1` hot PCs reviewed.
- [ ] Frame-time capture reviewed for stalls (p99, frames > 100 ms), not just
      the average.
- [ ] Frame limiter/idle loop checked.
- [ ] Cache-op fallback counts checked.
- [ ] Cross-chunk direct-call state checked.
- [ ] EFB access correct.
- [ ] FP helper/cache/host-call hotspots considered.
- [ ] Core decision documented: static, JIT, or both.
- [ ] Frame rate capped at 1.0/59.94.
- [ ] Before/after table recorded.
- [ ] No new fallbacks/SMC/exceptions.
