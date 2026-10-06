# Actseal executor entrypoint

Read and obey `AGENTS.md`. Start with `plan/STATE.md` and the exact task packet.
Implement only owned product/test files, preserve frozen interfaces, run the
listed commands, and return the specified REPORT. Other lanes may be working;
do not revert or edit their files. Only Codex accepts and integrates work.

Use dedicated Read/Edit/Write tools for source files. Run checks as separate,
literal commands; avoid shell editing, compound command chains and Unicode
control characters in shell text. A denied operation stays denied: record it,
do not retry it or disguise it through another tool. Continue independent allowed
work and report any real blocker. Packet hashes are supplied by Codex; inability
to run a redundant hash command does not authorize bypassing permission controls.
