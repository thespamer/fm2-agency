$env:OLLAMA_HOST = "http://127.0.0.1:11434"
$env:FM2_MODEL = "ollama/qwen3:14b-ctx8k"
uvicorn fm2_agency.server:app --port 8765
python -m fm2_agency.run_cli "Plano de conteudo para canal de IA local para CTOs"