"""Year streams of real dollars.

A stream is a list of length ``horizon``. Index ``t - 1`` holds year ``t``.
Flows sit at year end, so year ``t`` is discounted by ``(1 + r) ** t``.
Every growing stream is measured from ``t_g`` (default 1): year ``t`` holds
``amount * (1 + g) ** (t - t_g)``.
"""

from __future__ import annotations


def _require_span(first: int, length: int, horizon: int) -> None:
    """Raise ValueError when a positive span is not inside years 1..horizon."""
    if length < 0:
        raise ValueError(f"span length {length} is negative")
    if horizon < 0:
        raise ValueError(f"horizon {horizon} is negative")
    if length == 0:
        return
    last = first + length - 1
    if first < 1 or last > horizon:
        raise ValueError(f"span {first}..{last} exceeds horizon 1..{horizon}")


def level(amount: float, t0: int, n: int, horizon: int) -> list[float]:
    """Constant ``amount`` over years ``t0`` .. ``t0 + n - 1``. Zeros elsewhere."""
    _require_span(t0, n, horizon)
    stream = [0.0] * horizon
    for t in range(t0, t0 + n):
        stream[t - 1] = amount
    return stream


def growing(
    amount: float,
    g: float,
    t0: int,
    n: int,
    horizon: int,
    tg: int = 1,
) -> list[float]:
    """Growing amount over years ``t0`` .. ``t0 + n - 1``.

    Year ``t`` holds ``amount * (1 + g) ** (t - tg)``. Zeros elsewhere.
    """
    _require_span(t0, n, horizon)
    stream = [0.0] * horizon
    for t in range(t0, t0 + n):
        stream[t - 1] = amount * (1.0 + g) ** (t - tg)
    return stream


def weighted(
    total: float,
    weights: list[float],
    t_start: int,
    horizon: int,
    escalation: float = 0.0,
) -> list[float]:
    """Spread ``total`` by ``weights``, escalated on the calendar year.

    Year ``t = t_start + y - 1`` holds
    ``weights[y - 1] * total * (1 + escalation) ** (t - 1)``.
    """
    _require_span(t_start, len(weights), horizon)
    stream = [0.0] * horizon
    for y, weight in enumerate(weights, start=1):
        t = t_start + y - 1
        stream[t - 1] = weight * total * (1.0 + escalation) ** (t - 1)
    return stream


def pv(stream: list[float], r: float) -> float:
    """Present value. Year ``t`` (index ``t - 1``) is discounted by ``(1 + r) ** t``."""
    return sum(
        (value / (1.0 + r) ** t for t, value in enumerate(stream, start=1)),
        start=0.0,
    )


def undiscounted(stream: list[float]) -> float:
    """Sum of the stream, with no discounting."""
    return sum(stream, 0.0)


def pv_operator(
    x: float, g: float, r: float, t0: int, n: int, tg: int = 1
) -> float:
    """Closed form of ``pv(growing(x, g, t0, n, ...), r)``.

    When ``abs(g - r) >= 1e-12``:

        x * (1 + g) ** (t0 - tg) / (1 + r) ** (t0 - 1) * (1 - q ** n) / (r - g)

    with ``q = (1 + g) / (1 + r)``. Otherwise ``x * n * (1 + r) ** (-tg)``.
    """
    if abs(g - r) < 1e-12:
        return x * n * (1.0 + r) ** (-tg)
    q = (1.0 + g) / (1.0 + r)
    return (
        x
        * (1.0 + g) ** (t0 - tg)
        / (1.0 + r) ** (t0 - 1)
        * (1.0 - q**n)
        / (r - g)
    )


def add(*streams: list[float]) -> list[float]:
    """Element-wise sum. Every stream must have the same length."""
    if not streams:
        raise ValueError("add() requires at least one stream")
    length = len(streams[0])
    for stream in streams[1:]:
        if len(stream) != length:
            raise ValueError(
                f"streams must have equal length; got {length} and {len(stream)}"
            )
    return [sum(values) for values in zip(*streams, strict=True)]
