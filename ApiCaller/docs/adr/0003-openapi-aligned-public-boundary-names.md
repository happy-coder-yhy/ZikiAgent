# OpenAPI-Aligned Public Boundary Names

Public platform operation boundaries use Zata Platform OpenAPI field names, including camelCase names such as `sceneId`, `categoryCode`, and `projectId`. This applies to `ZataAPICaller` public business method parameters, OpenAPI-Aligned Request Object fields, and any future external tool schemas.

Internal Python implementation details, private helpers, low-level `APICaller` transport parameters, local variables, modules, and tests remain Pythonic snake_case.

This keeps Tool and OpenAPI terminology aligned for Agent callers while avoiding a full-project camelCase rewrite that would make ordinary Python internals harder to maintain.
