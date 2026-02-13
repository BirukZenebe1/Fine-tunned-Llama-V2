"""
MEDChat AI - Medical Chatbot Application

A Gradio-based web application powered by a fine-tuned Llama 2 model
for medical question-answering with:
- Conversation memory (multi-turn context)
- Persistent user authentication (bcrypt + JSON)
- Configurable model loading (local checkpoint or HuggingFace Hub)
"""

import argparse
import os
import torch
import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline

from auth import signup, login
from memory import ConversationMemory

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
generator = None
memory = ConversationMemory(persist=True)


def parse_args():
    parser = argparse.ArgumentParser(description="MEDChat AI Application")
    parser.add_argument(
        "--model_path",
        type=str,
        default="aboonaji/llama2finetune-v2",
        help="Model name on HuggingFace Hub or local path to fine-tuned checkpoint",
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=512,
        help="Maximum generation length in tokens",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to serve the application on",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public Gradio share link",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU-only mode (slow, for testing without GPU)",
    )
    return parser.parse_args()


def load_model(model_path, max_length, cpu_only=False):
    """Load the model and create the text-generation pipeline."""
    global generator

    if cpu_only:
        print("Loading model in CPU-only mode (slow)...")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            device_map="cpu",
            low_cpu_mem_usage=True,
        )
    else:
        print("Loading model with 4-bit quantization...")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quantization_config,
            device_map="auto",
        )

    model.config.use_cache = True  # Enable KV cache for inference

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_length=max_length,
    )
    print("Model loaded successfully.")


# ---------------------------------------------------------------------------
# Chat logic with memory
# ---------------------------------------------------------------------------
def generate_response(message, username):
    """Generate a response using conversation history for context."""
    if generator is None:
        return "Model is still loading. Please try again shortly."

    prompt = memory.build_prompt(username, message)
    raw = generator(prompt)[0]["generated_text"]

    # Extract only the new assistant response (after the last [/INST])
    if "[/INST]" in raw:
        response = raw.split("[/INST]")[-1].strip()
    else:
        response = raw.strip()

    # Remove trailing </s> tokens
    response = response.replace("</s>", "").strip()

    # Store the turn in memory
    memory.add_turn(username, message, response)

    return response


# ---------------------------------------------------------------------------
# Gradio UI handlers
# ---------------------------------------------------------------------------
def handle_signup(username, password):
    success, msg = signup(username, password)
    return msg


def handle_login(username, password):
    success, msg = login(username, password)
    if success:
        memory.load_history(username)
        chat_history = memory.get_display_history(username)
        return (
            gr.update(visible=True),   # Show chat UI
            gr.update(visible=False),  # Hide login UI
            "",                         # Clear login message
            gr.update(selected=3),     # Switch to Chat tab
            username,                   # Store username in state
            chat_history,               # Load existing chat history
        )
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        msg,
        gr.update(selected=2),
        "",
        [],
    )


def handle_logout(username):
    return (
        gr.update(visible=False),  # Hide chat UI
        gr.update(visible=True),   # Show login UI
        gr.update(selected=0),     # Switch to Home tab
        "",                         # Clear username state
        [],                         # Clear chat display
    )


def handle_chat(message, chat_history, username):
    if not message.strip():
        return "", chat_history
    if not username:
        return "", chat_history + [["Please log in first.", None]]

    response = generate_response(message, username)
    chat_history = chat_history + [[message, response]]
    return "", chat_history


def handle_clear_history(username):
    if username:
        memory.clear_history(username)
    return []


# ---------------------------------------------------------------------------
# Build the Gradio UI
# ---------------------------------------------------------------------------
def create_ui():
    css = """
    #create-btn button, #login-btn button, #submit-btn button,
    #logout-btn button, #clear-btn button {
        font-size: 13px !important;
        padding: 6px 12px !important;
        height: 34px !important;
        width: auto !important;
        min-width: 90px !important;
    }
    .chatbot-container { min-height: 400px; }
    """

    with gr.Blocks(theme="soft", css=css, title="MEDChat AI") as demo:
        # Hidden state for the logged-in username
        current_user = gr.State("")

        with gr.Tabs(selected=0, elem_id="tabs") as tabs:
            # --- Home Tab ---
            with gr.Tab("Home"):
                gr.Markdown("# MEDChat AI")
                gr.Markdown("---")
                gr.Markdown(
                    "A medical Q&A chatbot powered by fine-tuned Llama 2.\n\n"
                    "**Features:**\n"
                    "- Conversational memory (remembers your chat history)\n"
                    "- Secure authentication with encrypted passwords\n"
                    "- Medical domain knowledge via fine-tuned LLM\n"
                    "- Privacy-focused with local data storage"
                )
                gr.Markdown("---")
                gr.Markdown(
                    "Get started by creating an account in the **Sign Up** tab, "
                    "then **Login** to start chatting."
                )
                gr.Markdown("---")
                gr.Markdown(
                    "*MEDChat AI is for informational purposes only. "
                    "Always consult a healthcare professional for medical advice.*"
                )

            # --- Sign Up Tab ---
            with gr.Tab("Sign Up"):
                with gr.Column():
                    gr.Markdown("### Create Account")
                    new_username = gr.Textbox(label="Username (min 3 characters)")
                    new_password = gr.Textbox(label="Password (min 6 characters)", type="password")
                    create_account_btn = gr.Button("Create Account", elem_id="create-btn")
                    signup_msg = gr.Markdown()

            # --- Login Tab ---
            with gr.Tab("Login"):
                with gr.Column(visible=True) as login_ui:
                    gr.Markdown("### Login")
                    username_input = gr.Textbox(label="Username")
                    password_input = gr.Textbox(label="Password", type="password")
                    login_btn = gr.Button("Login", elem_id="login-btn")
                    login_msg = gr.Markdown()

            # --- Chat Tab ---
            with gr.Tab("Chat"):
                with gr.Column(visible=False) as chat_ui:
                    with gr.Row():
                        gr.Markdown("## MEDChat AI")
                        logout_btn = gr.Button("Logout", elem_id="logout-btn", scale=0)
                        clear_btn = gr.Button("Clear History", elem_id="clear-btn", scale=0)

                    chatbot = gr.Chatbot(
                        label="Conversation",
                        elem_classes="chatbot-container",
                        height=420,
                    )
                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="Ask a medical question...",
                            show_label=False,
                            scale=4,
                        )
                        submit_btn = gr.Button("Send", elem_id="submit-btn", scale=0)

                    gr.Markdown("### Try one of these:")
                    examples = gr.Examples(
                        examples=[
                            ["What does the immune system do?"],
                            ["What is Epistaxis?"],
                            ["Do our intestines contain germs?"],
                            ["What are allergies?"],
                            ["What are antibiotics?"],
                            ["What's the difference between bacteria and viruses?"],
                        ],
                        inputs=msg_input,
                    )

        # --- Wire up events ---
        create_account_btn.click(
            fn=handle_signup,
            inputs=[new_username, new_password],
            outputs=signup_msg,
        )

        login_btn.click(
            fn=handle_login,
            inputs=[username_input, password_input],
            outputs=[chat_ui, login_ui, login_msg, tabs, current_user, chatbot],
        )

        logout_btn.click(
            fn=handle_logout,
            inputs=[current_user],
            outputs=[chat_ui, login_ui, tabs, current_user, chatbot],
        )

        submit_btn.click(
            fn=handle_chat,
            inputs=[msg_input, chatbot, current_user],
            outputs=[msg_input, chatbot],
        )

        msg_input.submit(
            fn=handle_chat,
            inputs=[msg_input, chatbot, current_user],
            outputs=[msg_input, chatbot],
        )

        clear_btn.click(
            fn=handle_clear_history,
            inputs=[current_user],
            outputs=[chatbot],
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    args = parse_args()

    load_model(args.model_path, args.max_length, cpu_only=args.cpu)

    demo = create_ui()
    demo.launch(
        server_port=args.port,
        share=args.share,
    )


if __name__ == "__main__":
    main()
