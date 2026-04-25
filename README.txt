产品技术资料管理系统
========================

一个用于管理航空设备测试产品技术文档的 Web 系统。
直接运行在 Windows 上，无需 Docker。


快速开始
--------
1. 确保已安装 Python 3.9+（推荐 3.11）
   下载: https://www.python.org/downloads/
   安装时勾选 "Add Python to PATH"

2. 把整个 tech-doc-agent 文件夹复制到你的电脑上

3. 双击 "启动服务.bat"

4. 浏览器打开 http://localhost:8080

5. 用默认账号登录: admin / admin123
   ⚠️ 首次登录后请立即修改密码！


功能说明
--------
- 文档上传：支持 PDF/Word/Excel/PPT/CAD/图片/压缩包等
- 文档加密：所有上传的文件都经过 AES 加密存储
- 全文搜索：按标题、编号、产品型号快速查找
- 用户管理：管理员/编辑/普通用户三级权限
- 分类管理：按产品线组织文档（BY-6B、MII-100M-2 等）
- 操作日志：记录所有文档的上传、下载、查看操作
- REST API：提供 /api/documents 接口，便于未来系统集成


目录结构
--------
tech-doc-agent/
├── app.py              主程序
├── config.py           配置文件
├── database.py         数据库模型
├── auth.py             认证模块
├── encryption.py       文件加密
├── requirements.txt    Python 依赖
├── 启动服务.bat         Windows 启动脚本
├── templates/          页面模板
├── static/             静态资源
├── data/               加密文件存储
├── database/           SQLite 数据库
└── .secret_key         系统密钥（自动生成）
└── .doc_key            文档加密密钥（自动生成）


局域网部署
----------
1. 在主机上运行 "启动服务.bat"
2. 查看主机 IP 地址（命令行运行 ipconfig）
3. 其他同事在浏览器输入 http://主机IP:8080
4. 防火墙需要放行 8080 端口


修改端口
--------
编辑 config.py，修改 PORT = 8080 为你想要的端口


数据备份
--------
备份以下两个文件即可：
- database/app.db     （数据库）
- data/               （加密文档）
- .secret_key         （系统密钥）
- .doc_key            （文档加密密钥）


注意事项
--------
- .doc_key 是文档加密密钥，丢失后所有文档无法解密，请务必妥善备份！
- 数据库文件在 database/app.db，可用 SQLite 工具直接查看
- 所有上传的文件都经过加密，即使直接拿到文件也无法读取内容
