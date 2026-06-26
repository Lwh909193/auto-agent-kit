"""StateGraph — 轻量级 LangGraph 风格图编排引擎

受 LangGraph 启发，提供有状态图、条件分支、循环、检查点功能。
零外部依赖，纯 Python 实现。

核心概念：
- StateGraph: 有向图，节点处理步骤，边控制流程
- Node: 处理函数，接收 state 返回 state 更新
- Edge: 普通边（顺序执行）或条件边（分支路由）
- Checkpoint: 执行状态快照，支持暂停/恢复
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional


class NodeType(Enum):
    """节点类型"""
    FUNCTION = "function"       # 普通函数节点
    LLM = "llm"                 # LLM 调用节点
    TOOL = "tool"               # 工具调用节点
    SUBGRAPH = "subgraph"       # 子图节点
    INPUT = "input"             # 输入节点
    OUTPUT = "output"           # 输出节点


class EdgeType(Enum):
    """边类型"""
    NORMAL = "normal"           # 普通顺序边
    CONDITIONAL = "conditional" # 条件分支边
    LOOP = "loop"               # 循环边（回到前序节点）


@dataclass
class GraphNode:
    """图节点"""
    name: str
    node_type: NodeType = NodeType.FUNCTION
    fn: Optional[Callable] = None
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class GraphEdge:
    """图边"""
    source: str
    target: str
    edge_type: EdgeType = EdgeType.NORMAL
    condition_fn: Optional[Callable] = None  # 条件分支用
    label: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Checkpoint:
    """执行检查点"""
    id: str
    node_name: str
    state_snapshot: dict
    timestamp: float
    metadata: dict = field(default_factory=dict)


class StateGraph:
    """有状态图编排引擎

    用法:
        graph = StateGraph()
        graph.add_node("analyze", analyze_fn)
        graph.add_node("search", search_fn)
        graph.add_node("respond", respond_fn)
        graph.add_edge("analyze", "search")
        graph.add_conditional_edges("search", route_fn, {
            "respond": "respond",
            "search_more": "search"
        })
        graph.add_edge("respond", END)

        app = graph.compile()
        result = app.invoke({"query": "..."})
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._compiled = False
        self._adjacency: dict[str, list[GraphEdge]] = {}  # source -> edges
        self._reverse_adjacency: dict[str, list[GraphEdge]] = {}  # target -> edges
        self._topological_order: list[str] = []
        self._checkpoints: list[Checkpoint] = []
        self._execution_history: list[dict] = []

    def add_node(self, name: str, fn: Optional[Callable] = None,
                 node_type: NodeType = NodeType.FUNCTION,
                 metadata: Optional[dict] = None) -> GraphNode:
        """添加处理节点"""
        node = GraphNode(
            name=name,
            node_type=node_type,
            fn=fn,
            metadata=metadata or {}
        )
        self.nodes[name] = node
        self._compiled = False
        return node

    def add_edge(self, source: str, target: str,
                 label: str = "",
                 metadata: Optional[dict] = None):
        """添加普通边（顺序执行）"""
        self._validate_nodes(source, target)
        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=EdgeType.NORMAL,
            label=label or f"{source}->{target}",
            metadata=metadata or {}
        )
        self.edges.append(edge)
        self._compiled = False

    def add_conditional_edges(self, source: str,
                              condition_fn: Callable[[dict], str],
                              path_map: dict[str, str],
                              metadata: Optional[dict] = None):
        """添加条件分支边

        Args:
            source: 源节点
            condition_fn: 条件函数，接收 state，返回目标节点名
            path_map: 路径映射 {条件返回值: 目标节点名}
        """
        self._validate_nodes(source, *path_map.values())
        edge = GraphEdge(
            source=source,
            target="__conditional__",
            edge_type=EdgeType.CONDITIONAL,
            condition_fn=condition_fn,
            label=f"{source} -> conditional",
            metadata={
                "path_map": path_map,
                **(metadata or {})
            }
        )
        self.edges.append(edge)
        self._compiled = False

    def add_loop(self, source: str, target: str,
                 condition_fn: Optional[Callable[[dict], bool]] = None,
                 label: str = "",
                 metadata: Optional[dict] = None):
        """添加循环边

        Args:
            source: 源节点
            target: 目标节点（通常是前序节点）
            condition_fn: 循环条件，返回 True 继续循环
        """
        self._validate_nodes(source, target)
        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=EdgeType.LOOP,
            condition_fn=condition_fn,
            label=label or f"{source} -> {target} (loop)",
            metadata=metadata or {}
        )
        self.edges.append(edge)
        self._compiled = False

    def _validate_nodes(self, *node_names: str):
        """验证节点存在"""
        for name in node_names:
            if name not in self.nodes and name != "__end__":
                raise ValueError(f"节点 '{name}' 不存在")

    def compile(self) -> "CompiledGraph":
        """编译图为可执行应用"""
        if self._compiled:
            return CompiledGraph(self)

        # 构建邻接表
        self._adjacency = {name: [] for name in self.nodes}
        self._reverse_adjacency = {name: [] for name in self.nodes}

        for edge in self.edges:
            if edge.source in self._adjacency:
                self._adjacency[edge.source].append(edge)
            if edge.target != "__conditional__" and edge.target in self._reverse_adjacency:
                self._reverse_adjacency[edge.target].append(edge)

        # 拓扑排序（检测循环）
        self._topological_order = self._topological_sort()

        self._compiled = True
        return CompiledGraph(self)

    def _topological_sort(self) -> list[str]:
        """拓扑排序，检测循环"""
        in_degree = {name: 0 for name in self.nodes}
        adj = {name: [] for name in self.nodes}

        for edge in self.edges:
            if edge.edge_type == EdgeType.LOOP:
                continue  # 循环边不参与拓扑排序
            if edge.source in adj and edge.target in self.nodes:
                adj[edge.source].append(edge.target)
                in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        queue = [n for n, d in in_degree.items() if d == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 如果有节点没排到，说明有循环（非 loop 边）
        if len(result) != len(self.nodes):
            remaining = set(self.nodes.keys()) - set(result)
            # 非 loop 边的循环只是警告，不阻塞执行
            result.extend(remaining)

        return result

    def get_execution_paths(self) -> list[list[str]]:
        """获取所有可能的执行路径（用于分析）"""
        paths = []
        start_nodes = self._find_start_nodes()

        def dfs(current: str, path: list[str]):
            new_path = path + [current]
            edges = self._adjacency.get(current, [])
            if not edges:
                paths.append(new_path)
                return
            for edge in edges:
                if edge.edge_type == EdgeType.CONDITIONAL:
                    # 条件边：每条路径都是一个分支
                    path_map = edge.metadata.get("path_map", {})
                    for target in path_map.values():
                        if target in self.nodes:
                            dfs(target, new_path)
                        else:
                            paths.append(new_path + [f"__end__({target})"])
                elif edge.edge_type == EdgeType.LOOP:
                    # 循环边：最多走一次避免无限
                    if edge.target not in path:
                        dfs(edge.target, new_path)
                    else:
                        paths.append(new_path + [f"__loop__({edge.target})"])
                else:
                    if edge.target in self.nodes:
                        dfs(edge.target, new_path)
                    else:
                        paths.append(new_path + [f"__end__({edge.target})"])

        for start in start_nodes:
            dfs(start, [])

        return paths

    def _find_start_nodes(self) -> list[str]:
        """找起始节点（没有外部入边的节点）
        循环边不计入入边，因为循环边不会触发首次执行
        """
        has_incoming = set()
        for edge in self.edges:
            if edge.edge_type == EdgeType.LOOP:
                continue  # 循环边不计入
            if edge.target in self.nodes and edge.source != edge.target:
                has_incoming.add(edge.target)
        return [n for n in self.nodes if n not in has_incoming]

    def visualize(self) -> str:
        """生成 Mermaid 流程图文本"""
        lines = ["```mermaid", "graph TD;"]
        for name, node in self.nodes.items():
            node_type = node.node_type.value
            lines.append(f"    {name}[{name} ({node_type})];")

        for edge in self.edges:
            if edge.edge_type == EdgeType.CONDITIONAL:
                path_map = edge.metadata.get("path_map", {})
                for cond_val, target in path_map.items():
                    lines.append(f"    {edge.source} -->|{cond_val}| {target};")
            elif edge.edge_type == EdgeType.LOOP:
                lines.append(f"    {edge.source} -.->|loop| {edge.target};")
            else:
                lines.append(f"    {edge.source} --> {edge.target};")

        lines.append("```")
        return "\n".join(lines)

    def save_checkpoint(self, node_name: str, state: dict) -> Checkpoint:
        """保存检查点"""
        cp = Checkpoint(
            id=str(uuid.uuid4())[:8],
            node_name=node_name,
            state_snapshot=dict(state),
            timestamp=time.time()
        )
        self._checkpoints.append(cp)
        return cp

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """获取最新检查点"""
        return self._checkpoints[-1] if self._checkpoints else None

    def save_checkpoints_to_file(self, path: str):
        """保存所有检查点到文件"""
        data = {
            "checkpoints": [
                {
                    "id": cp.id,
                    "node_name": cp.node_name,
                    "state_snapshot": cp.state_snapshot,
                    "timestamp": cp.timestamp,
                    "metadata": cp.metadata
                }
                for cp in self._checkpoints
            ]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_checkpoints_from_file(self, path: str):
        """从文件加载检查点"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._checkpoints = [
            Checkpoint(
                id=cp["id"],
                node_name=cp["node_name"],
                state_snapshot=cp["state_snapshot"],
                timestamp=cp["timestamp"],
                metadata=cp.get("metadata", {})
            )
            for cp in data.get("checkpoints", [])
        ]


class CompiledGraph:
    """编译后的可执行图"""

    def __init__(self, graph: StateGraph):
        self.graph = graph
        self.max_iterations: int = 100  # 最大迭代次数（防无限循环）
        self.max_loop_depth: int = 10   # 单循环最大深度
        self._loop_counters: dict[str, int] = {}

    def invoke(self, initial_state: dict,
               start_node: Optional[str] = None,
               max_steps: Optional[int] = None) -> dict:
        """执行图

        Args:
            initial_state: 初始状态
            start_node: 起始节点（默认自动找）
            max_steps: 最大执行步数

        Returns:
            最终状态
        """
        state = dict(initial_state)
        state.setdefault("_history", [])
        state.setdefault("_errors", [])
        state.setdefault("_started_at", time.time())

        if start_node is None:
            start_nodes = self.graph._find_start_nodes()
            if not start_nodes:
                raise ValueError("图中没有起始节点")
            current = start_nodes[0]
        else:
            current = start_node

        steps = 0
        max_steps = max_steps or self.max_iterations
        self._loop_counters = {}

        while current is not None and steps < max_steps:
            steps += 1
            node = self.graph.nodes.get(current)
            if node is None:
                break

            # 执行节点函数
            if node.fn:
                try:
                    result = node.fn(state)
                    if isinstance(result, dict):
                        state.update(result)
                except Exception as e:
                    error_info = {
                        "node": current,
                        "error": str(e),
                        "step": steps,
                        "timestamp": time.time()
                    }
                    state["_errors"].append(error_info)
                    # 出错时记录并继续（不崩溃）
                    state.setdefault("_last_error", error_info)

            # 记录执行历史
            state["_history"].append({
                "node": current,
                "step": steps,
                "timestamp": time.time()
            })

            # 保存检查点（每 5 步 + 最后一步）
            if steps % 5 == 0:
                self.graph.save_checkpoint(current, state)

            # 找下个节点
            next_node = self._get_next_node(current, state)
            current = next_node

        # 最后一步也保存检查点
        if steps > 0 and steps % 5 != 0:
            self.graph.save_checkpoint(current or list(self.graph.nodes.keys())[-1], state)

        state["_total_steps"] = steps
        state["_finished_at"] = time.time()
        state["_elapsed"] = state["_finished_at"] - state["_started_at"]
        return state

    def _get_next_node(self, current: str, state: dict) -> Optional[str]:
        """根据边决定下一个节点"""
        edges = self.graph._adjacency.get(current, [])

        if not edges:
            return None  # 没有出边，结束

        if len(edges) == 1:
            edge = edges[0]
            return self._follow_edge(edge, state)

        # 多条边：按优先级处理
        # 1. 条件边优先
        conditional_edges = [e for e in edges if e.edge_type == EdgeType.CONDITIONAL]
        if conditional_edges:
            return self._follow_edge(conditional_edges[0], state)

        # 2. 循环边
        loop_edges = [e for e in edges if e.edge_type == EdgeType.LOOP]
        if loop_edges:
            return self._follow_edge(loop_edges[0], state)

        # 3. 普通边：取第一条
        return self._follow_edge(edges[0], state)

    def _follow_edge(self, edge: GraphEdge, state: dict) -> Optional[str]:
        """跟随一条边到目标节点"""
        if edge.edge_type == EdgeType.CONDITIONAL:
            if edge.condition_fn:
                result = edge.condition_fn(state)
                path_map = edge.metadata.get("path_map", {})
                target = path_map.get(result)
                if target and target in self.graph.nodes:
                    return target
                return None
            return None

        elif edge.edge_type == EdgeType.LOOP:
            # 检查循环条件
            if edge.condition_fn:
                should_loop = edge.condition_fn(state)
                if not should_loop:
                    return None  # 条件不满足，退出循环

            # 检查循环深度
            loop_key = f"{edge.source}->{edge.target}"
            self._loop_counters[loop_key] = self._loop_counters.get(loop_key, 0) + 1
            if self._loop_counters[loop_key] > self.max_loop_depth:
                return None  # 超过最大循环深度

            return edge.target

        else:
            # 普通边
            if edge.target in self.graph.nodes:
                return edge.target
            return None

    def stream(self, initial_state: dict) -> list[dict]:
        """逐步执行，返回每一步的状态快照"""
        state = dict(initial_state)
        state.setdefault("_history", [])
        state.setdefault("_errors", [])
        state["_started_at"] = time.time()

        start_nodes = self.graph._find_start_nodes()
        if not start_nodes:
            raise ValueError("图中没有起始节点")

        current = start_nodes[0]
        steps = 0
        snapshots = []
        self._loop_counters = {}

        while current is not None and steps < self.max_iterations:
            steps += 1
            node = self.graph.nodes.get(current)
            if node is None:
                break

            if node.fn:
                try:
                    result = node.fn(state)
                    if isinstance(result, dict):
                        state.update(result)
                except Exception as e:
                    state["_errors"].append({
                        "node": current, "error": str(e), "step": steps
                    })

            state["_history"].append({
                "node": current, "step": steps, "timestamp": time.time()
            })

            snapshots.append({
                "step": steps,
                "node": current,
                "state": dict(state),
                "elapsed": time.time() - state["_started_at"]
            })

            next_node = self._get_next_node(current, state)
            current = next_node

        return snapshots


# ============ 便捷构建函数 ============

def create_sequential_workflow(steps: list[tuple[str, Callable]],
                                name: str = "sequential") -> CompiledGraph:
    """创建顺序工作流（简化版）"""
    graph = StateGraph(name=name)
    for step_name, fn in steps:
        graph.add_node(step_name, fn)
    for i in range(len(steps) - 1):
        graph.add_edge(steps[i][0], steps[i + 1][0])
    return graph.compile()


def create_agent_loop(analyze_fn: Callable,
                      act_fn: Callable,
                      should_continue_fn: Callable[[dict], bool],
                      name: str = "agent_loop") -> CompiledGraph:
    """创建标准 Agent 循环（分析→行动→判断是否继续）"""
    graph = StateGraph(name=name)
    graph.add_node("analyze", analyze_fn)
    graph.add_node("act", act_fn)
    graph.add_edge("analyze", "act")
    graph.add_loop("act", "analyze",
                   condition_fn=should_continue_fn,
                   label="continue_loop")
    return graph.compile()


def create_branching_workflow(
        router_fn: Callable[[dict], str],
        branches: dict[str, list[tuple[str, Callable]]],
        name: str = "branching") -> CompiledGraph:
    """创建分支工作流（路由→各分支独立执行）"""
    graph = StateGraph(name=name)
    graph.add_node("router", router_fn)

    all_targets = []
    for branch_name, steps in branches.items():
        for step_name, fn in steps:
            graph.add_node(step_name, fn)
        # 路由到分支第一个节点
        first_step = steps[0][0]
        all_targets.append((branch_name, first_step))
        # 分支内部顺序连接
        for i in range(len(steps) - 1):
            graph.add_edge(steps[i][0], steps[i + 1][0])

    path_map = {name: target for name, target in all_targets}
    graph.add_conditional_edges("router", router_fn, path_map)
    return graph.compile()
