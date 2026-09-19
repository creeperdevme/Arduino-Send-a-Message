# Arduino-Send-a-Message

[English](README.md) | **繁體中文**

在瀏覽器打一則訊息，它就會顯示在接上 Arduino 的 16×2 LCD 上，並用兩聲短嗶提示。

Arduino 從序列埠接收資料。電腦上跑一支小型的 Python 網頁伺服器，提供網頁表單，把你打的字透過 USB 線送下去。

```text
瀏覽器  ──HTTP──▶  Python 網頁伺服器  ──USB 序列埠──▶  Arduino  ──▶  LCD + 蜂鳴器
                    (FastAPI / Flask)    9600 baud       "line1|line2\n"
```

---

## 功能

- **網頁介面** — 單頁表單，含即時字數統計、輸入驗證與 toast 通知
- **自動偵測序列埠** — 自動找出 Arduino，也可手動指定
- **兩行、每行 16 字元** — 與 LCD 的可顯示範圍完全對應
- **過濾非 ASCII 字元** — 中文等無法顯示的字元會在送達螢幕前就被濾掉
- **聲音提示** — 每則新訊息都會嗶兩聲
- **自動重連** — USB 拔掉再插回，下一次請求會自行重新連線

---

## 硬體需求

| 零件 | 說明 |
| --- | --- |
| Arduino Uno / Nano | 任何有硬體序列埠、且 5V 腳位足夠的板子 |
| 16×2 LCD（含 I2C 背板） | 預設 I2C 位址為 `0x27` |
| 被動式蜂鳴器 | 必須接在 PWM 腳位 —— 草稿碼用 **D9** 來控制音量 |

### 接線

| LCD（I2C） | Arduino Uno/Nano |
| --- | --- |
| GND | GND |
| VCC | 5V |
| SDA | A4 |
| SCL | A5 |

| 蜂鳴器 | Arduino |
| --- | --- |
| `+` | D9（PWM） |
| `−` | GND |

> 若使用 Mega 或其他 I2C 腳位不同的板子，請自行調整 SDA/SCL 接線。如果 LCD 全黑沒有畫面，先跑一支 I2C 掃描草稿碼 —— 有些背板出廠位址是 `0x3F` 而非 `0x27`，這時要改 [main.ino](main.ino) 裡的位址。

---

## 安裝

### 1. Arduino

1. 透過 *工具 → 管理程式庫* 安裝 **LiquidCrystal_I2C**（作者 Frank de Brabander）。
2. 開啟 [main.ino](main.ino) 並上傳到板子。
3. LCD 應該會顯示 `Server Ready!`。

### 2. Python

需要 Python 3.8 以上。

```bash
pip install -r requirements.txt
```

### 3. 啟動

```bash
python webserver.py
```

接著開啟 <http://127.0.0.1:3000> 就能送訊息。

---

## 設定

伺服器從環境變數讀取設定，[.env.example](.env.example) 列出了全部項目。複製它，並在你的 shell 中匯出這些值（程式是直接讀取行程環境變數，所以要用 `.env` 檔的話得自備載入器或寫進 shell 設定）。

| 變數 | 預設值 | 說明 |
| --- | --- | --- |
| `ARDUINO_PORT` | *（自動偵測）* | 序列埠，例如 Windows 的 `COM3` 或 Linux/macOS 的 `/dev/ttyACM0`。留空則由伺服器自行掃描。 |
| `ARDUINO_BAUD` | `9600` | 必須與草稿碼中的 `Serial.begin()` 一致 |
| `APP_HOST` | `0.0.0.0` | 網頁伺服器的綁定位址 |
| `APP_PORT` | `3000` | 網頁伺服器埠號 |
| `MAX_LINE_LENGTH` | `16` | 每行 LCD 的字元數上限 |
| `CONNECT_DELAY_SECONDS` | `2` | 開啟序列埠後、送出資料前的等待秒數 —— Arduino 在連線時會重置 |

範例（PowerShell）：

```powershell
$env:ARDUINO_PORT = "COM3"
python webserver.py
```

範例（bash）：

```bash
ARDUINO_PORT=/dev/ttyACM0 python webserver.py
```

> **啟動伺服器前，請先關閉 Arduino IDE 的序列埠監控視窗。** 同一個序列埠一次只能被一支程式佔用，這是連線失敗最常見的原因。

---

## 使用方式

### 網頁介面

開啟伺服器根目錄（`/`）會看到一個兩欄表單。每行上限 16 字元，只要輸入可列印 ASCII 以外的字元就會被即時擋掉。送出成功後表單會清空，LCD 同步更新。

### API

直接送訊息：

```bash
curl -X POST http://127.0.0.1:3000/api/send \
  -H "Content-Type: application/json" \
  -d '{"line1": "Hello", "line2": "World"}'
```

```json
{ "message": "Message sent successfully." }
```

確認 Arduino 是否連得上：

```bash
curl http://127.0.0.1:3000/health
# {"status":"ok"}                                   HTTP 200
# {"status":"arduino_not_connected"}                HTTP 503
```

| 方法 | 路徑 | 內容 / 查詢參數 | 回傳 |
| --- | --- | --- | --- |
| `GET` | `/` | — | 網頁表單 |
| `POST` | `/api/send` | JSON `{ "line1": str, "line2": str }` | 成功 `200`；兩行皆空 `400`；Arduino 未連線 `503`；內部錯誤 `500` |
| `GET` | `/health` | — | 已連線 `200`，否則 `503` |

若只給一行，另一行會顯示為空白。兩個欄位在伺服器端都會被截斷至 `MAX_LINE_LENGTH`，並濾掉不可列印的 ASCII 字元，所以螢幕內容不會被非預期輸入破壞。

---

## `webserver.py` 與 `server.py` 的差別

兩者透過同一套序列埠協定與同一份草稿碼溝通，差別在框架與功能範圍：

| | [webserver.py](webserver.py) | [server.py](server.py) |
| --- | --- | --- |
| 框架 | FastAPI + Uvicorn | Flask |
| 網頁介面 | 有，在 `/` 提供 | 無 |
| 端點 | `POST /api/send`（JSON） | `GET`/`POST /v1/display`（查詢參數或 JSON） |
| 預設埠 | `3000` | `8080` |
| 可設定項目 | 埠、主機、行長、延遲 | 埠、baud |

**除非你特別想要 Flask 那組較輕的相依，否則請用 `webserver.py`** —— 它是有在維護的路徑，也包含瀏覽器介面。`server.py` 是較早的精簡版本，適合只想接一個 HTTP 端點的情境。

---

## 序列埠協定

Arduino 預期每則訊息以一個換行字元結尾：

```text
line1|line2\n
```

- `|` 分隔兩列顯示內容。沒有 `|` 時，整段內容會顯示在第一行。
- `\n` 代表訊息結束，觸發螢幕更新與蜂鳴。
- 9600 baud，8N1。

你也可以完全不透過這兩支 Python 伺服器，直接用序列埠終端機操作硬體 —— 輸入 `Hello|World` 後按 Enter 即可。

---

## 專案結構

```text
Arduino-Send-a-Message/
├── main.ino          # Arduino 草稿碼 —— LCD + 蜂鳴器，讀取序列埠
├── webserver.py      # FastAPI 伺服器，含網頁介面（建議使用）
├── server.py         # 精簡版 Flask 伺服器
├── requirements.txt  # Python 相依套件
├── .env.example      # 設定範本
├── README.md         # 英文版
└── README.zh-TW.md   # 本檔案（繁體中文）
```

---

## 疑難排解

| 症狀 | 可能原因 |
| --- | --- |
| 顯示 `Arduino not connected` / 回傳 `503` | Arduino IDE 的序列埠監控還開著、`ARDUINO_PORT` 設錯，或用到只能充電的 USB 線 |
| 出現 `Multiple serial port candidates found` | 插了多個 USB 序列裝置 —— 直接指定 `ARDUINO_PORT` 即可 |
| LCD 全黑沒有畫面 | I2C 位址不符（`0x27` 對 `0x3F`），或背板上的對比度可變電阻要調整 |
| 字元顯示錯亂或缺字 | `ARDUINO_BAUD` 與草稿碼中的 `Serial.begin(9600)` 不一致 |
| 訊息有字母不見 | 輸入含非 ASCII 字元，被過濾掉了 —— 這是刻意設計，因為 LCD 字型無法顯示 |
| 蜂鳴器沒聲音 | 接在非 PWM 腳位，或 `beepTwice()` 裡的音量值（`10`）對你的蜂鳴器太小 —— 可試 `20` |

---

## 授權

本專案未附授權條款檔案。
