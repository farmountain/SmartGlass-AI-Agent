@ECHO OFF
SETLOCAL
IF NOT ""=="%GRADLE_HOME%" IF EXIST "%GRADLE_HOME%\bin\gradle.bat" (
  CALL "%GRADLE_HOME%\bin\gradle.bat" %*
  EXIT /B %ERRORLEVEL%
)
WHERE gradle >NUL 2>&1
IF %ERRORLEVEL% EQU 0 (
  gradle %*
  EXIT /B %ERRORLEVEL%
)
ECHO Gradle is required to run this project. Please install Gradle or set GRADLE_HOME.
EXIT /B 1
ENDLOCAL
