## 数据迁移指南 (从本地开发到生产环境)

本指南旨在帮助您将本地开发环境中积累的有用数据，安全、完整地迁移到云端生产服务器上。

---

### 1. 迁移背景

根据项目设计，核心数据被持久化在以下三个由 Docker Volume 映射的本地目录中：

*   `./data/`: 存储 SQLite 数据库文件（`.db`），包含所有结构化的生活事件和日程安排。
*   `./chroma_data/`: 存储 ChromaDB 的向量数据，包含所有的“软记忆”。
*   `./ollama_data/`: 存储 Ollama 下载的大语言模型文件。

迁移的目标就是将这三个目录从您的本地计算机同步到 Oracle Cloud 服务器的相应项目路径下。

---

### 2. 迁移前准备

1.  **停止本地服务：** 在本地项目根目录下，执行 `docker-compose down`，确保所有容器都已停止，防止在复制过程中有新数据写入。
2.  **准备服务器：**
    *   确保您可以通过 SSH 访问 Oracle Cloud 服务器。
    *   在服务器上，已经通过 `git clone` 或其他方式创建了与本地结构一致的项目目录。
    *   确保服务器上已安装 `rsync` (大多数 Linux 发行版自带)。`rsync` 是一个强大的文件同步工具，比 `scp` 更适合同步整个目录。

---

### 3. 迁移步骤

以下所有命令都在 **您的本地计算机** 的终端中执行。请将 `user@your_server_ip` 和 `/path/to/your/project` 替换为您的实际服务器用户名、IP 地址和项目路径。

#### A. 迁移 SQLite 数据库

这是最关键的数据。

```bash
# -a: 归档模式，保留文件属性
# -v: 显示详细过程
# -z: 传输时压缩
# --progress: 显示进度条
rsync -avz --progress ./data/ user@your_server_ip:/path/to/your/project/data/
```

#### B. 迁移 ChromaDB 向量数据

此目录可能较大，`rsync` 会非常高效。

```bash
rsync -avz --progress ./chroma_data/ user@your_server_ip:/path/to/your/project/chroma_data/
```

#### C. 迁移 Ollama 模型 (可选但推荐)

迁移模型可以避免在服务器上重新下载，节省时间和带宽。

```bash
rsync -avz --progress ./ollama_data/ user@your_server_ip:/path/to/your/project/ollama_data/
```

---

### 4. 最终启动

1.  **SSH 登录服务器：** `ssh user@your_server_ip`
2.  **进入项目目录：** `cd /path/to/your/project`
3.  **检查文件：** 使用 `ls -l data/` 和 `ls -l chroma_data/` 等命令，确认文件和目录已成功迁移。
4.  **启动生产服务：** 执行 `docker-compose up -d`。

现在，您在云端的 VedaAide 助手就拥有了所有本地的历史数据，可以无缝接续您的使用习惯。