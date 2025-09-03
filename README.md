# HDU Software Development Practice 2 Lab Backend

HDU 软件开发实践2: 刷题助手 (暂定名) (后端)

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
