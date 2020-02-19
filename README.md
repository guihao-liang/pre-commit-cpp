# pre-commit-cpp

git pre-commit hooks for C/C++

[![Build Status](https://travis-ci.com/guihao-liang/pre-commit-cpp.svg?branch=master)](https://travis-ci.com/guihao-liang/pre-commit-cpp)
[![codecov](https://codecov.io/gh/guihao-liang/pre-commit-cpp/branch/master/graph/badge.svg)](https://codecov.io/gh/guihao-liang/pre-commit-cpp)

## Hooks available

### `check-clang-format`

```yaml
repos:
  - repo: https://github.com/guihao-liang/pre-commit-cpp
    rev: master # still WIP, so use the most recent commit
    hooks:
      - id: check-clang-format
        args: ["-i", "--style=google"]
```

This hook is a thin wrapper that just redirects most options into `clang-format`, except for `--verbose`, which the hook provides extra feature enhancement with `diff`,

* `--verbose` will output `diff` between orignal file and clang-formatted output. No diff, no ouput.

```diff
--- testing/resources/test_free_style.cpp
+++ testing/resources/test_free_style.cpp (modified by clang-format)
@@ -1 +1,4 @@
-int main() { int i = 0; return i; }
+int main() {
+  int i = 0;
+  return i;
+}
```

`-i` can be chained with `--verbose`.

* `--version` can operate with `(<|<=|=|>|>=)` to restrict the clang-format version. For example, `--version>9.0.0` will fail if clang-format version is not greater than `9.0.0`.
