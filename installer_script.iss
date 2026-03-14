
; Script Inno Setup pour Network Tools V3
; Ce script génère un installeur Windows (.exe) professionnel.

[Setup]
AppId={{C0A2E9F1-D6C1-4D3B-A8C5-B9F1D6C14D3B}}
AppName=Network Tools V3
AppVersion=3.0.0
DefaultDirName={autopf}\NetworkToolsV3
DefaultGroupName=Network Tools V3
OutputDir=installeur
OutputBaseFilename=NetworkToolsV3_Setup
SetupIconFile=network-analysis.ico
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copier tous les fichiers générés par PyInstaller
Source: "dist\NetworkTools\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Network Tools V3"; Filename: "{app}\NetworkToolsV3.exe"; IconFilename: "{app}\network-analysis.ico"
Name: "{autodesktop}\Network Tools V3"; Filename: "{app}\NetworkToolsV3.exe"; Tasks: desktopicon; IconFilename: "{app}\network-analysis.ico"

[Run]
Filename: "{app}\NetworkToolsV3.exe"; Description: "{cm:LaunchProgram,Network Tools V3}"; Flags: nowait postinstall skipifsilent

[Messages]
french.WelcomeLabel2=Cet assistant va vous guider dans l'installation de Network Tools V3 sur votre ordinateur.%n%nIMPORTANT : Cette application nécessite Nmap et Npcap pour le scan réseau. Si vous ne les avez pas, installez-les via https://nmap.org/download.html
