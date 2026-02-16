
import subprocess
import time

def debug_focus():
    print("Attempting to focus Spotify via PowerShell...")
    ps_script = """
    $proc = Get-Process spotify -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($proc) {
        Write-Host "Found Process: $($proc.ProcessName) ID: $($proc.Id)"
        $hwnd = $proc.MainWindowHandle
        Write-Host "Window Handle: $hwnd"
        
        if ($hwnd -ne 0) {
            $wshell = New-Object -ComObject wscript.shell
            $success = $wshell.AppActivate($proc.Id)
            Write-Host "AppActivate Result: $success"
        } else {
            Write-Host "No Main Window Handle found (Minimzed to tray?)"
        }
    } else {
        Write-Host "Process 'spotify' not found."
    }
    """
    result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

if __name__ == "__main__":
    debug_focus()
