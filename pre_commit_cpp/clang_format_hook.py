import difflib
import os
import subprocess as sp
import sys

# import typing

CMT_FAILED = 1  # commit doesn't comply with clang-format, should not pass
CMD_FAILED = 2  # error eval clang-format


def _run_command_and_capture(cmd, file_names, retcode=None):
    """
    clang-format --verbose will output to stdout and stderr
    """
    proc = sp.Popen(
        cmd + file_names, stdout=sp.PIPE, stderr=sp.STDOUT, encoding="utf-8"
    )
    stdout, _ = proc.communicate()
    if retcode is not None and proc.returncode != retcode:
        raise sp.CalledProcessError(proc.returncode, cmd, output=stdout)
    return stdout


def _report_error_stderr(e):
    # noqa
    print("cmd output:\n", e.output, "\nreturn code:\n", e.returncode, file=sys.stderr)


def _split_files_from_cmd(cmd):
    file_names = list()
    for (ii, item) in enumerate(reversed(cmd)):
        if item.startswith("-"):
            # modify cmd inplace
            return cmd[: len(cmd) - ii], file_names
        else:
            file_names.insert(0, item)

    return list(), file_names


def _interpret_cmd_options(argv):
    state = dict()
    idx_to_del = set()

    for (ii, item) in enumerate(argv):
        if item == "-i":
            idx_to_del.add(ii)
            state["inplace"] = True
        elif item == "--verbose":
            idx_to_del.add(ii)
            state["verbose"] = True
        elif item.startswith("--version"):
            if item == "--version":
                print("--version needs operator and version number", file=sys.stderr)
                return CMD_FAILED
            state["version"] = item[9:]
            idx_to_del.add(ii)

    new_argv = [item for (ii, item) in enumerate(argv) if ii not in idx_to_del]
    return new_argv, state


def _run_files_in_batches(batch_size, cmd, file_names, retcode, inplace=False):
    """ `-i` doesn't work well with a large set of files in clang-format
    """
    ii = 0
    while ii < len(file_names):
        batch_names = file_names[ii : ii + batch_size]
        try:
            stdout = _run_command_and_capture(cmd, batch_names, retcode)
        except sp.CalledProcessError as e:
            _report_error_stderr(e)
            yield CMD_FAILED, e.output
        else:
            yield retcode, stdout

        ii += batch_size

    # deprecated
    # raise StopIteration()
    return


def _show_diff_result(cmd, file_names, verbose):
    """ run diff file by file
    """
    retval = 0
    for item in file_names:
        try:
            stdout = _run_command_and_capture(cmd, [item], 0)
        except sp.CalledProcessError as e:
            _report_error_stderr(e)
            retval = CMD_FAILED
        else:
            if stdout:
                with open(item) as origin:
                    lines = origin.read().splitlines(1)
                    for line in difflib.unified_diff(
                        lines,
                        stdout.splitlines(1),
                        fromfile=item,
                        tofile=item + " (modified by clang-format)",
                    ):
                        if verbose:
                            sys.stderr.write(line)
                        retval = CMT_FAILED
    return retval


def _parse_version_operator_and_operand(op_and_ver):
    """ supports >, >=, =, <, <=
    """
    missing_err = ValueError("--version{} is invalid".format(op_and_ver))

    if len(op_and_ver) == 1:
        raise missing_err

    if op_and_ver[0] == "=":
        return "=", op_and_ver[1:].strip()
    elif op_and_ver[0] == ">":
        if op_and_ver[1] == "=":
            if len(op_and_ver) < 3:
                raise missing_err
            return ">=", op_and_ver[2:].strip()
        else:
            return ">", op_and_ver[1:].strip()
    elif op_and_ver[0] == "<":
        if op_and_ver[1] == "=":
            if len(op_and_ver) < 3:
                raise missing_err
            return "<=", op_and_ver[2:].strip()
        else:
            return "<", op_and_ver[1:].strip()


def _get_system_version():
    _version = sp.check_output(["clang-format", "--version"], encoding="utf-8")
    return _version.split()[2]


def _assert_version(system_version, op_and_ver):
    retval = 0
    op, expected_version = _parse_version_operator_and_operand(op_and_ver)

    import pkg_resources

    system_version = pkg_resources.parse_version(system_version)
    expected_version = pkg_resources.parse_version(expected_version)

    if op == "=":
        if system_version != expected_version:
            retval = CMD_FAILED
    elif op == ">":
        if not (system_version > expected_version):
            retval = CMD_FAILED
    elif op == ">=":
        if not (system_version >= expected_version):
            retval = CMD_FAILED
    elif op == "<":
        if not (system_version < expected_version):
            retval = CMD_FAILED
    elif op == "<=":
        if not (system_version <= expected_version):
            retval = CMD_FAILED

    if retval == CMD_FAILED:
        print(
            "ERR: --version{}. Expected version {}, but "
            "system version is {}".format(op_and_ver, expected_version, system_version),
            file=sys.stderr,
        )
        print(
            "Edit your pre-commit config or " "use a different version of clang-format",
            file=sys.stderr,
        )
    return retval


def _prompt_before_return(retval, cmd, file_names):
    if retval == CMD_FAILED:
        sys.stdout.write("Error with command: %s" % " ".join(cmd + file_names))


def main(argv=None):
    """same with argparse behavior.

    If argv is None, use sys.argv, otherwise use argv. That says argv and
    sys.argv are exclusive.

    The way how sys.argv is handled is based on the assumption this `main`
    is invoked difrectly as console command.
    """
    cmd = list()
    if argv:
        cmd.extend(argv)
    elif len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    cmd, file_names = _split_files_from_cmd(cmd)

    if not file_names:
        raise ValueError("no files are provided for the command")

    cmd, state = _interpret_cmd_options(cmd)
    cmd.insert(0, "clang-format")

    if "version" in state:
        retval = _assert_version(_get_system_version(), state["version"])
        if retval != 0:
            return retval

    retval = 0
    # if -i is provided, we need check whether file is modified
    # or not.  If modified, it means the format of the source file
    # is not clang-format and user need to add the modified files
    # to staging area again.
    if state.get("inplace", False):
        # if -i chained with --verbose
        if state.get("verbose", False):
            retval = _show_diff_result(cmd, file_names, True)

        cmd.insert(1, "-i")
        file_times = [os.path.getmtime(f) for f in file_names]

        for (retval, stdout) in _run_files_in_batches(20, cmd, file_names, 0):
            if retval == CMD_FAILED:
                return retval

        for (item, item_last_modified) in zip(file_names, file_times):
            if os.path.getmtime(item) != item_last_modified:
                retval = CMT_FAILED
                break

    else:
        retval = _show_diff_result(cmd, file_names, state.get("verbose", False))

    _prompt_before_return(retval, cmd, file_names)

    return retval


if __name__ == "__main__":
    exit(main())
