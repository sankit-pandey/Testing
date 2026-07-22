"""Pipeline control-flow and validation exceptions."""


class InvalidTransitionError(Exception):
    """Raised when a state-machine transition is not allowed. Story 2.2."""


class PipelineSuspended(Exception):
    """Raised by a strategy stage (typically `orchestrate`) to signal that
    async external work (Lokalise upload, image sub-pipeline, human
    sign-off) has been dispatched. The executor stops advancing without
    marking anything failed; a webhook, poll, or join-barrier trip later
    calls `resume_pipeline` to continue. Stories 2.3, 2.5, LOCKED §7.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)
