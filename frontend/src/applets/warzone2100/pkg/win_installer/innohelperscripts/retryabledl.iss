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
// Script to assist in downloading with a TDownloadWizardPage in a retryable manner,
// also supporting a list of URLs (mirrors)
//
// Requires:
// - Innosetup 6.2+(?) (tested with 6.4.3)
//

[Code]
type
  TStringArray = array of String;
  RetryableDownloadResult = (DL_Success, DL_AbortedByUser, DL_RetryCancelledByUser, DL_ExhaustedMaxRetries);

function RetryableDownload(DownloadPage: TDownloadWizardPage; URLs: TStringArray; BaseName: String; RequiredSHA256OfFile: String; MaxRetries: Integer; DownloadErrorRetryTitle, DownloadErrorRetryPrompt: String): RetryableDownloadResult;
var
  DLRetryNum: Integer;
  DLURLNum: Integer;
begin
  DLRetryNum := 0;
  DLURLNum := 0;
  if GetArrayLength(URLs) = 0 then
  begin
    RaiseException('No URLs provided');
    Exit;
  end;
  repeat
    DownloadPage.Clear
    DownloadPage.Add(URLs[DLURLNum], BaseName, RequiredSHA256OfFile);
    try
      DownloadPage.Download; // This downloads the files to {tmp}
      // Success!
      Result := DL_Success;
      Exit; // return from the function
    except
      if DownloadPage.AbortedByUser then
      begin
        Log('Download aborted by user: ' + BaseName);
        Result := DL_AbortedByUser;
        Exit; // return from the function
      end
      else begin
        // Download failure
        Log(AddPeriod(GetExceptionMessage));
        if (DLURLNum + 1) < GetArrayLength(URLs) then
        begin
          // Try the next URL
          DLURLNum := DLURLNum + 1;
        end
        else begin
          if DLRetryNum >= MaxRetries then begin
            Log('Exhausted max download retries for: ' + BaseName);
            Result := DL_ExhaustedMaxRetries;
            Exit; // return from the function
          end;
          DLRetryNum := DLRetryNum + 1;
          // All URLs have been exhausted - prompt to retry
          case SuppressibleTaskDialogMsgBox(
              DownloadErrorRetryTitle,
              DownloadErrorRetryPrompt,
              mbError, MB_RETRYCANCEL, [], 0, IDCANCEL)
            of
            IDRETRY: begin
              // Retry, starting with URLs[0]
              DLURLNum := 0;
            end;
            IDCANCEL: begin
              Result := DL_RetryCancelledByUser;
              Exit; // return from the function
            end;
          end; // case SuppressibleTaskDialogMsgBox
        end; // if
      end;
    end;
  until False;
  Result := DL_ExhaustedMaxRetries;
end;