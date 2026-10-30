# OpenROAD dependency check

Checked: 2026-10-17

Host: Ubuntu 26.04 LTS on WSL. No packages were installed and no build was started. `sudo` requires an interactive password. `etc/DependencyInstaller.sh` accepts KLayout packages for Ubuntu 20.04, 22.04, and 24.04 only.

| Tool | Result | Path | Version |
| --- | --- | --- | --- |
| make | PASS | /usr/bin/make | GNU Make 4.4.1 |
| python3 | PASS | /usr/bin/python3 | Python 3.14.4 |
| cmake | FAIL | not found | not reported |
| gcc | PASS | /usr/bin/gcc | gcc (Ubuntu 15.2.0-16ubuntu1) 15.2.0 |
| g++ | PASS | /usr/bin/g++ | g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0 |
| swig | FAIL | not found | not reported |
| tcl | PASS | /usr/bin/tclsh | not reported |
| git | PASS | /usr/bin/git | git version 2.53.0 |

Summary: missing cmake, swig.
