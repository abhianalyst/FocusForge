#define MyAppName "FocusForge"
#define MyAppVersion "0.1.0"
#define MyAppExeName "FocusForge.exe"
[Setup]
AppId={{A94D14C7-2B10-4F68-934E-A2A8C0D10E61}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\FocusForge
DefaultGroupName=FocusForge
OutputDir=release
OutputBaseFilename=FocusForge_Setup
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
[Files]
Source: "dist\FocusForge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
[Icons]
Name: "{autoprograms}\FocusForge"; Filename: "{app}\FocusForge.exe"
Name: "{autodesktop}\FocusForge"; Filename: "{app}\FocusForge.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\FocusForge.exe"; Description: "Launch FocusForge"; Flags: postinstall nowait skipifsilent
