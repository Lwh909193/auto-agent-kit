#!/usr/bin/env python3
"""PyPI 发布脚本 — 构建 + 上传"""
import subprocess
import sys


def run(cmd: str, cwd: str | None = None) -> int:
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode


def main():
    project_dir = r"G:\.openclaw\workspace\projects\AutoAgentKit"

    print("=" * 60)
    print("  AutoAgentKit PyPI 发布流程")
    print("=" * 60)

    # 1. 清理旧构建
    print("\n[1/4] 清理旧构建文件...")
    run("rm -rf dist build *.egg-info", cwd=project_dir)

    # 2. 构建
    print("\n[2/4] 构建包...")
    if run("python -m build", cwd=project_dir) != 0:
        print("❌ 构建失败")
        sys.exit(1)

    # 3. 检查
    print("\n[3/4] 检查包内容...")
    run("twine check dist/*", cwd=project_dir)

    # 4. 上传
    print("\n[4/4] 上传到 PyPI...")
    print("  需要设置环境变量 TWINE_USERNAME 和 TWINE_PASSWORD")
    print("  或使用 API token: TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-xxx")
    print()
    resp = input("  确认上传到 PyPI? (y/N): ").strip().lower()
    if resp == "y":
        if run("twine upload dist/*", cwd=project_dir) == 0:
            print("\n✅ 发布成功!")
        else:
            print("\n❌ 上传失败")
            sys.exit(1)
    else:
        print("\n⏸️  跳过上传")


if __name__ == "__main__":
    main()
