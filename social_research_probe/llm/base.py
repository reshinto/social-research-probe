"""Abstract base class for all LLM runner implementations.

Why this exists: the pipeline and corroboration host need to call LLMs without
knowing which vendor is behind the call. Any new LLM (Claude, Gemini, a local
model) can be added by subclassing LLMRunner and registering it — no calling
code changes needed.

Who calls it: llm.registry (for type constraints), the pipeline, and the
corroboration host.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class LLMRunner(ABC):
    """Contract that every LLM runner must fulfil.

    Purpose: provide a uniform interface so callers are decoupled from any
    specific LLM vendor or binary.

    Lifecycle: subclasses are registered at import time via the @register
    decorator in llm.registry; the registry instantiates them on demand.

    Who instantiates it: llm.registry.get_runner(), never called directly.

    ABC/protocol fulfilled: ABC with two abstract methods — health_check and run.
    """

    # Each concrete subclass must set this to a unique string key (e.g. "claude").
    # The registry uses this key to look up the runner by name.
    name: ClassVar[str]

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if this runner is available and configured correctly.

        Returns:
            True if the runner's CLI binary (or env var) is present and usable,
            False otherwise. Never raises — failures surface as False.
        """
        ...

    @abstractmethod
    def run(self, prompt: str, *, schema: dict | None = None) -> dict:
        """Send prompt to the LLM and return the parsed JSON response.

        Args:
            prompt: The full prompt string to send to the LLM.
            schema: Optional JSON schema the response must conform to. Passed
                to the CLI if the vendor supports schema enforcement.

        Returns:
            Parsed dict from the LLM's JSON response.

        Raises:
            AdapterError: If the LLM call fails (non-zero exit, timeout) or the
                response body is not valid JSON.
        """
        ...
