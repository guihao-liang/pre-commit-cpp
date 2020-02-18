#!/bin/bash

set -e

echo "test check-clang-format"

pre-commit run -c testing/.pre-commit-config-test.yaml \
  --files testing/resources/test_google_style.cpp

pre-commit run -c testing/.pre-commit-config-test.yaml \
  --files testing/resources/test_free_style.cpp || test $? = 1
