#!/usr/bin/env bash

# Source the common helpers script.
source scripts/common.bash

# add -s for verbose output

print_banner "Python 3"

find . -name "__pycache__" -exec rm -rf {} \; >& /dev/null
find . -name "*.py?" -exec rm {} \;           >& /dev/null

python3 -m pytest --cov-report term-missing --cov-report html --cov=configparserenhanced
err=$?
if [ $err != 0 ]; then
    echo -e "<<< TESTING FAILED >>>"
fi

# Clean up generated bytecode
find . -name "__pycache__" -exec rm -rf {} \; >& /dev/null
find . -name "*.py?" -exec rm {} \;           >& /dev/null

exit $err
