import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
import gradio as gr

has_gpu = torch.cuda.is_available()
print(f"GPU Available: {has_gpu}")

generator = None

if has_gpu:
    print("Loading model on GPU...")
    try:
        llama_model = AutoModelForCausalLM.from_pretrained(
            pretrained_model_name_or_path="aboonaji/llama2finetune-v2",
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=getattr(torch, "float16"),
                bnb_4bit_quant_type="nf4"
            ),
            device_map="auto"
        )
        llama_model.config.use_cache = False
        llama_model.config.pretraining_tp = 1

        llama_tokenizer = AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path="aboonaji/llama2finetune-v2",
            trust_remote_code=True
        )
        llama_tokenizer.pad_token = llama_tokenizer.eos_token
        llama_tokenizer.padding_side = "right"

        generator = pipeline(
            "text-generation",
            model=llama_model,
            tokenizer=llama_tokenizer,
            max_length=500
        )
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        generator = None
else:
    print("No GPU detected - model loading skipped")

def generate_response(prompt):
    if not has_gpu:
        return "GPU not available. Please upgrade Space hardware to T4 GPU."
    if generator is None:
        return "Model failed to load. Please check logs or restart the Space."
    if not prompt or prompt.strip() == "":
        return "Please enter a question."
    try:
        response = generator(f"<s>[INST] {prompt} [/INST]")[0]["generated_text"]
        return response.split("[/INST]")[-1].strip()
    except Exception as e:
        return f"Error generating response: {str(e)}"

gpu_status = "GPU detected - model ready" if has_gpu else "CPU only - GPU required"

with gr.Blocks(theme="soft") as demo:
    gr.Markdown("## MEDChat AI")
    gr.Markdown(f"**Status:** {gpu_status}")

    with gr.Row():
        prompt = gr.Textbox(lines=5, placeholder="Enter your medical question here...", scale=4)

    with gr.Row():
        submit_btn = gr.Button("Submit", variant="primary")
        clear_btn = gr.Button("Clear")

    response = gr.Textbox(label="Response", lines=10, interactive=False)

    gr.Examples(
        examples=[
            ["What does the immune system do?"],
            ["What is Epistaxis?"],
            ["Do our intestines contain germs?"],
            ["What are allergies?"],
            ["Should I start taking creatine?"],
            ["What are antibiotics?"],
            ["Why do I get sick?"],
            ["What's the difference between bacteria and viruses?"],
            ["Where are some places that germs hide?"],
        ],
        inputs=prompt
    )

    submit_btn.click(fn=generate_response, inputs=prompt, outputs=response)
    clear_btn.click(fn=lambda: ("", ""), outputs=[prompt, response])

if __name__ == "__main__":
    demo.launch()
