// SPDX-License-Identifier: MIT
//
// Advanced Options Form
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

// To customize which advanced options are shown, you can define these in your main script before including this file:
// #define ADVANCEDOPTIONSFORM_NO_INSTALLMODES
// #define ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH
//
// If you define ADVANCEDOPTIONSFORM_NO_DEFINE_CUSTOMMESSAGES in your main script before including this file, it will
// suppress the definition of this script's CustomMessages, letting you easily define variations in your main script
// file or in custom .isl files.
//
// This script generally expects that you've hooked up installmodes and targetinstallarch in your main script as
// demonstrated in the examples in those files.
//

#ifndef ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH
#include <targetinstallarch.iss>
#endif
#ifndef ADVANCEDOPTIONSFORM_NO_INSTALLMODES
#include <installmodes.iss>
#endif

#ifndef ADVANCEDOPTIONSFORM_NO_DEFINE_CUSTOMMESSAGES
// Default custom messages - customize as needed:
[CustomMessages]
AdvancedOptionsTitle=Advanced Options - %1
StandardInstall=Standard Install
StandardInstallDesc=Install %1 on your PC. (Recommended)
StandardUpdate=Standard Install (Update)
StandardUpdateDesc=Update the existing install of %1 on your PC. (Recommended)
SideBySideInstall=Side-by-Side Install
SideBySideInstallDesc=Install this version separately from any other versions, including the Standard Install.
PortableInstall=Portable Install
PortableInstallDesc=Install to a USB drive, folder, etc. Fully self-contained in a single directory, including settings and saves.
InstallArchitecture=Install Architecture:
#endif

[Code]
var
  AdvancedInstallOptions_ArchEditMode: Integer; // 3 levels: (0: editing disabled, 1: editing enabled; 2: editing enabled + show all compatible archs (even x86 if it was hidden))
  AdvancedInstallOptions_InstallArchCombo: TNewComboBox;

function AdvancedInstallOptions_CompareTStrings(a: TStrings; b: TStrings): Boolean;
var
  I: Integer;
begin
  if a.Count <> b.Count then
  begin
    Result := False;
    Exit;
  end;
  for I := 0 to a.Count - 1 do
  begin
    if a.Strings[I] <> b.Strings[I] then
    begin
      Result := False;
      Exit;
    end;
  end;
  Result := True;
end;

procedure AdvancedInstallOptions_OnKeyDown(Sender: TObject; var Key: Word; Shift: TShiftState);
begin
  #ifndef ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH
  if ([ssAlt] = Shift) or ([ssCtrl] = Shift) then
  begin
    if AdvancedInstallOptions_ArchEditMode >= 2 then begin
      Exit;
    end else if AdvancedInstallOptions_ArchEditMode = 1 then begin
      Log('Toggle: Show all compatible architectures');
    end else begin
      Log('Toggle: Editable install architecture');
    end;
    AdvancedInstallOptions_ArchEditMode := AdvancedInstallOptions_ArchEditMode + 1;
    try
      AdvancedInstallOptions_InstallArchCombo.Enabled := True;
    except
      Log('Failed to update combo box enabled status');
    end;
  end;
  #endif
end;

#ifndef ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH

procedure AdvancedInstallOptions_PopulateArchCombo(InstallArchCombo: TNewComboBox; Force: Boolean);
var
  ArchStrings: TStrings;
  ItemIndex: Integer;
  SelectedArch: String;
begin
  ArchStrings := TStringList.Create;
  ItemIndex := 0;
  if not Force and (InstallArchCombo.Items.Count > 0) then
  begin
    SelectedArch := InstallArchCombo.Items.Strings[InstallArchCombo.ItemIndex];
  end
  else begin
    SelectedArch := GetCurrentTargetInstallArchitecture();
  end;
  try
    ArchStrings.Clear;
    if IsValidTargetArchitecture('arm64') then begin
      if IsArm64Compatible() then
        ArchStrings.Add('arm64');
        if SelectedArch = 'arm64' then
          ItemIndex := ArchStrings.Count - 1;
    end;
    if IsValidTargetArchitecture('x64') then begin
      if IsX64Compatible() then
        ArchStrings.Add('x64');
        if SelectedArch = 'x64' then
          ItemIndex := ArchStrings.Count - 1;
    end;
    if IsValidTargetArchitecture('x86') then begin
      if IsX86OS() or ((AdvancedInstallOptions_ArchEditMode >= 2) and IsX86Compatible()) or (SelectedArch = 'x86') then
        ArchStrings.Add('x86');
        if SelectedArch = 'x86' then
          ItemIndex := ArchStrings.Count - 1;
    end;
    // now check if this is different than the current combobox items
    if Force Or (AdvancedInstallOptions_CompareTStrings(InstallArchCombo.Items, ArchStrings) = False) then
    begin
      if Debugging then Log('Updating install arch combobox items');
      InstallArchCombo.Items.Clear;
      InstallArchCombo.Items.AddStrings(ArchStrings);
      InstallArchCombo.ItemIndex := ItemIndex;
    end;
  finally
    ArchStrings.Free();
  end;
end;

procedure InstallArchCombo_OnDropdown(Sender: TObject);
var
  InstallArchCombo: TNewComboBox;
begin
  InstallArchCombo := TNewComboBox(Sender);
  AdvancedInstallOptions_PopulateArchCombo(InstallArchCombo, False);
end;

#endif // ifndef ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH

procedure InstallModeDescText_OnClick(Sender: TObject);
var
  InstallModeDescText: TNewStaticText;
  InstallModeRadioBut: TNewRadioButton;
begin
  InstallModeDescText := TNewStaticText(Sender);
  if InstallModeDescText = nil then Exit;
  InstallModeRadioBut := TNewRadioButton(InstallModeDescText.FocusControl);
  if InstallModeRadioBut = nil then Exit;
  InstallModeRadioBut.Checked := True; // trigger checking of the associated radio button
end;

procedure AddCustomInstallModeOption(InstallModePanel: TPanel; Top: Integer; var RadioBut: TNewRadioButton; RadioButMessage: String; var InstallDesc: TNewStaticText; InstallDescMessage: String; Checked: Boolean; FontIncrease: Integer);
begin
  RadioBut := TNewRadioButton.Create(InstallModePanel);
  RadioBut.Parent := InstallModePanel;
  RadioBut.Top := Top;
  RadioBut.Left := ScaleX(10);
  RadioBut.Width := InstallModePanel.ClientWidth - ScaleX(2 * 10);
  RadioBut.Height := ScaleY(17);
  RadioBut.Anchors := [akLeft, akTop, akRight];
  RadioBut.Caption := RadioButMessage;
  RadioBut.Font := InstallModePanel.Font; // workaround: for some reason needed to ensure it gets a matching font
  RadioBut.Font.Style := [fsBold];
  RadioBut.Font.Size := InstallModePanel.Font.Size + FontIncrease;
  RadioBut.Checked := Checked;
  
  InstallDesc := TNewStaticText.Create(InstallModePanel);
  InstallDesc.Parent := InstallModePanel;
  InstallDesc.Top := RadioBut.Top + RadioBut.Height + ScaleY(2);
  InstallDesc.Left := ScaleX(26);
  InstallDesc.Width := InstallModePanel.ClientWidth - ScaleX(26 + 10);
  InstallDesc.Anchors := [akLeft, akTop, akRight];
  InstallDesc.WordWrap := True; // Must be set before Caption
  InstallDesc.Caption := InstallDescMessage;
  InstallDesc.AdjustHeight();
  InstallDesc.FocusControl := RadioBut;
  InstallDesc.TabStop := False;
  InstallDesc.OnClick := @InstallModeDescText_OnClick;
end;

procedure OpenAdvancedInstallOptionsModal(AppName, AppVersion: String);
var
  Form: TSetupForm;
  InstallModePanel: TPanel;
  StandardIsPatchExistingByDefault: Boolean;
  StandardInstallCustomMessage: String;
  StandardInstallDescCustomMessage: String;
  StandardInstallRadio: TNewRadioButton;
  StandardInstallDesc: TNewStaticText;
  SideBySideInstallRadio: TNewRadioButton;
  SideBySideInstallDesc: TNewStaticText;
  PortableInstallRadio: TNewRadioButton;
  PortableInstallDesc: TNewStaticText;
  InstallArchPanel: TPanel;
  InstallArchLabel: TNewStaticText;
  OKButton, CancelButton: TNewButton;
  PrevPanelBottom: Integer;
  W: Integer;
  SelectedArch: String;
begin
  AdvancedInstallOptions_ArchEditMode := 0;
  if (GetDefaultInstallArchitecture() <> GetCurrentTargetInstallArchitecture()) then
  begin
    AdvancedInstallOptions_ArchEditMode := 1;
  end;
  StandardIsPatchExistingByDefault := WizardForm.PrevAppDir <> '';
  Form := CreateCustomForm();
  try
    Form.ClientWidth := ScaleX(400);
    Form.ClientHeight := ScaleY(300);
    Form.Caption := FmtMessage(CustomMessage('AdvancedOptionsTitle'), [AppName]);
    Form.KeyPreview := True;
    Form.OnKeyDown := @AdvancedInstallOptions_OnKeyDown;
    PrevPanelBottom := 0;

    #ifndef ADVANCEDOPTIONSFORM_NO_INSTALLMODES
    
    // [Install Mode Panel]
    
    InstallModePanel := TPanel.Create(Form);
    InstallModePanel.Parent := Form;
    InstallModePanel.Top := ScaleY(8);
    InstallModePanel.Width := Form.ClientWidth - ScaleX(2 * 10);
    // Wait on setting height until after adding contents
    InstallModePanel.Left := ScaleX(10);
    InstallModePanel.Anchors := [akLeft, akTop, akRight];
    InstallModePanel.Color := Form.Color;
    InstallModePanel.BevelKind := bkTile;
    InstallModePanel.BevelOuter := bvNone;
    InstallModePanel.Font := Form.Font;
    
    StandardInstallCustomMessage := 'StandardInstall';
    if StandardIsPatchExistingByDefault then StandardInstallCustomMessage := 'StandardUpdate';
    StandardInstallDescCustomMessage := 'StandardInstallDesc';
    if StandardIsPatchExistingByDefault then StandardInstallDescCustomMessage := 'StandardUpdateDesc';
    
    AddCustomInstallModeOption(InstallModePanel, ScaleY(8), StandardInstallRadio, CustomMessage(StandardInstallCustomMessage), StandardInstallDesc, FmtMessage(CustomMessage(StandardInstallDescCustomMessage), [AppName]), IsCurrentCustomInstallMode(customInstallModeNormal), 1);
    W := StandardInstallDesc.Top + StandardInstallDesc.Height + ScaleY(10);
    
    AddCustomInstallModeOption(InstallModePanel, W, SideBySideInstallRadio, CustomMessage('SideBySideInstall'), SideBySideInstallDesc, CustomMessage('SideBySideInstallDesc'), IsCurrentCustomInstallMode(customInstallModeSideBySide), 0);
    W := SideBySideInstallDesc.Top + SideBySideInstallDesc.Height + ScaleY(8);

    AddCustomInstallModeOption(InstallModePanel, W, PortableInstallRadio, CustomMessage('PortableInstall'), PortableInstallDesc, CustomMessage('PortableInstallDesc'), IsCurrentCustomInstallMode(customInstallModePortable), 0);

    // Resize panel height based on total required height of contents
    InstallModePanel.Height := PortableInstallDesc.Top + PortableInstallDesc.Height + ScaleY(15);
    
    PrevPanelBottom := InstallModePanel.Top + InstallModePanel.Height;
    
    #endif // ifndef ADVANCEDOPTIONSFORM_NO_INSTALLMODES
    
    #ifndef ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH
    
    // [Architecture Panel]
    
    InstallArchPanel := TPanel.Create(Form);
    InstallArchPanel.Parent := Form;
    InstallArchPanel.Top := PrevPanelBottom + ScaleY(8);
    InstallArchPanel.Width := Form.ClientWidth - ScaleX(2 * 10);
    // Wait on setting height until after adding contents
    InstallArchPanel.Left := ScaleX(10);
    InstallArchPanel.Anchors := [akLeft, akTop, akRight];
    InstallArchPanel.Color := Form.Color;
    InstallArchPanel.BevelKind := bkTile;
    InstallArchPanel.BevelOuter := bvNone;
    
    InstallArchLabel := TNewStaticText.Create(Form);
    InstallArchLabel.Parent := InstallArchPanel;
    InstallArchLabel.Top := ScaleY(8);
    InstallArchLabel.Left := ScaleX(10);
    InstallArchLabel.Width := (InstallArchPanel.ClientWidth / 2) - ScaleX(20);
    InstallArchLabel.Anchors := [akLeft, akTop, akRight];
    InstallArchLabel.WordWrap := True; // Must be set before Caption
    InstallArchLabel.Caption := CustomMessage('InstallArchitecture');
    InstallArchLabel.AdjustHeight();
    InstallArchLabel.TabStop := False;
    
    AdvancedInstallOptions_InstallArchCombo := TNewComboBox.Create(Form);
    AdvancedInstallOptions_InstallArchCombo.Parent := InstallArchPanel;
    AdvancedInstallOptions_InstallArchCombo.Top := ScaleY(8);
    AdvancedInstallOptions_InstallArchCombo.Left := (InstallArchPanel.ClientWidth / 2);
    AdvancedInstallOptions_InstallArchCombo.Width := (InstallArchPanel.ClientWidth / 2) - ScaleX(10);
    AdvancedInstallOptions_InstallArchCombo.Anchors := [akTop, akRight];
    AdvancedInstallOptions_InstallArchCombo.Style := csDropDownList;
    AdvancedInstallOptions_PopulateArchCombo(AdvancedInstallOptions_InstallArchCombo, True);
    AdvancedInstallOptions_InstallArchCombo.OnDropDown := @InstallArchCombo_OnDropdown;
    AdvancedInstallOptions_InstallArchCombo.Enabled := (AdvancedInstallOptions_ArchEditMode > 0);

    // Resize panel height based on total required height of contents
    InstallArchPanel.Height := InstallArchLabel.Top + InstallArchLabel.Height + ScaleY(10);
    
    PrevPanelBottom := InstallArchPanel.Top + InstallArchPanel.Height;
    
    #endif // ifndef ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH
    
    // Resize form height based on total required height of contents (including buttons)
    Form.ClientHeight := PrevPanelBottom + ScaleY(10) + ScaleY(23) + ScaleY(10);
    
    OKButton := TNewButton.Create(Form);
    OKButton.Parent := Form;
    OKButton.Caption := SetupMessage(msgButtonOK);
    OKButton.Left := Form.ClientWidth - ScaleX(75 + 6 + 75 + 10);
    OKButton.Top := Form.ClientHeight - ScaleY(23 + 10);
    OKButton.Height := ScaleY(23);
    OKButton.Anchors := [akRight, akBottom];
    OKButton.ModalResult := mrOk;
    OKButton.Default := True;

    CancelButton := TNewButton.Create(Form);
    CancelButton.Parent := Form;
    CancelButton.Caption := SetupMessage(msgButtonCancel);
    CancelButton.Left := Form.ClientWidth - ScaleX(75 + 10);
    CancelButton.Top := Form.ClientHeight - ScaleY(23 + 10);
    CancelButton.Height := ScaleY(23);
    CancelButton.Anchors := [akRight, akBottom];
    CancelButton.ModalResult := mrCancel;
    CancelButton.Cancel := True;

    W := Form.CalculateButtonWidth([OKButton.Caption, CancelButton.Caption]);
    OKButton.Width := W;
    CancelButton.Width := W;

    Form.KeepSizeY := True;
    Form.FlipSizeAndCenterIfNeeded(True, WizardForm, False);
    Form.ActiveControl := OKButton;

    if Form.ShowModal() = mrOk then
    begin
      #ifndef ADVANCEDOPTIONSFORM_NO_INSTALLMODES
      // Update install mode
      if PortableInstallRadio.Checked then begin
        SetCustomInstallMode(customInstallModePortable, AppName, AppVersion);
      end else if SideBySideInstallRadio.Checked then begin
        SetCustomInstallMode(customInstallModeSideBySide, AppName, AppVersion);
      end else begin
        SetCustomInstallMode(customInstallModeNormal, AppName, AppVersion);
      end;
      #endif
      #ifndef ADVANCEDOPTIONSFORM_NO_TARGETINSTALLARCH
      // Update target install architecture
      SelectedArch := AdvancedInstallOptions_InstallArchCombo.Items.Strings[AdvancedInstallOptions_InstallArchCombo.ItemIndex];
      SetTargetInstallArchitecture(SelectedArch);
      #endif
    end;
  finally
    Form.Free();
  end;
end;
