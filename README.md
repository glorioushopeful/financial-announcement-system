# 金融行业公告数据采集与可视化系统

以 **贵州茅台（600519）** 为样本，实现上市公司公告的完整数据闭环：

```
巨潮资讯网/新浪财经 ──► Requests+BeautifulSoup 采集 ──► Pandas 清洗
        ──► Excel/CSV 导出 ──► SQLite 存储 ──► Flask API ──► ECharts 大屏
```

## 技术栈

| 层次 | 技术 |
|---|---|
| 采集 | `requests`、`BeautifulSoup4`、`lxml` |
| 清洗 | `pandas` |
| 存储 | `SQLite`（内置）、`openpyxl`（Excel）、CSV |
| 服务 | `Flask` |
| 展示 | HTML / CSS / JavaScript + `ECharts 5` |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 采集数据并启动大屏（推荐，一步到位）
python run.py

# 打开浏览器访问 http://127.0.0.1:5000
```

其他命令：

```bash
python run.py crawl              # 只跑采集流水线，不启动服务
python run.py serve              # 只启动服务，使用已有数据
python run.py crawl --sources mock          # 断网演练：使用本地样例数据
python run.py crawl --sources cninfo,sina   # 指定数据源顺序
python run.py --port 8080        # 指定端口
```

## 目录结构

```
├── config.py              全局配置（标的、数据源、路径、分类规则）
├── pipeline.py            流水线编排：采集→清洗→导出→入库
├── run.py                 命令行入口
├── app.py                 Flask API 与大屏托管
├── cleaner.py             Pandas 清洗（去标签、日期规整、去重、分类）
├── exporter.py            Excel / CSV 导出（带表头样式与列宽）
├── crawler/
│   ├── base.py            爬虫基类：重试、休眠、标准化
│   ├── cninfo.py          巨潮资讯网（主源，证监会指定披露平台）
│   ├── sina.py            新浪财经（备用源）
│   ├── mock.py            本地样例（断网兜底）
│   └── manager.py         数据源调度与自动降级
├── storage/database.py    SQLite 读写与聚合查询
├── web/
│   ├── index.html         大屏页面
│   ├── css/style.css      深色科技风样式
│   └── js/main.js         ECharts 渲染与交互
└── data/                  运行产物：announcements.db / .csv / .xlsx
```

## 数据源与降级策略

`config.DATA_SOURCES = ["cninfo", "sina", "mock"]` 按优先级依次尝试，
任一源返回非空数据即采用，全部失败才报错，保证系统在任何网络环境下都能跑通。

| 数据源 | 说明 | 特点 |
|---|---|---|
| `cninfo` | 巨潮资讯网查询接口 | 权威、结构化 JSON，含 PDF 原文链接 |
| `sina` | 新浪财经资讯页 | 备用，GBK 页面需解析 `div.datelist` |
| `mock` | 本地生成样例 | 完全离线，保留真实类型/时间分布特征 |

## 数据清洗规则

1. **标题**：剥离 HTML 标签与 `<em>` 高亮、压缩空白、剔除长度小于 4 的噪声
2. **日期**：统一转为 `datetime`，剔除非法值与未来日期
3. **去重**：按 `(标题, 发布日期)` 组合去重
4. **分类**：依据标题关键词归入 9 类——财务报告、分红配股、股东大会、治理变动、
   股权变动、关联交易、投资者关系、风险提示、其他公告
5. **派生字段**：年 / 月 / 季度 / 星期 / 标题长度，供大屏多维分析

规则可在 `config.py` 的 `CATEGORY_RULES` 中调整，**顺序敏感**，越靠前优先级越高。

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 可视化大屏页面 |
| GET | `/api/overview` | 总览：总量、分类数、时间跨度、来源分布 |
| GET | `/api/category` | 公告分类分布 |
| GET | `/api/trend` | 月度公告数量趋势 |
| GET | `/api/year` | 年度公告数量 |
| GET | `/api/quarter` | 季度分布 |
| GET | `/api/weekday` | 星期披露分布 |
| GET | `/api/recent?limit=12` | 最新公告 |
| GET | `/api/list?page=1&size=20&category=&keyword=` | 公告分页查询 |
| POST | `/api/refresh` | 触发一次完整采集流水线 |
| GET | `/api/refresh/status` | 查询采集任务状态与日志 |
| GET | `/api/download?format=csv\|xlsx` | 下载数据文件 |

统一响应格式：

```json
{ "code": 0, "msg": "success", "data": [] }
```

## 大屏功能

- **KPI 卡片**：公告总量、分类数、覆盖天数、最新公告日期、数据来源
- **月度趋势**：面积折线图，支持缩放滑块与峰值/谷值标注
- **分类占比**：玫瑰图（Nightingale）
- **年度/季度分布**：渐变柱状图
- **星期热力**：雷达图，观察披露的星期偏好
- **最新公告播报**：可滚动列表，点击直达 PDF 原文
- **公告明细**：支持分类筛选、关键词搜索、分页浏览
- **一键采集**：点击「重新采集」实时查看后端流水线日志，完成后自动刷新大屏

## 更换标的

修改 `config.py` 中的三个字段即可切换到其他上市公司：

```python
STOCK_CODE = "600519"          # 股票代码
STOCK_NAME = "贵州茅台"        # 股票名称
STOCK_KEYWORDS = [...]         # 资讯源筛选关键词
```

## 说明

- 抓取内置请求间隔与失败重试，避免对目标站点造成压力
- 数据库以 `(标题, 发布日期)` 为业务唯一键，重复运行执行 UPSERT 而非重复插入
- 前端 ECharts 使用 CDN，主源不可用时自动回退到备用 CDN
