; AutoParts CRM — Inno Setup installer script
; Requires Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
; Build with:  ISCC installer.iss
; Or open in Inno Setup IDE and press F9

#define AppName      "AutoParts CRM"
#define AppVersion   "1.0"
#define AppPublisher "AutoParts"
#define AppExeName   "AutoPartsCRM.exe"
#define AppDataName  "AutoPartsCRM"
; Path to the PyInstaller output folder (run build.bat first)
#define BuildDir     "dist\AutoPartsCRM"

[Setup]
AppId={{F3A2B1C4-9D5E-4F7A-8B3C-1E2D6F0A4C8B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://1.erp.tw1.su
DefaultDirName={autopf}\{#AppDataName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
; Output
OutputDir=dist
OutputBaseFilename=AutoPartsCRM_Setup_v{#AppVersion}
; Privileges — install per-machine (requires UAC elevation)
PrivilegesRequired=admin
; Windows version requirement (Windows 10+)
MinVersion=10.0
; Uninstaller
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
; Show "Open AutoParts CRM" checkbox after install
InfoAfterFile=
; Wizard style
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Ярлык в панели быстрого запуска"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Copy entire PyInstaller output folder
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Launch app after install (optional, can uncheck)
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Nothing extra needed — user data lives in %LOCALAPPDATA%\AutoPartsCRM (preserved)

[Code]
// Show a note that user data is preserved on uninstall
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataPath := ExpandConstant('{localappdata}\AutoPartsCRM');
    if DirExists(DataPath) then
      MsgBox('База данных и настройки сохранены в:' + #13#10 + DataPath + #13#10#13#10 +
             'Удалите эту папку вручную, если хотите полностью очистить данные.',
             mbInformation, MB_OK);
  end;
end;
