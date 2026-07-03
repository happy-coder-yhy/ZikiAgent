# Keep One-Off Integration Results Out Of Docs

One-off real-server integration outputs should live under `results/` rather than `docs/`, because they record a single validation run instead of long-lived developer guidance. Stable testing rules such as the test server, serial request discipline, and minimum delay between API calls may remain in README or development docs, while observed counts, request sequences, and temporary resource IDs should be archived as dated results.
