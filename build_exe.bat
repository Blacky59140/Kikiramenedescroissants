@echo off
REM ============================================================
REM Compilation de "Kikiramenedescroissants ?" en .exe autonome
REM avec PyInstaller.
REM A executer directement sur Windows, depuis le dossier du
REM projet (celui qui contient main.py).
REM ============================================================

echo Installation des dependances aux versions figees (requirements-build.txt)...
pip install -r requirements-build.txt

echo.
echo Compilation en cours (cela peut prendre 1 a 2 minutes)...
echo.

pyinstaller --noconfirm --onefile --windowed ^
    --name "Kikiramenedescroissants" ^
    --hidden-import babel.numbers ^
    main.py

echo.
echo ============================================================
echo Termine !
echo L'executable se trouve dans : dist\Kikiramenedescroissants.exe
echo.
echo IMPORTANT :
echo  - Copie le dossier "Images" (s'il existe deja) a cote de
echo    Kikiramenedescroissants.exe dans le dossier dist\.
echo  - evenements.json et parametres_fenetres.json seront crees
echo    automatiquement au premier lancement, au meme endroit que
echo    l'exe (aucune action de ta part necessaire pour ces fichiers).
echo ============================================================
pause
