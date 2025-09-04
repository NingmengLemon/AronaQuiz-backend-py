# HDU Software Development Practice 2 Hw - Backend

HDU 软件开发实践2: 刷题助手 (暂定名) (后端)

前端参见: [Bian-Mu/term2_web_frontend](https://github.com/Bian-Mu/term2_web_frontend)

> 其实还是自己的练手作~~和后端开发处女作~~ (目移)

## 部署

安装 [uv](https://docs.astral.sh/uv/)

clone 仓库, cd 到仓库根目录

```bash
uv sync --no-dev
uv run fastapi run src/app
```

更多自定义参数自行添加

## 开发/测试

clone, cd

```bash
uv sync --all-groups
```

提供 `data/example.db` 作为测试素材 (内容摘自 HDU 题库)

运行测试:

```bash
uv run pytest
```

## (以下写给自己看)

### Models

- 数据库用模型 (带`DB`前缀)
    `id`字段有默认工厂, 能自动生成
  - `DBOption` - 选项模型
  - `DBProblem` - 问题模型
  - `DBProblemSet` - 问题集模型
  - `DBUser` - 用户模型
  - `DBAnswerRecord` - 答题记录模型 (统计用~~, 计划后续改为记录每次答题而不是总数~~)

- 请求创建用模型 (带`Submit`后缀)
    没有`id`字段, 因为入库时会由数据库用模型自动生成
  - `OptionSubmit` - 选项提交模型
  - `ProblemSubmit` - 问题提交模型
  - `ProblemSetSubmit` - 问题集提交模型

- 响应用模型 (带`Response`后缀)
    `id`字段必填, 因为要作为响应交给前端
  - `OptionResponse` - 选项响应模型
  - `ProblemResponse` - 问题响应模型 (包含统计信息)
  - `ProblemSetResponse` - 问题集响应模型 (包含题目数量)
  - `UserResponse` - 用户响应模型

- 基类/Mixin用模型 (带`Base`前缀)
  - `_BaseOption` - 选项基类
  - `_BaseProblem` - 问题基类
  - `_BaseProblemSet` - 问题集基类
  - `_BaseStatistic` - 统计基类
  - `_BaseUser` - 用户基类

- 枚举类型
  - `ProblemType` - 问题类型枚举 (single_select, multi_select)
  - `ProblemSetCreateStatus` - 问题集创建状态枚举 (success, already_exists)

### DB Operations

涉及到写/多次读的操作方法会单开 transaction 执行, 且失败会自动回滚

- `create_problemset()` - 创建问题集
- `add_problems()` - 添加问题
- `search_problem()` - 搜索问题
- `delete_problems()` - 删除问题
- `delete_problemset()` - 删除问题集
- `get_problem_count()` - 获取问题数量
- `sample()` - 随机抽样问题
- `list_problemset()` - 列出问题集
- `query_user()` - 查询用户
- `ensure_user()` - 确保用户存在
- `report_attempt()` - 报告答题尝试
- `delete_all()` - 删除所有数据 (测试用)

### Web API

#### 问题管理 (`/api/v1/problem`)

- `POST /create_set` - 创建问题集
- `GET /list_set` - 列出所有问题集
- `POST /add` - 添加问题到问题集
- `GET /search` - 搜索问题
- `GET /get` - 获取问题列表
- `GET /count` - 获取问题数量
- `POST /delete` - 删除问题
- `POST /_delete_all` - 删除所有问题 (测试用)

#### 题目表 (`/api/v1/sheet`)

- `GET /random` - 随机获取指定数量的题目
- `GET /report` - 报告答题尝试 ~~(其实我觉得应该用POST? 但是既然前端都这么说了...)~~

### 项目功能

- 问题管理: 支持创建问题集、添加/删除问题、搜索问题
- 题目类型: 支持单选题 (`single_select`) 和多选题 (`multi_select`)
- 答题功能: 随机抽题与答题记录统计
- 统计功能: 记录每个用户对每个题目的答题正确情况
- 搜索功能: 支持按关键词搜索问题和选项内容

### 技术栈

- 框架: FastAPI
- 数据库: SQLite (开发/测试), 计划支持 PostgreSQL
- ORM: SQLModel (基于 SQLAlchemy 和 Pydantic)
- 异步: 全异步
- 测试: pytest

### 数据库设计

- 使用 UUID 作为主键
- 答题记录使用联合主键
- 支持事务操作
- 支持级联删除 (?) ~~(不知道是写法不对还是SQLite不支持, 还是得手动删)~~

### 目录结构

```
src/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── problem.py    # 问题管理API
│   │   │   └── sheet.py      # 答题表API
│   │   └── deps.py           # 依赖注入与管理
│   ├── db/
│   │   ├── models.py         # 数据库模型
│   │   ├── operations.py     # 数据库操作
│   │   ├── core.py           # 数据库核心
│   │   ├── decos.py          # 装饰器
│   │   └── utils.py          # 工具函数
│   ├── schemas/
│   │   └── problem.py        # Pydantic模型
│   └── main.py               # 应用入口
tests/
├── test_api.py               # API测试
└── test_db.py                # 数据库测试
```
