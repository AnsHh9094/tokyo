"""
Build Tokyo AI into a single .exe with all dependencies and data files.
Run: python build_exe.py
"""
import PyInstaller.__main__
import shutil
from pathlib import Path

def build():
    print("🚀 Building Tokyo AI Executable...")
    
    # Clean previous builds
    shutil.rmtree('build', ignore_errors=True)
    shutil.rmtree('dist', ignore_errors=True)
    
    PyInstaller.__main__.run([
        'main.py',
        '--onefile',
        '--noconsole',
        '--name=Jarvis',
        '--icon=assets/icon.ico',
        # Data files
        '--add-data=assets;assets',
        '--add-data=core/templates;core/templates',
        '--add-data=core/prompt.txt;core',
        '--add-data=config;config',
        '--add-data=vosk-model-small-en-us-0.15;vosk-model-small-en-us-0.15',
        '--add-data=memory;memory',
        '--add-data=actions;actions',
        '--clean',
        # Hidden imports (all modules that PyInstaller can't auto-detect)
        '--hidden-import=PIL',
        '--hidden-import=tkinter',
        '--hidden-import=sounddevice',
        '--hidden-import=numpy',
        '--hidden-import=vosk',
        '--hidden-import=flask',
        '--hidden-import=flask_cors',
        '--hidden-import=edge_tts',
        '--hidden-import=speech_recognition',
        '--hidden-import=aiohttp',
        '--hidden-import=engineio.async_drivers.threading',
        '--hidden-import=core.audio_hub',
        '--hidden-import=core.clap',
        '--hidden-import=core.wake_word',
        '--hidden-import=core.speech_to_text',
        '--hidden-import=core.llm',
        '--hidden-import=core.tts',
        '--hidden-import=core.server',
        '--hidden-import=core.browser',
        # Collect all vosk data
        '--collect-all=vosk',
    ])
    
    print("\n✅ Build Complete! → dist/Jarvis.exe")

if __name__ == "__main__":
    build()
