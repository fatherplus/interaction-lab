# Surface brief — index.html（光学实验台入口）

scope: 索引页重设计（replacement world）+ 六集共享顶栏。mode: Experience。
audience: 设计/前端学习者，桌面浏览器。job: 把玩六条交互思想、进入对应标本。
proof: 六个可操作迷你标本 + 各集真实页面 + 原片抽帧参数。constraints: 单文件无外部依赖、轻量、无障碍。

## Direction contract

THESIS: 索引本身就是一台「光学实验台」——同一束光、同一套深度语言下的六个可操作标本；它拒绝「六张互不相干的渐变缩略图 + 死卡片」的拼盘式目录。协调来自统一的框架（光/材质/语法），而非把六个标本磨成一样。

OWN-WORLD: 深石墨底（#0a0c0f，非纯黑）+ 左上暖白主光 + 单一琥珀指示灯（#f0a832，小面积点亮，无泛光）+ 冷钢辅助。凸面承「被看见」、凹 wells 承「动作」（EP27）。玻璃标本背后铺硬边色块/网格（EP30）。展示字 Bricolage Grotesque（内联自托管）管品牌/数字/英文；中文系统 CJK；mono 仅用于真实测量 readout。无渐变字、无 eyebrow、无霓虹泛光。

STORY: 访客一眼看到「六种经验共享一套语法」，悬停任一标本即点亮它、其余让位退场（EP31），在卡片里直接上手把玩该集思想（EP26–30），再点「进入」到完整标本。理解→把玩→进入。

FIRST VIEWPORT: 左对齐 masthead（H1「六种界面经验，一套共同语法。」weight 800，无 eyebrow）+ 一段 lead + mono 来源 readout；紧接一条 ruled「共同语法」legend（六条，非卡片）；桌面首屏即见 3×2 标本台，每卡凹 well 内是活的迷你标本。主操作=每卡「进入 →」与可玩标本。

FORM: 选定「光学实验台标本目录」（ordered list 第 1 位；备选：编辑式长文目录、纯缩略图画廊）。seed: none (pinned) — 用户明确选定「可操作迷你标本 + 深色光学实验台 + 索引+统一顶栏」。

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## 签名交互 / 运动语法
- 签名：整台 focus-yield——悬停/聚焦一个标本，它抬起点亮，左右邻居按方向让位 + 变暗（EP31 位移语法），由 JS 按相对位置设 transform。
- 缓动族：入场/让位 cubic-bezier(.16,1,.3,1)；吸附 cubic-bezier(.22,.61,.36,1)（EP30）；按压 scale .96（EP28）。
- transform-only 跟手；backdrop-filter 仅限玻璃标本与顶栏；reduced-motion 关闭位移/动画但保留状态。

## 未决
- 无（方向已由用户三问确认）。