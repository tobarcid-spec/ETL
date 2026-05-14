@echo off
cd /d "c:\procesos\ETL"
set PYTHON="C:\Users\Isabel Tobar\AppData\Local\Programs\Python\Python313\python.exe"
set SHEET_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vTfvZQvzeO8vZD3VyQLOexWjN_UwXdG8csF7_sOzIiZoHSIpkyNKwSg05Ea42p6jVdRXlxAkaxnbnRv/pub?gid=0&single=true&output=csv"

echo [%date% %time%] Iniciando proceso diario...

echo [%date% %time%] Paso 1: Actualizando cancelados desde Google Sheets...
%PYTHON% flow/flow_cancelados_mysql.py --sheet-url %SHEET_URL%

echo [%date% %time%] Paso 2: Enviando correos a 3 dias...
%PYTHON% flow/flow_email_avisos.py --dias 3

echo [%date% %time%] Paso 3: Enviando correos a 14 dias...
%PYTHON% flow/flow_email_avisos.py --dias 14

echo [%date% %time%] Paso 4: Enviando correos anuales (30 dias)...
%PYTHON% flow/flow_email_avisos.py --dias 30

echo [%date% %time%] Proceso diario completado.
