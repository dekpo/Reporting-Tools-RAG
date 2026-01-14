# PyInstaller Build Process

This document describes how to package the DTN Reporting Tools application into a standalone executable using PyInstaller.

## ⚠️ Important Notice

**The executable CANNOT run standalone!** You must distribute it with supporting files:
- Source files: `app.py`, `lib.py`, `pages/`
- Assets: `assets/`, `.streamlit/`
- Data: `chroma_db/`, `data_storage/`, `logs/`
- Model: `en_core_web_md/`

See the **[Distribution Package Structure](#distribution-package-structure)** section for complete details.

## Overview

The application is a Streamlit-based multi-page application that can be packaged as a Windows executable for easier distribution to users who don't have Python installed. The executable serves as a launcher that runs the Streamlit application without requiring Python to be installed on the end user's machine.

## Prerequisites

1. Python environment with all dependencies installed (see `requirements.txt`)
2. PyInstaller installed:
   ```bash
   pip install pyinstaller
   ```

## Build Process

### Step 1: Create Runner File

The first step is to create a runner file at the root of the project. This file serves as the entry point for PyInstaller and runs the Streamlit application in production mode.

**File name format:** `reporting-tools_v{VERSION}.py` (e.g., `reporting-tools_v2.8.py`)

**Purpose:** This naming convention embeds the version number in the executable name, making it easier to track different releases.

**File content:**

```python
import streamlit
import streamlit.web.cli as stcli
import os, sys


def resolve_path(path):
    resolved_path = os.path.abspath(os.path.join(os.getcwd(), path))
    return resolved_path


if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
```

**Key points:**
- `resolve_path()` ensures the app.py file is found relative to the executable location
- `--global.developmentMode=false` disables development features for production use
- The file invokes Streamlit's CLI programmatically instead of using command-line execution

### Step 2: Create PyInstaller Hooks

PyInstaller needs custom hooks to properly package metadata for certain dependencies (ChromaDB and Streamlit). Create a `hooks` directory with the following files:

#### File: `./hooks/hook-chromadb.py`

```python
from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("chromadb")
```

#### File: `./hooks/hook-streamlit.py`

```python
from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("streamlit")
```

**Purpose:** These hooks ensure that package metadata (version info, dependencies, etc.) for ChromaDB and Streamlit are included in the executable, preventing runtime errors related to missing metadata.

### Step 3: Run PyInstaller

Execute the following command from the project root:

```bash
pyinstaller --onefile --additional-hooks-dir=./hooks reporting-tools_v2.8.py --clean
```

**Command breakdown:**
- `--onefile` - Packages everything into a single executable file
- `--additional-hooks-dir=./hooks` - Points to our custom hooks directory
- `reporting-tools_v2.8.py` - The runner file created in Step 1
- `--clean` - Cleans PyInstaller cache and removes temporary files before building

**Output:**
This command generates:
- `build/` - Temporary build files (can be deleted after build)
- `dist/` - Contains the final executable: `reporting-tools_v2.8.exe`
- `reporting-tools_v2.8.spec` - PyInstaller specification file (needs editing - see Step 4)

### Step 4: Edit the .spec File

After running PyInstaller, a `.spec` file is generated (e.g., `reporting-tools_v2.8.spec`). This file needs to be manually edited to include all necessary data files and dependencies.

**Replace the entire contents** of the generated `.spec` file with the following configuration:

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

datas = [("./.venv/Lib/site-packages/streamlit/runtime", "./streamlit/runtime")]
datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")
datas += collect_data_files("streamlit_antd_components")
datas += copy_metadata("streamlit_antd_components")
datas += [("./.venv/Lib/site-packages/chromadb", "./chromadb")]
datas += collect_data_files("chromadb")
datas += copy_metadata("chromadb")
datas += [("./.venv/Lib/site-packages/posthog", "./posthog")]
datas += collect_data_files("posthog")
datas += copy_metadata("posthog")
datas += [("./.venv/Lib/site-packages/chromadb_rust_bindings", "./chromadb_rust_bindings")]
datas += [("./.venv/Lib/site-packages/backoff", "./backoff")]
datas += [("./.venv/Lib/site-packages/onnxruntime", "./onnxruntime")]
datas += [("./.venv/Lib/site-packages/langchain", "./langchain")]
datas += collect_data_files("langchain")
datas += copy_metadata("langchain")
datas += collect_data_files("matplotlib")
datas += copy_metadata("matplotlib")
datas += collect_data_files("seaborn")
datas += copy_metadata("seaborn")
datas += collect_data_files("plotly")
datas += copy_metadata("plotly")

block_cipher = None

a = Analysis(
    ['reporting-tools_v2.8.py'],  # UPDATE THIS to match your version
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=["streamlit_antd_components","docx2txt","pandas","webvtt","docx","spacy","openai","pyperclip","PyPDF2","langchain","chromadb","pandas","langchain_experimental.agents","langchain-experimental","langchain-openai","openpyxl","tabulate","matplotlib","seaborn","plotly","typing-extensions"],
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pkg_resources"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='reporting-tools_v2.8',  # UPDATE THIS to match your version
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

#### Key Configuration Sections:

**Data Files Collection:**
- Collects runtime files, metadata, and data for all required packages
- Includes: Streamlit, ChromaDB, LangChain, Plotly, Matplotlib, Seaborn, and their dependencies
- Special handling for packages with Rust bindings (chromadb_rust_bindings) and native libraries (onnxruntime)

**Hidden Imports:**
- Lists all modules that PyInstaller might not automatically detect
- Includes data processing libraries (pandas, openpyxl), document handlers (docx, PyPDF2), and AI/ML tools (openai, langchain, spacy)

**Analysis Configuration:**
- `pathex=["."]` - Searches current directory for imports
- `hookspath=['./hooks']` - Uses our custom hooks from Step 2
- `excludes=["pkg_resources"]` - Excludes problematic package to avoid conflicts

**EXE Configuration:**
- `console=True` - Shows console window (useful for debugging; set to False for production if desired)
- `upx=True` - Compresses the executable using UPX
- `debug=False` - Production mode without debug output

#### Important: Version Updates

When creating a new version, update these two lines:
1. Line in `Analysis()`: `['reporting-tools_v2.8.py']` → Update to your version
2. Line in `EXE()`: `name='reporting-tools_v2.8'` → Update to your version

### Step 5: Final Build

After editing the `.spec` file, run PyInstaller again using the spec file:

```bash
pyinstaller reporting-tools_v2.8.spec --clean
```

This will generate the final executable in the `dist/` folder: `reporting-tools_v2.8.exe`

**Expected build time:** 5-15 minutes depending on your system (the executable will be several hundred MB due to all bundled dependencies)

---

## Testing the Executable

After building, perform these tests:

1. **Local Test (Development Machine):**
   ```bash
   cd dist
   .\reporting-tools_v2.8.exe
   ```
   The application should launch and open in your default browser.

2. **Clean Machine Test (Recommended):**
   - Copy the executable to a machine without Python installed
   - Run the executable
   - Verify all features work correctly (file uploads, AI processing, export, etc.)

3. **Check for Missing Dependencies:**
   - Watch the console output for error messages
   - Test all application pages and features
   - Verify database operations (ChromaDB)
   - Test document processing capabilities

---

## Troubleshooting

### Common Issues and Solutions

**Issue: "Module not found" errors**
- **Solution:** Add the missing module to `hiddenimports` in the `.spec` file, then rebuild

**Issue: Executable crashes on startup**
- **Solution:** Run with `console=True` to see error messages
- Check if all data files are properly collected in the `datas` section

**Issue: ChromaDB errors**
- **Solution:** Ensure `chromadb_rust_bindings` folder is included in datas
- Verify the hooks are being loaded correctly

**Issue: Streamlit runtime errors**
- **Solution:** Verify the streamlit runtime folder path in datas matches your environment
- Check that `streamlit/runtime` files are bundled

**Issue: Very large executable size**
- **Solution:** This is expected (500MB-1GB+) due to:
  - ML models (spaCy, ChromaDB)
  - Multiple plotting libraries
  - LangChain and AI dependencies
- Consider using `--onedir` instead of `--onefile` if size is critical (creates a folder with multiple files)

---

## Version Control Best Practices

### Main Branch - Development Files

Files to commit to the main branch:
- ✅ `reporting-tools_v{VERSION}.py` (runner file)
- ✅ `reporting-tools_v{VERSION}.spec` (spec file)
- ✅ `hooks/` directory
- ✅ `PyInstaller_Process.md` (this documentation)
- ✅ All source code (`app.py`, `lib.py`, `pages/`, etc.)

### Files to Exclude (already in `.gitignore`):
- ❌ `build/` directory
- ❌ `dist/` directory
- ❌ Large binary files (executable)
- ❌ Database files that are user-generated
- ❌ `.streamlit/secrets.toml` (contains sensitive API keys)

### Branch Strategy for Releases

Consider using an **`exe` branch** for distributing pre-built packages:

1. **Main branch**: Source code, build scripts, documentation
2. **Exe branch**: Could contain release notes, download links, or checksums
   - Do NOT commit the large exe or distribution packages directly to Git
   - Instead, use GitHub Releases to host the distribution ZIP files
   - The exe branch can contain release metadata and instructions

**Recommended workflow:**
```bash
# Build on main branch
git checkout main
# ... perform build process ...

# Create distribution package
# ... copy files as per Distribution Package Structure ...

# Create GitHub Release (preferred over committing binaries)
# Upload the distribution ZIP to GitHub Releases with version tag

# Or use exe branch for release metadata
git checkout -b exe
# Add release notes, checksums, version info
git add RELEASES.md
git commit -m "Release v2.8 metadata"
git push origin exe
```

---

## Distribution Package Structure

⚠️ **CRITICAL:** The executable alone is NOT sufficient to run the application. You must distribute it with the following files and folders:

### Required Files and Folders

The following must be placed in the **same directory** as the `.exe` file:

```
reporting-tools_v2.8.exe          # The compiled executable
app.py                             # Main Streamlit application
lib.py                             # Library/helper functions
pages/                             # Streamlit pages directory
  ├── 00_home.py
  ├── 01_anonymize.py
  ├── 02_chatgpt.py
  ├── 03_revert.py
  └── 04_help.py
assets/                            # Application assets
  ├── ceb-logo-blue.svg
  ├── ceb-logo-full-text-blue.svg
  ├── css/
  │   └── style.css
  └── favicon.ico
chroma_db/                         # ChromaDB vector database
  └── (all database files)
data_storage/                      # Application data storage
  └── (runtime data files)
logs/                              # Application logs directory
  └── (log files - can be empty initially)
.streamlit/                        # Streamlit configuration
  └── (config files - ensure secrets.toml is excluded if it contains sensitive data)
en_core_web_md/                    # spaCy language model
  └── (all model files)
```

### Creating the Distribution Package

1. **After successful build**, navigate to the `dist/` folder
2. **Copy the executable** to a new distribution folder
3. **Copy all required files and folders** (listed above) to the same location
4. **Verify the structure** matches the layout above

**Example PowerShell commands:**

```powershell
# Create distribution folder
mkdir DTN-Reporting-Tools-v2.8

# Copy the executable
copy dist\reporting-tools_v2.8.exe DTN-Reporting-Tools-v2.8\

# Copy all required files and folders
copy app.py DTN-Reporting-Tools-v2.8\
copy lib.py DTN-Reporting-Tools-v2.8\
xcopy /E /I pages DTN-Reporting-Tools-v2.8\pages
xcopy /E /I assets DTN-Reporting-Tools-v2.8\assets
xcopy /E /I chroma_db DTN-Reporting-Tools-v2.8\chroma_db
xcopy /E /I data_storage DTN-Reporting-Tools-v2.8\data_storage
xcopy /E /I logs DTN-Reporting-Tools-v2.8\logs
xcopy /E /I .streamlit DTN-Reporting-Tools-v2.8\.streamlit
xcopy /E /I en_core_web_md DTN-Reporting-Tools-v2.8\en_core_web_md

# Optional: Remove sensitive files
del DTN-Reporting-Tools-v2.8\.streamlit\secrets.toml
```

### Why These Files Are Required

- **`app.py` and `lib.py`**: Core application logic that Streamlit loads
- **`pages/`**: Multi-page Streamlit app structure
- **`assets/`**: UI resources (logos, CSS, favicon)
- **`chroma_db/`**: Vector database for RAG (Retrieval Augmented Generation)
- **`data_storage/`**: Runtime data and user uploads
- **`logs/`**: Application logging output
- **`.streamlit/`**: Streamlit configuration (themes, settings)
- **`en_core_web_md/`**: spaCy's English language model for NLP processing

### Distribution Best Practices

1. **Compress for Transfer:**
   - Zip the entire distribution folder
   - Expected size: 1-2 GB (compressed: 400-800 MB)
   - The package compresses well due to model files

2. **Include Documentation:**
   - User guide or README
   - System requirements (Windows 10/11, 64-bit)
   - Known limitations
   - Installation instructions (just extract and run)

3. **Security Considerations:**
   - **IMPORTANT:** Remove `.streamlit/secrets.toml` if it contains API keys or sensitive data
   - Consider adding a template `secrets.toml.example` with placeholder values
   - Some antivirus software may flag PyInstaller executables - this is a false positive

4. **End User Instructions:**
   ```
   1. Extract the entire ZIP file to a folder
   2. Double-click reporting-tools_v2.8.exe
   3. The application will open in your default browser
   4. To close: Close the console window or press Ctrl+C
   ```

5. **Updates:**
   - Users need to download and replace the entire folder for updates
   - Database and logs can be preserved between versions (copy them over)

---

## Quick Reference - Complete Build & Distribution Process

```bash
# 1. Ensure all dependencies are installed
pip install -r requirements.txt
pip install pyinstaller

# 2. Initial build to generate .spec file
pyinstaller --onefile --additional-hooks-dir=./hooks reporting-tools_v2.8.py --clean

# 3. Edit the .spec file (see Step 4 above)

# 4. Final build with customized .spec
pyinstaller reporting-tools_v2.8.spec --clean

# 5. Create distribution package
mkdir DTN-Reporting-Tools-v2.8
copy dist\reporting-tools_v2.8.exe DTN-Reporting-Tools-v2.8\
copy app.py DTN-Reporting-Tools-v2.8\
copy lib.py DTN-Reporting-Tools-v2.8\
xcopy /E /I pages DTN-Reporting-Tools-v2.8\pages
xcopy /E /I assets DTN-Reporting-Tools-v2.8\assets
xcopy /E /I chroma_db DTN-Reporting-Tools-v2.8\chroma_db
xcopy /E /I data_storage DTN-Reporting-Tools-v2.8\data_storage
xcopy /E /I logs DTN-Reporting-Tools-v2.8\logs
xcopy /E /I .streamlit DTN-Reporting-Tools-v2.8\.streamlit
xcopy /E /I en_core_web_md DTN-Reporting-Tools-v2.8\en_core_web_md

# 6. Remove sensitive files (if any)
del DTN-Reporting-Tools-v2.8\.streamlit\secrets.toml

# 7. Test the complete package
cd DTN-Reporting-Tools-v2.8
.\reporting-tools_v2.8.exe

# 8. Create distribution ZIP
# Right-click folder → Send to → Compressed (zipped) folder
# Or use PowerShell:
Compress-Archive -Path DTN-Reporting-Tools-v2.8 -DestinationPath DTN-Reporting-Tools-v2.8.zip
```

---

## Notes

- Build artifacts (`build/`, `dist/`) are excluded from version control via `.gitignore`
- The `hooks/` directory should be committed to the repository for reproducible builds
- Always test the executable on a clean machine without Python installed to ensure all dependencies are properly bundled
- Build time increases significantly with each compilation due to the large number of dependencies
