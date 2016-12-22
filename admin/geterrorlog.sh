#!/bin/bash

if [ "$1" != "" ]
then
    ERROR=$(egrep 'WARNING|ERROR' "$1" |sort -rnk1,2 | head -10)
    if [ -z "$ERROR" ]
    then
        echo -e "$1:\nHooray, No error."
    else
        echo -e "$1:\n$ERROR"
    fi
else
    echo "Missing log file !"
fi
