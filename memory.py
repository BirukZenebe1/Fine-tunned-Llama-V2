"""
Conversation memory module for the medical chatbot.

Maintains per-session chat history so the model receives prior context
when generating responses. History is stored in-memory (per server session)
and optionally persisted to disk per user.
"""

import json
import os
from collections import defaultdict

HISTORY_DIR = os.path.join(os.path.dirname(__file__), "data", "history")
MAX_HISTORY_TURNS = 10  # Keep last N turns to fit within context window


class ConversationMemory:
    """Manages conversation history for multiple users."""

    def __init__(self, persist=True):
        self.persist = persist
        # {username: [{"role": "user"/"assistant", "content": "..."}]}
        self._sessions = defaultdict(list)

    def _history_path(self, username):
        os.makedirs(HISTORY_DIR, exist_ok=True)
        return os.path.join(HISTORY_DIR, f"{username}.json")

    def load_history(self, username):
        """Load conversation history from disk for a user."""
        if not self.persist:
            return
        path = self._history_path(username)
        if os.path.exists(path):
            with open(path, "r") as f:
                self._sessions[username] = json.load(f)

    def save_history(self, username):
        """Persist conversation history to disk for a user."""
        if not self.persist:
            return
        path = self._history_path(username)
        with open(path, "w") as f:
            json.dump(self._sessions[username], f, indent=2)

    def add_turn(self, username, user_msg, assistant_msg):
        """Add a user/assistant exchange to the conversation history."""
        self._sessions[username].append({"role": "user", "content": user_msg})
        self._sessions[username].append({"role": "assistant", "content": assistant_msg})
        # Trim to keep context window manageable
        max_messages = MAX_HISTORY_TURNS * 2  # 2 messages per turn
        if len(self._sessions[username]) > max_messages:
            self._sessions[username] = self._sessions[username][-max_messages:]
        self.save_history(username)

    def get_history(self, username):
        """Return the conversation history for a user."""
        return list(self._sessions[username])

    def build_prompt(self, username, new_message):
        """
        Build a Llama 2 chat-format prompt that includes conversation history.

        Format: <s>[INST] <<SYS>> system_prompt <</SYS>> user_msg [/INST] assistant_msg </s>
                <s>[INST] user_msg [/INST] ...
        """
        system_prompt = (
            "You are MEDChat AI, a helpful and knowledgeable medical assistant. "
            "Provide accurate, clear medical information based on established knowledge. "
            "Always recommend consulting a healthcare professional for personal medical decisions. "
            "If you are unsure, say so honestly."
        )

        history = self.get_history(username)

        # Build multi-turn prompt in Llama 2 chat format
        parts = []

        # First turn includes the system prompt
        if not history:
            parts.append(
                f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{new_message} [/INST]"
            )
        else:
            # Reconstruct conversation with system prompt in first turn
            first_user = history[0]["content"] if history else new_message
            parts.append(
                f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{first_user} [/INST]"
            )
            # Add remaining history pairs
            for i in range(1, len(history), 2):
                assistant_msg = history[i]["content"] if i < len(history) else ""
                parts.append(f" {assistant_msg} </s>")
                if i + 1 < len(history):
                    user_msg = history[i + 1]["content"]
                    parts.append(f"<s>[INST] {user_msg} [/INST]")

            # Handle the last assistant reply if history has odd count
            if len(history) % 2 == 0:
                assistant_msg = history[-1]["content"]
                parts.append(f" {assistant_msg} </s>")

            # Append the new user message
            parts.append(f"<s>[INST] {new_message} [/INST]")

        return "".join(parts)

    def clear_history(self, username):
        """Clear conversation history for a user."""
        self._sessions[username] = []
        self.save_history(username)

    def get_display_history(self, username):
        """Return history formatted for Gradio Chatbot display (list of [user, assistant] pairs)."""
        history = self.get_history(username)
        pairs = []
        for i in range(0, len(history) - 1, 2):
            user_msg = history[i]["content"]
            assistant_msg = history[i + 1]["content"]
            pairs.append([user_msg, assistant_msg])
        return pairs
