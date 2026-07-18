; Inno Setup 6 script — Private AI Video Cleaner
#ifndef AppVersion
  #define AppVersion "0.7.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\PrivateAIVideoCleaner"
#endif
#ifndef OutDir
  #define OutDir "..\dist\installer"
#endif

[Setup]
AppId={{A18D7C01-PAVC-4E11-9C6D-PRIVAI VIDEO}}
AppName=Private AI Video Cleaner
AppVersion={#AppVersion}
DefaultDirName={autopf}\Private AI Video Cleaner
DefaultGroupName=Private AI Video Cleaner
OutputDir={#OutDir}
OutputBaseFilename=PrivateAIVideoCleaner-{#AppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Start-PrivateAIVideoCleaner.bat

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Private AI Video Cleaner"; Filename: "{app}\Start-PrivateAIVideoCleaner.bat"
Name: "{autodesktop}\Private AI Video Cleaner"; Filename: "{app}\Start-PrivateAIVideoCleaner.bat"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\Start-PrivateAIVideoCleaner.bat"; Description: "Launch Private AI Video Cleaner"; Flags: nowait postinstall skipifsilent
