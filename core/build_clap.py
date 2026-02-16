"""
Build script for clap_native.c → clap_native.dll
Tries MSVC (cl.exe) first, then MinGW (gcc), then TCC (tcc).
"""
import subprocess
import sys
import shutil
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "clap_native.c"
OUT = HERE / "clap_native.dll"


def try_msvc():
    """Try building with MSVC cl.exe."""
    cl = shutil.which("cl")
    if not cl:
        return False
    try:
        result = subprocess.run(
            ["cl", "/O2", "/LD", "/Fe:" + str(OUT), str(SRC)],
            cwd=str(HERE), capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and OUT.exists():
            print(f"✅ Built with MSVC: {OUT}")
            # Clean up .obj and .lib files
            for ext in [".obj", ".lib", ".exp"]:
                f = HERE / f"clap_native{ext}"
                if f.exists():
                    f.unlink()
            return True
        print(f"MSVC failed: {result.stderr}")
    except Exception as e:
        print(f"MSVC error: {e}")
    return False


def try_gcc():
    """Try building with MinGW gcc."""
    gcc = shutil.which("gcc")
    if not gcc:
        return False
    try:
        result = subprocess.run(
            ["gcc", "-O2", "-shared", "-o", str(OUT), str(SRC), "-lm"],
            cwd=str(HERE), capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and OUT.exists():
            print(f"✅ Built with GCC: {OUT}")
            return True
        print(f"GCC failed: {result.stderr}")
    except Exception as e:
        print(f"GCC error: {e}")
    return False


def try_tcc():
    """Try building with TCC (Tiny C Compiler)."""
    tcc = shutil.which("tcc")
    if not tcc:
        return False
    try:
        result = subprocess.run(
            ["tcc", "-shared", "-o", str(OUT), str(SRC), "-lm"],
            cwd=str(HERE), capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and OUT.exists():
            print(f"✅ Built with TCC: {OUT}")
            return True
        print(f"TCC failed: {result.stderr}")
    except Exception as e:
        print(f"TCC error: {e}")
    return False


if __name__ == "__main__":
    print(f"Building {SRC.name} → {OUT.name} ...")
    
    if OUT.exists():
        OUT.unlink()
    
    if try_msvc() or try_gcc() or try_tcc():
        print("🎉 Build successful!")
        sys.exit(0)
    else:
        print("❌ No C compiler found. Install one of:")
        print("   - Visual Studio Build Tools (cl.exe)")
        print("   - MinGW-w64 (gcc)")
        print("   - TCC (tcc)")
        print("")
        print("The clap detector will fall back to pure Python mode.")
        sys.exit(1)
