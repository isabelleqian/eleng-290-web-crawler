# Policy Database 交互完善计划

**目标**　用本地 73 条候选和 1,290 条筛选记录做一个可检查的静态预览。读者可以组合筛选文档、跟踪筛选决定、查看原文证据，并在候选库和筛选归档之间切换。

**实现方式**　沿用现有 Python 预览流程、共享站点导航、Tailwind 样式和原生 JavaScript。在生成阶段连接本地数据，候选库和归档共用渲染与筛选逻辑。预览输出到独立目录，验证后再决定公开发布的数据范围。

## 1. 生成可复现的预览数据

从仓库旁的 `policy-search/data/` 读入以下文件。现有的 `policy-search/scripts/build_policy_site_preview.py` 已有日期回退、原文链接和措施 CSV 解析逻辑，沿用这些转换；目前它只选取 Round 3 模型标为 `INCLUDE` 的记录，并读取旧版措施 CSV，这两处需要更新。

| 输入 | 用途 | 基准校验 |
|---|---|---|
| `policy_candidate_evidence_index_2026-11-17.json` | 候选成员、暂定文档组、发布机构、原文与证据页 | 73 个唯一 ID、71 个暂定组，包含线上 66 个 ID |
| `source_verification_round3.json` | 归档成员、检索批次、采集渠道、Round 3 模型建议 | 1,290 个唯一 ID；模型建议 66 纳入、546 待定、678 排除 |
| `human_document_decisions_overlay_2026-11-17.json` | 更新人工决定和适用范围 | 仅在 `human_validated === true` 时显示为人工已判定 |
| `five_document_measure_trials_revision_2026-11-17.csv` 及对应 manifest | 更新探索性措施与证据行 | 5 份文档、10 个暂定措施实例、11 条证据行 |

- [ ] 通过 `artifact_id` 连接候选索引、Round 3 和人工决定；保留 `pc_<artifact_id>` 与现有 `#doc-pc-<artifact_id>` 链接。把 73 条候选作为 1,290 条归档的子集。
- [ ] 分别保存 Round 3 模型建议、后续候选成员身份、人工决定及其范围。归档中的 Round 3 计数按原快照计算；候选库显示审计后范围；后续决定覆盖同一记录的对应决定字段并保留出处。若文件之间的人工状态不一致，生成核对清单再决定页面展示值。
- [ ] 按已有文档 ID 关联试编码，按措施实例 ID 合并证据行。文档组用于提示可能的同源或版本关联，每条来源记录仍可单独访问。年份携带原文或平台元数据来源；缺失时显示未知。只有能在预览中打开的 PDF 才显示为站内 PDF。
- [ ] 生成供两个视图读取的精简 JSON，明确列出可展示字段。将本地文件路径、原始采集内容和人工讨论留在输入与核对材料中。对照基准校验唯一 ID、候选归档交集、措施计数和本地 PDF 链接。

## 2. 完善候选库与筛选归档

- [ ] 改造 `docs/policy_database.html` 的筛选区。首屏保留搜索、人工判定、措施提取、年份和发布机构；提供 `Has saved PDF` 与 `Has publisher link`；把 Query ID 放进更多筛选。各维度组合生效，结果计数随筛选更新，清空恢复完整候选集。搜索覆盖标题、发布机构、文档 ID、措施 ID 和可展示的筛选说明。
- [ ] 加入 `policy_database_archive.html`。候选页提供 **View Screening Archive (1,290 records)**，归档页提供返回 **Policy Database (73 candidates)**。归档优先展示 Round 3 模型建议、人工判定、候选成员身份、检索批次和采集渠道。标题附近注明筛选快照版本。归档里的低证据记录也可检索，并显示其证据和审核状态。
- [ ] 复用 `news_importer/generate_infographics.py` 中 `generate_database_html` 的组合筛选、带计数选项、结果提示、清空和空结果样式，以及 `parseUrlParams` 和 `revealHash` 的交互。Policy 侧补齐筛选状态写回 URL。两个 Policy 页面共用脚本 `docs/policy_database.js`，按数据字段和页面模式配置各自的选项。News 页面沿用自己的生成逻辑。
- [ ] 沿用 `news_importer/site_navigation.py` 的全站导航。将 Policy 归档加入该模块的同步范围；归档与候选的切换链接放在页面内容区。

## 3. 让概要、图表和证据表格联动

- [ ] 候选页概要显示来源记录数、暂定文档组数和含探索性措施的文档数。筛选控件旁显示当前匹配条数，让读者能区分整个候选库和筛选结果。
- [ ] 加入一个可点选的出版年份柱状图。柱子使用文档记录计数，标明日期来源口径并显示未知年份；点击柱子等同于选择年份筛选。图表和年份控件共享同一个筛选状态。审核进度用带计数的按钮呈现。
- [ ] 表格优先显示文档、发布机构与时间、人工筛选、措施提取和原文。证据详情沿用现有 `appendPolicyFields` 的展开模式，展示候选代码、PDF 页与印刷页、证据摘录和开放问题。试编码地点只出现在详情里。现有 News Topic、Actionability、Governing Level 和 Law Crosswalk 列由这些字段替换。

## 4. 本地验收

在网页仓库运行 `python -X utf8 -m scripts.build_policy_preview`，预览从 `policy-search/outputs/policy-interaction-preview/` 启动静态 HTTP 服务。此目录独立于已有的 News／Policy 预览。先核对生成的 JSON，再用浏览器走一遍以下路径。

- [ ] **初始视图**　候选页 73 条，归档页 1,290 条，各自的计数和标签与数据一致。确认旧候选的直达链接仍可打开。
- [ ] **组合筛选**　用审查状态与年份、机构或 Query ID 交叉筛选，与 JSON 的交集对照。一个多批次命中的记录只在结果中出现一次。分别验证可空字段、零结果与清空。
- [ ] **图表与链接**　点击年份柱，核对同年份下拉选择的结果和计数；复制 URL 并刷新，筛选状态可恢复。测试直达记录与已有筛选不匹配时，页面能定位记录并提示筛选状态的变化。
- [ ] **证据详情**　抽查新增候选、暂定同组来源、人工排除、尚未确认的人工状态、一个多措施文档和一个含多条证据的实例。核对原文链接、页码及措施/证据计数。
- [ ] **浏览体验**　验证桌面及窄屏键盘操作，归档首次打开和组合筛选时表格可正常滚动。若 1,290 条实测造成明显卡顿，再加入分页。运行 `python -X utf8 -m unittest discover -s tests -p test_site_navigation.py`，并抽查 News 候选与归档的切换。

验收交付物是本地预览链接和核对结果。GitHub Pages 发布作为后续一步，待确认哪些筛选说明、证据摘录和本地 PDF 可以公开，再生成发布版本。
