# Keep Workflow Verification Separate From API Caller

Workflow verification should live outside `APICaller` and `ZataAPICaller`, for example in an independent `verifier.py`, because configuration matching rules are expected to change frequently while the API caller boundary should remain a stable wrapper around Zata Platform operations. The verifier should report gaps, conflicts, and resolved platform IDs from a snapshot, but it should not call write APIs or own creation, deletion, or rollback of Collection Project, Task, or Job resources.
