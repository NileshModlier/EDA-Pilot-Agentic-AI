# Build OpenROAD

Checked on 2026-10-17 against checkout `ef421749a`.

These two files are absent:

- `tools/OpenROAD/build/bin/openroad`
- `tools/install/OpenROAD/bin/openroad`

`source ./env.sh` puts `tools/install/OpenROAD/bin` on `PATH`. The CMake build tree, when a local compile finishes, is `tools/OpenROAD/build/bin/openroad`. Neither binary exists, so `openroad -version` cannot run. The build was not started.

## This WSL distro

The distro is Ubuntu 26.04 LTS. `etc/DependencyInstaller.sh` in this checkout installs KLayout only for Ubuntu 20.04, 22.04, and 24.04. On any other release it exits with `Unsupported Ubuntu version`. `sudo ./setup.sh` on this 26.04 distro stops there.

Two more blockers showed up before a compile could start:

- `cmake` and `swig` are not installed. `make`, `python3`, `gcc`, `g++`, `tclsh`, and `git` are present. See `reports/openroad_dependencies.md`.
- `sudo` asks for a password, and this session cannot answer that prompt.

Disk space is not the blocker. `/home` has hundreds of gigabytes free. The compile itself needs the supported OS, the missing packages, and a sudo password. A full local build also takes a long time and should be left running in an Ubuntu terminal, not cancelled mid-compile.

## Supported Ubuntu and WSL

Use Ubuntu 22.04 or 24.04, either as the WSL distro or as a separate machine. From the checkout:

```bash
cd /home/administrator/OpenROAD-flow-scripts
git submodule update --init --recursive
sudo ./setup.sh
./build_openroad.sh --local
```

`setup.sh` must be run with sudo on Linux. It installs OpenROAD's packages and then the common ORFS packages. `build_openroad.sh --local` compiles on this machine instead of building a Docker image. The log is `build_openroad.log` in the checkout root.

`--threads N` limits the compile. `--openroad_only` with `--local` builds OpenROAD and skips Yosys. The gcd flow still needs Yosys, so the benchmark machine should use the plain `--local` build.

Load the built tools and check the binary:

```bash
source ./env.sh
command -v openroad
openroad -version
test -x tools/OpenROAD/build/bin/openroad && echo build-tree-ok
test -x tools/install/OpenROAD/bin/openroad && echo install-tree-ok
```

`openroad -version` has to print a version line before the gcd smoke test in `reports/openroad_smoke_test.md` can pass.

## WSL notes

Install Ubuntu 22.04 or 24.04 with `wsl --install -d Ubuntu-22.04` or `Ubuntu-24.04` if the current 26.04 distro should stay as it is. Clone or copy the checkout there, then run the same `sudo ./setup.sh` and `./build_openroad.sh --local` commands.

Docker is the other path documented in the checkout at `docs/user/BuildWithDocker.md` and `docs/user/BuildWithWSL.md`. That path was not used here. The benchmark still needs an `openroad` executable that `openroad -version` can run.

Upstream build notes for this commit live in the checkout:

- `docs/user/BuildLocally.md`
- `docs/user/BuildWithWSL.md`
