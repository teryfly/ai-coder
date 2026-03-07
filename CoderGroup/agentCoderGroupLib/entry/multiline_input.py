from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings


class MultilineInput:
    """
    Reusable multiline input reader.

    Notes:
    - Enter keeps newline in multiline mode.
    - Submit shortcuts:
      1) Ctrl+J (widely supported in terminals)
      2) Esc then Enter (fallback combo)
    """

    def __init__(self):
        self._session = PromptSession(multiline=True, wrap_lines=True)
        self._bindings = KeyBindings()
        self._register_submit_keys()

    def _register_submit_keys(self) -> None:
        # Ctrl+J submit (portable in most terminals)
        @self._bindings.add("c-j")
        def _submit_ctrl_j(event):
            event.current_buffer.validate_and_handle()

        # Esc + Enter submit fallback
        @self._bindings.add("escape", "enter")
        def _submit_alt_enter(event):
            event.current_buffer.validate_and_handle()

    def read_multiline(self, prompt: str = "> ") -> str:
        return self._session.prompt(prompt, key_bindings=self._bindings).rstrip()