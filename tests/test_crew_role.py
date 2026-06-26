"""CrewRole — 角色系统测试"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_agent_kit import Crew, Role, CrewTask as Task, CrewResult, ProcessType

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")

# ============ 1. 角色创建 ============
print("\n=== 1. 角色创建 ===")

r = Role(name="研究员", goal="收集信息", backstory="资深研究员", tools=["web_search"])
test("角色名称", r.name == "研究员")
test("角色目标", r.goal == "收集信息")
test("角色工具", r.tools == ["web_search"])
test("角色系统提示", "研究员" in r.build_system_prompt())
test("角色系统提示含目标", "收集信息" in r.build_system_prompt())

# ============ 2. 任务创建 ============
print("\n=== 2. 任务创建 ===")

t = Task(description="收集 AI 框架信息", expected_output="框架列表", agent_role="研究员")
test("任务描述", t.description == "收集 AI 框架信息")
test("任务角色", t.agent_role == "研究员")
test("任务 ID 自动生成", len(t.task_id) == 8)
test("任务序列化", t.to_dict()["description"] == "收集 AI 框架信息")

# ============ 3. Crew 创建 ============
print("\n=== 3. Crew 创建 ===")

crew = Crew(name="test_crew", process_type=ProcessType.SEQUENTIAL)
test("Crew 名称", crew.name == "test_crew")
test("流程类型", crew.process_type == ProcessType.SEQUENTIAL)
test("初始角色数", len(crew.roles) == 0)
test("初始任务数", len(crew.tasks) == 0)

# ============ 4. 添加角色 ============
print("\n=== 4. 添加角色 ===")

crew.add_role(r)
test("添加后角色数", len(crew.roles) == 1)
test("获取角色", crew.get_role("研究员") is not None)
test("获取不存在角色", crew.get_role("不存在") is None)

r2 = Role(name="分析师", goal="分析数据")
crew.add_role(r2)
test("添加第二个角色", len(crew.roles) == 2)

# ============ 5. 添加任务 ============
print("\n=== 5. 添加任务 ===")

crew.add_task(t)
t2 = Task(description="分析收集的数据", agent_role="分析师")
crew.add_task(t2)
test("添加后任务数", len(crew.tasks) == 2)
test("获取任务", crew.get_task(t.task_id) is not None)
test("移除任务", crew.remove_task(t.task_id) == True)
test("移除后任务数", len(crew.tasks) == 1)
test("移除不存在任务", crew.remove_task("nonexistent") == False)

# 加回来
crew.add_task(t)
test("加回任务", len(crew.tasks) == 2)

# ============ 6. 任务分配 ============
print("\n=== 6. 任务分配 ===")

assignment = crew.assign_tasks()
test("分配包含研究员", "研究员" in assignment)
test("分配包含分析师", "分析师" in assignment)
test("研究员任务数", len(assignment["研究员"]) == 1)
test("分析师任务数", len(assignment["分析师"]) == 1)

# ============ 7. 角色提示词 ============
print("\n=== 7. 角色提示词 ===")

prompt = crew.get_role_prompt("研究员", t)
test("提示词含角色名", "研究员" in prompt)
test("提示词含目标", "收集信息" in prompt)
test("提示词含任务", "AI 框架" in prompt)
test("提示词含期望输出", "框架列表" in prompt)

# 带上下文的提示词
t_with_ctx = Task(description="写报告", context=["研究结果", "分析数据"])
prompt_ctx = crew.get_role_prompt("分析师", t_with_ctx)
test("提示词含上下文", "研究结果" in prompt_ctx)

# ============ 8. 顺序执行 ============
print("\n=== 8. 顺序执行 ===")

exec_log = []
def handler(role_name, task, prompt):
    exec_log.append(f"{role_name}:{task.description[:20]}")
    return f"{role_name} 完成了 {task.description}"

crew2 = Crew(name="seq_crew", process_type=ProcessType.SEQUENTIAL)
crew2.add_roles([r, r2])
crew2.add_tasks([t, t2])
result = crew2.execute(handler)

test("顺序执行成功", result.success)
test("执行结果数", len(result.task_results) == 2)
test("执行顺序", exec_log[0].startswith("研究员"))
test("执行顺序2", exec_log[1].startswith("分析师"))
test("持续时间 > 0", result.duration_ms > 0)
test("CrewResult 序列化", "crew_name" in result.to_dict())

# ============ 9. 层级执行 ============
print("\n=== 9. 层级执行 ===")

exec_log2 = []
def handler2(role_name, task, prompt):
    exec_log2.append(f"{role_name}:{task.description[:20]}")
    return f"{role_name} done"

manager = Role(name="产品经理", goal="管理项目", allow_delegation=True)
worker = Role(name="开发者", goal="实现功能")
crew3 = Crew(name="hier_crew", process_type=ProcessType.HIERARCHICAL)
crew3.add_roles([manager, worker])
crew3.add_tasks([
    Task(description="规划项目路线图", agent_role="产品经理"),
    Task(description="实现登录功能", agent_role="开发者"),
])
result3 = crew3.execute(handler2)

test("层级执行成功", result3.success)
test("层级执行结果数", len(result3.task_results) == 2)
test("主管先执行", exec_log2[0].startswith("产品经理"))

# ============ 10. 并行执行 ============
print("\n=== 10. 并行执行 ===")

crew4 = Crew(name="par_crew", process_type=ProcessType.PARALLEL)
crew4.add_roles([r, r2])
crew4.add_tasks([t, t2])
result4 = crew4.execute(handler)

test("并行执行成功", result4.success)
test("并行结果数", len(result4.task_results) == 2)

# ============ 11. 无 handler 执行 ============
print("\n=== 11. 无 handler 执行 ===")

crew5 = Crew(name="no_handler_crew")
crew5.add_role(r)
crew5.add_task(Task(description="测试任务", agent_role="研究员"))
result5 = crew5.execute()

test("无 handler 成功", result5.success)
test("提示词生成", result5.task_results[0]["status"] == "prompt_generated")
test("提示词内容", "研究员" in result5.task_results[0]["prompt"])

# ============ 12. 任务失败处理 ============
print("\n=== 12. 任务失败处理 ===")

def failing_handler(role_name, task, prompt):
    raise ValueError("模拟失败")

crew6 = Crew(name="fail_crew")
crew6.add_role(r)
crew6.add_task(Task(description="会失败的任务", agent_role="研究员"))
result6 = crew6.execute(failing_handler)

test("失败不崩溃", result6.success == False)
test("错误记录", len(result6.errors) == 1)
test("错误信息", "模拟失败" in result6.errors[0]["error"])
test("失败任务状态", result6.task_results[0]["status"] == "failed")

# ============ 13. 序列化 ============
print("\n=== 13. 序列化 ===")

crew7 = Crew(name="serialize_test")
crew7.add_roles([r, r2])
crew7.add_tasks([t, t2])

d = crew7.to_dict()
test("序列化含名称", d["name"] == "serialize_test")
test("序列化含角色", len(d["roles"]) == 2)
test("序列化含任务", len(d["tasks"]) == 2)
test("序列化含流程", d["process_type"] == "sequential")

# JSON 序列化
j = crew7.to_json()
test("JSON 序列化", "serialize_test" in j)
test("JSON 可解析", isinstance(json.loads(j), dict))

# 反序列化
crew8 = Crew.from_dict(d)
test("反序列化名称", crew8.name == "serialize_test")
test("反序列化角色", len(crew8.roles) == 2)
test("反序列化任务", len(crew8.tasks) == 2)

crew9 = Crew.from_json(j)
test("JSON 反序列化", crew9.name == "serialize_test")

# ============ 14. 角色删除 ============
print("\n=== 14. 角色删除 ===")

crew10 = Crew(name="delete_test")
crew10.add_roles([r, r2])
test("删除前", len(crew10.roles) == 2)
test("删除成功", crew10.remove_role("研究员") == True)
test("删除后", len(crew10.roles) == 1)
test("删除不存在", crew10.remove_role("不存在") == False)

# ============ 15. 批量添加 ============
print("\n=== 15. 批量添加 ===")

crew11 = Crew(name="batch_test")
crew11.add_roles([
    Role(name="A", goal="Goal A"),
    Role(name="B", goal="Goal B"),
    Role(name="C", goal="Goal C"),
])
test("批量添加角色", len(crew11.roles) == 3)

crew11.add_tasks([
    Task(description="Task 1", agent_role="A"),
    Task(description="Task 2", agent_role="B"),
    Task(description="Task 3", agent_role="C"),
])
test("批量添加任务", len(crew11.tasks) == 3)

# ============ 16. 便捷工厂 ============
print("\n=== 16. 便捷工厂 ===")

analysis_crew = Crew.create_analysis_team("AI Agent 框架")
test("分析团队名称", "analysis_team" in analysis_crew.name)
test("分析团队角色数", len(analysis_crew.roles) == 3)
test("分析团队任务数", len(analysis_crew.tasks) == 3)
test("分析团队流程", analysis_crew.process_type == ProcessType.SEQUENTIAL)
test("研究员有工具", "web_search" in analysis_crew.get_role("研究员").tools)

dev_crew = Crew.create_development_team("MyApp")
test("开发团队角色数", len(dev_crew.roles) == 3)
test("开发团队流程", dev_crew.process_type == ProcessType.HIERARCHICAL)
test("产品经理可委托", dev_crew.get_role("产品经理").allow_delegation == True)
test("开发者有工具", len(dev_crew.get_role("开发者").tools) > 0)

# ============ 17. Role 序列化 ============
print("\n=== 17. Role 序列化 ===")

r_dict = r.to_dict()
test("Role 序列化", r_dict["name"] == "研究员")
r_clone = Role.from_dict(r_dict)
test("Role 反序列化", r_clone.name == "研究员")
test("Role 目标一致", r_clone.goal == "收集信息")
test("Role 工具一致", r_clone.tools == ["web_search"])

# ============ 18. CrewResult 属性 ============
print("\n=== 18. CrewResult 属性 ===")

res = CrewResult(crew_name="test", process_type=ProcessType.SEQUENTIAL)
test("成功属性", res.success == True)
test("摘要含名称", "test" in res.summary)

res.errors.append({"task_id": "1", "role": "x", "error": "err"})
test("失败属性", res.success == False)
test("摘要含错误", "1 错误" in res.summary)

# ============ 19. 角色元数据 ============
print("\n=== 19. 角色元数据 ===")

r_meta = Role(name="带元数据", goal="测试", metadata={"priority": "high", "version": 2})
test("角色元数据", r_meta.metadata["priority"] == "high")
test("元数据序列化", r_meta.to_dict()["metadata"]["version"] == 2)

# ============ 20. 自定义流程 ============
print("\n=== 20. 自定义流程 ===")

crew_custom = Crew(name="custom_crew", process_type=ProcessType.CUSTOM)
crew_custom.add_role(Role(name="执行者", goal="执行"))
crew_custom.add_task(Task(description="自定义任务", agent_role="执行者"))
result_custom = crew_custom.execute(handler)
test("自定义流程执行", result_custom.success)
test("自定义流程结果", len(result_custom.task_results) == 1)

# ============ 总结 ============
print(f"\n{'='*40}")
print(f"结果: {passed} 通过, {failed} 失败, 共 {passed+failed} 测试")
print(f"{'='*40}")

sys.exit(0 if failed == 0 else 1)
