#!/bin/bash
cd "$( cd "$( dirname "$0" )" && pwd )"
coffee -o ../js/ -cw .
