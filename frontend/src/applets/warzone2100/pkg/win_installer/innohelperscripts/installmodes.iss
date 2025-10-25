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
// Script to assist in getting / setting custom install modes for an installer
// Supports "normal", "sidebyside", and "portable" modes
//
// Example Usage:
//
// ```
// #include "installmodes.iss"
//
// [Setup]
// AppId={code:InstallModes_AppId|{#MyBaseAppId},{#MyAppVersion}} // NOTE!: Define MyBaseAppId to something unique for your app! (See: AppId documentation)
// DefaultDirName={code:InstallModes_DefaultDirName|{#MyAppName},{#MyAppVersion}}
// Uninstallable=not IsPortableMode
// UninstallDisplayName={code:InstallModes_AppInstallationName|{#MyAppName},{#MyAppVersion}}
// // Unfortunately, these are both required when setting the AppId using constants
// UsePreviousLanguage=no
// UsePreviousPrivileges=no
//
// [Icons]
// Name: "{autoprograms}\{code:InstallModes_AppInstallationName|{#MyAppName},{#MyAppVersion}}"; Filename: "{app}\{#MyAppExeName}"; Check: not IsPortableMode and not WizardNoIcons
// Name: "{autodesktop}\{code:InstallModes_AppInstallationName|{#MyAppName},{#MyAppVersion}}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Check: not IsPortableMode
//
// ```
//
// By default, this will handle two new command-line options for the installer:
// /portable
// - which enables portable mode
// /sidebyside
// - which enables side-by-side versions mode (allowing multiple versions of the same app to be easily installed)
//
// There is also SetInstallMode(Mode: TCustomInstallMode) to support changing this install mode at runtime.
// It takes one of: customInstallModeNormal, customInstallModeSideBySide, customInstallModePortable
//
// Notes:
// - Tested with Innosetup 6.4.3
//

#ifndef __INCLUDE_INSTALL_MODES
#define __INCLUDE_INSTALL_MODES

[Code]
type
  TCustomInstallMode = (customInstallModeNormal, customInstallModeSideBySide, customInstallModePortable);

var
  CustomInstallMode: TCustomInstallMode;

function CustomInstallModeToStr(Mode: TCustomInstallMode): String;
begin
  case Mode of
    customInstallModeNormal: Result := 'normal';
    customInstallModeSideBySide: Result := 'sidebyside';
    customInstallModePortable: Result := 'portable';
  end;
end;

function GetCurrentCustomInstallMode(): TCustomInstallMode;
begin
  Result := CustomInstallMode;
end;

function IsCurrentCustomInstallMode(Mode: TCustomInstallMode): Boolean;
begin
  Result := (Mode = CustomInstallMode);
end;

function IsPortableMode(): Boolean;
begin
  Result := (CustomInstallMode = customInstallModePortable);
end;

function AppendSuffixIfPortableMode(Input, PortableSuffix: String): String;
begin;
  Result := Input;
  if IsPortableMode then
  begin
    Result := Result + PortableSuffix;
  end;
end;

function InstallModes_AppId(Param: String): String;
var
  Input: array of String;
begin;
  // Param is expected to be comma-separated BaseAppId,AppVersion
  Input := StringSplitEx(Param, [','], '"', stAll);

  case CustomInstallMode of
    customInstallModeNormal: begin
      Result := Input[0];
    end;
    customInstallModeSideBySide: begin
      // Side by side mode is like normal but appends the version as well, to ensure a version-specific AppId that is distinct from the normal one
      Result := Input[0] + '_' + Input[1];
    end;
    customInstallModePortable: begin
      // If portable mode is enabled from the command-line, appending '_portable' here
      // ensures that the AppId differs from the non-portable versions.
      // This ensures that the portable install is not considered the same application as
      // the non-portable install (we don't want the portable install picking up the previous
      // app dir from a non-portable install).
      Result := Input[0] + '_portable';
    end;
  end;
end;

// Can be used for things like UninstallDisplayName, or the 'Name' of an [Icons] entry
// Param is expected to be comma-separated: BaseAppName,AppVersion
function InstallModes_AppInstallationName(Param: String): String;
var
  Input: array of String;
begin;
  // Param is expected to be comma-separated BaseAppName,AppVersion
  Input := StringSplitEx(Param, [','], '"', stAll);

  case CustomInstallMode of
    customInstallModeNormal: begin
      Result := Input[0];
    end;
    customInstallModeSideBySide: begin
      // Side by side mode is like normal but appends the version as well
      Result := Input[0] + ' (' + Input[1] + ')';
    end;
    customInstallModePortable: begin
      // If portable mode is enabled from the command-line, appending '_portable' here
      // ensures that the AppId differs from the non-portable versions.
      // This ensures that the portable install is not considered the same application as
      // the non-portable install (we don't want the portable install picking up the previous
      // app dir from a non-portable install).
      Result := Input[0] + ' Portable';
    end;
  end;
end;

function InstallModes_DefaultDirName(Param: String): String;
var
  Input: array of String;
begin
  // Param is expected to be comma-separated BaseAppName,AppVersion
  Input := StringSplitEx(Param, [','], '"', stAll);
  
  case CustomInstallMode of
    customInstallModeNormal: begin
      // {autopf}\AppName
      Result := AddBackslash(ExpandConstant('{autopf}')) + Input[0];
    end;
    customInstallModeSideBySide: begin
      // Side by side mode is like normal, but appends the version as well
      Result := AddBackslash(ExpandConstant('{autopf}')) + Input[0] + ' ' + Input[1];
    end;
    customInstallModePortable: begin
      // Portable mode uses a default of the current directory of the setup file, with a subfolder named after the "<AppName>-Portable-AppVersion"
      Result := AddBackslash(ExpandConstant('{src}')) + AppendSuffixIfPortableMode(Input[0], '-Portable') + '-' + Input[1];
    end;
  end;
end;

procedure SetCustomInstallMode(NewMode: TCustomInstallMode; AppName, AppVersion: String);
begin
  if CustomInstallMode = NewMode then
    Exit; // no change
  CustomInstallMode := NewMode;
  Log(Format('InstallMode: %s', [CustomInstallModeToStr(NewMode)]));
  // Check the "Don't create a Start Menu folder" option appropriately
  WizardForm.NoIconsCheck.Checked := (CustomInstallMode = customInstallModePortable);
  // Change the default installation dir
  WizardForm.DirEdit.Text := InstallModes_DefaultDirName(AppName + ',' + AppVersion);
  Log('Updating default installation dir to: ' + WizardForm.DirEdit.Text);
end;

function CommandLineParameterExists(const Value: String): Boolean;
var
  I: Integer;
begin
  // Parameter 0 is the full setup file name - start at index 1
  for I := 1 to ParamCount do
  begin
    if CompareText(Value, ParamStr(I)) = 0 then // use CompareText (it's case-insensitive)
    begin
      Result := True;
      Exit;
    end;
  end;
  Result := False;
end;

<event('InitializeSetup')>
function InstallModes_InitializeSetup(): Boolean;
var
  PortableMode: Boolean;
  SideBySideMode: Boolean;
begin
  PortableMode := CommandLineParameterExists('/portable');
  SideBySideMode := CommandLineParameterExists('/sidebyside');
  
  if PortableMode then begin
    if SideBySideMode then Log('Portable mode takes precedence over side-by-side mode. Using portable mode.');
    CustomInstallMode := customInstallModePortable;
  end else if SideBySideMode then begin
    CustomInstallMode := customInstallModeSideBySide;
  end else begin
    CustomInstallMode := customInstallModeNormal;
  end;
  Log(Format('Initial InstallMode: %s', [CustomInstallModeToStr(CustomInstallMode)]));
  Result := True;
end;

<event('InitializeWizard')>
procedure InstallModes_InitializeWizard();
begin
  if IsPortableMode then
    // Check the "Don't create a Start Menu folder" option
    WizardForm.NoIconsCheck.Checked := True;
    // Rely on the consuming script using InstallModes_DefaultDirName for DefaultDirName to set the path at start
end;

// end __INCLUDE_INSTALL_MODES
#endif