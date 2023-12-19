---
title: 常见问题
---

## 名词解释

#### 什么是申请人（申请案例）、数据点、项目？

「申请人」（或「申请案例」）指的是某个同学的所有信息。「数据点」指的是某个申请人申请某个项目的结果，属于申请人。「项目」指的是某个项目的信息，所有申请人共享。每个数据点对应一个项目。

#### 数据点和申请人是什么关系？

一个申请人可以有多个数据点，代表申请人申请的多个项目。

## 提交数据

#### 在选择项目时找不到自己申请的项目

如果您申请的项目还不在数据库中，您可以通过以下步骤添加：

??? note "添加项目的步骤"

    **1. 在“项目”栏对应的格子中点击 + 号**
    !!! note ""
        ![](assets/add-record.png)

    **2. 点击左上角返回按钮**

    !!! note ""
        ![](assets/add-record-1.png)

    **3. 点击右上角添加记录**

    !!! note ""
        ![](assets/add-record-2.png)

    **4. 输入项目信息并点击右下角提交**
    
    请注意，不需要在这个界面中添加数据点。

    !!! note ""
        ![](assets/add-record-3.png)

#### 如何删除已提交的个人资料/数据点？

在一行的最左侧处右键，选择“删除行”即可。

??? note "查看图片"
    ![](assets/delete-record.png)

## 文档更新

#### 提交了个人信息/数据点，但是没有找到申请案例/看到更新

本文档并非实时更新。我们使用 GitHub Actions 自动更新文档，频率为 6 小时一次，在网页左下角可以看到上一次更新的时间。在下一次更新时您的信息将会被更新到文档中。

#### 文档更新后还是看不到提交/更新的申请案例/数据点

为避免无效案例出现在文档中，我们会对案例进行筛选。只要您的个人资料中包括至少一个有效（即信息完整的）数据点，您的申请案例就会被更新到文档中。具体逻辑请参考[相关代码](https://github.com/liang2kl/feiyue-database/blob/main/feiyue/backend/__init__.py)。

#### 文档有 PDF 版本吗？

目前还没有。我们计划在每年申请季开始将前一年的案例制作为 PDF，并发布在 [Release 页面](https://github.com/liang2kl/feiyue-database/releases)上。

## 数据公开与安全

#### 数据是否完全公开？我可以通过什么方式获取？

完整的数据库公开在 SeaTable 上。除了直接在 SeaTable 上浏览，您也可以在 SeaTable 页面中右上角点击导出下载完整数据库。我们不限制清华大学以外的同学访问。

#### 如何保证数据安全？

每次使用 GitHub Actions 更新文档时，我们会对完整数据库进行备份，存于 Actions 的 Artifacts 中，您可以在 [Actions 页面](https://github.com/liang2kl/feiyue-database/actions/workflows/publish.yml)中查看。另外，我们也会定期使用 Internet Archive 的 Wayback Machine 对文档进行快照，您可以在[这里](https://web.archive.org/web/*/https://liang2kl.github.io/feiyue-database/)查看。

#### 如何防止恶意行为？

完整数据库只有公开的只读权限。任何人可以添加申请人信息/数据点，但只能修改当前账号创建的记录。为了方便提交数据，我们无法完全防止恶意行为，但会通过定期清除无效数据解决。
