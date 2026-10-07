# REVIEW 09 — Example and release-note sdist inclusion

Verdict: **ACCEPT** for Codex glue commit dd1bafe7553e551f43dba7824921d350b313a82c only. Parent25 distribution tests passed in2.13s, hooks and diff check passed. Independent2 real-sdist tests passed in0.63s. All18 example/source/archive files plus release notes are included byte-for-byte; no runtime dependency, wheel-content, broad-glob or private-path addition.

Reviewed pyproject.toml SHA256b9952a15737013297e0709c32b369d36a7cde0c7a1b1d823a96109eff8508994; tests/release/test_check_release_distributions.py SHA256206f62e9c07b752f5a640c2542654564c445c48473f235acf187e831c75ae78c. Full exact-head hosted/rehearsal/publication gates remain; docs publishing text must reflect the new packaged release-note input.
