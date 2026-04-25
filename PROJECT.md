# 产品技术资料管理系统 - 项目文档

> 航空设备测试产品技术资料管理系统
> GitHub: https://github.com/zf9702/product-tech-agent
> 最后更新: 2026-04-25

---

## 一、项目概述

为航空设备测试工程师打造的产品技术资料管理系统，支持文档加密存储、
在线预览、知识问答（AI）、投标文件符合性检查等功能。

**用户**: 桂林长海发展有限责任公司（桂林厂）
**主要产品线**: BY-6B整流装置、IMP-200BY输出接触器、MII-100M-2电动机构
**部署方式**: Windows 本地运行，局域网约30人使用

---

## 二、技术架构

```
前端: Bootstrap 5 + Jinja2 模板 + 原生 JavaScript
后端: FastAPI (Python) + SQLite + Fernet 加密
AI:   可配置（DeepSeek/OpenAI/通义千问/MiMo）
Office: pywin32 调用 WPS/Word COM 接口转 PDF
```

### 文件结构

```
tech-doc-agent/
├── app.py              主程序（路由、启动、所有页面逻辑）
├── config.py           配置（路径、端口、加密密钥、文件类型）
├── database.py         数据库模型（SQLAlchemy ORM）
├── auth.py             认证（JWT + bcrypt）
├── encryption.py       文件加密/解密（Fernet AES）
├── doc_parser.py       文档内容提取 + FTS5全文检索
├── ai_engine.py        AI模型接口（可配置后端）
├── office_convert.py   WPS/Word COM 转 PDF
├── requirements.txt    Python 依赖
├── 启动服务.bat         Windows 启动脚本
├── templates/          15个HTML模板
├── static/             静态资源（CSS/JS）
├── data/               加密文件存储
├── database/           SQLite 数据库
├── .secret_key         JWT密钥（自动生成）
├── .doc_key            文档加密密钥（自动生成）
└── ai_config.json      AI配置（首次使用时配置）
```

### 数据库表

| 表名 | 用途 |
|------|------|
| users | 用户（admin/editor/viewer 三级权限） |
| categories | 文档分类（自定义） |
| doc_number_rules | 文件编号规则（国标规范） |
| documents | 文档记录（元数据） |
| access_logs | 操作日志 |
| product_specs | 产品技术参数卡片 |
| doc_fts | FTS5全文检索虚拟表 |

---

## 三、已完成功能

### 文档管理
- [x] 用户登录认证（JWT，8小时有效期）
- [x] 三级权限（管理员/编辑/普通用户）
- [x] 单个上传 + 批量上传（多文件拖拽，自动编号）
- [x] AES加密存储（Fernet对称加密）
- [x] 文件编号自动生成（国标规范，10个预设规则）
- [x] 文档分类管理（自定义添加）
- [x] 批量删除（复选框+确认）
- [x] 全文搜索（FTS5 + LIKE中文兼容）
- [x] 在线预览（PDF/图片/Word via WPS转PDF）
- [x] 操作日志记录

### AI 功能
- [x] 知识问答（聊天式，基于文档+参数卡片）
- [x] 符合性检查（投标文件 vs 标准，逐条比对）
- [x] AI模型配置页面（支持多种提供商）
- [x] 测试连接按钮

### 产品参数卡片
- [x] 结构化存储（产品型号/参数类别/名称/值/单位/标准要求）
- [x] 6个参数类别（电气/机械/环境/性能/安全/其他）
- [x] Excel批量导入
- [x] 问答和符合性检查自动引用参数卡片

### 系统管理
- [x] 用户管理（增删改、启用/禁用）
- [x] 分类管理
- [x] 编号规则管理
- [x] AI设置
- [x] 局域网部署（防火墙端口开放）

---

## 四、待开发功能

### 优先级高
- [ ] 修改密码功能（当前admin没有改密码入口）
- [ ] 文档版本管理（同一文档多版本）
- [ ] 重新索引功能（管理界面一键重建全文索引）

### 优先级中
- [ ] 数据统计报表（按产品/分类/时间统计）
- [ ] 数据备份工具（一键备份数据库+文件）
- [ ] 文档在线编辑（基于WPS Web SDK）
- [ ] 多人协作标注

### 优先级低
- [ ] MS系统集成
- [ ] 移动端适配
- [ ] 数据导入导出

---

## 五、部署步骤

### 新机器部署

1. 安装 Python 3.9+（推荐3.11，安装时勾选Add to PATH）
2. 安装 WPS Office（用于Word预览）
3. 克隆仓库：
   ```
   git clone https://github.com/zf9702/product-tech-agent.git
   cd product-tech-agent
   ```
4. 安装依赖：
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
5. 启动：
   ```
   python app.py
   ```
6. 浏览器打开 http://localhost:8080
7. 默认账号 admin / admin123（首次登录后修改密码）

### 局域网部署
- 开放防火墙端口8080
- 同事访问 http://你的IP:8080
- 查IP: 命令行运行 ipconfig

---

## 六、关键设计决策

1. **加密存储**: 所有上传文件用Fernet(AES)加密，密钥在.doc_key文件中
   - ⚠️ .doc_key丢失 = 所有文件无法解密，务必备份

2. **中文搜索**: FTS5的unicode61分词器不支持中文词组
   - 方案: FTS5优先，失败回退LIKE搜索，再失败返回文档目录

3. **Word预览**: 使用pywin32调用WPS COM接口转PDF
   - 需要WPS或Word安装在本地
   - 转换结果缓存在data/pdf_cache/

4. **AI配置**: 支持所有OpenAI兼容API
   - 配置保存在ai_config.json
   - 不配置也能用（只是问答和符合性检查不可用）

5. **编号规则**: 按国标规范，格式: 产品型号-类型码-年份-流水号
   - 预设10个航空产品文件类型码（TD/DW/JS/JY/GY/BZ/YJ/FA/BG/QT）

---

## 七、常见问题

### Q: 上传后搜索不到内容？
A: 上传时会自动提取文本并建索引。旧文档需要重新上传或手动重建索引。

### Q: Word预览显示失败？
A: 需要安装WPS或Microsoft Word。检查pywin32是否安装：pip install pywin32

### Q: AI问答没有反应？
A: 需要在 系统管理 > AI 设置 中配置模型接口。推荐DeepSeek（便宜好用）。

### Q: 局域网其他人访问不了？
A: 检查防火墙是否放行8080端口，检查IP地址是否正确。

---

## 八、数据备份

备份以下文件即可：
- database/app.db     （数据库）
- data/               （加密文档）
- .secret_key         （JWT密钥）
- .doc_key            （文档加密密钥）
- ai_config.json      （AI配置）

⚠️ .doc_key 和 .secret_key 丢失将无法恢复数据！
