产品技术资料管理系统
====================

航空设备测试产品技术资料管理平台
支持文档加密存储、在线预览、AI知识问答、投标文件符合性检查

GitHub: https://github.com/zf9702/product-tech-agent


快速开始
--------
1. 安装 Python 3.9+（勾选 Add to PATH）
2. 安装 WPS Office（Word预览需要）
3. 双击 "启动服务.bat"
4. 浏览器打开 http://localhost:8080
5. 账号 admin / admin123


功能
----
- 文档管理：上传/下载/预览/批量上传/批量删除
- 智能编号：按国标规范自动生成文件编号
- 在线预览：PDF/图片/Word（WPS转PDF）
- 知识问答：AI基于文档和参数卡片回答问题
- 符合性检查：投标文件vs标准逐条比对
- 参数卡片：产品技术参数结构化管理
- 用户管理：管理员/编辑/普通用户三级权限
- 加密存储：所有文件AES加密


局域网部署
----------
- 开放防火墙：netsh advfirewall firewall add rule name="TechDocAgent" dir=in action=allow protocol=TCP localport=8080
- 同事访问：http://你的IP:8080


技术栈
------
FastAPI + SQLite + Fernet + Bootstrap 5 + pywin32
