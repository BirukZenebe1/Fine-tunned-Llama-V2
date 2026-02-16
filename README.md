# MEDChat AI (LLaMA 2 Medical Chatbot)

Minimal baseline version of the project, restored to the original structure.

## Project Scope

This repository intentionally contains only:

- `LLM.py`: Colab-exported script used for loading/fine-tuning and launching the chatbot UI
- `requirements.txt`: Python dependencies for the script
- `README.md`: Project documentation

## Quick Start

1. Create and activate a Python environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the script:
   ```bash
   python LLM.py
   ```

Note: `LLM.py` was originally exported from Google Colab and still includes notebook-style install commands (`!pip ...`). If you run locally as plain Python, remove/comment those lines first.

## Model and Data

- Base/fine-tuned model: `aboonaji/llama2finetune-v2`
- Training dataset used in script: `aboonaji/wiki_medical_terms_llam2_format`
- Fine-tuning method in script: LoRA with TRL `SFTTrainer`

## Disclaimer

For educational use only. This is not medical advice and should not replace professional healthcare guidance.
