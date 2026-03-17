; StockVision Bridge — Inno Setup 스크립트
; 빌드: iscc local_server/installer.iss
; 사전 조건: PyInstaller onedir 빌드 완료 (dist/stockvision-local/)

#define MyAppName "StockVision Bridge"
#define MyAppVersion "0.1.3"
#define MyAppPublisher "StockVision"
#define MyAppExeName "stockvision-local.exe"
#define MyAppURL "https://github.com/wansu-ha/StockVision"

[Setup]
AppId={{B8F3A2D1-5E7C-4A9B-8D6F-1C3E5A7B9D2F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\StockVision
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=StockVision-Bridge-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}
WizardStyle=modern

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 생성"; GroupDescription: "추가 옵션:"; Flags: unchecked

[Files]
Source: "..\dist\stockvision-local\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; stockvision:// 딥링크 프로토콜 등록
Root: HKCU; Subkey: "Software\Classes\stockvision"; ValueType: string; ValueName: ""; ValueData: "URL:stockvision Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\stockvision"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\stockvision\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "StockVision Bridge 실행"; Flags: nowait postinstall skipifsilent
