# Data Management API / 数据管理 API

数据管理包含采集数据、review、归档数据集、数据集映射等更偏数据流转的接口。当前版本不把数据管理作为开发重点。

## Current Scope / 当前范围

本页只保留边界说明，不展开字段和接口细节。当前项目的主要目标仍是：

- 平台配置读取与受控修改。
- 采集工作定义，即 Project / Task / Job 的创建和生命周期管理。
- 创建前 verifier 行为契约。

当运行时代码需要数据管理能力时，应先在本页补充对应 API 分类、字段来源、请求顺序和测试规则，再实现代码。

## Related Docs / 相关文档

审核和归档相关能力暂见 [../audit_archive_api.md](../audit_archive_api.md)。

