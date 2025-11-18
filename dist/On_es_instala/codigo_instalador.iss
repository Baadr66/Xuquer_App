[Setup]
AppName=Badr_Prova
AppVersion=1.0
DefaultDirName={pf}\Badr_Prova           ; Instala en C:\Program Files\Badr_Prova
OutputDir="C:\Xuquer\Badr_Prova\Xuquer-main\Xuquer-main\dist\On_es_instala"
OutputBaseFilename=Instalador_Badr_Prova
Compression=lzma
SolidCompression=yes

[Files]
Source: "C:\Xuquer\Badr_Prova\Xuquer-main\Xuquer-main\dist\app_main.exe"; DestDir: "{app}"

[Icons]
Name: "{commondesktop}\Badr_Prova"; Filename: "{app}\app_main.exe"

