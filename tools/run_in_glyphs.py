#!/usr/bin/env python3
"""Run this project's interactive tools inside the running Glyphs 3 app.

Examples (from the project directory):
    python3 tools/run_in_glyphs.py --list
    python3 tools/run_in_glyphs.py create_scaled_glyphs_from_components
    python3 tools/run_in_glyphs.py tools/generate_component_layers.py

Uses Glyphs' remote scripting API. No installation into Glyphs' Scripts folder,
source copying, or hard-coded project paths. Python needs PyObjC/Foundation.
"""

import argparse
from pathlib import Path
import sys
import textwrap
import uuid


PROJECT = Path(__file__).resolve().parent.parent
TOOLS = PROJECT / "tools"
PORT = "com.GeorgSeifert.Glyphs3"


def available_scripts(directory=TOOLS):
    result = {}
    for path in sorted(directory.glob("*.py")):
        with path.open(encoding="utf-8-sig") as source:
            first_line = source.readline().strip()
        if first_line.startswith("# MenuTitle:"):
            result[path.stem] = (path, first_line.split(":", 1)[1].strip())
    return result


def select_script(value, scripts):
    # Accept a stem, filename, or project-relative tools/filename.py.
    name = value.removeprefix("tools/")
    if name.endswith(".py"):
        name = name[:-3]
    if name not in scripts:
        raise ValueError("Unknown Glyphs tool. Use --list to see the available names.")
    path = scripts[name][0].resolve()
    if path.parent != TOOLS:
        raise ValueError("The tool must be a file in this project's tools directory.")
    return path


def make_payload(relative_script, marker, project=PROJECT):
    """Run in a fresh __main__ namespace, including dataclass support via runpy."""
    return textwrap.dedent('''\
        def _run_project_tool():
            import os
            from pathlib import Path
            import runpy
            import sys
            import traceback
            from GlyphsApp import Glyphs

            project = Path(%r)
            relative_script = %r
            marker = %r
            original_cwd = os.getcwd()
            original_path = sys.path[:]
            original_bytecode = sys.dont_write_bytecode
            try:
                font = Glyphs.font
                if relative_script is None:
                    print("Connected to Glyphs 3.")
                    if font is None:
                        print("Open this project's font before running a tool.")
                    else:
                        print("Active font: " + font.familyName)
                else:
                    if font is None or not font.filepath:
                        raise RuntimeError("Open a saved font from this project in Glyphs first.")
                    if project not in Path(font.filepath).resolve().parents:
                        raise RuntimeError("The active font belongs to another project. Select this project's font first.")
                    os.chdir(str(project))
                    sys.path.insert(0, str(project / "tools"))
                    sys.path.insert(0, str(project))
                    sys.dont_write_bytecode = True
                    runpy.run_path(str(project / relative_script), run_name="__main__")
            except SystemExit as error:
                if error.code not in (None, 0):
                    print("Tool exited: " + str(error.code), file=sys.stderr)
                    print("\\n" + marker + "error")
                else:
                    print("\\n" + marker + "ok")
            except BaseException:
                traceback.print_exc()
                print("\\n" + marker + "error")
            else:
                print("\\n" + marker + "ok")
            finally:
                os.chdir(original_cwd)
                sys.path[:] = original_path
                sys.dont_write_bytecode = original_bytecode

        _run_project_tool()
        del _run_project_tool
        ''') % (str(project), relative_script, marker)


class Output:
    """Stream normal output, retaining a private completion marker for exit status."""
    def __init__(self, marker, stdout=None, stderr=None):
        self.marker = marker
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.pending = ""
        self.status = None

    def write(self, value):
        self.pending += str(value)
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            if line.startswith(self.marker):
                self.status = line[len(self.marker):]
            else:
                self.stdout.write(line + "\n")
                self.stdout.flush()

    def error(self, value):
        self.stderr.write(str(value))
        self.stderr.flush()

    def finish(self):
        if self.pending:
            self.stdout.write(self.pending)
            self.stdout.flush()


def run_remote(relative_script):
    try:
        from Foundation import NSConnection, NSObject
    except ImportError as error:
        raise RuntimeError("This Python needs PyObjC. Install pyobjc-framework-Cocoa in a project virtual environment.") from error

    connection = NSConnection.connectionWithRegisteredName_host_(PORT, None)
    if connection is None:
        raise RuntimeError("Cannot connect to Glyphs 3. Open the app and this project's font, then try again.")
    # A dialog may remain open while the user chooses settings. Never auto-retry
    # a timeout, since the script may already be modifying the open font.
    connection.setRequestTimeout_(10)
    connection.setReplyTimeout_(86400)
    app = connection.rootProxy()
    marker = "__project_tool_" + uuid.uuid4().hex + ":"
    output = Output(marker)

    class ProjectToolOutput(NSObject):
        def setWrite_(self, value):
            output.write(value)

        def setWriteError_(self, value):
            output.error(value)

    receiver = ProjectToolOutput.alloc().init()
    app.scriptingHandler().runMacroString_stdOut_(make_payload(relative_script, marker), receiver)
    output.finish()
    if output.status is None:
        raise RuntimeError("Glyphs did not confirm completion. Check its Macro Panel before running the tool again.")
    return 0 if output.status == "ok" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("script", nargs="?", help="tool stem or tools/filename.py")
    parser.add_argument("--list", action="store_true", help="list the project's interactive Glyphs tools")
    parser.add_argument("--check", action="store_true", help="check the connection without running a tool")
    args = parser.parse_args(argv)
    scripts = available_scripts()
    if args.list or not args.script and not args.check:
        for name, (_, title) in scripts.items():
            print("%-38s %s" % (name, title))
        return 0
    if args.check and args.script:
        parser.error("--check does not take a script")
    try:
        path = select_script(args.script, scripts) if args.script else None
        relative_script = path.relative_to(PROJECT).as_posix() if path else None
        return run_remote(relative_script)
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Disconnected. A submitted tool may still be running in Glyphs; check the app before retrying.", file=sys.stderr)
        return 130
    except Exception as error:
        print("Glyphs connection failed (%s). Check the app before retrying; a submitted tool may still be running."
              % type(error).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
