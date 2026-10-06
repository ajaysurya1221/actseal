# ADR 0010: Shared bounded input and digest helpers

Status: accepted. Date: 2026-10-06. Owner: Codex.

T10 supplied four small helpers beyond the original public signature inventory.
T40 and T50 need the same raw UTF-8 reader, lock decoder and canonical digests.
Duplicating those operations would create inconsistent newline, size or sealing
rules. Accept read_input_text, parse_lock, case_digest and lock_digest as explicit
public helpers, with the exact signatures and behavior in CONTRACTS section 3.
Constants for the already specified limits, fault inventory and reason codes are
permitted conveniences; they create no new behavior or record fields.

The reader must bound the read before allocation, not check size after reading
an arbitrary file. Creation, standalone validation and parsing must agree about
the 32 MiB wire ceiling; canonical output includes its terminal LF. Standalone
validation checks disjoint IDs using both available inventories. Calibration
state texts cannot be reconstructed from hashes, so that check requires inputs.

No dependency, product scope or shared record changes. A new helper does not
make an unverified lock trusted: parse_lock is structural decoding, and callers
must validate the seal and implementation through validate_lock. Read-time OS
errors propagate; schema/limit errors use SchemaError.

Alternatives: duplicate the logic downstream (rejected for inconsistent rules),
or move it into the frozen T00 module (rejected as unnecessary shared-file churn).
T10 remains REVISE until its three independently reproduced defects are fixed.
