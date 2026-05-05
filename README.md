# MyJetCard

基于 Django 的自托管航空摄影作品集。每位用户拥有独立的照片库，包含足迹地图、数据统计和照片审核流程。

[欢迎来看看](https://myjetcard.top/jxclbx/)

https://myjetcard.top/jxclbx/

---

## 功能介绍

### 公开页面

**落地页** (`/`)
- 动态云朵与飞机动画场景
- 各用户作品集的入口

**个人主页** (`/<username>/`)
- 汇总数据：照片总数、航司数、机场数、独立注册号数
- 基于 Leaflet + 高德地图的交互式足迹地图，标记所有到访机场，悬停显示机场全名
- 置顶照片、精选照片、随机照片展示区
- 年度柱状图与航司占比饼图（ECharts）

**画廊** (`/<username>/gallery/`)
- 无限滚动网格，使用小缩略图（`image_sm`）加速加载
- 筛选条件：航司、机场、机型、注册号、日期、年份/月份
- 标签筛选：彩绘、货机、公务机、直升机、罕见机型
- 全局关键词搜索（`q=`），同时匹配注册号、机型、细分型号、航司、机场、备注，注册号搜索忽略横杠（如 `B6789` 可匹配 `B-6789`）
- 独立注册号模式：每个注册号只显示最新一张
- 同时筛选航司与机型时，自动展开该组合下的注册号面板

**照片详情页** (`/<username>/photo/?id=`)
- 默认加载高清大图（`image_lg`），点击可查看无损原图
- 机场字段显示完整名称（由内置 IATA → 机场名映射解析）
- 各元数据字段可点击，直接跳转到对应筛选结果

**统计页** (`/<username>/stats/`)
- 年份切换，含月度柱状图、日历热力图、年度对比
- 航司、机型、机场各自的排行榜（前50名）及占比饼图
- 筛选面板：点击排行条目可直接跳转到对应的画廊筛选视图；同时选中航司+机型时，自动展开注册号面板

---

### 上传与审核流程

**提交照片** (`/manage/photos/add/`)
- 任意登录用户均可提交，照片进入 `PendingPhoto` 队列，状态为 `pending`
- 表单约束：最大 3 MB、仅支持 JPEG/PNG/WebP、最长边不超过 2560 px
- 提交后立即生成小缩略图（`image_sm`），用于审核队列预览

**审核队列** (`/manage/review/`) — 仅限 staff/superuser
- 展示所有待审照片及缩略图
- **通过**：将原图和元数据复制到正式 `Photo` 记录；`Photo.save()` 自动生成 `image_sm` 和 `image_lg`；`PendingPhoto.image` 字段引用清空（物理文件保留，由 `clean_orphan_media` 统一清理）
- **拒绝**：记录拒绝原因，`PendingPhoto.image` 引用清空，缩略图保留供历史查看
- 物理文件从不在审核流程中删除，统一由 `clean_orphan_media --delete` 管理命令处理
- 审核时可修改提交信息再通过
- 通过后的条目通过 `OneToOneField` 与生成的 `Photo` 关联；若该 `Photo` 后续被删除，字段置空而非级联删除

**直接发布** (`/manage/photos/add-direct/`) — 仅限 staff/superuser
- 跳过审核队列，直接创建正式 `Photo` 记录

---

### 内容管理

**我的照片** (`/manage/photos/`)
- 带缩略图的分页列表，支持搜索和筛选
- 按条目编辑元数据或删除
- 图片替换：staff 可上传替换图，缩略图自动重新生成

**我的提交** (`/manage/photos/pending/`)
- 展示用户自己的提交历史及状态标签（待审/已通过/已拒绝）
- 已拒绝条目隐藏编辑区；已通过条目显示跳转到对应正式照片的链接（若照片已删除则提示）

**站点配置** (`/manage/site/`)
- 头像（自动裁剪为正方形，压缩至 128×128 px JPEG）
- 横幅（最长边缩放至 1920 px，JPEG）
- 地点与个人简介文字
- 置顶照片 ID 列表（JSON 数组）
- 性能面板开关

**装备管理** — 相机机身和镜头按站点存储，可在照片表单中选择

---

### API

所有接口位于 `/api/<username>/`，返回 JSON。每个 API 响应头中包含 `X-Process-Time`（毫秒），记录后端处理耗时。

| 接口 | 说明 |
|------|------|
| `GET /api/<username>/home` | 汇总数据、机场列表、置顶/精选/随机照片、图表数据 |
| `GET /api/<username>/photos` | 分页照片列表，支持完整筛选/搜索/排序 |
| `GET /api/<username>/photos/<id>/` | 单张照片详情 |
| `GET /api/<username>/stats/overview/` | 年度统计、排行榜、筛选下拉选项 |
| `GET /api/<username>/stats/year/?year=` | 指定年份的月度统计与日历热力图数据 |
| `GET /api/<username>/site/` | 站点配置信息 |
| `GET /api/pending/` | 待审队列（普通用户只看自己，staff 看全部） |
| `POST /api/pending/<pk>/approve/` | 审核通过（仅 staff） |
| `POST /api/pending/<pk>/reject/` | 审核拒绝，可附拒绝原因（仅 staff） |

---

## 数据模型

```
User（Django 内置）
 └── SiteProfile          一对一；存储头像、横幅、置顶 ID、装备列表
      └── GearItem         相机或镜头，每个档案可有多条

Photo                      正式照片记录
 ├── image                 原始上传文件
 ├── image_sm              300 px 缩略图，含锐化（保存时自动生成）
 ├── image_lg              1500 px 预览图，含锐化（保存时自动生成）
 ├── camera → GearItem
 ├── lens   → GearItem
 └── source_pending → PendingPhoto（可空 OneToOne，反向关联）

PendingPhoto               待审照片
 ├── image                 原始上传文件（审核后引用清空）
 ├── image_sm              300 px 缩略图（保留供历史展示）
 ├── status                pending | approved | rejected
 ├── review_note           拒绝原因
 ├── camera → GearItem
 ├── lens   → GearItem
 └── approved_photo → Photo（可空 OneToOne）

AircraftSubModel           机型/细分型号计数缓存表
 ├── model
 ├── sub_model
 └── usage_count           由 Photo.save() 和 Photo.delete() 自动增减
```

`AircraftSubModel` 由系统自动维护：`Photo.save()` 在创建、修改、删除时调用 `sync_variant_pair()` 同步计数。如需全量重建，执行 `python manage.py sync_aircraft_submodels`。

---

## 文件结构

```
planehub/
├── photos/                     主应用
│   ├── models.py               Photo、PendingPhoto、AircraftSubModel、SiteProfile、GearItem
│   ├── services.py             业务逻辑：机型计数、审核通过/拒绝、机场数据加载
│   ├── forms.py                上传/编辑表单（文件校验、IATA/ICAO 标准化）
│   ├── admin.py                所有模型的 Django Admin 注册
│   ├── urls.py                 管理页面与 API 的全部路由
│   ├── views/
│   │   ├── view_photos.py      照片 CRUD 视图
│   │   ├── view_pending.py     待审照片视图
│   │   └── view_site_profile.py  站点配置与装备视图
│   ├── api/
│   │   ├── api_photos.py       首页 + 照片列表/详情接口
│   │   ├── api_stats.py        统计接口
│   │   ├── api_review.py       审核队列接口
│   │   └── api_site.py         站点配置接口
│   └── management/commands/
│       ├── sync_aircraft_submodels.py  从 Photo 表全量重建 AircraftSubModel
│       ├── clean_orphan_media.py       查找/删除数据库中无引用的媒体文件
│       └── delete_entry.py             通过命令行按 ID 删除 Photo 或 PendingPhoto
├── web/                        公开页面渲染的轻量应用
│   └── views.py                落地页、主页、画廊、照片详情、统计页
├── planehub/
│   ├── settings.py
│   ├── urls.py
│   └── middleware.py           ApiTimingMiddleware（为 /api/ 响应注入 X-Process-Time）
├── templates/
│   ├── global_landing.html
│   ├── home.html
│   ├── gallery.html
│   ├── photo_page_detailed.html
│   ├── stats.html
│   └── manage/                 需登录的管理页面模板
└── static/
    ├── base.css                全局字体与通用组件样式（Inter 字体）
    ├── home.js                 主页：地图、图表、照片展示区
    ├── gallery.js              画廊：无限滚动、筛选、注册号面板
    ├── photo-detail.js         照片详情：缩放、元数据渲染
    ├── stats.js                统计：ECharts 图表、筛选面板、跳转联动
    ├── airport-data.js         IATA → 机场全名 + ICAO 映射（约 9000 个机场）
    ├── airport-coords.js       IATA → 经纬度坐标，供地图标记使用
    └── cloud/                  落地页动画所用 PNG 云图素材
```

---

## 管理命令

```bash
# 从 Photo 表全量重建机型计数缓存
python manage.py sync_aircraft_submodels

# 列出数据库中无引用的孤立媒体文件
python manage.py clean_orphan_media

# 删除孤立媒体文件
python manage.py clean_orphan_media --delete

# 通过 ID 删除指定 Photo 或 PendingPhoto 记录
python manage.py delete_entry photo 1 2 5 10
python manage.py delete_entry pending 42 43
```

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端框架 | Django 6，SQLite |
| 图片处理 | Pillow（缩略图生成、头像裁剪、横幅缩放） |
| 前端图表 | ECharts |
| 前端地图 | Leaflet + 高德地图瓦片 |
| 样式 | Tailwind CSS（CDN）+ 自定义 `base.css` |
| 字体 | Inter |
| 响应压缩 | Django `GZipMiddleware`（动态响应） |
