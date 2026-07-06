@echo off
:: Set the directory you want to list, or leave empty for current folder
set "TARGET_DIR=%~1"

if "%TARGET_DIR%"=="" set "TARGET_DIR=%cd%"

:: Set the output file
set "OUTPUT_FILE=list.txt"

:: Clear previous output
if exist "%OUTPUT_FILE%" del "%OUTPUT_FILE%"

:: Write the tree structure into the file
tree "%TARGET_DIR%" /F /A > "%OUTPUT_FILE%"

echo File listing saved to %OUTPUT_FILE%
pause