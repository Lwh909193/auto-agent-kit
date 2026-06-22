"""生成 AutoAgentKit 实战指南 PDF"""
import os
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('SimSun', '', 10)
        self.cell(0, 10, 'AutoAgentKit - AI Agent 实战指南', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('SimSun', '', 8)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, 0, 'C')

pdf = PDF()
pdf.add_font('SimSun', '', r'C:\Windows\Fonts\simfang.ttf', uni=True)
pdf.add_font('SimSun', 'B', r'C:\Windows\Fonts\simfang.ttf', uni=True)
pdf.set_auto_page_break(auto=True, margin=15)

# 封面
pdf.add_page()
pdf.set_font('SimSun', 'B', 24)
pdf.ln(60)
pdf.cell(0, 15, 'AutoAgentKit', 0, 1, 'C')
pdf.set_font('SimSun', '', 16)
pdf.cell(0, 10, '生产级 AI Agent 工具包实战指南', 0, 1, 'C')
pdf.ln(20)
pdf.set_font('SimSun', '', 12)
pdf.cell(0, 8, '版本：v0.2.0', 0, 1, 'C')
pdf.cell(0, 8, 'GitHub: github.com/Lwh909193/auto-agent-kit', 0, 1, 'C')
pdf.cell(0, 8, 'PyPI: pip install auto-agent-kit', 0, 1, 'C')

# 目录
pdf.add_page()
pdf.set_font('SimSun', 'B', 16)
pdf.cell(0, 12, '目录', 0, 1, 'L')
pdf.ln(5)
pdf.set_font('SimSun', '', 12)
chapters = [
    '第一章：为什么需要 AutoAgentKit',
    '第二章：快速开始',
    '第三章：PlanMode - 计划执行模式',
    '第四章：ErrorReflection - 错误反射',
    '第五章：ToolRouter - 工具路由器',
    '第六章：Dashboard - 仪表板',
    '第七章：AccessControl - 访问控制',
    '第八章：MCPServer - MCP 协议服务器',
    '第九章：Plugin - 插件系统',
    '第十章：AsyncPlan - 异步执行',
    '附录：常见问题与最佳实践',
]
for c in chapters:
    pdf.cell(0, 8, c, 0, 1, 'L')

# 第一章
pdf.add_page()
pdf.set_font('SimSun', 'B', 16)
pdf.cell(0, 12, '第一章：为什么需要 AutoAgentKit', 0, 1, 'L')
pdf.ln(5)
pdf.set_font('SimSun', '', 11)
lines = [
    '市面上 Agent 框架很多（LangChain、CrewAI、AutoGen），',
    '但它们普遍缺少生产级工程能力。',
    '',
    '常见问题：',
    '- 工具调用失败后盲目重试，没有智能恢复策略',
    '- 上下文膨胀导致 Agent 质量下降',
    '- 工具太多模型选错',
    '- 不知道 Agent 在干什么（黑盒运行）',
    '- 权限失控',
    '- 协议不标准，无法互通',
    '',
    'AutoAgentKit 的目标：把在真实系统中验证过的',
    '生产级能力打包成一个 pip install 就能用的工具包。',
    '',
    '6 大核心模块：',
    '1. PlanMode - 计划执行模式，Plan/Act 分离',
    '2. ErrorReflection - 20+ 错误类型自动分类',
    '3. ToolRouter - 阶段性工具暴露（<=8/阶段）',
    '4. Dashboard - 实时指标监控',
    '5. AccessControl - 4 级权限策略',
    '6. MCPServer - JSON-RPC 2.0 + SSE',
    '',
    'v0.2.0 新增：',
    '7. Plugin - 插件系统，钩子生命周期',
    '8. AsyncPlanMode - 异步计划执行',
]
for line in lines:
    pdf.cell(0, 6, line, 0, 1, 'L')

# 第二章
pdf.add_page()
pdf.set_font('SimSun', 'B', 16)
pdf.cell(0, 12, '第二章：快速开始', 0, 1, 'L')
pdf.ln(5)
pdf.set_font('SimSun', '', 11)
lines2 = [
    '安装：',
    '  pip install auto-agent-kit',
    '',
    '一分钟上手：',
    '',
    '  from auto_agent_kit import PlanMode, ErrorReflection',
    '',
    '  # 计划执行模式',
    '  planner = PlanMode()',
    '  plan = planner.create_plan("分析数据", ["收集", "分析", "报告"])',
    '',
    '  # 错误反射',
    '  reflector = ErrorReflection()',
    '  recovery = reflector.classify_and_recover(error)',
    '',
    '  # 工具路由器',
    '  router = ToolRouter()',
    '  router.register_phase("research", ["web_search", "web_fetch"])',
    '  router.activate_phase("research")',
]
for line in lines2:
    pdf.cell(0, 6, line, 0, 1, 'L')

# 第三章
pdf.add_page()
pdf.set_font('SimSun', 'B', 16)
pdf.cell(0, 12, '第三章：PlanMode - 计划执行模式', 0, 1, 'L')
pdf.ln(5)
pdf.set_font('SimSun', '', 11)
lines3 = [
    'PlanMode 的核心思想：先计划，再执行。',
    '',
    '不是让 Agent 边想边做，而是先制定完整计划，',
    '然后按步骤执行。每一步都知道自己在做什么。',
    '',
    '核心功能：',
    '- create_plan(goal, steps) - 创建计划',
    '- start_step(step_id) - 开始步骤',
    '- complete_step(step_id, result) - 完成步骤',
    '- get_next_ready() - 获取下一个可执行的步骤',
    '- get_plan_status() - 获取计划状态',
    '',
    '步骤依赖解析：自动判断哪些步骤可以并行，',
    '哪些需要等待前置步骤完成。',
]
for line in lines3:
    pdf.cell(0, 6, line, 0, 1, 'L')

# 第四章
pdf.add_page()
pdf.set_font('SimSun', 'B', 16)
pdf.cell(0, 12, '第四章：ErrorReflection - 错误反射', 0, 1, 'L')
pdf.ln(5)
pdf.set_font('SimSun', '', 11)
lines4 = [
    '工具调用失败是常态。关键是怎么恢复。',
    '',
    '支持 20+ 错误类型：',
    '- RATE_LIMIT - 限流，指数退避重试',
    '- TIMEOUT - 超时，增加超时时间重试',
    '- AUTH_INVALID - 认证失效，轮换凭证',
    '- CONTEXT_OVERFLOW - 上下文溢出，压缩重试',
    '- SERVICE_UNAVAILABLE - 服务不可用，切换备用',
    '- UNKNOWN - 未知错误，优雅降级',
    '',
    '连续失败自动升级策略：',
    '第1次 -> 重试',
    '第2次 -> 指数退避',
    '第3次 -> 切换备用',
    '第4次 -> 升级告警',
]
for line in lines4:
    pdf.cell(0, 6, line, 0, 1, 'L')

# 后续章节概要
pdf.add_page()
pdf.set_font('SimSun', 'B', 16)
pdf.cell(0, 12, '第五章至第十章（概要）', 0, 1, 'L')
pdf.ln(5)
pdf.set_font('SimSun', '', 11)
lines5 = [
    'ToolRouter：阶段性工具暴露，每阶段 <= 8 个工具。',
    '减少模型选择负担，提高工具调用准确率。',
    '',
    'Dashboard：实时指标监控。',
    '记录 CPU、内存、工具调用、错误率等指标。',
    '',
    'AccessControl：4 级权限策略。',
    'SAFE -> SENSITIVE -> DANGEROUS -> CRITICAL',
    '',
    'MCPServer：JSON-RPC 2.0 + SSE 协议服务器。',
    '让任何 MCP 客户端都能调用你的工具。',
    '',
    'Plugin：插件系统，支持钩子生命周期。',
    'LoggingPlugin、MetricsPlugin 内置。',
    '',
    'AsyncPlanMode：异步计划执行。',
    '并发步骤、超时控制、死锁检测。',
]
for line in lines5:
    pdf.cell(0, 6, line, 0, 1, 'L')

# 附录
pdf.add_page()
pdf.set_font('SimSun', 'B', 16)
pdf.cell(0, 12, '附录：快速参考', 0, 1, 'L')
pdf.ln(5)
pdf.set_font('SimSun', '', 11)
lines6 = [
    '安装：pip install auto-agent-kit',
    '升级：pip install --upgrade auto-agent-kit',
    'GitHub：https://github.com/Lwh909193/auto-agent-kit',
    'PyPI：https://pypi.org/project/auto-agent-kit/',
    '中文教程：README_CN.md',
    '实战教程：TUTORIAL_CN.md',
    '',
    '版本历史：',
    'v0.1.0 - 6 大核心模块',
    'v0.2.0 - 插件系统 + 异步支持',
    '',
    '开源协议：MIT',
]
for line in lines6:
    pdf.cell(0, 6, line, 0, 1, 'L')

outpath = r'G:\.openclaw\workspace\projects\AutoAgentKit\dist\AutoAgentKit实战指南.pdf'
pdf.output(outpath)
print(f'PDF saved: {outpath}')
print(f'Size: {os.path.getsize(outpath)} bytes')
