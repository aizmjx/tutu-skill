# SuperTuTu Open Platform API Reference

完整的对外 API 参考文档。SKILL.md 偏 Claude 使用视角；本文档偏「我自己写代码调用」视角，
列每个端点的完整签名、参数、响应、错误。

## 鉴权

所有接口仅接受 API Key 认证。在 HTTP Header 携带：

```
X-API-KEY: ak_xxxxxxxxxxxx
Content-Type: application/json
```

API Key 在 <https://sso.aizmjx.com/home/apikey> 获取。

## Base URL

```
https://tutu.aizmjx.com/api/v1/openapi
```

本地联调时（前端 dev + 后端 jar 跑起来）替换为：

```
http://localhost:10001/api/v1/openapi
```

## 响应信封

所有响应都用同一份信封结构：

```json
{
  "code":    200,
  "message": "成功",
  "data":    { ... }
}
```

- `code == 200` 表示业务成功，`data` 字段为实际载荷
- 其他 code 表示失败，`message` / `errorMessage` 透传给用户

## HTTP 状态码 + 业务 code

| HTTP | 业务 code | 含义 |
|---|---|---|
| 200 | 200 | 成功 |
| 200 | 非 200 | 业务错误（看 `message`） |
| 401 | 401 | API Key 缺失 / 无效 / 过期 |
| 400 | 40001 | 请求体校验失败（@Valid / @Pattern / @Size） |
| 404 | 40403 | 资源 / 路由不存在 |
| 500 | 50000+ | 服务端错误（已脱敏） |

---

## 端点目录

| 分类 | 端点 | 用途 |
|---|---|---|
| 创作 | `POST /comic` | 漫画生成（自动 LLM + 图像，全程异步） |
| 创作 | `POST /article-illustration` | 文章配图（≥300 字文章 → 4-10 张图） |
| 创作 | `POST /image` | 自定义生图（无 LLM，prompt → 图最快） |
| 创作 | `POST /prompt` | 仅生成分镜提示词，不生图（精修流程入口） |
| 精修 | `PATCH /shot/{shotId}/caption` | 修改单格字幕（split / split_with_bubble 生效） |
| 精修 | `PATCH /shot/{shotId}/dialogue` | 修改单格气泡台词（merged / split_with_bubble 生效） |
| 精修 | `PUT /shot/{shotId}/prompt` | 修改单格图像提示词（不消耗积分） |
| 精修 | `POST /work/{workId}/render` | 续接生图（用当前最新分镜状态触发渲染） |
| 查询 | `GET /work/{workId}` | 查询单个作品状态（轮询用） |
| 查询 | `GET /works` | 分页查询作品列表 |
| 查询 | `GET /styles` | 查询可用风格列表（按大类） |

---

## 创作接口

### `POST /comic` — 漫画生成

LLM 自动生成各格分镜提示词，完成后**自动续接图像生成**，全程一次调用搞定。

**请求体**：
```json
{
  "content":     "故事文案（必填，≤5000 字）",
  "title":       "标题（可选，留空 AI 自动生成）",
  "shotCount":   4,
  "aspectRatio": "1:1",
  "styleTypeId": 12,
  "outputMode":  "image_only"
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `content` | string | ✓ | — | 故事文案，1-5000 字 |
| `title` | string | | "" | 留空时 LLM 自动生成 |
| `shotCount` | int | | 4 | 分镜格数 1-8 |
| `aspectRatio` | string | | `1:1` | `1:1` / `3:4` / `4:3` / `16:9` / `9:16` |
| `styleTypeId` | long | | null | 风格 ID（用 `GET /styles` 查询） |
| `outputMode` | string | | `image_only` | 见下表 |

**outputMode 可选值**：

| 值 | 效果 |
|---|---|
| `image_only` | 纯画面，不带任何文字 / 气泡 |
| `split` | 画面 + 字幕条（图下贴近原文一行） |
| `merged` | 气泡对话（角色头顶气泡） |
| `split_with_bubble` | 字幕 + 气泡同时（长漫场景） |

**响应 data**：`SkillWorkStatusResponse`（shots 字段此时为 null，需轮询 `GET /work/{workId}` 拿结果）

**积分**：1（提示词）+ shotCount × 2（生图） = 4 格漫画 9 积分

---

### `POST /article-illustration` — 文章配图

根据文章内容，AI 自动选取关键段落生成 4-10 张配图。

**请求体**：
```json
{
  "articleContent":      "文章正文（必填，≥300 字，≤5000 字）",
  "imageCount":          4,
  "illustrationStyleId": null,
  "illustrationStyle":   "warm_illustration",
  "aspectRatio":         "3:4",
  "generationMode":      "pure_image",
  "characterId":         null,
  "referenceImageUrls":  []
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `articleContent` | string | ✓ | — | 文章正文，**≥300 字**，≤5000 字 |
| `imageCount` | int | ✓ | — | 配图数量 1-10 |
| `illustrationStyleId` | long | △ | — | 二选一：风格 ID |
| `illustrationStyle` | string | △ | — | 二选一：风格 key（见下表） |
| `aspectRatio` | string | | `3:4` | 推荐 `3:4` 小红书 / 公众号竖图 |
| `generationMode` | string | | `pure_image` | `pure_image` / `text_blend` |
| `characterId` | long | | null | 角色模板 ID（跨张保持角色一致） |
| `referenceImageUrls` | string[] | | [] | 风格参考图，最多 3 张 |

`illustrationStyleId` 和 `illustrationStyle` 必须二选一。

**illustrationStyle 可选值**：

| key | 中文 |
|---|---|
| `workplace` | 职场 / 商务 |
| `warm_illustration` | 温暖 / 治愈 |
| `rednote` | 小红书 |
| `infographic` | 知识图 / 信息图 |
| `humor` | 幽默 / 搞笑 |
| `narrative` | 故事 / 叙事 |
| `literary` | 文艺 / 文学 |
| `cute` | 可爱 / Q 版 |

**响应 data**：`SkillWorkStatusResponse`（轮询拿结果）

**积分**：1（提示词）+ imageCount × 2（生图）

---

### `POST /image` — 自定义生图

直接 prompt → 图，**无 LLM 阶段，速度最快**。

**请求体**：
```json
{
  "prompt":      "图像描述（必填，≤2000 字符，英文效果更佳）",
  "title":       "标题（可选）",
  "aspectRatio": "1:1",
  "seed":        "12345"
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `prompt` | string | ✓ | — | ≤2000 字符。底层 Seedream 对英文 prompt 敏感 |
| `title` | string | | prompt 前 20 字 | 留空时取 prompt 前缀 |
| `aspectRatio` | string | | `1:1` | 见 aspect ratio 表 |
| `seed` | string | | null | 固定随机种子（复现同画面） |

**响应 data**：`SkillWorkStatusResponse`，**结果在 `coverImageUrl`，`shots[]` 为空**。

**积分**：2

---

### `POST /prompt` — 仅生成分镜提示词

跟 `/comic` 同样的 LLM 阶段，**但不续接图像生成**。适合分步精修流程的入口。

**请求体**：
```json
{
  "content":     "故事文案（必填，≤5000 字）",
  "title":       "标题（可选）",
  "shotCount":   4,
  "styleTypeId": null,
  "outputMode":  "split"
}
```

字段大致同 `/comic`，**不接受** `aspectRatio`（图像阶段才用）。

⚠️ **`outputMode` 在 prompt 阶段就生效** —— 决定 LLM 是否生成 caption / dialogue：

| outputMode | LLM 行为 |
|---|---|
| `image_only`（默认）| 不生成字幕，不生成气泡。**分步精修阶段没东西可让用户 review** |
| `split` | 生成 caption（画面+字幕）|
| `merged` | 生成 dialogue（气泡对话）|
| `split_with_bubble` | 同时生成 caption + dialogue |

分步精修场景务必按所选风格的 `defaultLayout` 推 outputMode：caption → `split`，bubble → `merged`。

**响应 data**：`SkillWorkStatusResponse`。
轮询到 `shots[].status === "ready"` 表示提示词已生成，`shots[].prompt` / `caption` / `dialogue` 即可用。

**积分**：1

---

## 分镜精修接口

精修接口允许在生图前修改单个分镜的内容。改完后调 `POST /work/{workId}/render` 跑生图。

所有精修接口都做越权校验（`shot.userId == 当前 API Key 用户`），不存在或不属于当前用户都返回
`NOT_EXIST` 不暴露存在性。**精修动作本身不消耗积分**。

### `PATCH /shot/{shotId}/caption` — 修改字幕

**路径参数**：`shotId` — 分镜 ID，从 `work.shots[].shotId` 拿。

**请求体**：
```json
{ "caption": "新字幕文案（≤500 字，空串=清空）" }
```

**响应 data**（`ShotCaptionVO`）：
```json
{
  "id":        12345,
  "shotIndex": 0,
  "caption":   "新字幕文案",
  "updatedAt": "2026-05-17T10:23:00"
}
```

**生效模式**：`outputMode = split` 或 `split_with_bubble`。其他模式下 caption 不会被注入图像 prompt。

---

### `PATCH /shot/{shotId}/dialogue` — 修改气泡对话

**路径参数**：`shotId`

**请求体**：
```json
{
  "dialogue": [
    {
      "role":      "猫咪",
      "text":      "我饿了！",
      "type":      "speech",
      "direction": "右"
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `role` | 选填 | 说话人；独白 / 旁白可省略 |
| `text` | ✓ | 台词文本，≤200 字 |
| `type` | 选填 | `speech`（默认气泡）/ `caption`（旁白矩形框） |
| `direction` | 选填 | `左` / `右` / `上` / `下`（气泡尾巴方向） |

- 空数组 `[]` 或 `null` 视为清空所有台词
- 最多 20 条

**响应 data**（`ShotDialogueVO`）：
```json
{
  "id":        12345,
  "shotIndex": 0,
  "dialogue": [ {"role":"猫咪","text":"我饿了！","type":"speech","direction":"右"} ],
  "updatedAt": "2026-05-17T10:23:00"
}
```

**生效模式**：`outputMode = merged` 或 `split_with_bubble`。

---

### `PUT /shot/{shotId}/prompt` — 修改图像提示词

**路径参数**：`shotId`

**请求体**：
```json
{ "finalPrompt": "覆盖 LLM 提示词的新文本" }
```

**响应 data**：`true`（boolean）。

**生效**：下一次单格重生或 `POST /work/{workId}/render` 时用新 prompt。

---

### `POST /work/{workId}/render` — 续接生图

把当前 work 下所有 `READY` / `FAILED` 状态的分镜批量送进图像生成队列。
**不重新走 LLM，不丢精修内容**。

**路径参数**：`workId`

**查询参数**：

| 字段 | 必填 | 说明 |
|---|---|---|
| `seed` | 选填 | 固定随机种子，多格保持画风一致 |

**响应 data**：`SkillWorkStatusResponse`（触发后的最新 work + shots 状态）。需要继续轮询
`GET /work/{workId}` 直到 `status=completed`。

**常见错误**：
- `没有可生成的分镜` — work 下所有 shot 不在 READY/FAILED 状态（可能正在生成或已完成）
- `服务繁忙` — 图像服务熔断器打开或容量已满
- `积分不足` — 检查余额，最少 `shotCount × 2` 积分

**积分**：READY/FAILED 分镜数 × 2

---

## 查询接口

### `GET /work/{workId}` — 查询单个作品状态

**路径参数**：`workId`

**响应 data**（`SkillWorkStatusResponse`）：
```json
{
  "workId":       "uuid",
  "status":       "generating",
  "coverImageUrl": null,
  "errorMessage": null,
  "shots": [
    {
      "shotId":       12345,
      "shotIndex":    0,
      "status":       "completed",
      "imageUrl":     "https://...",
      "prompt":       "a cat in kitchen, anime style...",
      "caption":      "今天我要做饭！",
      "dialogue": [
        {"role":"猫","text":"喵","type":"speech","direction":"右"}
      ],
      "errorMessage": null
    }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `status` | `generating` / `completed` / `failed` |
| `coverImageUrl` | `custom_image` 类型的结果在这里；`comic` / `article_illustration` 此字段为 null |
| `errorMessage` | 仅 `status=failed` 时有值，已脱敏 |
| `shots[].status` | `generating` / `ready` / `completed` / `failed` |
| `shots[].imageUrl` | `completed` 后才有值 |
| `shots[].prompt` | `ready` 后即有值（LLM 已写完图像 prompt） |
| `shots[].caption` | LLM 生成的字幕（可用精修接口覆盖） |
| `shots[].dialogue` | LLM 生成的气泡台词数组（可用精修接口覆盖） |
| `shots[].errorMessage` | 单格失败原因，仅 `status=failed` 时有值 |

**轮询建议**：每 4-6 秒一次，`completed` / `failed` 时停止。漫画/自定义生图通常 30s-2 分钟，
文章配图通常 1-5 分钟。

---

### `GET /works` — 分页查询作品列表

**查询参数**：

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `page` | | 1 | 页码，从 1 开始 |
| `pageSize` | | 10 | 每页 1-50 |
| `type` | | (全部) | `comic` / `article_illustration` / `custom_image` |

**响应 data**（`SkillWorkListResponse`）：
```json
{
  "total":    100,
  "current":  1,
  "pageSize": 10,
  "records": [
    {
      "workId":        "uuid",
      "title":         "猫咪厨神",
      "type":          "comic",
      "status":        "completed",
      "coverImageUrl": "https://...",
      "createdAt":     "2026-05-01T10:00:00"
    }
  ]
}
```

---

### `GET /styles` — 查询可用风格列表

用于"风格发现"——拿到列表后客户端可让用户挑、或按 `slug` / `name` 做 fuzzy 匹配挑出 ID。

**查询参数**：

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `category` | | `comic` | `comic` / `article_illustration` |

**响应 data**：`List<SkillStyleVO>`，按 `sort_order` 升序，只返回已上架且当前用户可见的风格。

```json
[
  {
    "id":                     12,
    "slug":                   "healing",
    "name":                   "治愈漫画风",
    "emoji":                  "🌿",
    "styleLabel":             "温柔系",
    "tagline":                "...",
    "recommendedAspectRatio": "1:1",
    "defaultLayout":          "caption"
  }
]
```

| 字段 | 说明 |
|---|---|
| `id` | 风格 ID，创作接口传 `styleTypeId` 用 |
| `slug` | 字符串别名（同 category 内唯一），客户端可做 fuzzy 匹配 |
| `name` | 中文风格名 |
| `emoji` | 风格 emoji（前端 chip 用） |
| `styleLabel` | 风格副标（如「反差金句型」） |
| `tagline` | 一句话描述 |
| `recommendedAspectRatio` | 推荐画面比例 |
| `defaultLayout` | 默认输出形态，映射到创作接口的 `outputMode`：`caption` → `split` / `bubble` → `merged` / `none` → `image_only` / `null` → 未设置（客户端自决） |

---

## 数据结构

### `SkillWorkStatusResponse`

工作状态响应。所有创作接口的初始响应 + `GET /work/{workId}` 都返回这个结构。

```typescript
{
  workId:        string;
  status:        "generating" | "completed" | "failed";
  coverImageUrl: string | null;     // 仅 custom_image 有
  errorMessage:  string | null;     // 仅 status=failed 时有值，已脱敏
  shots:         ShotResult[] | null;
}
```

### `ShotResult`

```typescript
{
  shotId:       number;
  shotIndex:    number;
  status:       "generating" | "ready" | "completed" | "failed";
  imageUrl:     string | null;
  prompt:       string | null;     // LLM 生成的图像 prompt
  caption:      string | null;     // 字幕文案
  dialogue:     DialogueItem[];    // 气泡台词数组
  errorMessage: string | null;     // 仅 status=failed 时有值，已脱敏
}
```

### `DialogueItem`

```typescript
{
  role:      string | null;        // 说话人
  text:      string;               // 台词文本，≤200 字
  type:      "speech" | "caption"; // speech=圆形气泡（默认）/ caption=旁白矩形框
  direction: "左" | "右" | "上" | "下" | null;  // 气泡尾巴方向
}
```

### `SkillStyleVO` / `SkillWorkListResponse`

见上文对应章节。

---

## 异步轮询模型

所有创作接口（`/comic` / `/article-illustration` / `/image` / `/prompt`）+ `/work/{workId}/render`
都是异步的：返回 `workId` 后任务进入队列，客户端需要轮询 `GET /work/{workId}` 直到完成。

```
1. POST /comic                       → workId
2. loop (interval 4-6s):
     GET /work/{workId}
     if status == "completed": done
     if status == "failed":    handle + show errorMessage
     else:                     continue
```

参考 `scripts/_client.py` 的 `poll_until_done()` 实现：
- 前 3 次 4s 间隔（赶快任务）
- 之后 6s 退避（多数任务 30s+，省一半请求）
- 连续 3 次查询异常自动停止
- 超时时**返回当前部分进度**而不是丢数据

---

## 并发与积分

### 并发限制

每个用户最多同时 **3 个 work 在生成中**。超过返回：

```json
{ "code": 50001, "message": "当前已有 3 个作品在生成中，请等待完成后再提交（上限 3 个）" }
```

### 积分扣费规则

| 动作 | 积分 |
|---|---|
| LLM 提示词生成（`/comic` / `/article-illustration` / `/prompt`） | **1** |
| 每张图像生成 | **2** |
| 自定义生图（`/image`） | **2** |
| 修改 caption / dialogue / prompt | **0**（免费） |

漫画 4 格典型：1（LLM）+ 4 × 2（生图）= **9 积分**。

### 创作门槛

发起新作品（含 `/comic`、`/article-illustration`、`/image`、`/prompt`）需要账户余额
≥ **10 积分**。不足时返回：

```json
{ "code": 50003, "message": "积分不足，至少需要 10 积分才能创作。当前剩余 X 积分，请先充值。" }
```

`/work/{workId}/render` 续接生图**不受此门槛限制**（已是存量 work 的二次操作）。

---

## 失败 / 错误响应示例

```json
// API Key 缺失 / 无效
{ "code": 401, "message": "未授权", "errorMessage": "缺少必要的认证参数" }

// 校验失败
{ "code": 40001, "message": "请求参数错误", "errorMessage": "故事内容不能为空" }

// 资源不存在 / 越权
{ "code": 40404, "message": "资源不存在", "errorMessage": "作品不存在或无权访问" }

// 业务错误
{ "code": 50000, "message": "操作失败", "errorMessage": "图像服务暂时不可用，请稍后重试" }
```

错误消息已经过 `ErrorMessageSanitizer.stripBrandNames` 脱敏，剥除底层模型名 / 渠道域名等内部细节，
可直接透传给用户展示。

---

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-05-17 | `POST /prompt` 接受 `outputMode` 参数（分步精修场景必备，否则 LLM 不生成 caption/dialogue） |
| 2026-05-17 | `GET /styles` 响应加 `defaultLayout` 字段（`caption` / `bubble` / `none` / null）|
| 2026-05-17 | 新增 `POST /work/{workId}/render` 续接生图端点 |
| 2026-05-17 | 新增 `PATCH /shot/{shotId}/caption` / `PATCH /shot/{shotId}/dialogue` / `PUT /shot/{shotId}/prompt` 分镜精修端点 |
| 2026-05-17 | `GET /work/{workId}` 响应加 `shotId` / `dialogue` / `errorMessage` 字段 |
| 2026-05-17 | 新增 `GET /styles` 风格发现端点 |
| 2026-05-17 | `POST /comic` 接受 `outputMode` 参数 |
| 2026-05-03 | 初版 |
