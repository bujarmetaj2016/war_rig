"""Immutable unit-02 offline identities, exact source prices and replay correlation.

Only deterministic stdlib and unit-06 UTC primitives are allowed. Constructors
reject malformed identities/units; no account credential, real permit, clock read,
persistence or broker operation is representable here.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from v3.offline.calendar_completion import VerifiedEventClock, require_utc


@dataclass(frozen=True)
class Identity:
    """Bounded immutable ASCII identity; subclasses are distinct domain types."""

    value: str

    def __post_init__(self) -> None:
        """Reject empty, nontext, path-like and unbounded identifiers."""
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", self.value, flags=re.ASCII
        ):
            raise ValueError("Invalid bounded domain identity")


class MarketId(Identity):
    """Market identity, not an instrument or account identifier."""


class InstrumentId(Identity):
    """Stable instrument-family identity, not a dated listing."""


class PolicyId(Identity):
    """Fixture policy identity; not an owner authorisation."""


class EventId(Identity):
    """Source event identity, independent of model attribution."""


class RunId(Identity):
    """Immutable synthetic run identity."""


@dataclass(frozen=True)
class SimulatedAccountId(Identity):
    """Explicit synthetic account label; no real account identifier is admitted."""

    def __post_init__(self) -> None:
        """Require a validated identity and the non-authoritative SIMULATED prefix."""
        super().__post_init__()
        if not self.value.startswith("SIMULATED_"):
            raise ValueError("Only a simulated account identity is permitted")


@dataclass(frozen=True)
class Digest:
    """Exact lowercase SHA-256 reference; never a cryptographic signature."""

    value: str

    def __post_init__(self) -> None:
        """Reject malformed or wrongly typed digest references."""
        if not isinstance(self.value, str) or not re.fullmatch(r"[a-f0-9]{64}", self.value):
            raise ValueError("Invalid SHA-256 identity")


@dataclass(frozen=True)
class PriceUnit:
    """Source-price dimension and exact grid; never broker stake or payout units."""

    name: Identity
    currency: str
    precision: int
    increment: Decimal

    def __post_init__(self) -> None:
        """Validate explicit currency, finite positive increment and decimal precision."""
        if (
            not isinstance(self.currency, str)
            or not re.fullmatch(r"[A-Z]{3}", self.currency)
            or type(self.precision) is not int
            or not 0 <= self.precision <= 12
            or not isinstance(self.increment, Decimal)
            or not self.increment.is_finite()
            or self.increment <= 0
        ):
            raise ValueError("Invalid source-price dimension")
        exponent = self.increment.as_tuple().exponent
        if not isinstance(exponent, int) or exponent < -self.precision:
            raise ValueError("Increment exceeds the declared quote precision")

    def check(self, price: Decimal) -> Decimal:
        """Return a positive exact-grid source price or raise; no rounding or conversion."""
        if not isinstance(price, Decimal) or not price.is_finite() or price <= 0:
            raise ValueError("Invalid exact source price")
        numerator, denominator = price.as_integer_ratio()
        step_numerator, step_denominator = self.increment.as_integer_ratio()
        if (numerator * step_denominator) % (denominator * step_numerator):
            raise ValueError("Price is not on its declared source grid")
        return price


@dataclass(frozen=True)
class RunContext:
    """Pinned fixture run/account/market/instrument/policy/build/clock correlation."""

    run: RunId
    account: SimulatedAccountId
    market: MarketId
    instrument: InstrumentId
    policy: PolicyId
    policy_sha256: Digest
    build_sha256: Digest
    source_sha256: Digest
    feature_schema_sha256: Digest
    clock_id: Identity
    valid_from: datetime
    valid_until: datetime

    def __post_init__(self) -> None:
        """Require a finite, nonempty UTC run interval."""
        require_utc(self.valid_from)
        require_utc(self.valid_until)
        if self.valid_until <= self.valid_from:
            raise ValueError("Run validity interval must be nonempty")

    @property
    def sha256(self) -> str:
        """Return a deterministic context digest; it conveys no execution permission."""
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()


@dataclass(frozen=True)
class ReplayCursor:
    """One source stream's checked replay position; durable ledger dedup is separate."""

    stream: Identity
    sequence: int
    event: EventId
    event_sha256: Digest
    clock: VerifiedEventClock

    def __post_init__(self) -> None:
        """Reject missing sequence or untrusted synthetic event-clock evidence."""
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("A positive replay sequence is required")
        self.clock.elapsed_to(self.clock)

    def advance(self, other: "ReplayCursor") -> "ReplayCursor":
        """Return the next cursor; identical retry is idempotent, gaps/conflicts deny."""
        if other == self:
            return self
        if (
            other.stream != self.stream
            or other.sequence != self.sequence + 1
            or other.event == self.event
        ):
            raise ValueError("Replay stream, order or event identity conflict")
        self.clock.elapsed_to(other.clock)
        return other
