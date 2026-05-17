---
name: supertutu-creator
description: >
  Use this skill to create AI-generated content via the SuperTuTu Open Platform:
  comics (漫画 / 条漫 / 多格分镜), article illustrations (公众号/小红书配图),
  custom images (自定义生图), or just storyboard prompts (分镜提示词，不生图).
  Trigger whenever the user wants to generate any of these — even if they don't
  say "SuperTuTu" explicitly. Also use this skill to list previously created works
  or check the status of an ongoing generation task. This skill handles the full
  async flow: submit, poll until complete, and return the final image URLs.
---

# SuperTuTu Creator Skill

SuperTuTu is an AI creative platform for Chinese content creators. This skill calls
its Open Platform API (`/v1/openapi`) and includes 5 ready-to-run Python scripts.

## 第一步：确认 API Key

在做任何事之前，先确认手上有 API Key（`ak_` 开头）。

**如果用户对话里给了 Key**：直接用，下文「调用脚本」会说明怎么把 Key 传进去。

**如果用户没给 Key**：先回复：
> 使用 SuperTuTu 创作功能需要先获取 API Key。
> 请前往 <https://sso.aizmjx.com/home/apikey> 获取，然后把 Key 发给我，我来帮你生成。

---

## 使用前：收集必要信息

调用任何 API 之前，先确认用户提供了必要信息。**不要假设，直接问。**

### 漫画 — 必须有故事内容
用户说"帮我做个漫画"但没给故事时：
> 好的！请告诉我故事内容，比如："一只懒猫不想上班，看到主人准备猫罐头后立刻跳起来"。
> 字数不限，越详细效果越好。
>
> 可选：几格（默认 4 格，最多 8 格）？风格偏好（治愈/趣味/职场/小林/对比/故事/育儿/条漫…）？

### 文章配图 — 必须有文章正文（≥300 字）和张数
用户说"帮我配图"但没给文章时：
> 请把文章正文发给我（300 字以上效果更好），以及想要几张配图？
> 另外风格偏好：职场/温暖/小红书/知识图/幽默/故事/文艺/可爱？

如果用户给的文章片段不足 300 字：
> 这段文字比较短，能把完整文章发给我吗？配图效果会好很多。

### 自定义生图 — 必须有描述
用户说"生张图"但没有描述时：
> 想生成什么样的图？描述越具体越好，比如场景、风格、色调、构图。
> 例如："夜晚的日式拉面馆，暖橙色灯光，窗外下雨，电影感"。

### 用户已提供足够信息时 — 直接提交，无需再问
用户给了完整故事 / 文章 / 提示词，直接调用 API，不要再追问非必填项。

---

## 调用脚本（Claude 直接执行）

本 skill 自带 8 个脚本，Claude 用 `python scripts/xxx.py` 直接执行，无需手写 HTTP 请求。

| 脚本 | 端点 | 用途 | 结果字段 |
|---|---|---|---|
| `scripts/create_comic.py` | `POST /comic` | 漫画生成 | `imageUrls[]`（每格一张）|
| `scripts/create_article_illustration.py` | `POST /article-illustration` | 文章配图 | `imageUrls[]` |
| `scripts/create_image.py` | `POST /image` | 自定义生图 | `imageUrl`（单张）|
| `scripts/create_prompt.py` | `POST /prompt` | 仅生成分镜提示词 | `shots[].prompt` |
| `scripts/update_shot.py` | `PATCH /shot/{id}/...` | 精修单格字幕/气泡/提示词 | 修改回执 |
| `scripts/render_work.py` | `POST /work/{id}/render` | 用当前最新分镜触发生图 | `imageUrls[]` |
| `scripts/list_works.py` | `GET /works` | 查询作品列表 | `records[]` |
| `scripts/list_styles.py` | `GET /styles` | 查询可用风格 | `[{id, slug, name, ...}]` |

**前置要求**：Python 3.9+ 和 `pip install requests`。

### API Key 传入方式（两种任选）

**方式 A — 命令行参数**（推荐 Claude 在对话里拿到 Key 时使用）：
```bash
python scripts/create_comic.py --api-key ak_xxxxxxxx --content "故事内容"
```

**方式 B — 环境变量**（推荐用户长期使用）：
```bash
export SUPERTUTU_API_KEY=ak_xxxxxxxx
python scripts/create_comic.py --content "故事内容"
```

参数优先于环境变量。两者都没有时脚本会友好退出并提示获取地址。

### 输出约定

所有脚本：
- **stdout**：JSON 结果（适合管道 / 程序消费）
- **stderr**：进度日志（`⏳` `📤` `[1/75] status=...`）
- 退出码：`0` 成功 / 超时（保留部分进度），`1` 业务失败

### 示例输出

漫画：
```json
{
  "workId": "uuid",
  "title": "AI 生成的标题",
  "imageUrls": ["https://cdn.../1.jpg", "https://cdn.../2.jpg"],
  "status": "completed"
}
```

分镜提示词（不生图）：
```json
{
  "workId": "uuid",
  "title": "AI 生成的标题",
  "status": "completed",
  "shots": [
    {"shotIndex": 0, "prompt": "...", "caption": "..."},
    {"shotIndex": 1, "prompt": "...", "caption": "..."}
  ]
}
```

---

## 各脚本参数详解

### `create_comic.py` — 漫画生成

```
--content       故事文案（必填，≤5000 字）
--title         标题（可选，留空 AI 自动生成）
--shots         格数 1-8，默认 4
--ratio         画面比例，默认 1:1
--style-id      风格 ID（用 list_styles.py 查询；不填用默认风格）
--output-mode   输出模式（默认 image_only）：
                  image_only         纯画面，无文字
                  split              画面 + 字幕条（图下贴近原文一行）
                  merged             气泡对话（角色头顶气泡）
                  split_with_bubble  字幕 + 气泡同时出（长漫场景）
--api-key       API Key（可选，优先于环境变量）
```

### `create_article_illustration.py` — 文章配图

```
--content       文章正文（必填，≥300 字，≤5000 字）
--count         生成张数 1-10，默认 4
--style         风格 key（默认 warm_illustration）
                workplace / warm_illustration / rednote / infographic /
                humor / narrative / literary / cute
--style-id      风格 ID（指定后覆盖 --style）
--ratio         默认 3:4（小红书/公众号竖图）
--mode          pure_image（默认）/ text_blend
--character-id  角色模板 ID（可选，跨张保持角色一致）
--ref-image     风格参考图 URL，可重复，最多 3 张
--api-key       API Key
```

**风格 key 映射**（用户中文 → `--style` 值）：

| 用户说 | --style |
|---|---|
| 职场 / 商务 / 工作 | `workplace` |
| 温暖 / 治愈 / 插画 | `warm_illustration` |
| 小红书 / 红薯 | `rednote` |
| 知识 / 信息图 / 图解 | `infographic` |
| 幽默 / 搞笑 | `humor` |
| 故事 / 叙事 | `narrative` |
| 文艺 / 文学 | `literary` |
| 可爱 / Q 版 | `cute` |

### `create_image.py` — 自定义生图

```
--prompt    图像描述（必填，≤2000 字符，英文效果更佳）
--title     标题（可选）
--ratio     画面比例，默认 1:1
--seed      随机种子（可选，复现同画面用）
--api-key   API Key
```

**⚠️ 注意**：结果在 `imageUrl`（单张），不在 `imageUrls[]`。

### `create_prompt.py` — 仅生成提示词

```
--content     故事文案（必填，≤5000 字）
--title       标题（可选）
--shots       格数 1-8，默认 4
--style-id    风格 ID
--api-key     API Key
```

适合：拿提示词去别处生图 / 先看分镜再决定要不要生图。所有 shots 到 `ready`
状态即终止，比走完整生图省时省积分。

### `list_works.py` — 查询作品

```
--page        页码（默认 1）
--page-size   每页 1-50，默认 10
--type        comic / article_illustration / custom_image（可选过滤）
--api-key     API Key
```

### `list_styles.py` — 查询可用风格

```
--category    comic（默认）/ article_illustration
--api-key     API Key
```

### `update_shot.py` — 精修单格分镜

```
--shot-id    分镜 ID（必填；从 work.shots[].shotId 拿）
--caption    新字幕文案（≤500 字，空串=清空）；split / split_with_bubble 模式生效
--dialogue   气泡对话 JSON 数组字符串；空数组 []=清空台词
--prompt     新图像提示词（覆盖 LLM 生成版本，不消耗积分）
--api-key    API Key
```

### `render_work.py` — 续接生图（精修完成后触发图像）

```
--work-id    作品 ID（必填；从 create_prompt.py 输出拿）
--seed       随机种子（可选，多格画风一致用）
--no-wait    只触发不轮询，立即返回
--api-key    API Key
```

把当前 work 下所有 READY/FAILED 分镜批量送进图像生成队列。**不重新走 LLM、不丢精修**。
内部走标准生图链路（积分预扣 + 熔断 / 容量校验 + 新队列入队）。默认轮询到 completed/failed/timeout，
加 `--no-wait` 时只触发不等。

至少传 `--caption` / `--dialogue` / `--prompt` 中的一个；可同时传多个。
**任一字段失败不影响其他字段** —— 脚本是"逐字段独立提交"，最后输出 `updates` 数组告诉你哪些字段成功了。

dialogue JSON 结构（每条最多 200 字，最多 20 条）：
```json
[
  {
    "role":      "猫咪",
    "text":      "我饿了！",
    "type":      "speech",
    "direction": "右"
  }
]
```
- `role`（选填）：说话人；独白 / 旁白可省略
- `text`（必填）：台词文本
- `type`（选填）：`speech`（默认，圆形气泡）/ `caption`（旁白矩形框）
- `direction`（选填）：`左` / `右` / `上` / `下` —— 气泡尾巴指向

---

## 分步精修流程（漫画专用）

这是漫画场景的高级玩法。如果用户说"先看看分镜文案对不对再决定要不要生图"、
"我想改第 3 格的台词"、"这格的字幕换一句更点睛的"，**优先走这条流程**而不是直接调 `create_comic.py`：

```
1) 生成提示词（不生图，仅扣 1 积分提示词费）
   python scripts/create_prompt.py --content "故事..." --shots 4
   ↓ 拿到 workId + shots[] = [{shotId, prompt, caption, dialogue}, ...]

2) 把分镜内容呈现给用户 review
   - 给用户看每格的 caption（字幕）+ dialogue（气泡）+ prompt（图像提示词概要）
   - 询问"第 N 格 X 字段要不要改？"

3) 用户提了修改意见，调 update_shot.py 落库（不消耗积分）
   python scripts/update_shot.py --shot-id 8521 \
       --caption "新字幕" \
       --dialogue '[{"role":"猫","text":"喵！","direction":"右"}]'
   ↓ 仅这一格被改，其他格不受影响

4) 全部满意后调 render_work.py 用精修后的分镜走生图（扣 shotCount × 2 积分）
   python scripts/render_work.py --work-id <workId>
   ↓ 自动轮询到 completed/failed/timeout，输出 imageUrls[]
```

**关键**：第 4 步用 `render_work.py` **不会重新走 LLM**——它读 work 当前最新的 `shots[].finalPrompt`
（已含你的精修）直接派发图像。整个流程精修内容零丢失，全程在脚本里完成，无需前端介入。

**积分账单**：1 积分（提示词）+ N×2 积分（生图）= 漫画 4 格 9 积分；跟直接调 `create_comic.py` 一样，
精修是免费动作。

---

## 风格 ID 查询

漫画 / 配图（`--style-id`）传的是 `workspace_types.id`（自增数字 ID）。
**用户说"治愈风"时，先调 `list_styles.py` 拿列表，按 `slug` 或 `name` 匹配**，再用对应 `id` 调创作脚本：

```bash
# Step 1：拿风格列表
python scripts/list_styles.py --category comic
# [{"id":12,"slug":"healing","name":"治愈漫画风",...}, ...]

# Step 2：用 id 创作
python scripts/create_comic.py --style-id 12 --content "..."
```

漫画当前已上架的风格（slug 一栏可作字符串别名匹配）：

| slug | 中文名 | 适用场景 |
|---|---|---|
| `healing` | 治愈漫画风 | 温柔系，情感故事 |
| `funny` | 趣味漫画风 | 反差金句，搞笑段子 |
| `workplace` | 职场漫画风 | 职场故事，编辑卡通 |
| `romance` | 恋爱漫画风 | 少女漫，温柔氛围 |
| `contrast` | 对比漫画风 | 二格对比，前后反差 |
| `story` | 故事漫画风 | 多格叙事，电影感 |
| `parenting` | 育儿漫画风 | 亲子，温暖治愈 |
| `webtoon` | 条漫风 | 竖版长漫 |
| `sketchy` | 手绘 Sketchy | 手绘墨水 + 水彩 |

> 上表会随后端上下架变化，**以 `list_styles.py` 实际返回为准**。

---

## 配置（Configuration）

```
BASE_URL = https://tutu.aizmjx.com/api/v1/openapi
API_KEY  = 从 https://sso.aizmjx.com/home/apikey 获取
```

所有请求都需要：
```
X-API-KEY: <API_KEY>
Content-Type: application/json
```

所有响应都用统一信封：
```json
{ "code": 200, "message": "...", "data": { ... } }
```

`code` 不是 200 表示失败 —— 脚本会把 `message` 透传给用户。

---

## 轮询行为

所有创作端点都是异步的，提交后立即返回 `workId`，需要轮询直到完成。

脚本内部已封装好轮询逻辑（自适应间隔 + 部分进度兜底），Claude 不需要手动循环：

- **自适应间隔**：前 3 次 4s（赶快任务），之后 6s（多数任务 30s+，省请求）
- **轮询上限**：漫画 / 自定义生图 / 提示词 75 次（≈7.5 分钟），文章配图 150 次（≈15 分钟）
- **超时不丢数据**：超时时返回已完成的部分 shots，`status` 标记为 `"timeout"`
- **连续 3 次查询异常自动停**：避免卡死，返回最后一次拿到的状态

---

## 错误处理

| 现象 | 含义 | 处理 |
|---|---|---|
| `❌ 提交失败：xxx` | 业务码非 200，`message` 透传 | 把消息原样告诉用户 |
| `status: failed` | 后端确认任务失败 | 透传 `errorMessage` 给用户，提示重试 |
| `status: timeout` | 轮询超时 | 已完成的 shots 仍可用，建议用户去前端 `gallery` 看 |
| HTTP 401 | API Key 无效 / 过期 | 让用户重新获取 |
| `当前已有 N 个作品` | 并发上限（3 个）| 等待已有任务完成 |
| 配图 `articleContent < 300` | 文章太短 | 让用户补全 |

任务失败时后端会返回 `errorMessage`（已脱敏，剥除内部模型名 / 渠道域名），脚本自动透传给用户。
典型值：「派发未完成，请重新生成」/「图像服务超时，请重新生成」/「未知失败原因，请重新生成」。

---

## Aspect Ratios（画面比例）

`1:1` 正方 · `3:4` 竖图（小红书 / 公众号）· `4:3` 横图 · `16:9` 宽屏 · `9:16` 竖屏长漫

---

## 用户安装指引

### 方法一：`claude skills add`（推荐）

```bash
claude skills add https://github.com/aizmjx/tutu-skill
```

### 方法二：克隆到本地

```bash
git clone https://github.com/aizmjx/tutu-skill ~/.claude/skills/supertutu-creator
claude skills add ~/.claude/skills/supertutu-creator
```

### 配置 API Key

**方式 A — 环境变量（推荐长期使用）**：

在 `~/.bashrc` 或 `~/.zshrc` 里加：
```bash
export SUPERTUTU_API_KEY=ak_你的key
```

**方式 B — 对话时告诉 Claude**：

直接说：`我的 SuperTuTu API Key 是 ak_xxxxxx`，Claude 会在调用时通过 `--api-key`
参数传入（本次会话有效，不会持久化）。

### 获取 API Key

前往 <https://sso.aizmjx.com/home/apikey> 登录后即可创建。
