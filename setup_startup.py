"""
Add Jarvis to Windows Startup.
Creates a shortcut in the Windows Startup folder so Jarvis launches on boot.
Run once: python setup_startup.py
"""
import os
import sys
from pathlib import Path

def create_startup_shortcut():
    """Create a .vbs launcher in Windows Startup folder."""

    # Paths
    project_dir = Path(__file__).parent.resolve()
    python_exe = project_dir / ".venv" / "Scripts" / "pythonw.exe"
    main_py = project_dir / "main.py"

    # Use regular python.exe if pythonw doesn't exist
    if not python_exe.exists():
        python_exe = project_dir / ".venv" / "Scripts" / "python.exe"

    if not python_exe.exists():
        print("❌ Python virtual environment not found!")
        print(f"   Expected at: {python_exe}")
        return False

    # Windows Startup folder
    startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    if not startup_folder.exists():
        print(f"❌ Startup folder not found: {startup_folder}")
        return False

    # Create a VBS script that launches Jarvis silently (no console window)
    vbs_path = startup_folder / "Jarvis_AI.vbs"

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{project_dir}"
WshShell.Run """{python_exe}"" ""{main_py}""", 0, False
'''

    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    # Create a Desktop shortcut as well
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    desktop_shortcut = desktop / "Jarvis AI.lnk"
    
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(desktop_shortcut))
        shortcut.TargetPath = str(python_exe)
        shortcut.Arguments = f'"{main_py}"'
        # Run minimized/no-console if possible, though shortcut directly to pythonw should be silent
        shortcut.WorkingDirectory = str(project_dir)
        shortcut.IconLocation = str(project_dir / "assets" / "icon.ico")
        shortcut.Save()
        print(f"✅ Desktop shortcut created: {desktop_shortcut}")
    except Exception as e:
        print(f"⚠️ Could not create desktop shortcut (requires pywin32): {e}")
        # Fallback: Create a batch file on desktop if pywin32 fails
        bat_path = desktop / "Jarvis AI.bat"
        with open(bat_path, "w") as f:
            f.write(f'@echo off\ncd /d "{project_dir}"\nstart "" "{python_exe}" "{main_py}"')
        print(f"📝 Created batch file on Desktop instead: {bat_path}")

    print("=" * 50)
    print("✅ Jarvis added to Windows Startup!")
    print(f"   Startup Script: {vbs_path}")
    print(f"   Python:   {python_exe}")
    print(f"   Project:  {project_dir}")
    print()
    print("   Jarvis will now start automatically when")
    print("   you log into Windows.")
    print()
    print("   To remove: run this script with --remove")
    print("=" * 50)
    return True


def remove_startup_shortcut():
    """Remove Jarvis from Windows Startup."""
    startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    vbs_path = startup_folder / "Jarvis_AI.vbs"

    if vbs_path.exists():
        vbs_path.unlink()
        print("✅ Jarvis removed from Windows Startup.")
    else:
        print("ℹ️ Jarvis was not in Startup.")


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove_startup_shortcut()
    else:
        create_startup_shortcut()
