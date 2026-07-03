# Structured Public API With Private Raw Platform Request

`ZataAPICaller` exposes platform operations as Structured API Calls with explicit business fields or typed request objects, so callers do not assemble raw JSON request bodies. The caller may keep private Raw Platform Request helpers such as `_request_rbac` and `_request_data_manager` for debugging and fast adaptation when Zata Platform APIs change. Raw Platform Request is not part of the public API or any future external Agent-callable tool surface.

This preserves schema safety for normal users and Agent runtimes while retaining a narrow internal escape hatch for API drift.
