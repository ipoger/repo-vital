# repo-vital

[English](README.md) | 中文

[![CI](https://github.com/ipoger/repo-vital/actions/workflows/ci.yml/badge.svg)](https://github.com/ipoger/repo-vital/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

**给仓库做一次"贡献友好度"体检，然后拿到一份按性价比排序的待办清单。**

一个陌生人打开你的项目，五分钟内就会决定要不要留下。repo-vital 只读工作区里的文件，告诉你这个人缺的是什么——license、CI、测试、issue 模板——以及哪个缺口最伤可信度。

不用配置文件，不联网，一条命令。

## 演示

```console
$ repo-vital /path/to/tiny-log

repo-vital 0.1.0  contributor readiness report
/path/to/tiny-log

  !  README              README.md is only 155 B
  ✔  License             MIT (LICENSE)
  ✘  Tests               no test files found
  ✘  CI                  no CI configuration — nothing verifies contributions
  ✘  Contributing guide  no CONTRIBUTING guide — newcomers do not know how to start
  ✔  Recent activity     committed today
  ✔  Package manifest    pyproject.toml
  ✔  Description         pyproject.toml: Structured logs for scripts, in one function.
  ✘  Code of conduct     no code of conduct
  ✔  Gitignore           2 rules
  ✘  Issue templates     no issue template — reports arrive incomplete
  ✘  PR template         no pull request template

  Score 42/100   Needs work   (42.5/100 points)

  Next steps
  1. README  +15 pts
     Explain what it is, why it matters, and how to run it.
     currently: README.md is only 155 B
  2. Tests  +15 pts
     Tests are what let a stranger change code without fear.
  3. CI  +15 pts
     Run tests automatically on every pull request.
```

## 安装

repo-vital 除了 Python 3.9+ 之外没有任何依赖。

```sh
pip install repo-vital
```

或者直接从仓库运行：

```sh
git clone https://github.com/ipoger/repo-vital.git
cd repo-vital
python3 -m repo_vital .
```

## 用法

```sh
repo-vital                 # 体检当前目录
repo-vital path/to/repo    # 体检别的仓库
repo-vital --json          # 输出机器可读的 JSON
repo-vital --fail-under 80 # 分数低于 80 时以退出码 1 结束
```

### 当作 CI 门禁

```yaml
- name: Check contributor readiness
  run: |
    pip install repo-vital
    repo-vital . --no-color --fail-under 80
```

`--json` 会输出总分、每一条检查的明细和待办，可以直接接看板或机器人：

```json
{
  "tool": "repo-vital",
  "score": 42,
  "band": "Needs work",
  "checks": [{ "id": "readme", "status": "warn", "weight": 15, "detail": "..." }],
  "next": [{ "id": "readme", "points": 15, "hint": "..." }]
}
```

### 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 扫描完成（若指定了 `--fail-under`，则同时满足门槛） |
| `1` | 分数低于 `--fail-under` |
| `2` | 用法错误，或路径不是目录 |

## 检查项

每条规则都只依赖工作区里的文件，权重加起来是 100。

| 规则 | 权重 | 什么情况下通过 |
| --- | --- | --- |
| README | 15 | 超过 400 字符，且提到 install、usage 或 quick start |
| License | 15 | 存在 `LICENSE`/`COPYING`，且内容能匹配到已知许可证 |
| Tests | 15 | 专门的 `tests/` 目录下至少有 5 个测试用例 |
| CI | 15 | `.github/workflows/` 下有 workflow，或其他常见 CI 配置文件 |
| 贡献指南 | 10 | `CONTRIBUTING.md` 提到测试、issue、PR、风格或 lint |
| 近期活跃 | 5 | 最后一次提交在 180 天内 |
| 包清单 | 5 | 存在 `pyproject.toml`、`package.json`、`Cargo.toml`、`go.mod` 等 |
| 项目描述 | 5 | 清单里带有超过 12 字符的描述 |
| 行为准则 | 5 | 存在 `CODE_OF_CONDUCT.md` |
| Gitignore | 5 | `.gitignore` 至少包含两条规则 |
| Issue 模板 | 3 | `.github/ISSUE_TEMPLATE/` 下至少有一个文件 |
| PR 模板 | 2 | 存在 `.github/pull_request_template.md` |

## 计分方式

- **pass** 拿满权重，**warn** 拿一半，**missing** 不得分。
- 分数区间：`85+` 优秀，`65–84` 良好，`40–64` 待改进，低于 40 属于起步阶段。
- warn 用来描述那些"有，但没用"的中间状态：README 存在却什么也没说、测试散落在 `tests/` 之外、项目半年没动。

权重是主观的，而且是刻意主观的。license 和测试的权重是 PR 模板的七倍，因为它们决定的是别人**能不能**贡献，而不是贡献得顺不顺手。

## 设计原则

1. **离线且确定。** 同样的文件树，同样的分数。不调 API、不爬徽章、不猜 star 数。
2. **零配置。** 如果一条规则需要写配置文件才有用，它就不适合放进这个五分钟体检里。
3. **给建议，不做审判。** 每个失败都必须说出下一步做什么。没有下一步的分数，只是一个多此一举的 linter。

## 路线图

- [x] `README.zh-CN.md`
- [ ] `--fix`：自动补齐机械性的缺口（`LICENSE`、模板、workflow）
- [ ] 分语言规则包（Go、Rust、TypeScript）
- [ ] GitHub Action 封装，在 PR 上直接评论分数

有规则想法？开一个 [Rule idea](https://github.com/ipoger/repo-vital/issues/new?template=rule_idea.yml) issue——模板只问三个真正重要的问题。

## 参与贡献

任何规模的贡献都欢迎，包括改措辞。先读 [CONTRIBUTING.md](CONTRIBUTING.md)。注意 CI 会拿这个工具检查本仓库自身：分数掉到 100 以下，构建就会失败。

## 许可证

[MIT](LICENSE) © 2026 ipoger
