"""RAG evaluation: measures retrieval and (optionally) generation quality
against a labeled set of question/expected-answer cases.

This package has no opinion about *which* questions to evaluate — see
`eval_datasets/sample_eval.json` for a small, clearly-labeled starter example
you're expected to replace with real questions and documents from your own
workspace. Metrics computed against a fabricated or trivial dataset are not
meaningful; this only becomes a genuine quality signal once it's run against
real cases.
"""
