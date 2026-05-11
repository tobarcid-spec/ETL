@echo off
cd /d "c:\procesos\ETL"
set PYTHON="C:\Users\Isabel Tobar\AppData\Local\Programs\Python\Python313\python.exe"

echo [%date% %time%] Iniciando actualizacion de playlists...

echo [%date% %time%] TikTok playlists...
%PYTHON% tiktok/tiktok_info_playslist.py

echo [%date% %time%] YouTube playlists...
%PYTHON% youtube/youtube_playslist_auto.py

echo [%date% %time%] Playlists completado.
