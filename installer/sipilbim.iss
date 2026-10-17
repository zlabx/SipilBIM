; Inno Setup script for SipilBIM.
;
; Builds a professional Windows installer: multilingual wizard, GPL license page,
; shortcuts, "Add or Remove Programs" entry and a clean uninstaller.
;
; Local build (needs Inno Setup 6+):
;     iscc /DMyAppVersion=0.2.0 installer\sipilbim.iss
;
; CI build: see .github/workflows/build-windows.yml
;
; The AppId is a FIXED GUID — never change it between versions, or Windows
; treats every release as a different app and upgrades stop being clean.

#define MyAppName "SipilBIM"
#define MyAppPublisher "SipilStock"
#define MyAppURL "https://sipilstock.com/sipilbim/"
#define MyAppExeName "sipilbim.exe"

; MyAppVersion is injected from the build command with /DMyAppVersion=X.Y.Z
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

[Setup]
; FIXED AppId GUID — generated once for SipilBIM. Changing it breaks upgrades.
AppId={{F3B9C9D7-A5EC-50CB-98F9-911195213717}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/zlabx/SipilBIM/issues
AppUpdatesURL=https://github.com/zlabx/SipilBIM/releases
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Modelador 3D libre para ingenieria y arquitectura
VersionInfoProductName={#MyAppName}

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Free software: the "license" page shows the GPL-3.0 text.
LicenseFile=..\LICENSE

OutputDir=..\dist
OutputBaseFilename=sipilbim-setup-v{#MyAppVersion}

WizardStyle=modern
; (Saved as UTF-8 WITH a BOM: that is how Inno Setup knows the texts
; below are UTF-8 — without it «Associações» would come out garbled.)
; The wizard speaks the language of Windows (English, Spanish, Brazilian
; Portuguese or Polish) and asks only when none of them matches (issue #135).
ShowLanguageDialog=auto
DisableProgramGroupPage=yes
; We register file-type icons/associations — tells Explorer to refresh them.
ChangesAssociations=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\resources\icons\sipilbim.ico

[Languages]
; English first: it is the fallback when Windows speaks something else.
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[CustomMessages]
english.SkpDefault=Open .skp files with SipilBIM (double-click)
english.FileAssociations=File associations:
english.IgzDocument=SipilBIM document
english.DaeModel=COLLADA model (SipilBIM)
english.SkpModel=SKP model (SipilBIM)
spanish.SkpDefault=Abrir archivos .skp con SipilBIM (doble clic)
spanish.FileAssociations=Asociaciones de archivos:
spanish.IgzDocument=Documento de SipilBIM
spanish.DaeModel=Modelo COLLADA (SipilBIM)
spanish.SkpModel=Modelo SKP (SipilBIM)
brazilianportuguese.SkpDefault=Abrir arquivos .skp com o SipilBIM (clique duplo)
brazilianportuguese.FileAssociations=Associações de arquivos:
brazilianportuguese.IgzDocument=Documento do SipilBIM
brazilianportuguese.DaeModel=Modelo COLLADA (SipilBIM)
brazilianportuguese.SkpModel=Modelo SKP (SipilBIM)
polish.SkpDefault=Otwieraj pliki .skp w SipilBIM (dwukrotne kliknięcie)
polish.FileAssociations=Skojarzenia plików:
polish.IgzDocument=Dokument SipilBIM
polish.DaeModel=Model COLLADA (SipilBIM)
polish.SkpModel=Model SKP (SipilBIM)

[Tasks]
Name: "skpdefault"; Description: "{cm:SkpDefault}"; \
    GroupDescription: "{cm:FileAssociations}"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The whole PyInstaller one-dir bundle.
Source: "..\dist\sipilbim\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
; Branded document icons, copied to the {app} root so [Registry] DefaultIcon
; entries can reference them with a stable path.
Source: "..\resources\icons\mimetypes\sipilbim-igz.ico"; DestDir: "{app}"; \
    Flags: ignoreversion
Source: "..\resources\icons\mimetypes\sipilbim-dae.ico"; DestDir: "{app}"; \
    Flags: ignoreversion
Source: "..\resources\icons\mimetypes\sipilbim-skp.ico"; DestDir: "{app}"; \
    Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Registry]
; ── Hybrid laptops (Intel + NVIDIA/AMD): run on the discrete GPU ─────────────
; This is the value Settings ▸ System ▸ Display ▸ Graphics writes when the user
; picks "High performance" for a program; without it Windows starts SipilBIM
; on the integrated chip and the viewport crawls. Only written when the user
; has not chosen anything yet (the app repeats the check at start-up).
Root: HKCU; Subkey: "Software\Microsoft\DirectX\UserGpuPreferences"; \
    ValueType: string; ValueName: "{app}\{#MyAppExeName}"; \
    ValueData: "GpuPreference=2;"; Flags: createvalueifdoesntexist uninsdeletevalue

; ── .igz — SipilBIM's own format: full association + branded document icon ──
; Double-click opens the document in SipilBIM and Explorer shows the .igz icon.
Root: HKA; Subkey: "Software\Classes\.igz"; ValueType: string; \
    ValueData: "SipilBIM.Document"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\SipilBIM.Document"; ValueType: string; \
    ValueData: "{cm:IgzDocument}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SipilBIM.Document\DefaultIcon"; \
    ValueType: string; ValueData: "{app}\sipilbim-igz.ico,0"
Root: HKA; Subkey: "Software\Classes\SipilBIM.Document\shell\open\command"; \
    ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

; ── .dae / .skp — standard interchange formats: "Open with" only ────────────
; We DO NOT take over the default program or the file icon (Windows ties the
; shown icon to the default handler, and stealing .dae/.skp from the
; programs the user already has would surprise them). Instead we register a ProgId and add it to
; each extension's OpenWithProgids list, so SipilBIM appears in the right-click
; "Open with" menu. The ProgId carries the branded icon, which only takes visual
; effect if the user later chooses SipilBIM as the default for these files.
Root: HKA; Subkey: "Software\Classes\SipilBIM.dae"; ValueType: string; \
    ValueData: "{cm:DaeModel}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SipilBIM.dae\DefaultIcon"; \
    ValueType: string; ValueData: "{app}\sipilbim-dae.ico,0"
Root: HKA; Subkey: "Software\Classes\SipilBIM.dae\shell\open\command"; \
    ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.dae\OpenWithProgids"; \
    ValueType: string; ValueName: "SipilBIM.dae"; ValueData: ""; \
    Flags: uninsdeletevalue

Root: HKA; Subkey: "Software\Classes\SipilBIM.skp"; ValueType: string; \
    ValueData: "{cm:SkpModel}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SipilBIM.skp\DefaultIcon"; \
    ValueType: string; ValueData: "{app}\sipilbim-skp.ico,0"
Root: HKA; Subkey: "Software\Classes\SipilBIM.skp\shell\open\command"; \
    ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.skp\OpenWithProgids"; \
    ValueType: string; ValueName: "SipilBIM.skp"; ValueData: ""; \
    Flags: uninsdeletevalue
; Optional task: make SipilBIM the DEFAULT opener for .skp (double-click).
; Checked by default — .skp now opens natively (openskp backend). Users who
; prefer another program for .skp can untick it; uninstall removes the value
; and Windows falls back to the previous handler.
Root: HKA; Subkey: "Software\Classes\.skp"; ValueType: string; \
    ValueData: "SipilBIM.skp"; Tasks: skpdefault; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#MyAppName}}"; \
    Flags: nowait postinstall skipifsilent
