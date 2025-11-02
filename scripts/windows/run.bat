@echo off

:: Set default host and port
set HOST=127.0.0.1
set PORT=8000

:: Override with environment variables if set
if not "%KUBEBUDDY_HOST%"=="" set HOST=%KUBEBUDDY_HOST%
if not "%KUBEBUDDY_PORT%"=="" set PORT=%KUBEBUDDY_PORT%

:: Override with argument if provided (PORT only for simplicity)
if not "%1"=="" set PORT=%1

:: Activate virtual environment
call buddyenv\Scripts\activate.bat

:: Run Django server
python manage.py runserver %HOST%:%PORT%
