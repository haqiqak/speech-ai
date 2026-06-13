# run_app.ps1 - launch Speech AI from a plain PowerShell terminal.
# Running outside VS Code frees ~1 GB of RAM, which the heavy ASR model needs.
#
#   How to use:
#     1. Close VS Code completely.
#     2. Open Windows Terminal / PowerShell (NOT inside VS Code).
#     3. Run:   L:\speech-ai\run_app.ps1
#        (or, if blocked by execution policy:
#           powershell -ExecutionPolicy Bypass -File L:\speech-ai\run_app.ps1 )

$ErrorActionPreference = "Stop"
Set-Location "L:\speech-ai"

$os = Get-CimInstance Win32_OperatingSystem
"Free RAM: {0:N0} MB / {1:N0} MB total" -f ($os.FreePhysicalMemory / 1KB), ($os.TotalVisibleMemorySize / 1KB)
"Launching Speech AI...  (first mic recording downloads CrisperWhisper, about 3 GB - be patient)"
""

& "L:\speech-ai\.venv313\Scripts\python.exe" -m streamlit run app.py
