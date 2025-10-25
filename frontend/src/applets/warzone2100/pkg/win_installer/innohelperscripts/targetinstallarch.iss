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
// Script to assist in getting / setting / detecting a target install architecture
//
// - Customize which architectures you actually provide with the TARGETARCH_SUPPORTS_* defines
// - Defaults to the best available target architecture (native, if possible)
// - Handles /targetarch=<x64,arm64,x86> command-line option
//
// Example Usage:
//
// [Files]
// Source: "bin\x64\*"; DestDir: "{app}\bin"; Check: IsTargettingInstallArchitecture('x64')
// Source: "bin\arm64\*"; DestDir: "{app}\bin"; Check: IsTargettingInstallArchitecture('arm64')
// Source: "bin\x86\*"; DestDir: "{app}\bin"; Check: IsTargettingInstallArchitecture('x86')
//
// Notes:
// - Tested with Innosetup 6.4.3
//

#ifndef __INCLUDE_TARGET_INSTALL_ARCH
#define __INCLUDE_TARGET_INSTALL_ARCH

#ifndef TARGETARCH_SUPPORTS_X86
  #define TARGETARCH_SUPPORTS_X86 1
#endif
#ifndef TARGETARCH_SUPPORTS_X64
  #define TARGETARCH_SUPPORTS_X64 1
#endif
#ifndef TARGETARCH_SUPPORTS_ARM64
  #define TARGETARCH_SUPPORTS_ARM64 1
#endif
#define TARGETARCH_DEFAULT_WHEN_NO_MATCH ""

[Code]
var
  TargetInstallArchitecture: String;
  TargetInstall_Arm64Compatible: Boolean;

function GetMachineTypeAttributes(Machine: WORD; var MachineTypeAttributes: Integer): Integer;
external 'GetMachineTypeAttributes@kernel32.dll stdcall delayload setuponly';

// Returns true if the system is Arm64 compatible
function IsArm64Compatible(): Boolean;
begin
  Result := TargetInstall_Arm64Compatible;
end;

function IsValidTargetArchitecture(sArch: String): Boolean;
begin
  #if TARGETARCH_SUPPORTS_X86
  if sArch = 'x86' then
  begin
    Result := True;
  end
  else
  #endif
  #if TARGETARCH_SUPPORTS_X64
  if sArch = 'x64' then
  begin
    Result := True;
  end
  else
  #endif
  #if TARGETARCH_SUPPORTS_ARM64
  if sArch = 'arm64' then
  begin
    Result := True;
  end
  else
  #endif
  begin
    Result := False;
  end;
end;

function IsCompatibleTargetArchitecture(sArch: String): Boolean;
begin
  #if TARGETARCH_SUPPORTS_X86
  if sArch = 'x86' then
  begin
    Result := IsX86Compatible();
  end
  else
  #endif
  #if TARGETARCH_SUPPORTS_X64
  if sArch = 'x64' then
  begin
    Result := IsX64Compatible();
  end
  else
  #endif
  #if TARGETARCH_SUPPORTS_ARM64
  if sArch = 'arm64' then
  begin
    Result := IsArm64Compatible();
  end
  else
  #endif
  begin
    Result := False;
  end;
end;

function GetDefaultInstallArchitecture(): String;
begin
  // Handle exact matches
  case ProcessorArchitecture of
  #if TARGETARCH_SUPPORTS_X86
    paX86: Result := 'x86';
  #endif
  #if TARGETARCH_SUPPORTS_X64
    paX64: Result := 'x64';
  #endif
  #if TARGETARCH_SUPPORTS_ARM64
    paArm64: Result := 'arm64';
  #endif
  else
    begin
      // Handle compatible matches
      Log('Did not find native match - checking for compatible architecture match');
      #if TARGETARCH_SUPPORTS_ARM64
      if IsArm64Compatible() then
      begin
        Result := 'arm64';
      end else
      #endif
      #if TARGETARCH_SUPPORTS_X64
      if IsX64Compatible() then
      begin
        Result := 'x64';
      end else
      #endif
      #if TARGETARCH_SUPPORTS_X86
      if IsX86Compatible() then
      begin
        Result := 'x86';
      end else
      #endif
      begin
        Result := '{#TARGETARCH_DEFAULT_WHEN_NO_MATCH}'; // No match
      end;
    end;
  end;
end;

function SetTargetInstallArchitecture(sArch: String): Boolean;
begin
  if not IsValidTargetArchitecture(sArch) then
  begin
    Log(Format('Attempt to set invalid TargetInstallArchitecture: %s', [sArch]));
    Result := False;
    Exit;
  end;
  if TargetInstallArchitecture = sArch then
    Exit; // no change
  TargetInstallArchitecture := sArch;
  Log(Format('Setting TargetInstallArchitecture: %s', [TargetInstallArchitecture]));
  Result := True;
end;

function GetCurrentTargetInstallArchitecture(): String;
begin
  Result := TargetInstallArchitecture;
end;

function IsTargettingInstallArchitecture(sArch: String): Boolean;
begin
  Result := (sArch = TargetInstallArchitecture);
end;

function SetCmdLineParamTargetInstallArchitecture(): Boolean;
var
  ParamTargetArch: String;
begin
  // Handle /targetarch=<x64,arm64,x86> command-line option:
  ParamTargetArch := LowerCase(ExpandConstant('{param:targetarch|default}'));
  if CompareText(ParamTargetArch, 'default') <> 0 then
  begin
    // SetTargetInstallArchitecture checks for validity (just string validity - does not check if it can run on this system - assume the caller knows best)
    if not SetTargetInstallArchitecture(ParamTargetArch) then
    begin
      Log(Format('Invalid /targetarch specified: %s', [ParamTargetArch]));
      Result := False;
      Exit;
    end;
    Log(Format('/targetarch specified: %s', [ParamTargetArch]));
    if not IsCompatibleTargetArchitecture(ParamTargetArch) then
    begin
      SuppressibleMsgBox(Format('Warning: /targetarch specified "%s", which may not run on this system. Proceeding under the assumption that you know what you are doing.', [ParamTargetArch]), mbError, MB_OK, MB_OK);
    end;
    Result := True;
    Exit;
  end;
  Result := False;
end;

<event('InitializeSetup')>
function TargetInstallArch_InitializeSetup(): Boolean;
var
  MachineTypeAttributes: Integer;
begin
  // Check & cache IsArm64Compatible value
  try
    // IMAGE_FILE_MACHINE_ARM64 => $AA64
    if (GetMachineTypeAttributes($AA64, MachineTypeAttributes) <> 0) then
      MachineTypeAttributes := 0;
  except
    // GetMachineTypeAttributes is unavailable, which presumably means this is < Windows 11 and couldn't be ARM64 compatible anyway
    Log('GetMachineTypeAttributes is unavailable');
  end;
  TargetInstall_Arm64Compatible := (MachineTypeAttributes and $1) <> 0; // Check UserEnabled flag
  
  if not SetCmdLineParamTargetInstallArchitecture() then
  begin
    // Get default target install architecture
    TargetInstallArchitecture := GetDefaultInstallArchitecture();
    Log(Format('Defaulting to TargetInstallArchitecture: %s', [TargetInstallArchitecture]));
  end;
  Result := True;
end;

// end __INCLUDE_TARGET_INSTALL_ARCH
#endif