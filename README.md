# MEDChat AI

A medical Q&A chatbot powered by a fine-tuned Llama 2 model with conversation memory, secure authentication, and free-tier deployment support.

> **Note:** GPU is required for training. Inference can run on CPU (slow) or GPU.

## Features

- **Conversation Memory** - Multi-turn chat with per-user history persistence
- **Secure Authentication** - bcrypt password hashing with JSON-file storage
- **Fine-tuned LLM** - Llama 2 fine-tuned on medical terminology via LoRA
- **4-bit Quantization** - Runs on consumer GPUs with ~4GB VRAM
- **Free-tier Deployment** - Docker and HuggingFace Spaces ready

## Project Structure

```
├── app.py              # Main Gradio web application
├── auth.py             # User authentication (bcrypt + JSON persistence)
├── memory.py           # Conversation memory management
├── train.py            # Model fine-tuning script
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container deployment
├── docker-compose.yml  # One-command deployment
├── .gitignore
└── copy_of_llm.py      # Original Colab script (legacy)
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

**With GPU (recommended):**
```bash
python app.py --share
```

**CPU-only (slow, for testing):**
```bash
python app.py --cpu --share
```

**With a local fine-tuned model:**
```bash
python app.py --model_path ./results/final_model --share
```

### 3. Open the Web UI

The app launches at `http://localhost:7860`. Use `--share` for a public URL.

## Training

Fine-tune the model on medical data with improved hyperparameters:

```bash
# Basic training
python train.py

# Custom training with all options
python train.py \
  --max_steps 500 \
  --lora_r 32 \
  --lora_alpha 64 \
  --learning_rate 2e-4 \
  --gradient_accumulation_steps 4 \
  --save_steps 50 \
  --use_wandb

# Resume from checkpoint
python train.py --resume_from_checkpoint ./results/checkpoint-100
```

### Training Improvements over Original

| Parameter | Original | Improved |
|-----------|----------|----------|
| Max steps | 100 | 300 (configurable) |
| LoRA rank | 16 | 32 |
| LoRA alpha | 16 | 64 |
| LoRA dropout | 0.1 | 0.05 |
| Gradient accumulation | 1 | 4 |
| Optimizer | default | paged_adamw_32bit |
| LR scheduler | default | cosine |
| Warmup steps | 0 | 30 |
| Double quantization | No | Yes |
| Checkpoint saving | No | Every 50 steps |
| LoRA target modules | default | q,k,v,o projections |

## Deployment

### Docker (Free-tier compatible)

```bash
# Build and run
docker-compose up --build

# Or manually
docker build -t medchat .
docker run -p 7860:7860 -v medchat-data:/app/data medchat
```

### HuggingFace Spaces

1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces) with **Gradio** SDK
2. Upload `app.py`, `auth.py`, `memory.py`, and `requirements.txt`
3. The Space will auto-build and deploy

### Railway / Render (Free Tier)

Use the included `Dockerfile` - both platforms auto-detect and build from it.

## CLI Options

```
python app.py --help

  --model_path   Model name or local path (default: aboonaji/llama2finetune-v2)
  --max_length   Max generation tokens (default: 512)
  --port         Server port (default: 7860)
  --share        Create public Gradio link
  --cpu          Force CPU-only mode
```

## Technologies

- Python / PyTorch
- Hugging Face Transformers + PEFT + TRL
- Gradio (Web UI)
- bcrypt (Authentication)
- Docker (Deployment)

## Disclaimer

MEDChat AI is for **educational and informational purposes only**. Always consult a qualified healthcare professional for medical advice, diagnosis, or treatment.
