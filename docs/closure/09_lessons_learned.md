# Lessons Learned

These come from the implemented system and the completed sky130hd runs.

## A passing clock is a different objective from a fast default

Default ORFS finished gcd, AES, and Ibex with DRC = 0 and still failed signoff on setup. Treating the default period as the thing to beat would have rewarded a broken clock. The leaderboard had to require setup and hold slack before it compared periods.

## The tighter clock spends area, power, and time

On every design, random search’s best signoff was smaller, lower power, and faster to produce than the agent’s best signoff. The agent won because the primary key was clock. A PPA-weighted score would have ranked the methods differently. That split should be said in the same sentence as the clock win.

## The model must not be on the launch path

Analyse and propose only suggest. The runs that mattered were the ones where validation, `make`, and metrics stayed in code. When a proposal was illegal, the flow did not start. That boundary held for the whole campaign.

## Windows cannot see GNU Make

The first real `run_flow` failed with `FileNotFoundError` because `make` exists inside WSL, not on the Windows `PATH`. The durable fix was a narrow bridge: detect a WSL flow path, run `make finish` there, then run `metadata-generate`. `finish` alone does not write `metadata.json`, and without that file the harness cannot score a successful GDS run.

## A “running” manifest is not a live run

Several AES and Ibex manifests stayed at `status: running` after the parent process died, including during a pause that did not survive overnight. Liveness had to be checked with the process list and the log timestamp. The scored record kept the completed trials and stored the dead attempt as unscored. Replaying an incomplete route database would have inflated runtime across the gap.

## Checkpoint after every scored trial

The campaign could resume only because each finished random trial was written before the next one started. The agent session was different: its decision log grew during the run, but the checkpoint row appeared at the end. A killed agent therefore needed the log replayed into the same clock bounds. Starting that search over repeated multi-hour AES flows.

## Early stop is a sample-size statement

Ibex converged on the first passing 9.0 ns run. That is a successful stop under the 0.05 ns rule, and it is one observation. Quoting it as a 100% signoff rate beside AES, which used 10 runs, overstates the evidence. The report now shows the denominator.

## Tool installation is part of the method

AutoTuner’s source tree was present for the whole study. gcd and AES still have an unavailable row because the executable was missing when those designs ran. Installing it later, on Ubuntu’s Python 3.14, failed the pinned Ray release. A Python 3.12 environment imported the CLI, and the Ibex launch then died because HyperOpt was not visible to Ray. An unmeasured method has to stay empty.

## Failure classes are more useful than exit status 2

gcd’s campaign file stored only “ORFS exited with status 2.” The logs showed density and detailed-placement errors, the same classes that dominated AES and Ibex. The cause line has to be captured when the run ends, or the failure table depends on archaeology.
