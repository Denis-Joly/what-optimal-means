# what-optimal-means

Code for the Spatium Novum series **What Optimal Means**, five posts on
mathematical optimisation and the guarantee it does and does not give you.

[spatium-novum.com](https://spatium-novum.com)

Everything here runs on open-source solvers. Nothing needs a licence, nothing
phones home, and every number that appears in a post is produced by a script
in this repository rather than typed in by hand.

| | Post | Folder | What the code does |
| --- | --- | --- | --- |
| 1 | [The Last Place "Optimal" Means Anything](https://spatium-novum.com/posts/the-last-place-optimal-means-anything) | [`post-01-the-last-place-optimal-means-anything`](post-01-the-last-place-optimal-means-anything) | Reruns Stigler's 1945 diet problem on all 77 commodities, the computation that took nine clerks 120 man-days in 1947. Prints the dual solution, which is the actual subject of the post. |
| 2 | [Rows, Columns, and What They Cost](https://spatium-novum.com/posts/rows-columns-and-what-they-cost) | [`post-02-rows-columns-and-what-they-cost`](post-02-rows-columns-and-what-they-cost) | Recomputes the Stigler and Netlib matrix statistics, counts standard-form candidate column sets, and generates the article's static and interactive figures. |
| 3 | When the Answer Is Yes or No | [`post-03-when-the-answer-is-yes-or-no`](post-03-when-the-answer-is-yes-or-no) | Solves and independently cross-checks the integer example, enumerates all lattice points, verifies a valid cut, records an exact branch-and-bound certificate trace, and generates the static and interactive figures. |
| 4 | Optimising Against a Guess | `post-04-…` | *not written yet* |
| 5 | Where the Proof Runs Out | `post-05-…` | *not written yet* |

## Run it

If you already have Python and git:

```
git clone https://github.com/Denis-Joly/what-optimal-means
cd what-optimal-means
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
make
```

The virtual environment is not optional politeness. A Homebrew or system
Python will refuse to install anything at all and hand you
`error: externally-managed-environment`, which is PEP 668 protecting the
interpreter your operating system depends on. A `.venv` is a private Python
that belongs to this folder, so nothing you install here can reach anything
else. It is already in `.gitignore`.

`make` runs every post's scripts and rewrites its figures. To run one post
only, `cd` into its folder and read its own README — each is self-contained.

Python 3.10 or later. The dependency list is short on purpose: **PuLP** as the
modelling layer and **HiGHS** as the solver, both open source. The same models
would go to Gurobi or CPLEX by changing one argument, which is worth knowing
and not worth paying for here.

If those four lines mean nothing to you, the next section is the long version.

## If you have never run someone else's code before

Nothing here needs an account, a subscription or an install if all you want is
to read: every file in this repository is visible in the browser, and so is
the output of every script, because the `out/` folders are committed. Click a
folder above and read. What follows is for actually running it.

You need two things on your machine, and you probably have neither, and that is
fine.

**Python** is the language the scripts are written in. **git** is the tool that
copies this repository onto your machine and, later, tells you what changed.
You can skip git entirely if you want — see the note at the end of step 2.

### Step 1 — install Python and git

- **macOS.** Open Terminal and type `python3 --version`. If it prints 3.10 or
  higher you are done. If it prints nothing useful, install Python from
  [python.org/downloads](https://www.python.org/downloads/) — the installer
  from the website, not the `python` that ships with the system, which is old
  and which macOS reserves for itself. Then `git --version`: if git is missing,
  macOS offers to install the developer tools when you run it. Say yes.
- **Windows.** Install Python from
  [python.org/downloads](https://www.python.org/downloads/) and **tick "Add
  python.exe to PATH"** on the first screen of the installer. That checkbox is
  the single most common reason a command works on someone else's machine and
  not on yours. Then install [git-scm.com](https://git-scm.com/downloads),
  which also gives you Git Bash, a terminal where the commands below behave the
  way they do on macOS and Linux. Use Git Bash rather than the Command Prompt.
- **Linux.** Your package manager has both:
  `sudo apt install python3 python3-pip python3-venv git` on Debian or Ubuntu.

Everywhere below, if `python3` is not found, try `python`, and if `pip3` is not
found, try `pip`. Windows tends to want the short forms, macOS and Linux the
long ones. Nothing else changes.

### Step 2 — get the code

```
git clone https://github.com/Denis-Joly/what-optimal-means
cd what-optimal-means
```

`git clone` makes a copy of this repository in a new folder inside whatever
folder your terminal is currently sitting in. `cd` then moves into it, so the
commands that follow apply to these files rather than to your home directory.
Nothing is installed and nothing leaves your machine.

*Without git:* click the green **Code** button at the top of this page,
**Download ZIP**, unzip it, and `cd` into the unzipped folder instead. You lose
the ability to pull later updates with one command. That is the whole
difference.

### Step 3 — make a virtual environment

```
python3 -m venv .venv
source .venv/bin/activate      # Windows, in Git Bash: source .venv/Scripts/activate
```

This step is optional and you should do it anyway. A virtual environment is a
private folder of libraries belonging to this project only. Without it, the
next step installs PuLP and HiGHS system-wide, where they can collide with
something a different project needs. With it, the collision is impossible and
deleting `.venv` undoes everything.

You will know it worked because your prompt grows a `(.venv)` prefix. It lasts
until you close the terminal; reopening one means running the `activate` line
again.

### Step 4 — install the two dependencies

```
python3 -m pip install -r requirements.txt
```

`requirements.txt` lists PuLP and HiGHS with minimum versions. `pip` is
Python's package installer; `-r` means "read the list from this file" rather
than naming packages by hand.

Note the `python3 -m` in front. Plain `pip install` runs whichever `pip`
happens to be first on your PATH, and on a Mac with Homebrew that is often
attached to a different Python from the `python3` that will run the scripts.
The install then succeeds, and the code fails a minute later saying the
package is missing. `python3 -m pip` installs into the interpreter you are
about to use, so the two cannot drift apart. It downloads from PyPI, the public Python
package index, and takes a few seconds. HiGHS arrives as a precompiled wheel,
so there is nothing to build and no compiler to install.

### Step 5 — run one script and read what it says

```
cd post-01-the-last-place-optimal-means-anything
python3 build_data.py
python3 stigler.py
```

`build_data.py` writes the two CSV files the solver reads, and only needs
running once. `stigler.py` is the 1947 computation. It should print something
close to this, with the timing depending on your machine:

```
The 1947 problem, all 77 commodities
------------------------------------
commodities offered   77
solved in             2.3 ms
daily cost            $0.1087
annual cost           $39.66
```

followed by the five commodities in the cheapest diet, and then the part the
post is about:

```
primal objective      $0.108662 per day
dual objective        $0.108662 per day
duality gap           0.00e+00
```

Those three lines are the point of the whole exercise. Two different objects
were computed — a diet, and a price for each nutritional minimum — and they
agree to machine precision. That agreement is the proof that no cheaper diet
exists. If you ever see a duality gap that is not zero here, something is
wrong, and I would like to know about it.

Then `python3 blend.py` for the two-variable problem, which also enumerates
every corner of the polygon by brute force, and `python3 make_figures.py`,
which writes the post's four figures into `out/` as SVG.

### Step 6 — or just run everything

From the repository root:

```
make
```

`make` reads the `Makefile` and runs the steps above in order for every post.
It exists so that no figure in a published post can drift away from the number
in the sentence next to it: regenerating the figures and recomputing the
numbers is one command, not a checklist I might skip.

**Windows has no `make`.** Either install it, or ignore it and run the four
`python3` lines from each post's README by hand, which is exactly what the
`Makefile` automates.

### When it does not work

- **`command not found: python3`** — Python is not on your PATH. On Windows
  this is almost always the unticked checkbox from step 1; reinstall and tick
  it. On macOS, try `python3.12` or whichever version you installed.
- **`No such file or directory: requirements.txt`** — you are not in the
  repository folder. `pwd` shows where you are, `ls` shows what is there.
- **`error: externally-managed-environment`** from pip. Not a broken setup:
  PEP 668, a recent Python refusing to let you install into the interpreter
  your operating system or Homebrew maintains. The remedy is the virtual
  environment from step 3, run from the repository folder:
  `python3 -m venv .venv && source .venv/bin/activate`, then install again.
  Homebrew will suggest `--break-system-packages`; you do not need it, and it
  is called that for a reason.
- **`ModuleNotFoundError: No module named 'pulp'` right after a successful
  install.** The classic one, and not your fault: `pip` and `python3` were
  different interpreters. Check with `which -a python3 pip` and
  `python3 -m pip -V`. The cure is to install through the interpreter itself,
  `python3 -m pip install -r requirements.txt`, and `make` now refuses to
  start until the modules are importable from the Python it is about to use.
  If you skipped the virtual environment, also look for `(.venv)` in your
  prompt.
- **A number differs from the post in the last decimal.** Expected, and
  discussed in the post. Solvers make different tie-breaking choices and the
  historical nutrient table is itself rounded. A different answer is a bug; a
  different fifth decimal is not.
- **Anything else** — open an issue on this repository with the command you ran
  and everything the terminal printed. A failure that reproduces is worth more
  to me than a compliment.

## Figures

Figures are written as standalone SVG by the scripts, not by a plotting
library. They reference the site's CSS custom properties with hex fallbacks, so
they follow the stylesheet when inlined into a page, including its dark
scheme, and still render correctly
when opened on their own. Every figure in a post is regenerated by `make`, so a
figure and the number in the sentence next to it cannot drift apart.

## Licence

MIT for the code. Data sources are credited in each post's README and are not
redistributed except where the table is small, historical and already public,
in which case it is committed as a CSV so the numbers being solved are
visible rather than buried in a library.
