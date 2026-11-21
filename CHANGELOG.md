# Changelog

## [Unreleased]

### Added — 声音设置：引擎/音色/语速/声调/音量，带「试听」（ACT.TTS_CN 的"测试"同款）

两套设置 UI（DSH 组合包页表单 `lib/client.js` + 独立设置页 `page.html`）都新增「声音」调节，
落盘 `~/.dsh/tts.json`（`voice` / `rate`(-10..10) / `pitch`(±Hz) / `volume`(0-100)，
另有引擎策略键 `engine` / `edgeTts`）；保存和试听共用 `applyTtsPatch` 同一套校验换算
（`src/settings/config.js`），口径在 `bin/tts.mjs` 只写一份：edge-tts 的 `--rate/--pitch/--volume`
换算（`edgeCliArgs`）与 SAPI 的 Rate/Volume/`<pitch>` XML（`buildSpeakCommand`）都从这里出，
示例适配器的三引擎入口（常驻通道 / 逐句兜底 / SAPI 兜底）同用这一份。

**「试听」按钮**：按面板当前参数**真的念一句**（不落盘），走陪看同一条合成链
（常驻合成器 → edge-tts 逐句 → SAPI 兜底），回执写明**实际出声的引擎**和**首声耗时**：

- **常驻热合成器**（`POST /tts-test`，`src/settings/tts-test.js`）：所有试听共用一个 daemon，
  参数随请求带（滑块随便拉不重启），第二次起首声 ~几百毫秒 —— 不再每次冷启动 python + 建连
  （实测冷 889~2214ms → 热 188~313ms）；闲置 3 分钟自动收。
- **新顶旧**：跑着的试听被下一次立刻掐断（AbortSignal + 通道 interrupt），按钮永不吞点击 ——
  以前跑着的时候是静默空转，用户看到的就是「点了没反应」。被掐断的那句回 `reason:'interrupted'`。
- **显式选了引擎就不兜底**：选 Edge 失败直接报原因，不静默换系统嗓 —— 试听要如实。
- daemon 的 `interrupt` 顺带修正为**取消整个合成任务**（原来只掐播放，合成剩下的音频块
  会混进下一句叠着响）；缓存键含参数（换音色/声调不共用旧缓存）。

### Changed — 语音引擎默认本地 SAPI，云端（edge-tts）显式开启

以前「装了 edge-tts 就优先用」，等于装了它的人在不知情时把要念的文本发给了微软。
现在默认走**本机 SAPI**（文本不出机器）；云端是三个显式开关之一才开：
`tts.json` 写 `{"engine":"edge"}`（写 `"sapi"` 强制本地，压过下面两条）/ `edgeTts` 点名可执行
文件路径 / 环境变量 `DSH_TTS_ENGINE=edge`（或 `DSH_TTS_BIN=<路径>`）。设置表单的引擎下拉同语义。
