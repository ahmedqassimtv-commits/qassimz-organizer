; QASSIMZ Organizer — Inno Setup script
#define AppName "QASSIMZ Organizer"
#ifndef AppVer
  #define AppVer "1.1.0"
#endif
#define AppExe "QASSIMZ Organizer.exe"

[Setup]
AppId=QASSIMZ.Organizer
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Ahmed Qassim — QASSIMZ
AppPublisherURL=https://github.com/ahmedqassimtv-commits/qassimz-organizer
AppSupportURL=https://github.com/ahmedqassimtv-commits/qassimz-organizer/issues
AppUpdatesURL=https://github.com/ahmedqassimtv-commits/qassimz-organizer/releases
DefaultDirName={localappdata}\Programs\QASSIMZ Organizer
DefaultGroupName=QASSIMZ
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
CloseApplications=force
RestartApplications=no
OutputDir=..\dist
OutputBaseFilename=QASSIMZ-Organizer-Setup-{#AppVer}
SetupIconFile=..\assets\logo.ico
UninstallDisplayIcon={app}\{#AppExe}
WizardStyle=modern
WizardImageFile=wizard.bmp
WizardSmallImageFile=wizard-small.bmp
InfoBeforeFile=..\docs\INSTRUCTIONS-AR.txt
LicenseFile=..\LICENSE
Compression=lzma2/ultra
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
#if FileExists(AddBackslash(SourcePath) + "Arabic.isl")
Name: "arabic"; MessagesFile: "Arabic.isl"
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\QASSIMZ Organizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\docs\INSTRUCTIONS-AR.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\تعليمات الاستخدام"; Filename: "{app}\INSTRUCTIONS-AR.txt"
Name: "{group}\GitHub — QASSIMZ Organizer"; Filename: "https://github.com/ahmedqassimtv-commits/qassimz-organizer"
Name: "{group}\الدعم والإبلاغ عن مشكلة"; Filename: "https://github.com/ahmedqassimtv-commits/qassimz-organizer/issues"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM ""{#AppExe}"""; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\QASSIMZ Organizer"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "QASSIMZ Organizer"; Flags: uninsdeletevalue dontcreatekey

; right-click any folder → "رتّب بـ QASSIMZ"
Root: HKCU; Subkey: "Software\Classes\Directory\shell\QassimzOrganizer"; ValueType: string; ValueName: ""; ValueData: "رتّب بـ QASSIMZ Organizer"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\QassimzOrganizer"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#AppExe}"
Root: HKCU; Subkey: "Software\Classes\Directory\shell\QassimzOrganizer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
; after a silent self-update, start the app again in the background
Filename: "{app}\{#AppExe}"; Parameters: "--background"; Flags: nowait; Check: ShouldSilentRun
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
Filename: "https://github.com/ahmedqassimtv-commits/qassimz-organizer"; Description: "افتح صفحة البرنامج على GitHub"; Flags: postinstall shellexec skipifsilent unchecked

[Code]
function ShouldSilentRun: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:AUTORUN|1}') = '1');
end;
