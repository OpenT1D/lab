# ADR 0104: Bound entry handoff and propose bundle-copy registration

- Status: accepted for bounded implementation; operational authorities stay empty
- Date: 2026-11-04

## Context

Entry frames have no transport, and saving a review bundle creates additional
private copies that still need explicit register reconciliation. Neither a
consistent frame nor a saved proposal establishes native host qualification or
effective erasure.

## Decision

Add a library for one frame and canonical acknowledgment over two independently
owned, already opened unidirectional endpoints. The current-fact function first
uses the existing observation gate; refusal must not touch caller endpoints.
Successful intake transfers endpoint ownership for this one exchange. Bound
bytes, chunks, backpressure, EOF, cancellation and the asynchronous handoff time.
The timer does not preempt synchronous observation/source hashing. Retain bounded
partial evidence on failure; remove only own listeners/timer/endpoints. Do not
add a CLI, spawn, worker import, journal writes or automatic launcher integration.
Bind acknowledgment bytes to the exact frame, grant, kind, attempt and nonce.
Independent byte readback keeps endpoint truth, phase, stdio and native flags false.

Propose one explicitly allocated, globally unused aggregate bundle-copy ID for
each existing retention subject. Bind each conservative derived copy to the
verified published manifest, exact base register, context and source. Preserve
every old subject/copy, origin, origin evidence, hold, policy and historical
recovery horizon exactly. Link the exact base as predecessor and reassess using
the unchanged retention planner. Coverage flags stay false. Do not adopt the
bundle's unapproved recovery proposal, save or activate a register, or admit
removal. Keep returned registration/provenance bytes outside the immutable bundle.

## Consequences

The existing launcher, supervisor, process owner, workers, journal, retention and
removal implementations, scientific references and four production authority
lists remain unchanged. Actual dedicated-channel/profile/fixed-entry wiring,
native instrumentation and C15-C18 remain separately gated. Copy/restore scope,
ordinary recovery coverage and effective removal still need their own evidence.
