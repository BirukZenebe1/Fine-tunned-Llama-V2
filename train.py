"""
Training script for fine-tuning Llama 2 on medical terminology data.

Supports:
- LoRA-based parameter-efficient fine-tuning
- 4-bit quantization for memory efficiency
- Checkpoint saving and resumption
- WandB experiment tracking
- Configurable hyperparameters via CLI arguments
"""

import argparse
import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig
from trl import SFTTrainer


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune Llama 2 on medical data")
    parser.add_argument(
        "--model_name",
        type=str,
        default="aboonaji/llama2finetune-v2",
        help="Pre-trained model name or path",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="aboonaji/wiki_medical_terms_llam2_format",
        help="Training dataset name or path",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./results",
        help="Directory to save model checkpoints",
    )
    parser.add_argument("--max_steps", type=int, default=300, help="Max training steps")
    parser.add_argument("--batch_size", type=int, default=1, help="Training batch size per device")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--warmup_steps", type=int, default=30, help="Warmup steps for scheduler")
    parser.add_argument("--lora_r", type=int, default=32, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=64, help="LoRA alpha scaling factor")
    parser.add_argument("--lora_dropout", type=float, default=0.05, help="LoRA dropout")
    parser.add_argument("--max_seq_length", type=int, default=512, help="Max sequence length for training")
    parser.add_argument("--logging_steps", type=int, default=10, help="Logging frequency")
    parser.add_argument("--save_steps", type=int, default=50, help="Checkpoint save frequency")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--use_wandb", action="store_true", help="Enable WandB logging")
    parser.add_argument("--wandb_run_name", type=str, default="medical-llama2-finetuning", help="WandB run name")
    parser.add_argument("--resume_from_checkpoint", type=str, default=None, help="Resume from checkpoint path")
    return parser.parse_args()


def load_model_and_tokenizer(model_name):
    """Load the base model with 4-bit quantization and its tokenizer."""
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        pretrained_model_name_or_path=model_name,
        quantization_config=quantization_config,
        device_map="auto",
    )
    model.config.use_cache = False
    model.config.pretraining_tp = 1

    tokenizer = AutoTokenizer.from_pretrained(
        pretrained_model_name_or_path=model_name,
        trust_remote_code=True,
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    return model, tokenizer


def create_training_args(args):
    """Create training arguments from CLI args."""
    report_to = "wandb" if args.use_wandb else "none"

    return TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_steps=args.max_steps,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        logging_steps=args.logging_steps,
        logging_first_step=True,
        save_steps=args.save_steps,
        save_total_limit=3,
        fp16=True,
        optim="paged_adamw_32bit",
        lr_scheduler_type="cosine",
        report_to=report_to,
        run_name=args.wandb_run_name if args.use_wandb else None,
    )


def create_lora_config(args):
    """Create LoRA configuration from CLI args."""
    return LoraConfig(
        task_type="CAUSAL_LM",
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )


def main():
    args = parse_args()
    print(f"=== Medical LLM Fine-Tuning ===")
    print(f"Model: {args.model_name}")
    print(f"Dataset: {args.dataset}")
    print(f"Output: {args.output_dir}")
    print(f"Max steps: {args.max_steps}")
    print(f"LoRA rank: {args.lora_r}, alpha: {args.lora_alpha}")
    print()

    # Load model and tokenizer
    print("Loading model and tokenizer...")
    model, tokenizer = load_model_and_tokenizer(args.model_name)

    # Load dataset
    print("Loading dataset...")
    dataset = load_dataset(path=args.dataset, split="train")
    print(f"Dataset size: {len(dataset)} samples")

    # Create configs
    training_args = create_training_args(args)
    lora_config = create_lora_config(args)

    # Create trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
    )

    # Train
    print("Starting training...")
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)

    # Save final model
    final_path = os.path.join(args.output_dir, "final_model")
    print(f"Saving final model to {final_path}...")
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)

    print("Training complete!")


if __name__ == "__main__":
    main()
