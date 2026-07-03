"""Collection work preflight verifier."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass
class VerificationResult:
    """采集工作创建前校验结果。"""

    can_create: bool
    configuration_gaps: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    resolved: dict[str, Any] = field(default_factory=dict)
    warnings: list[dict[str, Any]] = field(default_factory=list)


REQUIRED_FIELD_PROFILES = {
    "project": {
        "openapi_required": ("name",),
        "business_required": (),
    },
    "scene_task": {
        "openapi_required": ("collectMethod", "sceneId", "taskCategory", "title"),
        "fixed_fields": {"collectMethod": "web_video", "taskCategory": "scene"},
        "business_required": ("projectId",),
    },
    "instruction_task": {
        "openapi_required": ("collectMethod", "sceneId", "taskCategory", "title"),
        "fixed_fields": {"collectMethod": "web_video", "taskCategory": "instruction"},
        "business_required": ("projectId", "promptInstruction"),
    },
    "strict_task": {
        "openapi_required": ("collectMethod", "sceneId", "taskCategory", "title"),
        "fixed_fields": {"collectMethod": "robot", "taskCategory": "strict"},
        "business_required": (
            "projectId",
            "deviceTypeId",
            "initialState",
            "actionSteps",
            "objectBindings",
        ),
    },
    "strict_task_from_template": {
        "openapi_required": ("templateItems",),
        "fixed_fields": {"collectMethod": "robot"},
        "business_required": ("projectId", "collectMethod", "deviceTypeId"),
    },
    "task_template_item": {
        "openapi_required": ("templateId",),
        "business_required": (),
    },
    "job": {
        "openapi_required": ("requiredRepeat",),
        "business_required": (),
    },
}

UNCONFIRMED_PLATFORM_RULE_FIELDS = (
    "duration",
    "minDuration",
    "difficulty",
    "abnormalRatio",
)


def verify_collection_work(
    planned_project: Mapping[str, Any],
    planned_task: Mapping[str, Any],
    planned_jobs: Sequence[Mapping[str, Any]],
    platform_snapshot: Mapping[str, Any],
) -> VerificationResult:
    """校验计划中的采集工作是否可以创建。

    参数:
        planned_project (Mapping[str, Any]): 待创建的 Collection Project 字段。
        planned_task (Mapping[str, Any]): 待创建的 Collection Task 字段。
        planned_jobs (Sequence[Mapping[str, Any]]): 待创建的 Collection Job 列表。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。

    返回:
        VerificationResult: 包含是否可创建、缺失配置、冲突和解析结果的校验结果。
    """
    project_result = verify_project_creation(
        planned_project=planned_project,
        platform_snapshot=platform_snapshot,
    )
    task_result = _verify_task_for_collection_work(
        planned_task=planned_task,
        platform_snapshot=platform_snapshot,
    )
    jobs_result = verify_jobs_creation(planned_jobs=planned_jobs)

    return _combine_results(project_result, task_result, jobs_result)


def verify_project_creation(
    planned_project: Mapping[str, Any],
    platform_snapshot: Mapping[str, Any],
) -> VerificationResult:
    """校验单次 Collection Project 创建请求。

    参数:
        planned_project (Mapping[str, Any]): 待创建的 Collection Project 字段。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。

    返回:
        VerificationResult: Project 创建前校验结果。
    """
    conflicts: list[dict[str, Any]] = []
    configuration_gaps: list[dict[str, Any]] = []
    resolved: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []

    _require_fields(
        source=planned_project,
        fields=REQUIRED_FIELD_PROFILES["project"]["openapi_required"],
        scope="project",
        configuration_gaps=configuration_gaps,
        rule_type="openapi_required",
    )

    project_name = planned_project.get("name")
    if project_name:
        matching_projects = _find_by_field(platform_snapshot.get("projects", []), "name", project_name)
        if matching_projects:
            conflicts.append(
                _issue(
                    scope="project",
                    field="name",
                    expected=project_name,
                    reason="conflicting",
                    message=f"Collection Project name already exists: {project_name}",
                    rule_type="business_profile",
                    candidates=matching_projects,
                )
            )
        else:
            resolved["project.name"] = project_name

    return _build_result(
        configuration_gaps=configuration_gaps,
        conflicts=conflicts,
        resolved=resolved,
        warnings=warnings,
    )


def verify_scene_task_creation(
    planned_task: Mapping[str, Any],
    platform_snapshot: Mapping[str, Any],
    require_project_id: bool = True,
) -> VerificationResult:
    """校验单次场景采集任务创建请求。

    参数:
        planned_task (Mapping[str, Any]): 待创建的场景 Task 字段。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。
        require_project_id (bool): 是否要求 `projectId`，组合流程中可由 Project 创建补齐。

    返回:
        VerificationResult: 场景 Task 创建前校验结果。
    """
    return _verify_task_creation(
        planned_task=planned_task,
        platform_snapshot=platform_snapshot,
        profile_name="scene_task",
        require_project_id=require_project_id,
        validate_strict_references=False,
    )


def verify_strict_task_creation(
    planned_task: Mapping[str, Any],
    platform_snapshot: Mapping[str, Any],
    require_project_id: bool = True,
) -> VerificationResult:
    """校验单次严格采集任务直接创建请求。

    参数:
        planned_task (Mapping[str, Any]): 待创建的严格 Task 字段。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。
        require_project_id (bool): 是否要求 `projectId`，组合流程中可由 Project 创建补齐。

    返回:
        VerificationResult: 严格 Task 创建前校验结果。
    """
    return _verify_task_creation(
        planned_task=planned_task,
        platform_snapshot=platform_snapshot,
        profile_name="strict_task",
        require_project_id=require_project_id,
        validate_strict_references=True,
    )


def verify_instruction_task_creation(
    planned_task: Mapping[str, Any],
    platform_snapshot: Mapping[str, Any],
    require_project_id: bool = True,
) -> VerificationResult:
    """校验单次指令采集任务创建请求。

    参数:
        planned_task (Mapping[str, Any]): 待创建的指令 Task 字段。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。
        require_project_id (bool): 是否要求 `projectId`，组合流程中可由 Project 创建补齐。

    返回:
        VerificationResult: 指令 Task 创建前校验结果。
    """
    return _verify_task_creation(
        planned_task=planned_task,
        platform_snapshot=platform_snapshot,
        profile_name="instruction_task",
        require_project_id=require_project_id,
        validate_strict_references=False,
    )


def verify_strict_task_from_template_creation(
    planned_task: Mapping[str, Any],
    platform_snapshot: Mapping[str, Any],
    require_project_id: bool = True,
) -> VerificationResult:
    """校验单次严格采集任务模板创建请求。

    参数:
        planned_task (Mapping[str, Any]): 待创建的模板 Task 字段。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。
        require_project_id (bool): 是否要求 `projectId`，组合流程中可由 Project 创建补齐。

    返回:
        VerificationResult: 模板创建严格 Task 的创建前校验结果。
    """
    profile = REQUIRED_FIELD_PROFILES["strict_task_from_template"]
    source_with_fixed_fields = {**profile.get("fixed_fields", {}), **planned_task}
    configuration_gaps: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    resolved: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []
    business_required = _business_required_fields(profile, require_project_id)

    _require_fields(
        source=source_with_fixed_fields,
        fields=profile["openapi_required"],
        scope="task",
        configuration_gaps=configuration_gaps,
        rule_type="openapi_required",
    )
    _require_fields(
        source=source_with_fixed_fields,
        fields=business_required,
        scope="task",
        configuration_gaps=configuration_gaps,
        rule_type="business_profile",
    )

    _check_id_reference(
        value=planned_task.get("deviceTypeId"),
        field="deviceTypeId",
        items=platform_snapshot.get("device_types", []),
        id_key="id",
        scope="task",
        configuration_gaps=configuration_gaps,
        resolved=resolved,
    )

    template_items = planned_task.get("templateItems", []) or []
    for item in template_items:
        if not isinstance(item, Mapping):
            continue
        _require_fields(
            source=item,
            fields=REQUIRED_FIELD_PROFILES["task_template_item"]["openapi_required"],
            scope="task",
            configuration_gaps=configuration_gaps,
            rule_type="openapi_required",
            field_prefix="templateItems[].",
        )
        _check_id_reference(
            value=item.get("templateId"),
            field="templateItems[].templateId",
            items=platform_snapshot.get("scene_task_templates", platform_snapshot.get("templates", [])),
            id_key="id",
            scope="task",
            configuration_gaps=configuration_gaps,
            resolved=resolved,
            skip_when_candidates_missing=True,
        )

    _add_unconfirmed_rule_warnings(
        source=planned_task,
        scope="task",
        warnings=warnings,
    )

    return _build_result(
        configuration_gaps=configuration_gaps,
        conflicts=conflicts,
        resolved=resolved,
        warnings=warnings,
    )


def verify_jobs_creation(planned_jobs: Sequence[Mapping[str, Any]]) -> VerificationResult:
    """校验单次 Collection Job 创建请求。

    参数:
        planned_jobs (Sequence[Mapping[str, Any]]): 待创建的 Job 列表。

    返回:
        VerificationResult: Job 创建前校验结果。
    """
    configuration_gaps: list[dict[str, Any]] = []
    _validate_jobs(planned_jobs=planned_jobs, configuration_gaps=configuration_gaps)
    return _build_result(
        configuration_gaps=configuration_gaps,
        conflicts=[],
        resolved={},
        warnings=[],
    )


def _verify_task_for_collection_work(
    planned_task: Mapping[str, Any],
    platform_snapshot: Mapping[str, Any],
) -> VerificationResult:
    """按计划内容推断组合流程中的 Task 校验 profile。

    参数:
        planned_task (Mapping[str, Any]): 待创建的 Task 字段。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。

    返回:
        VerificationResult: Task 创建前校验结果。
    """
    if "templateItems" in planned_task:
        return verify_strict_task_from_template_creation(
            planned_task=planned_task,
            platform_snapshot=platform_snapshot,
            require_project_id=False,
        )
    if planned_task.get("taskCategory") == "instruction" or "promptInstruction" in planned_task:
        return verify_instruction_task_creation(
            planned_task=planned_task,
            platform_snapshot=platform_snapshot,
            require_project_id=False,
        )
    strict_fields = ("deviceTypeId", "initialState", "actionSteps", "objectBindings")
    if any(field in planned_task for field in strict_fields):
        return verify_strict_task_creation(
            planned_task=planned_task,
            platform_snapshot=platform_snapshot,
            require_project_id=False,
        )
    return verify_scene_task_creation(
        planned_task=planned_task,
        platform_snapshot=platform_snapshot,
        require_project_id=False,
    )


def _verify_task_creation(
    planned_task: Mapping[str, Any],
    platform_snapshot: Mapping[str, Any],
    profile_name: str,
    require_project_id: bool,
    validate_strict_references: bool,
) -> VerificationResult:
    """按指定 profile 校验 Task 创建请求。

    参数:
        planned_task (Mapping[str, Any]): 待创建的 Task 字段。
        platform_snapshot (Mapping[str, Any]): 平台配置快照。
        profile_name (str): `REQUIRED_FIELD_PROFILES` 中的 profile 名。
        require_project_id (bool): 是否要求 `projectId`。
        validate_strict_references (bool): 是否校验严格任务物品绑定。

    返回:
        VerificationResult: Task 创建前校验结果。
    """
    profile = REQUIRED_FIELD_PROFILES[profile_name]
    source_with_fixed_fields = {**profile.get("fixed_fields", {}), **planned_task}
    configuration_gaps: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    resolved: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []
    business_required = _business_required_fields(profile, require_project_id)

    _require_fields(
        source=source_with_fixed_fields,
        fields=profile["openapi_required"],
        scope="task",
        configuration_gaps=configuration_gaps,
        rule_type="openapi_required",
    )
    _require_fields(
        source=planned_task,
        fields=business_required,
        scope="task",
        configuration_gaps=configuration_gaps,
        rule_type="business_profile",
    )

    _check_id_reference(
        value=planned_task.get("sceneId"),
        field="sceneId",
        items=platform_snapshot.get("labels", []),
        id_key="id",
        scope="task",
        configuration_gaps=configuration_gaps,
        resolved=resolved,
    )

    if "deviceTypeId" in planned_task:
        _check_id_reference(
            value=planned_task.get("deviceTypeId"),
            field="deviceTypeId",
            items=platform_snapshot.get("device_types", []),
            id_key="id",
            scope="task",
            configuration_gaps=configuration_gaps,
            resolved=resolved,
        )

    if validate_strict_references:
        for binding in planned_task.get("objectBindings", []) or []:
            if not isinstance(binding, Mapping):
                continue
            _check_id_reference(
                value=binding.get("objectCategoryId"),
                field="objectBindings[].objectCategoryId",
                items=platform_snapshot.get("object_categories", []),
                id_key="id",
                scope="task",
                configuration_gaps=configuration_gaps,
                resolved=resolved,
            )
            for object_item_id in binding.get("objectItemIds", []) or []:
                _check_id_reference(
                    value=object_item_id,
                    field="objectBindings[].objectItemIds",
                    items=platform_snapshot.get("object_items", []),
                    id_key="id",
                    scope="task",
                    configuration_gaps=configuration_gaps,
                    resolved=resolved,
                )

    _add_unconfirmed_rule_warnings(
        source=planned_task,
        scope="task",
        warnings=warnings,
    )

    return _build_result(
        configuration_gaps=configuration_gaps,
        conflicts=conflicts,
        resolved=resolved,
        warnings=warnings,
    )


def _validate_jobs(
    planned_jobs: Sequence[Mapping[str, Any]],
    configuration_gaps: list[dict[str, Any]],
) -> None:
    """校验 Job 的本地结构字段。

    参数:
        planned_jobs (Sequence[Mapping[str, Any]]): 待创建的 Job 列表。
        configuration_gaps (list[dict[str, Any]]): 待追加的缺失配置列表。

    返回:
        None
    """
    for index, job in enumerate(planned_jobs):
        _require_fields(
            source=job,
            fields=REQUIRED_FIELD_PROFILES["job"]["openapi_required"],
            scope="job",
            configuration_gaps=configuration_gaps,
            rule_type="openapi_required",
            field_prefix=f"jobs[{index}].",
        )


def _check_id_reference(
    value: Any,
    field: str,
    items: Any,
    id_key: str,
    scope: str,
    configuration_gaps: list[dict[str, Any]],
    resolved: dict[str, Any],
    skip_when_candidates_missing: bool = False,
) -> None:
    """检查一个 ID 是否存在于平台快照列表中。

    参数:
        value (Any): 计划中引用的 ID。
        field (str): 计划字段名。
        items (Any): 平台快照候选列表。
        id_key (str): 候选项 ID 字段名。
        scope (str): 校验范围。
        configuration_gaps (list[dict[str, Any]]): 待追加的缺失配置列表。
        resolved (dict[str, Any]): 待追加的解析结果。
        skip_when_candidates_missing (bool): 候选池缺失时是否跳过存在性校验。

    返回:
        None
    """
    if value is None:
        return
    if skip_when_candidates_missing and not items:
        resolved[field] = value
        return
    if _contains_id(items, id_key, value):
        resolved[field] = value
        return
    configuration_gaps.append(
        _issue(
            scope=scope,
            field=field,
            expected=value,
            reason="missing",
            message=f"Referenced platform configuration does not exist: {field}={value}",
            rule_type="business_profile",
        )
    )


def _require_fields(
    source: Mapping[str, Any],
    fields: Sequence[str],
    scope: str,
    configuration_gaps: list[dict[str, Any]],
    rule_type: str,
    field_prefix: str = "",
) -> None:
    """检查一组必填字段是否存在且非空。

    参数:
        source (Mapping[str, Any]): 待检查字段来源。
        fields (Sequence[str]): 必填字段名列表。
        scope (str): 校验范围。
        configuration_gaps (list[dict[str, Any]]): 待追加的缺失配置列表。
        rule_type (str): 规则类型。
        field_prefix (str): 嵌套字段展示前缀。

    返回:
        None
    """
    for field in fields:
        if _is_present(source.get(field)):
            continue
        display_field = f"{field_prefix}{field}"
        configuration_gaps.append(
            _issue(
                scope=scope,
                field=display_field,
                expected=f"non-empty {display_field}",
                reason="missing",
                message=f"{display_field} is required.",
                rule_type=rule_type,
            )
        )


def _is_present(value: Any) -> bool:
    """判断字段值是否可视为已提供。

    参数:
        value (Any): 字段值。

    返回:
        bool: 已提供时为 True。
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    return True


def _business_required_fields(profile: Mapping[str, Sequence[str]], require_project_id: bool) -> tuple[str, ...]:
    """根据上下文返回业务 profile 必填字段。

    参数:
        profile (Mapping[str, Sequence[str]]): required profile。
        require_project_id (bool): 是否保留 `projectId` 要求。

    返回:
        tuple[str, ...]: 当前上下文需要校验的业务必填字段。
    """
    fields = tuple(profile["business_required"])
    if require_project_id:
        return fields
    return tuple(field for field in fields if field != "projectId")


def _add_unconfirmed_rule_warnings(
    source: Mapping[str, Any],
    scope: str,
    warnings: list[dict[str, Any]],
) -> None:
    """对尚未确认的平台规则生成非阻塞 warning。

    参数:
        source (Mapping[str, Any]): 待检查字段来源。
        scope (str): 校验范围。
        warnings (list[dict[str, Any]]): 待追加的 warning 列表。

    返回:
        None
    """
    for field in UNCONFIRMED_PLATFORM_RULE_FIELDS:
        if field not in source:
            continue
        warnings.append(
            _issue(
                scope=scope,
                field=field,
                expected="confirmed platform rule",
                reason="unconfirmed",
                message=f"Platform validation rule for {field} is not confirmed yet.",
                rule_type="unconfirmed_platform_rule",
            )
        )


def _build_result(
    configuration_gaps: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    resolved: dict[str, Any],
    warnings: list[dict[str, Any]],
) -> VerificationResult:
    """构造统一的校验结果。

    参数:
        configuration_gaps (list[dict[str, Any]]): 缺失配置列表。
        conflicts (list[dict[str, Any]]): 冲突列表。
        resolved (dict[str, Any]): 解析结果。
        warnings (list[dict[str, Any]]): 非阻塞提示列表。

    返回:
        VerificationResult: 统一校验结果。
    """
    can_create = not configuration_gaps and not conflicts
    return VerificationResult(
        can_create=can_create,
        configuration_gaps=configuration_gaps,
        conflicts=conflicts,
        resolved=resolved if can_create else {},
        warnings=warnings,
    )


def _combine_results(*results: VerificationResult) -> VerificationResult:
    """合并多个能力级校验结果。

    参数:
        *results (VerificationResult): 待合并的校验结果。

    返回:
        VerificationResult: 合并后的校验结果。
    """
    configuration_gaps: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    resolved: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []
    for result in results:
        configuration_gaps.extend(result.configuration_gaps)
        conflicts.extend(result.conflicts)
        warnings.extend(result.warnings)
        if result.can_create:
            resolved.update(result.resolved)
    return _build_result(
        configuration_gaps=configuration_gaps,
        conflicts=conflicts,
        resolved=resolved,
        warnings=warnings,
    )


def _contains_id(items: Any, id_key: str, expected_id: Any) -> bool:
    """判断候选列表是否包含指定 ID。

    参数:
        items (Any): 候选列表。
        id_key (str): ID 字段名。
        expected_id (Any): 预期 ID。

    返回:
        bool: 找到匹配 ID 时为 True。
    """
    return any(isinstance(item, Mapping) and item.get(id_key) == expected_id for item in items or [])


def _find_by_field(items: Any, field: str, expected: Any) -> list[dict[str, Any]]:
    """按字段值查找平台快照候选项。

    参数:
        items (Any): 候选列表。
        field (str): 字段名。
        expected (Any): 预期字段值。

    返回:
        list[dict[str, Any]]: 匹配的候选项列表。
    """
    return [
        dict(item)
        for item in items or []
        if isinstance(item, Mapping) and item.get(field) == expected
    ]


def _issue(
    scope: str,
    field: str,
    expected: Any,
    reason: str,
    message: str,
    rule_type: str,
    candidates: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """构造统一的校验问题对象。

    参数:
        scope (str): 问题所属范围。
        field (str): 失败字段。
        expected (Any): 期望值。
        reason (str): 失败原因。
        message (str): 面向人的说明。
        rule_type (str): 规则类型。
        candidates (Sequence[Mapping[str, Any]] | None): 可选候选项。

    返回:
        dict[str, Any]: 校验问题对象。
    """
    issue = {
        "scope": scope,
        "field": field,
        "expected": expected,
        "reason": reason,
        "rule_type": rule_type,
        "message": message,
    }
    if candidates:
        issue["candidates"] = [dict(item) for item in candidates]
    return issue
