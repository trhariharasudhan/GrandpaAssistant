$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$pythonExe = @(
    (Join-Path $repoRoot ".python311\python.exe"),
    (Join-Path $repoRoot ".venv\Scripts\python.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $pythonExe) {
    throw "No local Python runtime was found. Install Python 3.11 into the workspace or restore the project virtual environment first."
}

$ollamaExe = if (Test-Path "C:\Users\ASUS\AppData\Local\Programs\Ollama\ollama.exe") {
    "C:\Users\ASUS\AppData\Local\Programs\Ollama\ollama.exe"
} else {
    "ollama"
}

Write-Host "Upgrading pip in the project virtual environment..."
& $pythonExe -m pip install --upgrade pip

Write-Host "Installing required Python libraries..."
& $pythonExe -m pip install fastapi uvicorn requests opencv-python pytesseract sentence-transformers faiss-cpu vaderSentiment transformers

try {
    & $pythonExe -m pip install fasttext
} catch {
    Write-Warning "fasttext build failed on Windows. Falling back to fasttext-wheel."
    & $pythonExe -m pip install fasttext-wheel
}

Write-Host "Installing optional offline voice packages..."
& $pythonExe -m pip install openai-whisper piper-tts

Write-Host "Pulling Ollama models for the local assistant..."
& $ollamaExe pull mistral:7b
& $ollamaExe pull phi3:mini
& $ollamaExe pull deepseek-coder:6.7b

Write-Host "Pre-downloading sentence-transformers and IndicBERT assets..."
@'
from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoTokenizer

SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
AutoTokenizer.from_pretrained("ai4bharat/IndicBERTv2-MLM-only")
AutoModel.from_pretrained("ai4bharat/IndicBERTv2-MLM-only")

print("Cached sentence-transformers/all-MiniLM-L6-v2")
print("Cached ai4bharat/IndicBERTv2-MLM-only")
'@ | & $pythonExe -

Write-Host "Pre-downloading Whisper base for offline speech-to-text..."
@'
import whisper

whisper.load_model("base")
print("Cached Whisper base")
'@ | & $pythonExe -

Write-Host "Installed Ollama models:"
& $ollamaExe list
