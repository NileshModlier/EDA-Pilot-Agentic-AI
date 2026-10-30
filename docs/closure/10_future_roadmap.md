# Future Roadmap

The baseline is closed. Later work starts from `results/final_benchmark_results.json` and does not replace those trials.

## Now: make the missing method real

Repair the AutoTuner environment so Ray can import HyperOpt, confirm `openroad_autotuner --help` from the same Windows entry point the harness uses, and run budget 10, seed 1, on gcd, AES, and Ibex. Record a failure as a failure. Leave the existing default, random, and agent rows unchanged.

## Next: test whether the clock gains hold

Repeat random search and the agent at additional seeds on the same three designs and the same allowlist. Report the distribution of the best passing clock, not a single seed. Keep the 0.05 ns early-stop rule, and always publish the number of runs used.

## Then: separate the score from the story

Add a second published table that ranks the same trials by area and by power among signoff points. The current primary key stays the clock. Readers should be able to see both rankings without a new flow.

## After that: broaden the flow, one platform at a time

Candidates already named by the project, and not yet measured, are a second PDK such as nangate45 and a larger sky130hd design. Each addition needs `config.mk`, `constraint.sdc`, and `autotuner.json`, and the allowlist must still refuse names and ranges the design file tries to widen.

## Keep the boundary while the search changes

If a chat model replaces the offline clock search, it stays on analyse and propose. Validate, run, and check remain code. New knobs enter through `configs/allowed_parameters.json`, not through a prompt.

## Hardening that the campaign already paid for

- Write the ORFS error line into the trial record when `make` exits.
- Treat a dead parent as an unscored attempt even if the manifest still says running.
- Checkpoint the agent clock bounds after every iteration, not only at the end of the session.
- Source `env.sh` inside WSL for every flow launch, and generate metadata after a successful `finish`.

## Explicitly out of scope until the measurements above exist

DRC prediction, reinforcement learning, and SlackGNN were excluded from this project. They stay excluded until AutoTuner has scores and the clock result has been repeated across seeds.
