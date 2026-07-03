"""Zata 平台 HTTP 基础调用器和业务接口调用器。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence
from urllib import error, parse, request


class APIRequestError(Exception):
    """HTTP 请求失败时抛出的异常。"""


@dataclass
class APIResponse:
    """统一封装 HTTP 响应结果。"""

    status_code: int
    headers: Dict[str, str]
    body: Any
    raw_text: str


@dataclass
class APICallerConfig:
    """接口调用器配置。"""

    base_url: str
    timeout: float = 30.0
    default_headers: Dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )


@dataclass
class TaskUserReq:
    """任务人员请求对象。"""

    userId: str
    displayName: Optional[str] = None
    enabled: Optional[bool] = None
    userName: Optional[str] = None


@dataclass
class TaskActionStepReq:
    """任务动作步骤请求对象。"""

    actionText: str
    stepOrder: int
    atomicAbilityId: Optional[int] = None
    deviation: Optional[float] = None
    duration: Optional[float] = None


@dataclass
class TaskObjectBindingReq:
    """任务物品绑定请求对象。"""

    objectCategoryId: int
    placeholder: str
    objectItemIds: Optional[Sequence[int]] = None


@dataclass
class TaskTemplateItemReq:
    """严格任务模板创建请求项。"""

    templateId: int
    autoCreateInstance: Optional[bool] = None
    jobCount: Optional[int] = None
    jobPlanCollectCount: Optional[int] = None


@dataclass
class JobItemReq:
    """job 子项请求对象。"""

    displayName: str
    img: str
    name: str
    type: int
    value: int
    valueName: str
    id: Optional[int] = None


@dataclass
class CreateJobReq:
    """创建 job 请求对象。"""

    requiredRepeat: int
    description: Optional[str] = None
    items: Optional[Sequence[JobItemReq]] = None
    name: Optional[str] = None
    requiredMember: Optional[int] = None
    type: Optional[int] = None


class APICaller:
    """提供通用 HTTP 请求能力的基础类。"""

    def __init__(self, config: APICallerConfig):
        """初始化基础调用器。

        参数:
            config (APICallerConfig): 服务地址、超时时间和通用请求头配置。

        返回:
            None
        """
        self.config = config

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> APIResponse:
        """发送通用 HTTP 请求。

        参数:
            method (str): HTTP 方法，例如 GET、POST。
            path (str): 相对于 base_url 的接口路径。
            params (Optional[Mapping[str, Any]]): 查询参数。
            json_body (Optional[Mapping[str, Any]]): JSON 请求体。
            headers (Optional[Mapping[str, str]]): 本次请求使用的额外请求头。
            timeout (Optional[float]): 本次请求的超时时间。

        返回:
            APIResponse: 标准化响应对象。
        """
        url = self.build_url(path=path, params=params)
        request_headers = self._build_headers(extra_headers=headers)
        request_data = None
        if json_body is not None:
            request_data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url=url,
            data=request_data,
            headers=request_headers,
            method=method.upper(),
        )
        request_timeout = self.config.timeout if timeout is None else timeout
        try:
            with request.urlopen(req, timeout=request_timeout) as response:
                raw_text = response.read().decode("utf-8")
                parsed_body = self._parse_response_text(raw_text=raw_text)
                return APIResponse(
                    status_code=response.status,
                    headers=dict(response.headers.items()),
                    body=parsed_body,
                    raw_text=raw_text,
                )
        except error.HTTPError as exc:
            raw_text = exc.read().decode("utf-8", errors="replace")
            raise APIRequestError(f"HTTP {exc.code} 请求失败: {raw_text}") from exc
        except error.URLError as exc:
            raise APIRequestError(f"网络请求失败: {exc.reason}") from exc

    def build_url(
        self, path: str, params: Optional[Mapping[str, Any]] = None
    ) -> str:
        """构造带查询参数的完整 URL。

        参数:
            path (str): 相对于 base_url 的接口路径。
            params (Optional[Mapping[str, Any]]): 查询参数。

        返回:
            str: 拼接后的完整 URL。
        """
        normalized_path = path if path.startswith("/") else f"/{path}"
        base_url = self.config.base_url.rstrip("/")
        url = f"{base_url}{normalized_path}"
        if not params:
            return url
        query_pairs = {key: value for key, value in params.items() if value is not None}
        if not query_pairs:
            return url
        return f"{url}?{parse.urlencode(query_pairs, doseq=True)}"

    def _build_headers(
        self, extra_headers: Optional[Mapping[str, str]] = None
    ) -> MutableMapping[str, str]:
        """合并调用器配置和本次请求的请求头。

        参数:
            extra_headers (Optional[Mapping[str, str]]): 本次请求附加请求头。

        返回:
            MutableMapping[str, str]: 合并后的请求头。
        """
        headers: MutableMapping[str, str] = dict(self.config.default_headers)
        if extra_headers:
            headers.update(dict(extra_headers))
        return headers

    @staticmethod
    def _parse_response_text(raw_text: str) -> Any:
        """解析响应文本，优先按 JSON 解析。

        参数:
            raw_text (str): 原始响应文本。

        返回:
            Any: JSON 对象或原始响应字符串。
        """
        if not raw_text:
            return None
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return raw_text


def _to_json_value(value: Any) -> Any:
    """将结构化请求值转换为平台 JSON 值。

    参数:
        value (Any): 原始值，支持 dataclass、dict、list、tuple 和基础类型。

    返回:
        Any: 可 JSON 序列化的值。
    """
    if is_dataclass(value):
        return {
            item.name: _to_json_value(getattr(value, item.name))
            for item in fields(value)
            if getattr(value, item.name) is not None
        }
    if isinstance(value, Mapping):
        return {
            key: _to_json_value(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    return value


def _build_json_body(**items: Any) -> Dict[str, Any]:
    """从显式字段构造平台 JSON 请求体。

    参数:
        **items (Any): OpenAPI 字段名到字段值的映射。

    返回:
        Dict[str, Any]: 已移除 None 的 JSON 请求体。
    """
    return {
        key: _to_json_value(value)
        for key, value in items.items()
        if value is not None
    }


def _extract_metadata_items(body: Any) -> list[Any]:
    """从平台响应体中提取列表数据。

    参数:
        body (Any): APIResponse.body 或其中的 metadata 对象。

    返回:
        list[Any]: 提取出的列表数据；无法提取时返回空列表。
    """
    source = body.get("metadata", body) if isinstance(body, dict) else body
    if isinstance(source, list):
        return list(source)
    if not isinstance(source, dict):
        return []
    for key in ("records", "results", "list", "items", "data", "rows", "content"):
        value = source.get(key)
        if isinstance(value, list):
            return list(value)
    return []


def _flatten_label_nodes(
    nodes: list[Any], category_code: str, parent_id: Optional[int] = None
) -> list[Dict[str, Any]]:
    """将标签树节点展开为便于检索的扁平列表。

    参数:
        nodes (list[Any]): 标签树节点列表。
        category_code (str): 当前标签分类编码。
        parent_id (Optional[int]): 父标签 ID。

    返回:
        list[Dict[str, Any]]: 包含 categoryCode、id、code、name、parentId 的标签索引。
    """
    labels: list[Dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        labels.append(
            {
                "categoryCode": node.get("categoryCode") or category_code,
                "id": node_id,
                "code": node.get("code"),
                "name": node.get("name") or node.get("labelName") or node.get("title"),
                "parentId": node.get("parentId", parent_id),
            }
        )
        for child_key in ("children", "childNodes", "labels"):
            children = node.get(child_key)
            if isinstance(children, list):
                labels.extend(
                    _flatten_label_nodes(
                        nodes=children,
                        category_code=category_code,
                        parent_id=node_id if isinstance(node_id, int) else parent_id,
                    )
                )
    return labels


def _flatten_object_categories(
    nodes: list[Any], parent_id: Optional[int] = None
) -> list[Dict[str, Any]]:
    """将物品目录树展开为扁平列表。

    参数:
        nodes (list[Any]): 物品目录树节点列表。
        parent_id (Optional[int]): 父目录 ID。

    返回:
        list[Dict[str, Any]]: 包含 id、name、path、level、parentId 的目录索引。
    """
    categories: list[Dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        categories.append(
            {
                "id": node_id,
                "name": node.get("name"),
                "path": node.get("path"),
                "level": node.get("level"),
                "parentId": node.get("parentId", parent_id),
            }
        )
        children = node.get("children")
        if isinstance(children, list):
            categories.extend(
                _flatten_object_categories(
                    nodes=children,
                    parent_id=node_id if isinstance(node_id, int) else parent_id,
                )
            )
    return categories


class ZataAPICaller(APICaller):
    """封装 Zata RBAC 与 data-manager 业务接口的调用器。"""

    RBAC_PREFIX = "/api/zata-rbac"
    DATA_MANAGER_PREFIX = "/api/zata-manager"

    def __init__(self, config: APICallerConfig):
        """初始化 Zata 业务调用器。

        参数:
            config (APICallerConfig): Zata 平台根地址和通用请求配置。

        返回:
            None
        """
        super().__init__(config)
        self._access_token: Optional[str] = None

    def set_access_token(self, access_token: str) -> None:
        """设置后续受保护接口使用的 Bearer token。

        参数:
            access_token (str): 登录接口返回的访问令牌。

        返回:
            None
        """
        self._access_token = access_token

    def clear_access_token(self) -> None:
        """清除当前调用器保存的访问令牌。

        参数:
            无

        返回:
            None
        """
        self._access_token = None

    def _request_rbac(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
    ) -> APIResponse:
        """发送 zata-rbac 私有底层请求。

        参数:
            method (str): HTTP 方法。
            path (str): RBAC 资源路径。
            params (Optional[Mapping[str, Any]]): 查询参数。
            json_body (Optional[Mapping[str, Any]]): JSON 请求体。

        返回:
            APIResponse: 接口响应结果。
        """
        return self.request(
            method=method,
            path=self._rbac_path(path),
            params=params,
            json_body=json_body,
        )

    def _request_data_manager(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
    ) -> APIResponse:
        """发送 data-manager 私有底层请求。

        参数:
            method (str): HTTP 方法。
            path (str): data-manager 资源路径。
            params (Optional[Mapping[str, Any]]): 查询参数。
            json_body (Optional[Mapping[str, Any]]): JSON 请求体。

        返回:
            APIResponse: 接口响应结果。
        """
        return self.request(
            method=method,
            path=self._data_manager_path(path),
            params=params,
            json_body=json_body,
        )

    def userinfo(self) -> APIResponse:
        """查询当前登录用户信息。

        参数:
            无

        返回:
            APIResponse: 当前用户信息接口响应结果。
        """
        return self._request_rbac(method="GET", path="/userinfo")

    def login(self, username: str, password: str, organization: str) -> APIResponse:
        """调用 zata-rbac 登录接口并保存返回的 token。

        参数:
            username (str): 登录用户名。
            password (str): 登录密码。
            organization (str): Casdoor 组织标识。

        返回:
            APIResponse: 登录接口响应结果。
        """
        json_body = {"username": username, "password": password, "organization": organization}
        saved_access_token = self._access_token
        self._access_token = None
        try:
            response = self._request_rbac(
                method="POST", path="/login", json_body=json_body
            )
        finally:
            self._access_token = saved_access_token
        metadata = response.body.get("metadata", {}) if isinstance(response.body, dict) else {}
        access_token = metadata.get("accessToken")
        if access_token:
            self.set_access_token(access_token=access_token)
        return response

    def create_task(
        self,
        sceneId: int,
        title: str,
        collectMethod: str,
        taskCategory: str,
        projectId: Optional[int] = None,
        abnormalPlanCount: Optional[int] = None,
        abnormalRatio: Optional[float] = None,
        actionSteps: Optional[Sequence[TaskActionStepReq]] = None,
        aiCapabilities: Optional[Sequence[str]] = None,
        auditors: Optional[Sequence[TaskUserReq]] = None,
        collectModeId: Optional[int] = None,
        collectSchemeId: Optional[int] = None,
        collectors: Optional[Sequence[TaskUserReq]] = None,
        countdownSeconds: Optional[int] = None,
        customLabelIds: Optional[Sequence[int]] = None,
        description: Optional[str] = None,
        deviceTypeId: Optional[int] = None,
        difficulty: Optional[int] = None,
        duration: Optional[float] = None,
        initialState: Optional[str] = None,
        minDuration: Optional[float] = None,
        normalPlanCount: Optional[int] = None,
        objectBindings: Optional[Sequence[TaskObjectBindingReq]] = None,
        planCollectCount: Optional[int] = None,
        promptInstruction: Optional[str] = None,
        recognitionEnabled: Optional[bool] = None,
        remark: Optional[str] = None,
        sensorTypeId: Optional[int] = None,
        spaceId: Optional[int] = None,
        spaceIds: Optional[Sequence[int]] = None,
        templateId: Optional[int] = None,
        taskPurposeId: Optional[int] = None,
        taskType: Optional[int] = None,
        videoQuality: Optional[int] = None,
    ) -> APIResponse:
        """创建采集任务。

        参数:
            sceneId (int): 场景标签 ID。
            title (str): 任务标题。
            collectMethod (str): 采集方式，例如 robot 或 web_video。
            taskCategory (str): 任务分类，例如 strict、instruction 或 scene。
            projectId (Optional[int]): 项目 ID；提供时在项目下创建任务。

        返回:
            APIResponse: 创建任务接口响应结果。
        """
        json_body = _build_json_body(
            abnormalPlanCount=abnormalPlanCount,
            abnormalRatio=abnormalRatio,
            actionSteps=actionSteps,
            aiCapabilities=aiCapabilities,
            auditors=auditors,
            collectMethod=collectMethod,
            collectModeId=collectModeId,
            collectSchemeId=collectSchemeId,
            collectors=collectors,
            countdownSeconds=countdownSeconds,
            customLabelIds=customLabelIds,
            description=description,
            deviceTypeId=deviceTypeId,
            difficulty=difficulty,
            duration=duration,
            initialState=initialState,
            minDuration=minDuration,
            normalPlanCount=normalPlanCount,
            objectBindings=objectBindings,
            planCollectCount=planCollectCount,
            projectId=projectId,
            promptInstruction=promptInstruction,
            recognitionEnabled=recognitionEnabled,
            remark=remark,
            sceneId=sceneId,
            sensorTypeId=sensorTypeId,
            spaceId=spaceId,
            spaceIds=spaceIds,
            taskCategory=taskCategory,
            taskPurposeId=taskPurposeId,
            taskType=taskType,
            templateId=templateId,
            title=title,
            videoQuality=videoQuality,
        )
        resource_path = f"/projects/{projectId}/tasks" if projectId is not None else "/tasks"
        return self._request_data_manager(
            method="POST", path=resource_path, json_body=json_body
        )

    def create_jobs(self, taskId: int, jobs: Sequence[CreateJobReq]) -> APIResponse:
        """在指定任务下批量创建采集作业。

        参数:
            taskId (int): 任务 ID。
            jobs (Sequence[CreateJobReq]): 待创建 job 列表。

        返回:
            APIResponse: 创建作业接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path=f"/tasks/{taskId}/jobs",
            json_body=_build_json_body(jobs=jobs),
        )

    def create_strict_task(
        self,
        sceneId: int,
        title: str,
        projectId: int,
        abnormalPlanCount: Optional[int] = None,
        abnormalRatio: Optional[float] = None,
        actionSteps: Optional[Sequence[TaskActionStepReq]] = None,
        auditors: Optional[Sequence[TaskUserReq]] = None,
        collectMethod: str = "robot",
        collectModeId: Optional[int] = None,
        collectSchemeId: Optional[int] = None,
        collectors: Optional[Sequence[TaskUserReq]] = None,
        countdownSeconds: Optional[int] = None,
        customLabelIds: Optional[Sequence[int]] = None,
        description: Optional[str] = None,
        deviceTypeId: Optional[int] = None,
        difficulty: Optional[int] = None,
        duration: Optional[float] = None,
        initialState: Optional[str] = None,
        minDuration: Optional[float] = None,
        normalPlanCount: Optional[int] = None,
        objectBindings: Optional[Sequence[TaskObjectBindingReq]] = None,
        planCollectCount: Optional[int] = None,
        recognitionEnabled: Optional[bool] = None,
        remark: Optional[str] = None,
        sensorTypeId: Optional[int] = None,
        spaceIds: Optional[Sequence[int]] = None,
        taskPurposeId: Optional[int] = None,
        taskType: Optional[int] = None,
        videoQuality: Optional[int] = None,
    ) -> APIResponse:
        """直接创建严格采集任务。

        参数:
            sceneId (int): 场景标签 ID。
            title (str): 任务标题。
            projectId (int): 项目 ID。

        返回:
            APIResponse: 创建严格采集任务接口响应结果。
        """
        json_body = _build_json_body(
            abnormalPlanCount=abnormalPlanCount,
            abnormalRatio=abnormalRatio,
            actionSteps=actionSteps,
            auditors=auditors,
            collectMethod=collectMethod,
            collectModeId=collectModeId,
            collectSchemeId=collectSchemeId,
            collectors=collectors,
            countdownSeconds=countdownSeconds,
            customLabelIds=customLabelIds,
            description=description,
            deviceTypeId=deviceTypeId,
            difficulty=difficulty,
            duration=duration,
            initialState=initialState,
            minDuration=minDuration,
            normalPlanCount=normalPlanCount,
            objectBindings=objectBindings,
            planCollectCount=planCollectCount,
            projectId=projectId,
            recognitionEnabled=recognitionEnabled,
            remark=remark,
            sceneId=sceneId,
            sensorTypeId=sensorTypeId,
            spaceIds=spaceIds,
            taskCategory="strict",
            taskPurposeId=taskPurposeId,
            taskType=taskType,
            title=title,
            videoQuality=videoQuality,
        )
        return self._request_data_manager(
            method="POST",
            path=f"/projects/{projectId}/tasks",
            json_body=json_body,
        )

    def create_scene_task(
        self,
        sceneId: int,
        title: str,
        projectId: int,
        auditors: Optional[Sequence[TaskUserReq]] = None,
        collectMethod: str = "web_video",
        collectModeId: Optional[int] = None,
        collectSchemeId: Optional[int] = None,
        collectors: Optional[Sequence[TaskUserReq]] = None,
        customLabelIds: Optional[Sequence[int]] = None,
        description: Optional[str] = None,
        deviceTypeId: Optional[int] = None,
        difficulty: Optional[int] = None,
        planCollectCount: Optional[int] = None,
        recognitionEnabled: Optional[bool] = None,
        spaceIds: Optional[Sequence[int]] = None,
        taskPurposeId: Optional[int] = None,
        taskType: Optional[int] = None,
        videoQuality: Optional[int] = None,
    ) -> APIResponse:
        """创建场景采集任务。

        参数:
            sceneId (int): 场景标签 ID。
            title (str): 任务标题。
            projectId (int): 项目 ID。

        返回:
            APIResponse: 创建场景采集任务接口响应结果。
        """
        json_body = _build_json_body(
            auditors=auditors,
            collectMethod=collectMethod,
            collectModeId=collectModeId,
            collectSchemeId=collectSchemeId,
            collectors=collectors,
            customLabelIds=customLabelIds,
            description=description,
            deviceTypeId=deviceTypeId,
            difficulty=difficulty,
            planCollectCount=planCollectCount,
            projectId=projectId,
            recognitionEnabled=recognitionEnabled,
            sceneId=sceneId,
            spaceIds=spaceIds,
            taskCategory="scene",
            taskPurposeId=taskPurposeId,
            taskType=taskType,
            title=title,
            videoQuality=videoQuality,
        )
        return self._request_data_manager(
            method="POST",
            path=f"/projects/{projectId}/tasks",
            json_body=json_body,
        )

    def create_instruction_task(
        self,
        sceneId: int,
        title: str,
        promptInstruction: str,
        projectId: int,
        aiCapabilities: Optional[Sequence[str]] = None,
        auditors: Optional[Sequence[TaskUserReq]] = None,
        collectModeId: Optional[int] = None,
        collectSchemeId: Optional[int] = None,
        collectors: Optional[Sequence[TaskUserReq]] = None,
        customLabelIds: Optional[Sequence[int]] = None,
        description: Optional[str] = None,
        planCollectCount: Optional[int] = None,
        recognitionEnabled: Optional[bool] = None,
        spaceId: Optional[int] = None,
        spaceIds: Optional[Sequence[int]] = None,
        taskPurposeId: Optional[int] = None,
        videoQuality: Optional[int] = None,
    ) -> APIResponse:
        """创建指令采集任务。

        参数:
            sceneId (int): 场景标签 ID。
            title (str): 任务标题。
            promptInstruction (str): 指令任务提示文本。
            projectId (int): 项目 ID。

        返回:
            APIResponse: 创建指令采集任务接口响应结果。
        """
        json_body = _build_json_body(
            aiCapabilities=aiCapabilities,
            auditors=auditors,
            collectMethod="web_video",
            collectModeId=collectModeId,
            collectSchemeId=collectSchemeId,
            collectors=collectors,
            customLabelIds=customLabelIds,
            description=description,
            planCollectCount=planCollectCount,
            projectId=projectId,
            promptInstruction=promptInstruction,
            recognitionEnabled=recognitionEnabled,
            sceneId=sceneId,
            spaceId=spaceId,
            spaceIds=spaceIds,
            taskCategory="instruction",
            taskPurposeId=taskPurposeId,
            title=title,
            videoQuality=videoQuality,
        )
        return self._request_data_manager(
            method="POST",
            path=f"/projects/{projectId}/tasks",
            json_body=json_body,
        )

    def create_strict_task_from_template(
        self,
        projectId: int,
        templateItems: Sequence[TaskTemplateItemReq],
        abnormalPlanCount: Optional[int] = None,
        abnormalRatio: Optional[float] = None,
        aiCapabilities: Optional[Sequence[str]] = None,
        auditors: Optional[Sequence[TaskUserReq]] = None,
        collectMethod: str = "robot",
        collectModeId: Optional[int] = None,
        collectSchemeId: Optional[int] = None,
        collectors: Optional[Sequence[TaskUserReq]] = None,
        countdownSeconds: Optional[int] = None,
        customLabelIds: Optional[Sequence[int]] = None,
        deviceTypeId: Optional[int] = None,
        duration: Optional[float] = None,
        minDuration: Optional[float] = None,
        normalPlanCount: Optional[int] = None,
        planCollectCount: Optional[int] = None,
        recognitionEnabled: Optional[bool] = None,
        sensorTypeId: Optional[int] = None,
        taskPurposeId: Optional[int] = None,
        videoQuality: Optional[int] = None,
    ) -> APIResponse:
        """通过场景任务库模板创建严格采集任务。

        参数:
            projectId (int): 项目 ID。
            templateItems (Sequence[TaskTemplateItemReq]): 模板项列表。

        返回:
            APIResponse: 模板创建严格采集任务接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path=f"/projects/{projectId}/tasks/from-template",
            json_body=_build_json_body(
                abnormalPlanCount=abnormalPlanCount,
                abnormalRatio=abnormalRatio,
                aiCapabilities=aiCapabilities,
                auditors=auditors,
                collectMethod=collectMethod,
                collectModeId=collectModeId,
                collectSchemeId=collectSchemeId,
                collectors=collectors,
                countdownSeconds=countdownSeconds,
                customLabelIds=customLabelIds,
                deviceTypeId=deviceTypeId,
                duration=duration,
                minDuration=minDuration,
                normalPlanCount=normalPlanCount,
                planCollectCount=planCollectCount,
                projectId=projectId,
                recognitionEnabled=recognitionEnabled,
                sensorTypeId=sensorTypeId,
                taskPurposeId=taskPurposeId,
                templateItems=templateItems,
                videoQuality=videoQuality,
            ),
        )

    def list_projects(
        self,
        name: Optional[str] = None,
        sceneId: Optional[int] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询项目列表。

        参数:
            name (Optional[str]): 项目名称。
            sceneId (Optional[int]): 场景标签 ID。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: 项目列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path="/projects",
            params=_build_json_body(name=name, sceneId=sceneId, pageNum=pageNum, pageSize=pageSize),
        )

    def get_project(self, projectId: int) -> APIResponse:
        """查询项目详情。

        参数:
            projectId (int): 项目 ID。

        返回:
            APIResponse: 项目详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/projects/{projectId}")

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        sceneIds: Optional[Sequence[int]] = None,
        status: Optional[int] = None,
    ) -> APIResponse:
        """创建项目。

        参数:
            name (str): 项目名称。
            description (Optional[str]): 项目描述。
            sceneIds (Optional[Sequence[int]]): 场景标签 ID 列表。
            status (Optional[int]): 状态。

        返回:
            APIResponse: 创建项目接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/projects",
            json_body=_build_json_body(
                description=description,
                name=name,
                sceneIds=sceneIds,
                status=status,
            ),
        )

    def update_project(
        self,
        projectId: int,
        name: str,
        description: Optional[str] = None,
        sceneIds: Optional[Sequence[int]] = None,
        status: Optional[int] = None,
    ) -> APIResponse:
        """更新项目。

        参数:
            projectId (int): 项目 ID。
            name (str): 项目名称。

        返回:
            APIResponse: 项目更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/projects/{projectId}",
            json_body=_build_json_body(
                description=description,
                name=name,
                sceneIds=sceneIds,
                status=status,
            ),
        )

    def delete_project(self, projectId: int) -> APIResponse:
        """删除项目。

        参数:
            projectId (int): 项目 ID。

        返回:
            APIResponse: 项目删除接口响应结果。
        """
        return self._request_data_manager(method="DELETE", path=f"/projects/{projectId}")

    def list_label_categories(self, name: Optional[str] = None) -> APIResponse:
        """查询标签分类列表。

        参数:
            name (Optional[str]): 标签分类名称。

        返回:
            APIResponse: 标签分类列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET", path="/label-categories", params=_build_json_body(name=name)
        )

    def list_labels(
        self,
        categoryCode: Optional[str] = None,
        parentId: Optional[int] = None,
        name: Optional[str] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询标签列表。

        参数:
            categoryCode (Optional[str]): 标签分类编码。
            parentId (Optional[int]): 父标签 ID。
            name (Optional[str]): 标签名称。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: 标签列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path="/labels",
            params=_build_json_body(
                categoryCode=categoryCode,
                parentId=parentId,
                name=name,
                pageNum=pageNum,
                pageSize=pageSize,
            ),
        )

    def list_labels_by_category(
        self,
        categoryCode: str,
        parentId: Optional[int] = None,
        name: Optional[str] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """按分类查询任务字段可引用的标签候选值。

        参数:
            categoryCode (str): 标签分类编码，由标签分类查询结果或调用方提供。
            parentId (Optional[int]): 父标签 ID 筛选值。
            name (Optional[str]): 标签名称筛选值。
            pageNum (Optional[int]): 页码筛选值。
            pageSize (Optional[int]): 每页数量筛选值。

        返回:
            APIResponse: 指定分类下的标签列表接口响应结果。
        """
        params = {
            "categoryCode": categoryCode,
            "parentId": parentId,
            "name": name,
            "pageNum": pageNum,
            "pageSize": pageSize,
        }
        return self._request_data_manager(method="GET", path="/labels", params=params)

    def get_label_category(self, categoryCode: str) -> APIResponse:
        """按编码查询标签分类。

        参数:
            categoryCode (str): 标签分类编码。

        返回:
            APIResponse: 标签分类详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/label-categories/{categoryCode}")

    def create_label_category(
        self,
        name: str,
        code: Optional[str] = None,
        description: Optional[str] = None,
        isMultiple: Optional[bool] = None,
        isTree: Optional[bool] = None,
        parentCode: Optional[str] = None,
        sortOrder: Optional[int] = None,
        status: Optional[int] = None,
    ) -> APIResponse:
        """创建标签分类。

        参数:
            name (str): 标签分类名称。

        返回:
            APIResponse: 标签分类创建接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/label-categories",
            json_body=_build_json_body(
                code=code,
                description=description,
                isMultiple=isMultiple,
                isTree=isTree,
                name=name,
                parentCode=parentCode,
                sortOrder=sortOrder,
                status=status,
            ),
        )

    def update_label_category(
        self,
        categoryCode: str,
        name: str,
        description: Optional[str] = None,
        isMultiple: Optional[bool] = None,
        isTree: Optional[bool] = None,
        parentCode: Optional[str] = None,
        sortOrder: Optional[int] = None,
        status: Optional[int] = None,
    ) -> APIResponse:
        """更新标签分类。

        参数:
            categoryCode (str): 标签分类编码。
            name (str): 标签分类名称。

        返回:
            APIResponse: 标签分类更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/label-categories/{categoryCode}",
            json_body=_build_json_body(
                description=description,
                isMultiple=isMultiple,
                isTree=isTree,
                name=name,
                parentCode=parentCode,
                sortOrder=sortOrder,
                status=status,
            ),
        )

    def delete_label_category(self, categoryCode: str) -> APIResponse:
        """删除标签分类。

        参数:
            categoryCode (str): 标签分类编码。

        返回:
            APIResponse: 标签分类删除接口响应结果。
        """
        return self._request_data_manager(method="DELETE", path=f"/label-categories/{categoryCode}")

    def get_label(self, labelId: int) -> APIResponse:
        """按 ID 查询标签。

        参数:
            labelId (int): 标签 ID。

        返回:
            APIResponse: 标签详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/labels/{labelId}")

    def create_label(
        self,
        categoryCode: str,
        name: str,
        code: Optional[str] = None,
        description: Optional[str] = None,
        parentId: Optional[int] = None,
        sortOrder: Optional[int] = None,
    ) -> APIResponse:
        """创建标签。

        参数:
            categoryCode (str): 标签分类编码。
            name (str): 标签名称。

        返回:
            APIResponse: 标签创建接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/labels",
            json_body=_build_json_body(
                categoryCode=categoryCode,
                code=code,
                description=description,
                name=name,
                parentId=parentId,
                sortOrder=sortOrder,
            ),
        )

    def update_label(
        self,
        labelId: int,
        name: str,
        description: Optional[str] = None,
        sortOrder: Optional[int] = None,
    ) -> APIResponse:
        """更新标签。

        参数:
            labelId (int): 标签 ID。
            name (str): 标签名称。

        返回:
            APIResponse: 标签更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/labels/{labelId}",
            json_body=_build_json_body(
                description=description,
                name=name,
                sortOrder=sortOrder,
            ),
        )

    def delete_label(self, labelId: int) -> APIResponse:
        """删除标签。

        参数:
            labelId (int): 标签 ID。

        返回:
            APIResponse: 标签删除接口响应结果。
        """
        return self._request_data_manager(method="DELETE", path=f"/labels/{labelId}")

    def get_label_tree(
        self,
        categoryCode: str,
        parentId: Optional[int] = None,
        name: Optional[str] = None,
    ) -> APIResponse:
        """查询指定分类下的标签树。

        参数:
            categoryCode (str): 标签分类编码，接口必填字段。
            parentId (Optional[int]): 作为查询根节点的父标签 ID。
            name (Optional[str]): 标签名称筛选值。

        返回:
            APIResponse: 标签树接口响应结果。
        """
        params = {"categoryCode": categoryCode, "parentId": parentId, "name": name}
        return self._request_data_manager(method="GET", path="/labels/tree", params=params)

    def list_scene_labels(
        self, parentId: Optional[int] = None, name: Optional[str] = None
    ) -> APIResponse:
        """查询任务创建时可选用的场景标签树。

        参数:
            parentId (Optional[int]): 作为查询根节点的父场景标签 ID。
            name (Optional[str]): 场景标签名称筛选值。

        返回:
            APIResponse: `scene` 分类的标签树接口响应结果。
        """
        return self.get_label_tree(categoryCode="scene", parentId=parentId, name=name)

    def list_object_categories(
        self, name: Optional[str] = None
    ) -> APIResponse:
        """查询物品目录树。

        参数:
            name (Optional[str]): 目录名称筛选值。

        返回:
            APIResponse: 物品目录树接口响应结果。
        """
        return self._request_data_manager(
            method="GET", path="/object-categories", params=_build_json_body(name=name)
        )

    def create_object_category(
        self,
        name: str,
        parentId: Optional[int] = None,
        sortOrder: Optional[int] = None,
        status: Optional[int] = None,
    ) -> APIResponse:
        """创建物品目录。

        参数:
            name (str): 目录名称。

        返回:
            APIResponse: 物品目录创建接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/object-categories",
            json_body=_build_json_body(
                name=name,
                parentId=parentId,
                sortOrder=sortOrder,
                status=status,
            ),
        )

    def update_object_category(
        self,
        objectCategoryId: int,
        name: str,
        sortOrder: Optional[int] = None,
        status: Optional[int] = None,
    ) -> APIResponse:
        """更新物品目录。

        参数:
            objectCategoryId (int): 物品目录 ID。
            name (str): 目录名称。

        返回:
            APIResponse: 物品目录更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/object-categories/{objectCategoryId}",
            json_body=_build_json_body(name=name, sortOrder=sortOrder, status=status),
        )

    def delete_object_category(self, objectCategoryId: int) -> APIResponse:
        """删除物品目录。

        参数:
            objectCategoryId (int): 物品目录 ID。

        返回:
            APIResponse: 物品目录删除接口响应结果。
        """
        return self._request_data_manager(
            method="DELETE", path=f"/object-categories/{objectCategoryId}"
        )

    def list_object_items(
        self,
        categoryId: Optional[int] = None,
        keyword: Optional[str] = None,
        ids: Optional[Sequence[int]] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询物品列表。

        参数:
            categoryId (Optional[int]): 物品目录 ID。
            keyword (Optional[str]): 关键词。
            ids (Optional[Sequence[int]]): 物品 ID 列表。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: 物品列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path="/object-items",
            params=_build_json_body(
                categoryId=categoryId,
                keyword=keyword,
                ids=ids,
                pageNum=pageNum,
                pageSize=pageSize,
            ),
        )

    def create_object_item(
        self,
        categoryId: int,
        name: str,
        code: Optional[str] = None,
        description: Optional[str] = None,
        fileObjectKey: Optional[str] = None,
        fileUrl: Optional[str] = None,
        status: Optional[int] = None,
        thumbnailObjectKey: Optional[str] = None,
        thumbnailUrl: Optional[str] = None,
    ) -> APIResponse:
        """创建物品。

        参数:
            categoryId (int): 物品目录 ID。
            name (str): 物品名称。

        返回:
            APIResponse: 物品创建接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/object-items",
            json_body=_build_json_body(
                categoryId=categoryId,
                code=code,
                description=description,
                fileObjectKey=fileObjectKey,
                fileUrl=fileUrl,
                name=name,
                status=status,
                thumbnailObjectKey=thumbnailObjectKey,
                thumbnailUrl=thumbnailUrl,
            ),
        )

    def update_object_item(
        self,
        objectItemId: int,
        categoryId: int,
        name: str,
        code: Optional[str] = None,
        description: Optional[str] = None,
        fileObjectKey: Optional[str] = None,
        fileUrl: Optional[str] = None,
        status: Optional[int] = None,
        thumbnailObjectKey: Optional[str] = None,
        thumbnailUrl: Optional[str] = None,
    ) -> APIResponse:
        """更新物品。

        参数:
            objectItemId (int): 物品 ID。
            categoryId (int): 物品目录 ID。
            name (str): 物品名称。

        返回:
            APIResponse: 物品更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/object-items/{objectItemId}",
            json_body=_build_json_body(
                categoryId=categoryId,
                code=code,
                description=description,
                fileObjectKey=fileObjectKey,
                fileUrl=fileUrl,
                name=name,
                status=status,
                thumbnailObjectKey=thumbnailObjectKey,
                thumbnailUrl=thumbnailUrl,
            ),
        )

    def delete_object_item(self, objectItemId: int) -> APIResponse:
        """删除物品。

        参数:
            objectItemId (int): 物品 ID。

        返回:
            APIResponse: 物品删除接口响应结果。
        """
        return self._request_data_manager(method="DELETE", path=f"/object-items/{objectItemId}")

    def list_scene_task_templates(
        self,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
        title: Optional[str] = None,
        mainSceneId: Optional[int] = None,
        taskType: Optional[int] = None,
        sceneId: Optional[int] = None,
    ) -> APIResponse:
        """查询场景任务库模板列表。

        参数:
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。
            title (Optional[str]): 模板标题模糊查询值。
            mainSceneId (Optional[int]): 主场景标签 ID。
            taskType (Optional[int]): 任务类型。
            sceneId (Optional[int]): 场景标签 ID。

        返回:
            APIResponse: 场景任务库模板列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path="/templates",
            params=_build_json_body(
                title=title,
                mainSceneId=mainSceneId,
                taskType=taskType,
                sceneId=sceneId,
                pageNum=pageNum,
                pageSize=pageSize,
            ),
        )

    def get_scene_task_template(self, templateId: int) -> APIResponse:
        """查询场景任务库模板详情。

        参数:
            templateId (int): 模板 ID。

        返回:
            APIResponse: 场景任务库模板详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/templates/{templateId}")

    def list_device_types(
        self,
        name: Optional[str] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询设备类型候选列表。

        参数:
            name (Optional[str]): 设备类型名称。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: 设备类型列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path="/device-types",
            params=_build_json_body(name=name, pageNum=pageNum, pageSize=pageSize),
        )

    def create_device_type(
        self,
        name: str,
        description: Optional[str] = None,
        deviceBodyId: Optional[int] = None,
        deviceCameraId: Optional[int] = None,
        deviceEndId: Optional[int] = None,
        fileObjectKey: Optional[str] = None,
        status: Optional[int] = None,
        thumbnailObjectKey: Optional[str] = None,
    ) -> APIResponse:
        """创建设备类型。

        参数:
            name (str): 设备类型名称。

        返回:
            APIResponse: 设备类型创建接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/device-types",
            json_body=_build_json_body(
                description=description,
                deviceBodyId=deviceBodyId,
                deviceCameraId=deviceCameraId,
                deviceEndId=deviceEndId,
                fileObjectKey=fileObjectKey,
                name=name,
                status=status,
                thumbnailObjectKey=thumbnailObjectKey,
            ),
        )

    def get_device_type(self, deviceTypeId: int) -> APIResponse:
        """查询设备类型详情。

        参数:
            deviceTypeId (int): 设备类型 ID。

        返回:
            APIResponse: 设备类型详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/device-types/{deviceTypeId}")

    def update_device_type(
        self,
        deviceTypeId: int,
        name: str,
        description: Optional[str] = None,
        deviceBodyId: Optional[int] = None,
        deviceCameraId: Optional[int] = None,
        deviceEndId: Optional[int] = None,
        fileObjectKey: Optional[str] = None,
        status: Optional[int] = None,
        thumbnailObjectKey: Optional[str] = None,
    ) -> APIResponse:
        """更新设备类型。

        参数:
            deviceTypeId (int): 设备类型 ID。
            name (str): 设备类型名称。

        返回:
            APIResponse: 设备类型更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/device-types/{deviceTypeId}",
            json_body=_build_json_body(
                description=description,
                deviceBodyId=deviceBodyId,
                deviceCameraId=deviceCameraId,
                deviceEndId=deviceEndId,
                fileObjectKey=fileObjectKey,
                name=name,
                status=status,
                thumbnailObjectKey=thumbnailObjectKey,
            ),
        )

    def delete_device_type(self, deviceTypeId: int) -> APIResponse:
        """删除设备类型。

        参数:
            deviceTypeId (int): 设备类型 ID。

        返回:
            APIResponse: 设备类型删除接口响应结果。
        """
        return self._request_data_manager(method="DELETE", path=f"/device-types/{deviceTypeId}")

    def list_devices(
        self,
        deviceTypeId: Optional[int] = None,
        deviceCode: Optional[str] = None,
        deviceName: Optional[str] = None,
        status: Optional[int] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询设备列表。

        参数:
            deviceTypeId (Optional[int]): 设备类型 ID。
            deviceCode (Optional[str]): 设备编码。
            deviceName (Optional[str]): 设备名称。
            status (Optional[int]): 状态。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: 设备列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path="/devices",
            params=_build_json_body(
                deviceTypeId=deviceTypeId,
                deviceCode=deviceCode,
                deviceName=deviceName,
                status=status,
                pageNum=pageNum,
                pageSize=pageSize,
            ),
        )

    def create_device(
        self,
        deviceCode: str,
        deviceTypeId: int,
        deviceName: Optional[str] = None,
        modules: Optional[Sequence[str]] = None,
        status: Optional[int] = None,
    ) -> APIResponse:
        """创建设备。

        参数:
            deviceCode (str): 设备编码。
            deviceTypeId (int): 设备类型 ID。

        返回:
            APIResponse: 设备创建接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/devices",
            json_body=_build_json_body(
                deviceCode=deviceCode,
                deviceName=deviceName,
                deviceTypeId=deviceTypeId,
                modules=modules,
                status=status,
            ),
        )

    def get_device_by_code(self, deviceCode: str) -> APIResponse:
        """按设备编码查询设备详情。

        参数:
            deviceCode (str): 设备编码。

        返回:
            APIResponse: 设备详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/devices/code/{deviceCode}")

    def update_device(
        self,
        deviceId: int,
        deviceName: str,
        modules: Optional[Sequence[str]] = None,
    ) -> APIResponse:
        """更新设备。

        参数:
            deviceId (int): 设备 ID。
            deviceName (str): 设备名称。

        返回:
            APIResponse: 设备更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/devices/{deviceId}",
            json_body=_build_json_body(deviceName=deviceName, modules=modules),
        )

    def delete_device(self, deviceId: int) -> APIResponse:
        """删除设备。

        参数:
            deviceId (int): 设备 ID。

        返回:
            APIResponse: 设备删除接口响应结果。
        """
        return self._request_data_manager(method="DELETE", path=f"/devices/{deviceId}")

    def list_users(
        self,
        name: Optional[str] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询 RBAC 用户列表。

        参数:
            name (Optional[str]): 用户名。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: 用户列表接口响应结果。
        """
        return self._request_rbac(
            method="GET",
            path="/users",
            params=_build_json_body(name=name, pageNum=pageNum, pageSize=pageSize),
        )

    def list_users_by_name(self, name: str) -> APIResponse:
        """按用户名查询任务分配可引用的用户候选值。

        参数:
            name (str): 用户名称查询值。

        返回:
            APIResponse: RBAC 用户查询接口响应结果。
        """
        return self._request_rbac(method="GET", path="/users/name", params={"name": name})

    def list_tasks(
        self,
        projectId: Optional[int] = None,
        title: Optional[str] = None,
        status: Optional[int] = None,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询任务列表。

        参数:
            projectId (Optional[int]): 项目 ID。
            title (Optional[str]): 任务标题。
            status (Optional[int]): 任务状态。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: 任务列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path="/tasks",
            params=_build_json_body(
                projectId=projectId,
                title=title,
                status=status,
                pageNum=pageNum,
                pageSize=pageSize,
            ),
        )

    def get_task(self, taskId: int) -> APIResponse:
        """查询任务详情。

        参数:
            taskId (int): 任务 ID。

        返回:
            APIResponse: 任务详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/tasks/{taskId}")

    def update_task(
        self,
        taskId: int,
        sceneId: int,
        title: str,
        projectId: Optional[int] = None,
        abnormalPlanCount: Optional[int] = None,
        abnormalRatio: Optional[float] = None,
        actionSteps: Optional[Sequence[TaskActionStepReq]] = None,
        auditors: Optional[Sequence[TaskUserReq]] = None,
        collectMethod: Optional[str] = None,
        collectModeId: Optional[int] = None,
        collectSchemeId: Optional[int] = None,
        collectors: Optional[Sequence[TaskUserReq]] = None,
        countdownSeconds: Optional[int] = None,
        customLabelIds: Optional[Sequence[int]] = None,
        description: Optional[str] = None,
        deviceTypeId: Optional[int] = None,
        difficulty: Optional[int] = None,
        duration: Optional[float] = None,
        initialState: Optional[str] = None,
        minDuration: Optional[float] = None,
        normalPlanCount: Optional[int] = None,
        objectBindings: Optional[Sequence[TaskObjectBindingReq]] = None,
        planCollectCount: Optional[int] = None,
        recognitionEnabled: Optional[bool] = None,
        remark: Optional[str] = None,
        sensorTypeId: Optional[int] = None,
        spaceIds: Optional[Sequence[int]] = None,
        taskPurposeId: Optional[int] = None,
        taskType: Optional[int] = None,
        videoQuality: Optional[int] = None,
    ) -> APIResponse:
        """更新采集任务。

        参数:
            taskId (int): 任务 ID。
            sceneId (int): 场景标签 ID。
            title (str): 任务标题。

        返回:
            APIResponse: 任务更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/tasks/{taskId}",
            json_body=_build_json_body(
                abnormalPlanCount=abnormalPlanCount,
                abnormalRatio=abnormalRatio,
                actionSteps=actionSteps,
                auditors=auditors,
                collectMethod=collectMethod,
                collectModeId=collectModeId,
                collectSchemeId=collectSchemeId,
                collectors=collectors,
                countdownSeconds=countdownSeconds,
                customLabelIds=customLabelIds,
                description=description,
                deviceTypeId=deviceTypeId,
                difficulty=difficulty,
                duration=duration,
                initialState=initialState,
                minDuration=minDuration,
                normalPlanCount=normalPlanCount,
                objectBindings=objectBindings,
                planCollectCount=planCollectCount,
                projectId=projectId,
                recognitionEnabled=recognitionEnabled,
                remark=remark,
                sceneId=sceneId,
                sensorTypeId=sensorTypeId,
                spaceIds=spaceIds,
                taskPurposeId=taskPurposeId,
                taskType=taskType,
                title=title,
                videoQuality=videoQuality,
            ),
        )

    def update_task_keep_jobs(
        self,
        taskId: int,
        sceneId: int,
        title: str,
        projectId: Optional[int] = None,
        abnormalPlanCount: Optional[int] = None,
        abnormalRatio: Optional[float] = None,
        actionSteps: Optional[Sequence[TaskActionStepReq]] = None,
        auditors: Optional[Sequence[TaskUserReq]] = None,
        collectMethod: Optional[str] = None,
        collectModeId: Optional[int] = None,
        collectSchemeId: Optional[int] = None,
        collectors: Optional[Sequence[TaskUserReq]] = None,
        countdownSeconds: Optional[int] = None,
        customLabelIds: Optional[Sequence[int]] = None,
        description: Optional[str] = None,
        deviceTypeId: Optional[int] = None,
        difficulty: Optional[int] = None,
        duration: Optional[float] = None,
        initialState: Optional[str] = None,
        minDuration: Optional[float] = None,
        normalPlanCount: Optional[int] = None,
        objectBindings: Optional[Sequence[TaskObjectBindingReq]] = None,
        planCollectCount: Optional[int] = None,
        recognitionEnabled: Optional[bool] = None,
        remark: Optional[str] = None,
        sensorTypeId: Optional[int] = None,
        spaceIds: Optional[Sequence[int]] = None,
        taskPurposeId: Optional[int] = None,
        taskType: Optional[int] = None,
        videoQuality: Optional[int] = None,
    ) -> APIResponse:
        """更新采集任务并保留已有作业。

        参数:
            taskId (int): 任务 ID。
            sceneId (int): 场景标签 ID。
            title (str): 任务标题。

        返回:
            APIResponse: 更新任务并保留作业接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/tasks/{taskId}/keep-jobs",
            json_body=_build_json_body(
                abnormalPlanCount=abnormalPlanCount,
                abnormalRatio=abnormalRatio,
                actionSteps=actionSteps,
                auditors=auditors,
                collectMethod=collectMethod,
                collectModeId=collectModeId,
                collectSchemeId=collectSchemeId,
                collectors=collectors,
                countdownSeconds=countdownSeconds,
                customLabelIds=customLabelIds,
                description=description,
                deviceTypeId=deviceTypeId,
                difficulty=difficulty,
                duration=duration,
                initialState=initialState,
                minDuration=minDuration,
                normalPlanCount=normalPlanCount,
                objectBindings=objectBindings,
                planCollectCount=planCollectCount,
                projectId=projectId,
                recognitionEnabled=recognitionEnabled,
                remark=remark,
                sceneId=sceneId,
                sensorTypeId=sensorTypeId,
                spaceIds=spaceIds,
                taskPurposeId=taskPurposeId,
                taskType=taskType,
                title=title,
                videoQuality=videoQuality,
            ),
        )

    def delete_task(self, taskId: int) -> APIResponse:
        """删除采集任务。

        参数:
            taskId (int): 任务 ID。

        返回:
            APIResponse: 任务删除接口响应结果。
        """
        return self._request_data_manager(method="DELETE", path=f"/tasks/{taskId}")

    def publish_task(self, taskId: int) -> APIResponse:
        """发布采集任务。

        参数:
            taskId (int): 任务 ID。

        返回:
            APIResponse: 任务发布接口响应结果。
        """
        return self._request_data_manager(method="POST", path=f"/tasks/{taskId}/publish")

    def unpublish_task(self, taskId: int) -> APIResponse:
        """取消发布采集任务。

        参数:
            taskId (int): 任务 ID。

        返回:
            APIResponse: 取消发布接口响应结果。
        """
        return self._request_data_manager(method="POST", path=f"/tasks/{taskId}/unpublish")

    def archive_task(self, taskId: int) -> APIResponse:
        """归档采集任务。

        参数:
            taskId (int): 任务 ID。

        返回:
            APIResponse: 任务归档接口响应结果。
        """
        return self._request_data_manager(method="POST", path=f"/tasks/{taskId}/archive")

    def unarchive_task(self, taskId: int) -> APIResponse:
        """取消归档采集任务。

        参数:
            taskId (int): 任务 ID。

        返回:
            APIResponse: 取消归档接口响应结果。
        """
        return self._request_data_manager(method="POST", path=f"/tasks/{taskId}/unarchive")

    def list_jobs(
        self,
        taskId: int,
        pageNum: Optional[int] = None,
        pageSize: Optional[int] = None,
    ) -> APIResponse:
        """查询任务下的 job 列表。

        参数:
            taskId (int): 任务 ID。
            pageNum (Optional[int]): 页码。
            pageSize (Optional[int]): 每页数量。

        返回:
            APIResponse: job 列表接口响应结果。
        """
        return self._request_data_manager(
            method="GET",
            path=f"/tasks/{taskId}/jobs",
            params=_build_json_body(pageNum=pageNum, pageSize=pageSize),
        )

    def get_job(self, jobId: int) -> APIResponse:
        """查询 job 详情。

        参数:
            jobId (int): job ID。

        返回:
            APIResponse: job 详情接口响应结果。
        """
        return self._request_data_manager(method="GET", path=f"/jobs/{jobId}")

    def update_job(
        self,
        jobId: int,
        requiredRepeat: int,
        description: Optional[str] = None,
        items: Optional[Sequence[JobItemReq]] = None,
        name: Optional[str] = None,
        requiredMember: Optional[int] = None,
        type: Optional[int] = None,
    ) -> APIResponse:
        """更新 job。

        参数:
            jobId (int): job ID。
            requiredRepeat (int): 重复次数。

        返回:
            APIResponse: job 更新接口响应结果。
        """
        return self._request_data_manager(
            method="PUT",
            path=f"/jobs/{jobId}",
            json_body=_build_json_body(
                description=description,
                items=items,
                name=name,
                requiredMember=requiredMember,
                requiredRepeat=requiredRepeat,
                type=type,
            ),
        )

    def delete_jobs(self, ids: Sequence[int]) -> APIResponse:
        """批量删除 job。

        参数:
            ids (Sequence[int]): 待删除 job ID 列表。

        返回:
            APIResponse: job 批量删除接口响应结果。
        """
        return self._request_data_manager(
            method="POST",
            path="/jobs/batch-delete",
            json_body=_build_json_body(ids=ids),
        )

    def sync_platform_configuration(
        self, pageSize: int = 200, request_interval_seconds: float = 0.0
    ) -> Dict[str, Any]:
        """同步当前登录用户可访问的平台配置快照。

        参数:
            pageSize (int): 项目、任务、物品列表单次查询数量。
            request_interval_seconds (float): 连续请求之间的等待秒数，真实平台联调时使用。

        返回:
            Dict[str, Any]: 平台配置快照，包含原始响应、项目、任务、标签分类、标签树、
                扁平标签索引、物品目录、物品列表、设备类型和设备列表。
        """
        request_started = False

        def wait_for_next_request() -> None:
            """在同步流程内按需等待下一次请求。

            参数:
                无

            返回:
                None
            """
            nonlocal request_started
            if request_started and request_interval_seconds > 0:
                time.sleep(request_interval_seconds)
            request_started = True

        # 获取项目列表
        wait_for_next_request()
        projects_response = self.list_projects(pageNum=1, pageSize=pageSize)

        # 获取采集任务列表
        wait_for_next_request()
        tasks_response = self.list_tasks(pageNum=1, pageSize=pageSize)

        # 获取标签库信息
        ## 此处仅得到 标签库 下4类标签的categoryCode
        wait_for_next_request()
        label_categories_response = self.list_label_categories()
        label_categories = _extract_metadata_items(label_categories_response.body)

        label_trees: Dict[str, Any] = {}
        labels: list[Dict[str, Any]] = []
        label_tree_responses: Dict[str, Any] = {}
        for category in label_categories:
            if not isinstance(category, dict):
                continue
            category_code = category.get("code") or category.get("categoryCode")
            if not category_code:
                continue
            category_code = str(category_code)
            wait_for_next_request()
            tree_response = self.get_label_tree(category_code)
            tree_items = _extract_metadata_items(tree_response.body)
            label_tree_responses[category_code] = tree_response.body
            label_trees[category_code] = tree_items
            labels.extend(_flatten_label_nodes(tree_items, category_code))

        wait_for_next_request()
        object_categories_response = self.list_object_categories()
        object_category_tree = _extract_metadata_items(object_categories_response.body)
        object_categories = _flatten_object_categories(object_category_tree)
        object_items: list[Any] = []
        object_item_responses: Dict[str, Any] = {}
        for category in object_categories:
            category_id = category.get("id")
            if category_id is None:
                continue
            wait_for_next_request()
            item_response = self.list_object_items(
                categoryId=category_id,
                pageNum=1,
                pageSize=pageSize,
            )
            object_item_responses[str(category_id)] = item_response.body
            object_items.extend(_extract_metadata_items(item_response.body))

        wait_for_next_request()
        device_types_response = self.list_device_types(pageNum=1, pageSize=pageSize)
        wait_for_next_request()
        devices_response = self.list_devices(pageNum=1, pageSize=pageSize)

        return {
            "raw": {
                "projects": projects_response.body,
                "tasks": tasks_response.body,
                "label_categories": label_categories_response.body,
                "label_trees": label_tree_responses,
                "object_categories": object_categories_response.body,
                "object_items": object_item_responses,
                "device_types": device_types_response.body,
                "devices": devices_response.body,
            },
            "projects": _extract_metadata_items(projects_response.body),
            "tasks": _extract_metadata_items(tasks_response.body),
            "label_categories": label_categories,
            "label_trees": label_trees,
            "labels": labels,
            "object_category_tree": object_category_tree,
            "object_categories": object_categories,
            "object_items": object_items,
            "device_types": _extract_metadata_items(device_types_response.body),
            "devices": _extract_metadata_items(devices_response.body),
        }

    def _build_headers(self, extra_headers: Optional[Mapping[str, str]] = None) -> MutableMapping[str, str]:
        """构造包含当前 Bearer token 的 Zata 请求头。

        参数:
            extra_headers (Optional[Mapping[str, str]]): 本次请求附加请求头。

        返回:
            MutableMapping[str, str]: 合并后的请求头。
        """
        headers = super()._build_headers(extra_headers=extra_headers)
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    @classmethod
    def _rbac_path(cls, path: str) -> str:
        """拼接 zata-rbac 服务路径。

        参数:
            path (str): RBAC 资源相对路径。

        返回:
            str: 带服务前缀的 RBAC 请求路径。
        """
        return f"{cls.RBAC_PREFIX}/{path.lstrip('/')}"

    @classmethod
    def _data_manager_path(cls, path: str) -> str:
        """拼接 data-manager 服务路径。

        参数:
            path (str): data-manager 资源相对路径。

        返回:
            str: 带服务前缀的 data-manager 请求路径。
        """
        return f"{cls.DATA_MANAGER_PREFIX}/{path.lstrip('/')}"
