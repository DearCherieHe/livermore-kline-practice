my_indicator_name = "A13 涨停后缩量平台突破"
my_indicator_description = "识别涨停事件后的缩量整理，只在放量突破平台时开多；跌破事件K线中点或放量滞涨时平多。"

# --- QuantDinger execution contract (v1) ---
# signal_form: four_way
# exit_owner: indicator
# flip_mode: R1

# @param limit_up_pct float 0.095 涨停事件的最低单日涨幅
# @param min_wait_bars int 3 涨停后最少等待K线数
# @param max_wait_bars int 8 涨停后最多等待K线数
# @param contraction_ratio float 0.75 缩量阈值相对20期均量
# @param breakout_volume_ratio float 1.2 突破量相对20期均量
# @param blowoff_volume_ratio float 2.5 放量滞涨退出阈值

# @strategy entryPct 0.2
# @strategy trailingEnabled false
# @strategy tradeDirection long


def edge(signal):
    signal = signal.fillna(False).astype(bool)
    return signal & ~signal.shift(1, fill_value=False)


def marker_values(signal, price, multiplier):
    return [
        float(price.iloc[i]) * multiplier if bool(signal.iloc[i]) else None
        for i in range(len(df))
    ]


limit_up_pct = float(params.get("limit_up_pct", 0.095))
min_wait_bars = int(params.get("min_wait_bars", 3))
max_wait_bars = int(params.get("max_wait_bars", 8))
contraction_ratio = float(params.get("contraction_ratio", 0.75))
breakout_volume_ratio = float(params.get("breakout_volume_ratio", 1.2))
blowoff_volume_ratio = float(params.get("blowoff_volume_ratio", 2.5))

df = df.copy()
n = len(df)
bar_number = pd.Series(np.arange(n), index=df.index, dtype=float)

limit_up_event = df["close"].pct_change() >= limit_up_pct
last_event_bar = pd.Series(
    np.where(limit_up_event, bar_number, np.nan), index=df.index
).ffill()
bars_since_event = bar_number - last_event_bar
event_mid = ((df["high"] + df["low"]) / 2).where(limit_up_event).ffill()

volume_ma_20 = df["volume"].rolling(20).mean()
recent_volume = df["volume"].shift(1).rolling(3).mean()
platform_high = df["high"].shift(1).rolling(max_wait_bars).max()

inside_wait_window = (
    (bars_since_event >= min_wait_bars)
    & (bars_since_event <= max_wait_bars)
)
volume_contracting = recent_volume < volume_ma_20 * contraction_ratio
price_holds_event = df["close"] > event_mid
breaks_platform = df["close"] > platform_high
breakout_volume = df["volume"] > volume_ma_20 * breakout_volume_ratio

raw_open_long = (
    inside_wait_window
    & volume_contracting
    & price_holds_event
    & breaks_platform
    & breakout_volume
)
raw_close_long = (
    (df["close"] < event_mid)
    | (
        (df["volume"] > volume_ma_20 * blowoff_volume_ratio)
        & (df["close"] < df["open"])
    )
)

df["open_long"] = edge(raw_open_long)
df["close_long"] = edge(raw_close_long)
df["open_short"] = pd.Series(False, index=df.index, dtype=bool)
df["close_short"] = pd.Series(False, index=df.index, dtype=bool)

open_long_marks = marker_values(df["open_long"], df["low"], 0.995)
close_long_marks = marker_values(df["close_long"], df["high"], 1.005)
open_short_marks = marker_values(df["open_short"], df["high"], 1.005)
close_short_marks = marker_values(df["close_short"], df["low"], 0.995)

output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "涨停K线中点",
            "data": event_mid.fillna(0).tolist(),
            "color": "#FFC107",
            "overlay": True,
        },
        {
            "name": "整理平台上沿",
            "data": platform_high.fillna(0).tolist(),
            "color": "#42A5F5",
            "overlay": True,
        },
    ],
    "signals": [
        {"type": "buy", "text": "开多", "data": open_long_marks, "color": "#00E676"},
        {"type": "sell", "text": "平多", "data": close_long_marks, "color": "#FFAB40"},
        {"type": "sell", "text": "开空", "data": open_short_marks, "color": "#FF5252"},
        {"type": "buy", "text": "平空", "data": close_short_marks, "color": "#40C4FF"},
    ],
    "calculatedVars": {
        "market": "A-share",
        "signal_logic": "limit-up event -> volume contraction -> platform breakout",
    },
}
