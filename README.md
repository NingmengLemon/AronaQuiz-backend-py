# HDU Software Development Practice 2 Lab Backend

HDU 软件开发实践2: 刷题助手 (暂定名) (后端)

## 部署

安装 [uv](https://docs.astral.sh/uv/)

clone 仓库, cd 到仓库根目录

```bash
uv sync --no-dev
uv run fastapi run src/app
```

更多自定义参数自行添加, 需要开发用依赖就把`--no-dev`去掉
