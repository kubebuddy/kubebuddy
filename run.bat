@echo off

:: Set default host and port
set HOST=127.0.0.1
set PORT=8000

:: Override with environment variables if set
if not "%KUBEBUDDY_HOST%"=="" set HOST=%KUBEBUDDY_HOST%
if not "%KUBEBUDDY_PORT%"=="" set PORT=%KUBEBUDDY_PORT%

:: Parse command-line arguments
:parse_args
if "%1"=="" goto after_args
if "%1"=="--host" (
    set HOST=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--port" (
    set PORT=%2
    shift
    shift
    goto parse_args
)
shift
goto parse_args

:after_args

:: Activate virtual environment
call buddyenv\Scripts\activate.bat

:: Run Django server
python manage.py runserver %HOST%:%PORT%
