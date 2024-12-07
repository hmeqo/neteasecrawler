# 网易云歌单导出/下载

## 运行环境

下载 Chrome 浏览器

安装 uv, 以下为不同平台的 uv 安装命令

- Windows

  ```sh
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

- Linux

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

然后到项目目录下执行

```bash
uv sync --forzen
```

## 运行 cli

```sh
uv run python neteasecrawler.py
```
