"""Shared test helpers: a scripted fake LLM client and message builders,
used by both the agent and router seam tests.
"""

import json
from types import SimpleNamespace


def msg(content=None, tool_calls=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content=content, tool_calls=tool_calls))]
    )


def tool_call(name, args, id="call_1"):
    return SimpleNamespace(
        id=id, function=SimpleNamespace(name=name, arguments=json.dumps(args))
    )


class FakeClient:
    """Plays back scripted responses; records every create() kwargs."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)
