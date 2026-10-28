; A per-user offline candidate. All dependencies are already inside PAYLOAD.
Unicode true
RequestExecutionLevel user
ManifestDPIAware true
SetCompressor zlib
SetDatablockOptimize on
Name "OpenT1D (${BUILD_ID})"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\OpenT1D"
InstallDirRegKey HKCU "Software\OpenT1D" "InstallDir"
BrandingText "OpenT1D research software — installation candidate"
VIProductVersion "0.0.0.0"
VIAddVersionKey "ProductName" "OpenT1D"
VIAddVersionKey "FileDescription" "OpenT1D offline Windows installation candidate"
VIAddVersionKey "FileVersion" "${BUILD_ID}"
VIAddVersionKey "LegalCopyright" "OpenT1D contributors"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"
!define APP_KEY "Software\OpenT1D"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenT1D"

Var CurrentVersionDir
Var VersionDir
Var StopResult
Var MutexHandle
Var IncomingVersionDir
Var RetainedVersionDir
Var PathProbe
Var PathParent
Var Sequence

!define MUI_WELCOMEPAGE_TITLE "Install OpenT1D"
!define MUI_WELCOMEPAGE_TEXT "Install OpenT1D for this Windows account.$\r$\n$\r$\nThis test version includes the current graphical workflows and their locked Python environments. GitHub, Git, Python, WSL, administrator rights and installation-time internet access are not required.$\r$\n$\r$\nIt runs locally and opens in your browser. It is research software, not a clinical tool.$\r$\n$\r$\nSupported target: Windows 11 on an Intel/AMD 64-bit computer."
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Open OpenT1D"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApplication
!define MUI_FINISHPAGE_TITLE "OpenT1D is installed"
!define MUI_FINISHPAGE_TEXT "OpenT1D is installed for this account. Start it from the OpenT1D shortcut.$\r$\n$\r$\nExperiments are stored separately in:$\r$\n$LOCALAPPDATA\OpenT1D\workspace$\r$\n$\r$\nUpdates retain previous program versions for reconstruction. Repair retains the previous copy in a retained-repair folder. Uninstall removes shortcuts and registration, while retaining experiments and these readers."
!define MUI_UNCONFIRMPAGE_TEXT_TOP "Remove OpenT1D shortcuts and Windows app registration? OpenT1D will first close its local server.$\r$\n$\r$\nYour experiments remain in $LOCALAPPDATA\OpenT1D. Program versions are retained in $INSTDIR\versions so their exact readers remain available for reconstruction."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${PAYLOAD}\THIRD-PARTY-NOTICES.txt"
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

!macro AcquireInstallerMutex
  System::Call 'kernel32::CreateMutexW(p 0, i 0, w "Local\OpenT1D-Installation") p .r0'
  StrCpy $MutexHandle $0
  ${If} $MutexHandle == 0
    MessageBox MB_ICONSTOP "OpenT1D could not reserve the installer. Please try again."
    Abort
  ${EndIf}
  System::Call 'kernel32::WaitForSingleObject(p $MutexHandle, i 30000) i .r1'
  ${If} $1 != 0
  ${AndIf} $1 != 128
    System::Call 'kernel32::CloseHandle(p $MutexHandle)'
    StrCpy $MutexHandle 0
    MessageBox MB_ICONSTOP "OpenT1D is starting or another installer is running. Wait for it to finish and try again."
    Abort
  ${EndIf}
!macroend

!macro ReleaseInstallerMutex
  ${If} $MutexHandle != 0
    System::Call 'kernel32::ReleaseMutex(p $MutexHandle)'
    System::Call 'kernel32::CloseHandle(p $MutexHandle)'
    StrCpy $MutexHandle 0
  ${EndIf}
!macroend

Function .onGUIEnd
  !insertmacro ReleaseInstallerMutex
FunctionEnd

Function un.onGUIEnd
  !insertmacro ReleaseInstallerMutex
FunctionEnd

Function .onInit
  !insertmacro AcquireInstallerMutex
  ${IfNot} ${IsNativeAMD64}
    MessageBox MB_ICONSTOP "This candidate requires an Intel/AMD 64-bit Windows computer. ARM64 and 32-bit Windows are not supported."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin11}
    MessageBox MB_ICONSTOP "This OpenT1D candidate requires Windows 11."
    Abort
  ${EndIf}
  ${If} ${IsServerOS}
    MessageBox MB_ICONSTOP "This installer targets Windows 11 desktop computers. Windows Server is outside this candidate's installation scope."
    Abort
  ${EndIf}
  SetShellVarContext current
  SetRegView 64
FunctionEnd

Function un.onInit
  !insertmacro AcquireInstallerMutex
  SetShellVarContext current
  SetRegView 64
FunctionEnd

!macro StopCurrentApplication
  ${If} $CurrentVersionDir != ""
    IfFileExists "$CurrentVersionDir\runtime\pythonw.exe" 0 missing_runtime
    ClearErrors
    SetOutPath "$CurrentVersionDir\app"
    ExecWait '"$CurrentVersionDir\runtime\pythonw.exe" -B -E -s -m experiments.desktop --stop' $StopResult
    ${If} ${Errors}
      Goto stop_failed
    ${EndIf}
    ${If} $StopResult != 0
      Goto stop_failed
    ${EndIf}
  ${EndIf}
  Goto stopped
missing_runtime:
  MessageBox MB_ICONSTOP "The installed runtime is missing. Use Exit OpenT1D in the application, then reinstall this same installer to repair its files before removing or updating it. No experiments have been deleted."
  Abort
stop_failed:
  MessageBox MB_ICONSTOP "OpenT1D could not close safely. Use Exit OpenT1D in the application and try again. Installation has stopped; your experiments are unchanged."
  Abort
stopped:
!macroend

Function VerifyInstallationPath
  ; Inspect every existing ancestor without following a reparse directory.
  Exch $PathProbe
verify_ancestor:
  ; Capture LastError inside this call: another plug-in invocation can overwrite it.
  System::Call 'kernel32::GetFileAttributesW(w "$PathProbe") i .r0 ?e'
  Pop $3
  ${If} $0 != -1
    IntOp $1 $0 & 0x400
    IntOp $2 $0 & 0x10
    ${If} $1 != 0
    ${OrIf} $2 == 0
      MessageBox MB_ICONSTOP "OpenT1D cannot install through a linked directory or a file. The existing installation and experiments have not been changed."
      Abort
    ${EndIf}
  ${Else}
    ${If} $3 != 2
    ${AndIf} $3 != 3
      MessageBox MB_ICONSTOP "OpenT1D cannot inspect its installation folder. Check access to your local application-data folder and retry."
      Abort
    ${EndIf}
  ${EndIf}
  ${GetParent} "$PathProbe" $PathParent
  ${If} $PathParent == ""
  ${OrIf} $PathParent == $PathProbe
    Pop $PathProbe
    Return
  ${EndIf}
  StrCpy $PathProbe $PathParent
  Goto verify_ancestor
FunctionEnd

Function SelectFreshVersionPaths
  StrCpy $Sequence 0
find_free_paths:
  StrCpy $IncomingVersionDir "$VersionDir.incoming-$Sequence"
  StrCpy $RetainedVersionDir "$VersionDir.retained-repair-$Sequence"
  System::Call 'kernel32::GetFileAttributesW(w "$IncomingVersionDir") i .r0'
  ${If} $0 != -1
    Goto next_paths
  ${EndIf}
  System::Call 'kernel32::GetFileAttributesW(w "$RetainedVersionDir") i .r0'
  ${If} $0 == -1
    Return
  ${EndIf}
next_paths:
  IntOp $Sequence $Sequence + 1
  ${If} $Sequence > 1000
    MessageBox MB_ICONSTOP "Too many retained installer attempts exist. No existing installation or experiments were changed."
    Abort
  ${EndIf}
  Goto find_free_paths
FunctionEnd

Section "OpenT1D" SEC_APPLICATION
  ; Repair must work even if the previously installed runtime is missing.
  ; Run trusted incoming maintenance code before changing any installed version.
  InitPluginsDir
  StrCpy $CurrentVersionDir "$PLUGINSDIR\OpenT1D-maintenance"
  ClearErrors
  SetOutPath "$CurrentVersionDir"
  ${If} ${Errors}
    MessageBox MB_ICONSTOP "OpenT1D could not create its temporary installer folder. Check access and free space, then retry. Your existing installation is unchanged."
    Abort
  ${EndIf}
  File /r "${PAYLOAD}\*"
  ${If} ${Errors}
    MessageBox MB_ICONSTOP "OpenT1D could not prepare its installer. Check free disk space and retry. Your existing installation and experiments are unchanged."
    Abort
  ${EndIf}
  !insertmacro StopCurrentApplication
  StrCpy $VersionDir "$INSTDIR\versions\${BUILD_ID}"
  Push $VersionDir
  Call VerifyInstallationPath
  Call SelectFreshVersionPaths
  ; Complete a new sibling before touching the currently registered version.
  ClearErrors
  SetOutPath "$IncomingVersionDir"
  ${If} ${Errors}
    MessageBox MB_ICONSTOP "OpenT1D could not create its staging folder. Check access and free space, then retry. Your existing installation is unchanged."
    Abort
  ${EndIf}
  SetOverwrite off
  File /r "${PAYLOAD}\*"
  ${If} ${Errors}
    MessageBox MB_ICONSTOP "OpenT1D could not prepare its new program files. Check free disk space and rerun this installer. The existing installation, retained attempts and experiments remain available."
    Abort
  ${EndIf}
  SetOutPath "$INSTDIR"
  System::Call 'kernel32::GetFileAttributesW(w "$VersionDir") i .r0'
  ${If} $0 != -1
    ClearErrors
    Rename "$VersionDir" "$RetainedVersionDir"
    ${If} ${Errors}
      MessageBox MB_ICONSTOP "OpenT1D could not move the previous copy aside. Close other OpenT1D windows, wait briefly and rerun this installer. The existing installation and experiments were not changed."
      Abort
    ${EndIf}
  ${Else}
    StrCpy $RetainedVersionDir ""
  ${EndIf}
  ClearErrors
  Rename "$IncomingVersionDir" "$VersionDir"
  ${If} ${Errors}
    ${If} $RetainedVersionDir != ""
      ClearErrors
      Rename "$RetainedVersionDir" "$VersionDir"
      ${If} ${Errors}
        MessageBox MB_ICONSTOP "OpenT1D could not activate or restore its program folder. Rerun this installer. The previous copy remains in $RetainedVersionDir and experiments are unchanged."
        Abort
      ${EndIf}
      MessageBox MB_ICONSTOP "OpenT1D could not activate its prepared program folder. The previous version was restored. Wait briefly and rerun this installer; experiments are unchanged."
      Abort
    ${EndIf}
    MessageBox MB_ICONSTOP "OpenT1D could not activate its prepared program folder. Wait briefly and rerun this installer. Prepared files were retained and experiments are unchanged."
    Abort
  ${EndIf}
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall OpenT1D.exe"
  CreateDirectory "$SMPROGRAMS\OpenT1D"
  CreateDirectory "$SMPROGRAMS\OpenT1D\Saved readers"
  SetOutPath "$VersionDir\app"
  CreateShortcut "$SMPROGRAMS\OpenT1D\Saved readers\${BUILD_ID}.lnk" "$VersionDir\runtime\pythonw.exe" "-B -E -s -m experiments.desktop"
  CreateShortcut "$SMPROGRAMS\OpenT1D\OpenT1D.lnk" "$VersionDir\runtime\pythonw.exe" "-B -E -s -m experiments.desktop"
  CreateShortcut "$DESKTOP\OpenT1D.lnk" "$VersionDir\runtime\pythonw.exe" "-B -E -s -m experiments.desktop"
  CreateShortcut "$SMPROGRAMS\OpenT1D\Uninstall OpenT1D.lnk" "$INSTDIR\Uninstall OpenT1D.exe"
  WriteRegStr HKCU "${APP_KEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${APP_KEY}" "CurrentVersionDir" "$VersionDir"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "OpenT1D"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${BUILD_ID}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "OpenT1D contributors"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall OpenT1D.exe$\"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '$\"$INSTDIR\Uninstall OpenT1D.exe$\" /S'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Function LaunchApplication
  !insertmacro ReleaseInstallerMutex
  SetOutPath "$VersionDir\app"
  Exec '"$VersionDir\runtime\pythonw.exe" -B -E -s -m experiments.desktop'
FunctionEnd

Section "Uninstall"
  ReadRegStr $CurrentVersionDir HKCU "${APP_KEY}" "CurrentVersionDir"
  !insertmacro StopCurrentApplication
  Delete "$DESKTOP\OpenT1D.lnk"
  Delete "$SMPROGRAMS\OpenT1D\OpenT1D.lnk"
  Delete "$SMPROGRAMS\OpenT1D\Uninstall OpenT1D.lnk"
  RMDir "$SMPROGRAMS\OpenT1D"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  DeleteRegKey HKCU "${APP_KEY}"
  Delete "$INSTDIR\Uninstall OpenT1D.exe"
  ; No recursive deletion: versioned readers and user-owned archives are retained.
SectionEnd
