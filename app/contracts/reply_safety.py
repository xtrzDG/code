"""Checks of what the assistant says that need a model of their own."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.dto.reply_safety import ClaimCheckRequest, ClaimCheckResult


class ClaimCheckFacilitatorContract(FacilitatorContract, Protocol):
    def check_claims(self, request: ClaimCheckRequest) -> ClaimCheckResult:
        """
        Whether the evidence backs each claim, asked of a cheap verifier
        model. Never raises for a failed or unreadable verifier answer: such
        claims come back UNCHECKED and the reply is sent; with the check
        off (no verifier model) the result has no findings.
        """
        raise NotImplementedError
