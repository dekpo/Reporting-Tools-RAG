# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

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

# Collect ONLY plotly.graph_objs submodules (all chart types) - targeted, not the entire plotly package
plotly_graph_objs_hidden = collect_submodules('plotly.graph_objs')

# Add metadata for visualization dependencies (PIL is imported as PIL but packaged as Pillow)
datas += copy_metadata("Pillow")
datas += copy_metadata("kiwisolver")
datas += copy_metadata("pyparsing")

block_cipher = None

a = Analysis(
    ['reporting-tools_v2.8.py'],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "streamlit_antd_components","docx2txt","pandas","webvtt","docx","spacy","openai","pyperclip","PyPDF2",
        "langchain","chromadb","langchain_experimental.agents","langchain-experimental","langchain-openai",
        "openpyxl","tabulate","typing-extensions",
        # Matplotlib and PIL imports
        "matplotlib","matplotlib.pyplot","matplotlib.backends","matplotlib.backends.backend_agg",
        "seaborn","PIL","PIL.Image",
        # Plotly - main modules + ALL graph_objs chart types
        "plotly","plotly.express","plotly.graph_objects","plotly.io","plotly.subplots",
    ] + plotly_graph_objs_hidden,  # Add ALL plotly.graph_objs submodules
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
    name='reporting-tools_v2.8',
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
