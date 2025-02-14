# Feiyue 模块

## 项目简介

**Feiyue** 是一个集成后端数据处理与前端文档生成的自动化工具集。通过与 Seatable API 的无缝集成，Feiyue 模块能够高效地获取、处理和清洗数据，并基于这些数据生成多种格式的结构化文档，如 LaTeX 和 MkDocs。该模块旨在简化文档项目的创建与维护，适用于需要系统化管理和展示大量数据的各类项目。

## 主要功能

### 后端 (Backend)

- **数据获取**
  - 从 Seatable API 获取所有相关数据表（本科专业、申请人、项目、数据点）的完整数据集。

- **数据处理与关联**
  - 重建申请人与数据点之间的关系，确保数据的完整性和一致性。

- **数据验证与过滤**
  - 过滤掉无效或不完整的数据记录，保证数据质量。

- **数据更新**
  - 自动设置申请人的最新学期信息。
  - 更新申请人的昵称，确保每个申请人都有唯一的标识。
  - 替换申请总结中的图片 URL 为本地路径，便于前端模块引用本地资源。

- **图片处理**
  - 下载申请人总结中的图片资源，确保图片在生成的文档中能够正确显示。

### 前端 (Frontend)

- **自动生成文档结构**
  - 根据申请人、专业、项目等数据自动创建相应的文档页面。

- **模板化设计**
  - 使用 Jinja2 模板引擎，支持自定义模板以满足不同的文档内容和样式需求。

- **多格式支持**
  - 支持生成多种格式的文档，如 LaTeX 和 MkDocs，适应不同的文档发布平台和需求。

- **资源管理**
  - 支持复制图片等资源到生成的文档目录，确保文档中图片的正确显示。

- **自动生成配置文件**
  - 根据生成的文档结构，自动创建相应的配置文件（如 `mkdocs.yml`），简化项目配置流程。

- **时间戳生成**
  - 在文档中自动添加生成时间，便于版本管理和追踪。

## 子模块介绍

### Backend 子模块

**Backend** 子模块负责从 Seatable API 获取和处理数据，为前端文档生成提供结构化的数据信息。

- **`__init__.py`**

  - **数据获取**
    - `get_all_rows(api_key: str) -> tuple[dict, dict, dict, dict]`  
      使用提供的 API 密钥初始化 Seatable API，并获取所有的本科专业、申请人、项目和数据点数据。
  
  - **数据关联**
    - `_rebuild_relations(applicants: dict, datapoints: dict)`  
      重建申请人与数据点之间的关联，确保每个申请人包含其对应的数据点。
  
  - **数据过滤**
    - `filter_out_invalid(applicants: dict, datapoints: dict, programs: dict, majors: dict)`  
      过滤掉无效的申请人、数据点、项目和专业，确保数据的有效性和完整性。
  
  - **数据更新**
    - `set_term(applicants: dict, datapoints: dict, key: str)`  
      为每个申请人设置最新的学期信息。
    - `update_nickname(applicants: dict)`  
      为缺少昵称的申请人自动生成昵称。
    - `update_image_path(applicants: dict, base_path: str) -> list[tuple[str, str]]`  
      将申请总结中的图片 URL 替换为本地路径，并返回替换的映射关系。
  
  - **图片下载**
    - `download_image(path: str, api_key: str) -> bytes`  
      下载指定路径的图片内容。

- **`api.py`**

  - **API 请求**
    - `seatable_request(method: str, path: str, params: dict = None, data: dict = None)`  
      通用的 Seatable API 请求函数，处理请求的发送和响应的验证。
  
  - **初始化 API Token**
    - `init_base_token(api_key: str)`  
      使用提供的 API 密钥获取访问令牌和数据表 UUID，初始化 API 访问所需的全局变量。
  
  - **获取所有行**
    - `get_all_rows(table_name: str)`  
      分批次从指定的数据表中获取所有行数据，确保数据的完整性。
  
  - **获取图片直接链接**
    - `get_image_direct_url(file_name: str, api_key: str) -> str`  
      获取指定文件名的图片的直接下载链接，便于下载图片内容。

### Frontend 子模块

**Frontend** 子模块负责基于处理后的数据生成多种格式的文档，包括 LaTeX 和 MkDocs。

- **`__init__.py`**
  - 定义了 `Frontend` 基类，提供通用的初始化、预构建、构建文档及资源管理功能。

- **`latex.py`**

  - **LatexFrontend**
    - **生成文件**
      - `main.tex`
      - `all_areas.tex`
      - `applicant/<applicant_id>.tex`
      - `major/<major_id>.tex`
      - `program/<program_id>.tex`
    
    - **功能特点**
      - **LaTeX 特殊字符转义**
        - 确保生成的 LaTeX 文档格式正确，避免编译错误。
      
      - **自定义列表缩进**
        - 兼容不同编辑器的缩进需求，确保列表格式在 LaTeX 中正确显示。
      
      - **数据排序与统计**
        - 按院系排序专业，按数据点数量排序项目，计算 GPA 中位数等，提升文档的组织性。
      
      - **模板渲染**
        - 使用 Jinja2 模板生成各类 LaTeX 文件，确保内容一致且格式统一。

- **`mkdocs.py`**

  - **MkDocsFrontend**
    - **生成文件**
      - `docs/`
        - `index.md`
        - `area.md`
        - `applicant/index.md`
        - `applicant/<applicant_id>.md`
        - `major/index.md`
        - `major/<major_id>.md`
        - `program/index.md`
        - `program/<program_id>.md`
      - `mkdocs.yml`
    
    - **功能特点**
      - **MkDocs 结构生成**
        - 自动创建适用于 MkDocs 的文档目录结构，便于快速搭建和维护项目文档网站。
      
      - **配置文件生成**
        - 自动生成 `mkdocs.yml` 配置文件，简化 MkDocs 项目的配置流程。
      
      - **模板渲染**
        - 使用 Jinja2 模板生成各类 Markdown 文件，确保内容一致且格式统一。
      
      - **数据排序与统计**
        - 按申请人数量排序专业，按数据点数量排序项目，提升文档的组织性和可导航性。

## 目录结构

**Feiyue** 模块的基本目录结构如下：

```
feiyue/
├── backend/
│   ├── __init__.py          # 数据获取与处理核心功能
│   └── api.py               # Seatable API 交互功能
├── frontend/
│   ├── __init__.py          # Frontend 基类
│   ├── latex.py             # LatexFrontend 子模块
│   └── mkdocs.py            # MkDocsFrontend 子模块
```

- **backend/**: 负责数据的获取与处理，与 Seatable API 进行交互。
  - **`__init__.py`**: 包含从 Seatable API 获取和处理数据的主要函数。
  - **`api.py`**: 提供与 Seatable API 进行通信的接口函数。

- **frontend/**: 负责文档的生成，包括 LaTeX 和 MkDocs 格式的文档输出。
  - **`__init__.py`**: 定义了 `Frontend` 基类，提供通用的初始化、预构建、构建文档及资源管理功能。
  - **`latex.py`**: 实现了 `LatexFrontend` 类，用于生成 LaTeX 格式的文档。
  - **`mkdocs.py`**: 实现了 `MkDocsFrontend` 类，用于生成 MkDocs 格式的文档。

## 依赖项

Feiyue 模块依赖以下主要库：

- **Jinja2**: 模板引擎，用于渲染 Markdown 和 LaTeX 文档。
- **requests**: 用于发送 HTTP 请求，与 Seatable API 进行通信。
- **pathlib**: 处理文件和目录路径。
- **datetime**: 生成构建时间戳。
- **shutil**: 复制文件和目录。
- **re**: 正则表达式处理。
- **statistics**: 进行统计计算，如计算 GPA 中位数。

*注：部分依赖库如 `pathlib`、`re` 和 `statistics` 是 Python 标准库的一部分，无需额外安装。*
