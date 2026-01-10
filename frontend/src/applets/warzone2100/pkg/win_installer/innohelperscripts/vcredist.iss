// SPDX-License-Identifier: MIT
//
// Copyright (c) 2025 past-due - https://github.com/past-due/innohelperscripts/
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
// 
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
// 
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
// 
// ----------------------------------------------------------------------------------
//
// Script to assist in downloading and installing the VC Runtime / UCRT system component
//
// To use, call VCRuntime_DownloadAndInstallArch('arch', ...), where 'arch' is one of:
// - 'arm64', 'x64', 'x86'
// And the additional parameters are display strings (see the example below).
//
// Requires:
// - Innosetup 6.2+ (tested with 6.4.3)
// - innofilecheck.dll (https://github.com/past-due/innofilecheck)
//
// ----------------------------------------------------------------------------------
//
// Simple Example Usage:
//
// // If innofilecheck.dll is located somewhere other than alongside your main script,
// // uncomment this define and point to the folder containing it:
// // #define INNOFILECHECK_DLL_DIR "path_to_folder_containing_innofilecheck_dll"
//
// #include "vcredist.iss"
// 
// [CustomMessages]
// VCRuntimeInstalling=Installing Visual C++ Runtime Redistributable
// VCRuntimeWaiting=Waiting for installation to complete...
// VCRuntimeVerifying=Verifying Download
//
// [Code]
// function NextButtonClick(CurPageID: Integer): Boolean;
// begin
//   if CurPageID = wpReady then begin
//     // Download & install VC Redist
//     if not VCRuntime_DownloadAndInstallArch('x64', CustomMessage('VCRuntimeVerifying'), CustomMessage('VCRuntimeInstalling'), CustomMessage('VCRuntimeWaiting')) then
//     begin
//       // TODO: Handle failure
//     end;
//   end;
//   Result := True;
// end;
//

#define VC_REDIST_EXE_NAME "vc_redist.exe"

#ifndef INNOFILECHECK_DLL_DIR
// Default to assuming that innofilecheck.dll has been placed in the same directory as the main including script
#define INNOFILECHECK_DLL_DIR SourcePath
#endif

#if FileExists(INNOFILECHECK_DLL_DIR + "\innofilecheck.dll") == 0
  #error innofilecheck.dll cannot be found - either download the file to the SourcePath, or define INNOFILECHECK_DLL_DIR appropriately before including vcredist.iss. See: https://github.com/past-due/innohelperscripts for more details
#endif

[Files]
Source: "{#INNOFILECHECK_DLL_DIR}\innofilecheck.dll"; Flags: dontcopy solidbreak

[Code]
var
  VCRuntimeDownloadPage: TDownloadWizardPage;
  VCRuntimeOutputProgressWizardPage: TOutputMarqueeProgressWizardPage;
  VCRuntimeNeedsRestart: Boolean;

function FCVerifyFileCodeSignature(const filePath: String; const certName: String; const certIssuerName: String; const microsoftRootCheck: BOOL): Integer;
external 'VerifyFileCodeSignature@files:innofilecheck.dll cdecl delayload setuponly';

function FCGetFileVersionString(const filePath: String; const stringName: String; wLanguage: Word; wCodePage: Word; out_str: String; out_len: UINT): Integer;
external 'GetFileVersionString@files:innofilecheck.dll cdecl delayload setuponly';

function GetVCRuntimeURLForArchitecture(sArch: String): String;
begin
  case sArch of
    'arm64': Result := 'https://aka.ms/vs/17/release/vc_redist.arm64.exe';
    'x64': Result := 'https://aka.ms/vs/17/release/vc_redist.x64.exe';
    'x86': Result := 'https://aka.ms/vs/17/release/vc_redist.x86.exe';
  else
    Result := '';
  end;
end;

function GetFileVersionStringWrapper(filePath: String; const stringName: String; wLanguage: Word; wCodePage: Word; var out_str: String): Boolean;
var
  FileCheckResult: Integer;
  BufferLength: Integer;
begin
  // Call once to determine required length of string
  FileCheckResult := FCGetFileVersionString(filePath, stringName, wLanguage, wCodePage, '', 0);
  if FileCheckResult < 0 then
  begin
    Log('GetFileVersionString of "' + filePath + '" failed with code: ' + IntToStr(FileCheckResult));
    Result := False;
    Exit;
  end;
  // Allocate a buffer of desired length (including space for null terminator)
  BufferLength := FileCheckResult + 1;
  SetLength(out_str, BufferLength);
  // Request the string value
  FileCheckResult := FCGetFileVersionString(filePath, stringName, wLanguage, wCodePage, out_str, BufferLength);
  if FileCheckResult < 0 then
  begin
    Log('GetFileVersionString of "' + filePath + '" failed with code: ' + IntToStr(FileCheckResult));
    Result := False;
    Exit;
  end;
  // Check for truncation (should only happen if the file changed between the initial and subsequent calls)
  if FileCheckResult >= BufferLength then
  begin
    Log('GetFileVersionString of "' + filePath + '" unexpectedly truncated string');
    Result := False;
    Exit;
  end;
  // Set the buffer length to the returned length
  SetLength(out_str, FileCheckResult);
  Result := True;
end;

function VC_Redist_Validated(VC_Redist_Exe_Path: String): Boolean;
var
  FileCheckResult: Integer;
  BufferW: String;
begin
  if not (FileExists(VC_Redist_Exe_Path)) then
  begin
    Result := False;
    Exit;
  end;
  FileCheckResult := FCVerifyFileCodeSignature(VC_Redist_Exe_Path, 'Microsoft Corporation', '', True);
  if FileCheckResult <> 0 then
  begin
    Log('"' + VC_Redist_Exe_Path + '" failed code signature checks with failure code: ' + IntToStr(FileCheckResult));
    Result := False;
    Exit;
  end;
  if not GetFileVersionStringWrapper(VC_Redist_Exe_Path, 'FileDescription', 1033, 1252, BufferW) then
  begin
    Log('"' + VC_Redist_Exe_Path + '" failed to retrieve file version info');
    Result := False;
    Exit;
  end;
  if not WildcardMatch(BufferW, 'Microsoft Visual C++ *') then
  begin
    Log('"' + VC_Redist_Exe_Path + '" failed file checks: "' + BufferW + '"');
    Result := False;
    Exit;
  end;
  Log('"' + VC_Redist_Exe_Path + '" passed validation');
  Result := True;
end;

function AddVCRuntimeToDownloadPage(DownloadPage: TDownloadWizardPage; BaseName: String; sArch: String): Boolean;
var
  VcRuntimeDLURL: String;
begin
  VcRuntimeDLURL := GetVCRuntimeURLForArchitecture(sArch)
  if Length(VcRuntimeDLURL) = 0 then
  begin
    Result := False;
    Exit;
  end;
  DownloadPage.Add(VcRuntimeDLURL, BaseName, '');
  Result := True;
end;

function TryInstallVCRuntime(vcRedistDLPath: String): Boolean;
var
  ResultCode: Integer;
begin
  // Launch vc_redist quietly and wait for it to terminate (if running a "current-user" install, this will yield a UAC prompt for the vcredist)
  if Exec(vcRedistDLPath, '/install /quiet /norestart', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode) then
  begin
    // Handle success if necessary; ResultCode contains the exit code
    if ResultCode = 3010 then
    begin
      Log('VC Redistributable exit code 3010: Needs Restart');
      VCRuntimeNeedsRestart := True;
      Result := True;
      Exit;
    end
    else if ResultCode <> 0 then
    begin
      // Unknown failure
      Log('VC Redistributable failure exit code: ' + IntToStr(ResultCode));
      Result := False;
      Exit;
    end;
    // Success with exit code 0
    Log('VC Redistributable exit code: Success');
    Result := True;
    Exit;
  end
  else begin
    // Execution failed
    Log('VC Redistributable installer failed with error: ' + IntToStr(ResultCode) + ': ' + SysErrorMessage(ResultCode));
    SuppressibleMsgBox(FmtMessage(SetupMessage(msgErrorExtractionFailed), ['Visual C++ Runtime Redistributable']), mbCriticalError, MB_OK, IDOK);
    Result := False;
    Exit;
  end;
end;

function VCRuntime_OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if Progress = ProgressMax then
    Log(Format('Successfully downloaded VC Redistributable to {tmp}: %s', [FileName]));
  Result := True;
end;

<event('InitializeSetup')>
function VCRuntime_InitializeSetup(): Boolean;
begin
  Result := True;
end;

<event('InitializeWizard')>
procedure VCRuntime_InitializeWizard;
begin
  VCRuntimeDownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), @VCRuntime_OnDownloadProgress);
  VCRuntimeDownloadPage.ShowBaseNameInsteadOfUrl := True;
  VCRuntimeOutputProgressWizardPage := CreateOutputMarqueeProgressPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc));
  VCRuntimeNeedsRestart := False;
end;

<event('NeedRestart')>
function VCRuntime_NeedRestart(): Boolean;
begin
  Result := VCRuntimeNeedsRestart;
end;

function VCRuntime_DownloadAndInstallArch(sArch: String; VCRuntimeVerifying, VCRuntimeInstalling, VCRuntimeWaiting: String): Boolean;
var
  vcRedistDLPath: String;
begin
  VCRuntimeDownloadPage.Clear;
  if not AddVCRuntimeToDownloadPage(VCRuntimeDownloadPage, '{#VC_REDIST_EXE_NAME}', sArch) then
  begin
    Result := False;
    Exit;
  end;
  VCRuntimeDownloadPage.Show;
  try
    try
      VCRuntimeDownloadPage.Download; // Downloads the file to '{tmp}'
      Result := True;
    except
      if VCRuntimeDownloadPage.AbortedByUser then
        Log('VC Redistributable download aborted by user.')
      else
        SuppressibleMsgBox(AddPeriod(GetExceptionMessage), mbCriticalError, MB_OK, IDOK);
      Result := False;
    end;
  finally
    VCRuntimeDownloadPage.Hide;
  end;
  
  if not Result then
    Exit;
  
  try
    VCRuntimeOutputProgressWizardPage.SetText(VCRuntimeVerifying, '');
    VCRuntimeOutputProgressWizardPage.Show;
    VCRuntimeOutputProgressWizardPage.Animate();
  
    // Validate downloaded file
    vcRedistDLPath := ExpandConstant('{tmp}\{#VC_REDIST_EXE_NAME}')
    if not VC_Redist_Validated(vcRedistDLPath) then
    begin
      Result := False;
      Exit;
    end;
    
    VCRuntimeOutputProgressWizardPage.SetText(VCRuntimeInstalling, VCRuntimeWaiting);
    VCRuntimeOutputProgressWizardPage.Animate();
    
    // Attempt install
    Result := TryInstallVCRuntime(vcRedistDLPath);
    
  finally
    VCRuntimeOutputProgressWizardPage.Hide;
  end;
end;