"""Drive find_probe.py through many run modes and directory layouts."""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(HERE, ".venv", "bin", "python")
PROBE = os.path.join(HERE, "scripts", "find_probe.py")

results = {"pass": 0, "fail": 0}


def run_probe(mode, cwd, base, args, settrace=False, frozen=False):
    env = dict(os.environ)
    env["FIND_BASE"] = base
    env.pop("PYTHONPATH", None)
    probe_src = open(PROBE).read()
    # Optionally wrap to install a tracer or set sys.frozen before calling.
    prelude = ""
    if settrace:
        prelude += "import sys\nsys.settrace(lambda *a: None)\n"
    if frozen:
        prelude += "import sys\nsys.frozen=True\n"
    if mode == "script":
        proc = subprocess.run(
            [PY, PROBE, *args], cwd=cwd, env=env, capture_output=True, text=True
        )
    elif mode == "module":
        # run as module: copy probe into cwd as a package-free module
        modpath = os.path.join(cwd, "finder_mod.py")
        with open(modpath, "w") as fh:
            fh.write(prelude + probe_src)
        proc = subprocess.run(
            [PY, "finder_mod.py", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
    elif mode == "minusm":
        modpath = os.path.join(cwd, "finder_mod.py")
        with open(modpath, "w") as fh:
            fh.write(prelude + probe_src)
        proc = subprocess.run(
            [PY, "-m", "finder_mod", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
    elif mode == "minusc":
        code = (
            prelude
            + "import runpy,sys; sys.argv=['x',"
            + ",".join(repr(a) for a in args)
            + "]; runpy.run_path(%r)" % PROBE
        )
        proc = subprocess.run(
            [PY, "-c", code], cwd=cwd, env=env, capture_output=True, text=True
        )
    elif mode == "stdin":
        code = (
            prelude
            + "import runpy,sys; sys.argv=['x',"
            + ",".join(repr(a) for a in args)
            + "]; runpy.run_path(%r)" % PROBE
        )
        proc = subprocess.run(
            [PY], cwd=cwd, env=env, input=code, capture_output=True, text=True
        )
    else:
        raise ValueError(mode)
    return proc


def check(label, mode, cwd, base, args, **kw):
    proc = run_probe(mode, cwd, base, args, **kw)
    out = proc.stdout.strip().splitlines()
    data = None
    for ln in out:
        if ln.startswith("{"):
            data = json.loads(ln)
    if data is None:
        print("NO OUTPUT", label, mode, proc.stdout, proc.stderr[-300:])
        results["fail"] += 1
        return
    if data["oracle"] == data["mine"]:
        results["pass"] += 1
    else:
        results["fail"] += 1
        print("MISMATCH", label, mode, data)


def main():
    # Build a tree: base/a/b/  with .env at base/a/
    for scenario in ("env_in_parent", "no_env", "env_at_root_of_tree"):
        base = tempfile.mkdtemp()
        a = os.path.join(base, "a")
        b = os.path.join(a, "b")
        os.makedirs(b)
        if scenario == "env_in_parent":
            open(os.path.join(a, ".env"), "w").write("X=1\n")
        elif scenario == "env_at_root_of_tree":
            open(os.path.join(base, ".env"), "w").write("X=1\n")
        for mode in ("script", "module", "minusm", "minusc", "stdin"):
            # run from b
            check(f"{scenario}/default", mode, b, base, [".env", "0", "0"])
            check(f"{scenario}/usecwd", mode, b, base, [".env", "1", "0"])
            check(f"{scenario}/raise", mode, b, base, [".env", "0", "1"])
            check(f"{scenario}/custom-name", mode, b, base, ["cfg.ini", "0", "0"])
        # tracer + frozen variants (script mode uses module file)
        check(
            f"{scenario}/tracer", "module", b, base, [".env", "0", "0"], settrace=True
        )
        check(f"{scenario}/frozen", "module", b, base, [".env", "0", "0"], frozen=True)
        shutil.rmtree(base)
    print(f"\nfind_dotenv: {results['pass']} passed, {results['fail']} failed")


if __name__ == "__main__":
    main()
