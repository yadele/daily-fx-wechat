
import os
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CURRENCIES = {
    "USD": "美元",
    "GBP": "英镑",
    "SGD": "新加坡元",
    "AUD": "澳元",
}

def get_rates(currency, today):
    start = today - timedelta(days=30)
    params = urllib.parse.urlencode({
        "from": start.isoformat(),
        "to": today.isoformat(),
        "base": currency,
        "quotes": "CNY",
    })

    url = "https://api.frankfurter.dev/v2/rates?" + params    
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)


    # 排除周末日期，避免把周末延用值当成新汇率
    by_date = {
        r["date"]: float(r["rate"])
        for r in data
        if r.get("base") == currency
        and r.get("quote") == "CNY"
        and float(r.get("rate", 0)) > 0
        and datetime.fromisoformat(r["date"]).weekday() < 5
    }

    dates = sorted(by_date, reverse=True)
    if len(dates) < 2:
        raise RuntimeError(f"{currency} 汇率数据不足")

    latest_date, previous_date = dates[:2]
    rate = by_date[latest_date]
    previous = by_date[previous_date]
    change = (rate / previous - 1) * 100

    return latest_date, previous_date, rate, change


def send_wechat(title, content):
    key = os.environ["SERVERCHAN_SENDKEY"]
    url = f"https://sctapi.ftqq.com/{key}.send"

    data = urllib.parse.urlencode({
        "title": title,
        "desp": content,
    }).encode("utf-8")

    request = urllib.request.Request(
        url, data=data, method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("code") != 0:
        raise RuntimeError(
            "Server酱推送失败：" +
            str(result.get("message", result))
        )


def main():
    now = datetime.now(ZoneInfo("Asia/Shanghai"))

    lines = [
        f"## 每日汇率播报 {now:%Y-%m-%d %H:%M}",
        "",
        "1单位外币兑换人民币（CNY）",
        "",
        "| 货币 | 人民币汇率 | 涨跌幅 |",
        "|---|---:|---:|",
    ]
    date_notes = []

    for currency, name in CURRENCIES.items():
        latest, previous, rate, change = get_rates(
            currency, now.date()
        )

        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        lines.append(
            f"| {name} {currency} | ¥{rate:.4f} "
            f"| {arrow} {change:+.2f}% |"
        )
        date_notes.append(
            f"- {currency}：{latest} 对比 {previous}"
        )

    lines += [
        "",
        "**实际数据日期与对比日期：**",
        "",
        *date_notes,
        "",
        "周末或节假日可能沿用最近公布的数据。",
        "涨跌幅表示外币兑人民币参考汇率的变化。",
        "数据：Frankfurter；非银行实时成交价。",
    ]

    content = "\n".join(lines)
    print(content)
    send_wechat("每日外汇汇率播报", content)
    print("推送请求已成功提交")


if __name__ == "__main__":
    main()
