# Contributing to AutoAgentKit

感谢你对 AutoAgentKit 的兴趣！🎉

## 开发环境

```bash
# 克隆仓库
git clone git@github.com:Lwh909193/auto-agent-kit.git
cd auto-agent-kit

# 安装开发依赖
pip install -e .

# 运行测试
python -m pytest tests/
```

## 代码规范

- Python 3.8+ 兼容
- 遵循 PEP 8
- 所有公共 API 必须有类型注解和 docstring
- 新增功能必须附带测试

## 模块结构

```
auto_agent_kit/
├── __init__.py          # 统一导出
├── core/
│   ├── plan_mode.py     # 计划执行模式
│   ├── error_reflection.py  # 错误反射
│   ├── tool_router.py   # 工具路由器
│   ├── dashboard.py     # 仪表板
│   ├── access_control.py    # 访问控制
│   └── mcp_server.py    # MCP 协议服务器
├── examples/
│   └── demo.py          # 完整示例
└── tests/
    └── test_all.py      # 单元测试
```

## 提 PR 流程

1. Fork 仓库
2. 创建功能分支：`git checkout -b feat/my-feature`
3. 提交改动：`git commit -m "feat: add my feature"`
4. 推送到你的 Fork：`git push origin feat/my-feature`
5. 创建 Pull Request

## Commit 规范

- `feat:` — 新功能
- `fix:` — 修复
- `docs:` — 文档
- `refactor:` — 重构
- `test:` — 测试
- `chore:` — 杂项

## 问题反馈

- Bug 报告：请描述复现步骤、预期行为和实际行为
- 功能请求：请描述使用场景和期望的 API
- 使用问题：请提供最小可复现代码

## 许可证

MIT License
