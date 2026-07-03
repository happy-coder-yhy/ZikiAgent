# Zata Data Collection Platform

This context defines the business language for automating administrator operations on the remote data collection platform.

## Language

**Platform Operator**:
平台管理员. A platform user whose primary responsibility is defining collection work by creating collection projects, tasks, and jobs, then confirming tasks before release; the same user may also have platform configuration permissions.
_Avoid_: Task Administrator Assistant, Agent, workflow brain, Collector, Auditor

**Collector**:
采集员. A platform user who receives Collection Jobs and completes them by producing and uploading the required collection data.
_Avoid_: Platform Operator, Auditor, task owner

**Auditor**:
审核员. A platform user who reviews uploaded collection data and records whether it should be accepted, rejected, or prepared for archival.
_Avoid_: Platform Operator, Collector, data collector

**Zata API Caller Toolkit**:
The core purpose of this project: a reusable tool package that exposes Zata Platform operations as structured API calls for humans, scripts, and future Agent runtimes.
_Avoid_: Agent system, task generator, workflow brain

**Structured API Call**:
A platform operation invoked through explicit business fields or a typed request object, rather than by asking the caller to assemble raw JSON.
_Avoid_: Raw payload, arbitrary request body

**OpenAPI-Aligned Request Object**:
A typed request object whose name and field names follow the Zata Platform OpenAPI schema directly.
_Avoid_: Python-renamed payload wrapper, inferred business model

**OpenAPI-Aligned Public Boundary**:
The public platform operation surface whose externally visible operation inputs use Zata Platform OpenAPI field names.
_Avoid_: Pythonic field translation at the tool boundary

**Raw Platform Request**:
A private low-level request path used inside the Zata API Caller Toolkit for debugging or emergency adaptation when Zata Platform APIs change.
_Avoid_: Public tool, Agent-callable operation, normal workflow API

**Platform Configuration**:
The existing platform-managed options that a Platform Operator references when defining collection work, including asset libraries, labels, devices, users, and existing collection work.
_Avoid_: Options, settings, metadata

**Platform Configuration Snapshot**:
A synchronized, current-user view of Platform Configuration returned by `ZataAPICaller.sync_platform_configuration`, including projects, tasks, label categories, label trees, flattened label references, object category trees, object items, device types, and devices.
_Avoid_: Static config, hardcoded IDs

**Configuration Gap**:
A missing or conflicting Platform Configuration item found while validating a planned collection workflow, usually while preparing a Collection Task. All gaps should be listed before the current workflow is stopped, and the stop does not imply automatic deletion of platform resources.
_Avoid_: Auto-fix, silent default, partial configuration creation

**Collection Project**:
采集项目. The top-level collection work container that represents the business demand or customer request for a data collection effort.
_Avoid_: Task, Job, requirement source

**Collection Task**:
采集任务. A unit of collection work under a Collection Project that represents one task scene or robot skill to be collected.
_Avoid_: Task template, requirement, Job, collection device type

**Strict Collection Task**:
严格采集任务. A Collection Task whose device type, initial state, action steps, object bindings, and collection constraints are explicitly defined. `collectMethod=robot` only supports this task category; `collectMethod=web_video` may also create strict tasks for uploaded-video collection.
_Avoid_: Robot task, video task, scene task, instruction task

**Instruction Collection Task**:
指令采集任务. A Collection Task for `collectMethod=web_video` collection whose core definition is a prompt instruction rather than strict action steps or object bindings.
_Avoid_: Robot task, strict task, scene task, action-step task

**Scene Collection Task**:
场景采集任务. A Collection Task for `collectMethod=web_video` collection that constrains the collection scene with a lighter task definition and does not require full action-step specification.
_Avoid_: Video task, loose task, strict task, instruction task

**Collection Job**:
采集作业. The atomic work item under a Collection Task that a collector receives and completes by producing the required amount of collection data.
_Avoid_: Subtask, assignment, Task

**Task Release**:
The act of making a prepared Collection Task available for execution after its content has been confirmed.
_Avoid_: Publish, dispatch, submit

**Destructive Confirmation**:
A human confirmation required before deleting platform resources, expressed as a fixed phrase that includes the resource type and resource ID.
_Avoid_: Yes/no confirmation, safety prompt
