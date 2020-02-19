import os
from shutil import copyfile

import pytest

import pre_commit_cpp.clang_format_hook as clang_format_hook
from pre_commit_cpp.clang_format_hook import CMD_FAILED
from pre_commit_cpp.clang_format_hook import CMT_FAILED
from pre_commit_cpp.clang_format_hook import main
from testing.utils import get_resource_path


@pytest.mark.parametrize(
    ("args", "expected_cmd", "expected_state"),
    [
        ([], [], {}),
        (["-i"], [], {"inplace": True}),
        (["--verbose"], [], {"verbose": True}),
        (["-i", "-i"], [], {"inplace": True}),
        (
            ["-i", "--verbose", "--length=100"],
            ["--length=100"],
            {"inplace": True, "verbose": True},
        ),
        (
            ["-i", "-i", "--verbose", "--length=100"],
            ["--length=100"],
            {"inplace": True, "verbose": True},
        ),
        (["-i", "--length=100", "-i"], ["--length=100"], {"inplace": True}),
    ],
)
def test_interpret_cmd_options(args, expected_cmd, expected_state):
    cmd, state = clang_format_hook._interpret_cmd_options(args)
    assert cmd == expected_cmd
    assert state == expected_state


@pytest.mark.parametrize(
    ("args", "expected_cmd", "expected_files"),
    [
        ([], [], []),
        (["-i", "a"], ["-i"], ["a"]),
        (["-i"], ["-i"], []),
        (["a", "b"], [], ["a", "b"]),
    ],
)
def test_split_file_from_cmd(args, expected_cmd, expected_files):
    cmd, files = clang_format_hook._split_files_from_cmd(args)
    assert cmd == expected_cmd
    assert files == expected_files


@pytest.mark.parametrize(
    ("filename", "expected_retval"),
    (("test_free_style.cpp", CMT_FAILED), ("test_google_style.cpp", 0)),
)
def test_main(filename, expected_retval):
    ret = main([get_resource_path(filename)])
    assert ret == expected_retval


@pytest.mark.parametrize(
    ("filename", "expected_retval"),
    (("test_free_style.cpp", CMT_FAILED), ("test_google_style.cpp", 0)),
)
def test_main_verbose(filename, expected_retval):
    ret = main(["--verbose", get_resource_path(filename)])
    assert ret == expected_retval

    ret = main(["--verbose", "--style=google", get_resource_path(filename)])
    assert ret == expected_retval


@pytest.mark.parametrize(
    "filename, expected_retval",
    [("test_free_style.cpp", CMT_FAILED), ("test_google_style.cpp", 0)],
)
def test_main_inline(tmpdir, filename, expected_retval):
    src = get_resource_path(filename)
    # resolve the issue that multiple pytest session shares same folder
    dst = tmpdir.join("".join("%02x" % x for x in os.urandom(16)) + filename)
    copyfile(src, dst)
    retval = main(["-i", dst.strpath])

    if retval != expected_retval:
        print("may caused by sharing same path by other pytest session:", dst.strpath)

    assert retval == expected_retval


@pytest.mark.parametrize(
    "filename, expected_retval",
    [("test_free_style.cpp", CMT_FAILED), ("test_google_style.cpp", 0)],
)
def test_main_inline_verbose(tmpdir, filename, expected_retval):
    src = get_resource_path(filename)
    dst = tmpdir.join("".join("%02x" % x for x in os.urandom(16)) + filename)
    copyfile(src, dst)
    assert main(["-i", "--verbose", dst.strpath]) == expected_retval
    assert main(["-i", "--verbose", "--style=google", dst.strpath]) == 0


@pytest.mark.parametrize(
    "filename, expected_retval",
    [("test_free_style.cpp", CMD_FAILED), ("test_google_style.cpp", CMD_FAILED)],
)
def test_invalid_options(tmpdir, filename, expected_retval):
    f = tmpdir.join(filename)
    with open(get_resource_path(filename)) as origin:
        f.write(origin.read())
    assert main(["-i", "--not-an-option", f.strpath]) == expected_retval
    assert main(["--not-an-option", f.strpath]) == expected_retval


@pytest.mark.parametrize(
    "filename, expected_retval",
    [("test_free_style", CMD_FAILED), ("some/test_google_style", CMD_FAILED)],
)
def test_invalid_file(tmpdir, filename, expected_retval):
    invalid_path = os.path.join(tmpdir.strpath, filename)
    assert main(["--style=google", invalid_path]) == expected_retval
    assert main(["--verbose", invalid_path]) == expected_retval


@pytest.mark.parametrize(
    "sys_ver, operator, expected_ver, expected_retval",
    (
        ("9.0.0", ">=", "8.0.0", 0),
        ("9.0.0", ">", "8.0.0", 0),
        ("9.0.0", "=", "9.0.0", 0),
        ("9.0.0", "=", "8.2", CMD_FAILED),
        ("9.0.0", "<", "8.2.0", CMD_FAILED),
        ("9.0.0", "<=", "8.2.0", CMD_FAILED),
    ),
)
def test_version_comparison(sys_ver, operator, expected_ver, expected_retval):
    assert (
        clang_format_hook._assert_version(sys_ver, operator + expected_ver)
        == expected_retval
    )


@pytest.mark.parametrize(
    "filename, expected_retval",
    [("test_google_style.cpp", 0), ("test_free_style.cpp", CMT_FAILED)],
)
def test_version_operator_valid(tmpdir, filename, expected_retval):
    fpath = get_resource_path(filename)
    assert main(["--version>=0.0.0", fpath]) == expected_retval
    assert main(["--version>0.0.0", fpath]) == expected_retval


@pytest.mark.parametrize(
    "filename, expected_retval",
    [("test_google_style.cpp", CMD_FAILED), ("test_free_style.cpp", CMD_FAILED)],
)
def test_version_operator_invalid(tmpdir, filename, expected_retval):
    fpath = get_resource_path(filename)
    assert main(["--version<=0.0.0", fpath]) == expected_retval
    assert main(["--version=0.0.0", fpath]) == expected_retval
    assert main(["--version<0.0.0", fpath]) == expected_retval
