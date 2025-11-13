
# log_analyzer.py
# Save this file and run it in the same directory as your access.log and error.log
# It is the same code that generated/ran in the notebook (trimmed header).
# (For brevity, this is the essential parsing + reporting routine)

import re
from datetime import datetime, timezone
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ACCESS_LOG = "access.log"
ERROR_LOG = "error.log"
PDF_OUT = "apache_log_analysis_report.pdf"

access_pattern = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<proto>[^"]+)" (?P<status>\d{3}) (?P<size>\S+) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"'
)

error_pattern = re.compile(r'^\[(?P<time>[^\]]+)\] \[(?P<module>[^:]+):(?P<level>[^\]]+)\] \[pid (?P<pid>\d+)\] \[client (?P<client>[^\]]+)\] (?P<message>.*)$')

def classify_browser(ua: str) -> str:
    if "Chrome" in ua and "Edg" not in ua:
        return "Chrome"
    if "Firefox" in ua:
        return "Firefox"
    if "Edg" in ua or "Edge" in ua:
        return "Edge"
    if "Safari" in ua and "Chrome" not in ua:
        return "Safari"
    return "Other"

def parse_access_log(path):
    records = []
    with open(path) as f:
        for line in f:
            m = access_pattern.search(line)
            if not m:
                continue
            d = m.groupdict()
            try:
                ts = datetime.strptime(d["time"], "%d/%b/%Y:%H:%M:%S %z")
            except ValueError:
                continue
            rec = {
                "ip": d["ip"],
                "time": ts,
                "method": d["method"],
                "path": d["path"].split('?')[0],
                "status": int(d["status"]),
                "size": int(d["size"]) if d["size"].isdigit() else 0,
                "referer": d["referer"],
                "agent": d["agent"]
            }
            records.append(rec)
    return pd.DataFrame(records)

def parse_error_log(path):
    records = []
    with open(path) as f:
        for line in f:
            m = error_pattern.search(line.strip())
            if not m:
                continue
            d = m.groupdict()
            ts = None
            for fmt in ("%a %b %d %H:%M:%S.%f %Y", "%a %b %d %H:%M:%S %Y"):
                try:
                    ts = datetime.strptime(d["time"], fmt).replace(tzinfo=timezone.utc)
                    break
                except Exception:
                    pass
            records.append({
                "time": ts,
                "module": d["module"],
                "level": d["level"],
                "pid": int(d["pid"]),
                "client": d["client"].split(":")[0] if ":" in d["client"] else d["client"],
                "message": d["message"]
            })
    return pd.DataFrame(records)

def generate_report(access_df, error_df, out_pdf):
    access_df = access_df.copy()
    error_df = error_df.copy()
    access_df["browser"] = access_df["agent"].apply(classify_browser)
    access_df["hour"] = access_df["time"].dt.floor("H")
    error_df["hour"] = error_df["time"].dt.floor("H")

    page_counts = access_df["path"].value_counts().rename_axis("page").reset_index(name="access_count")
    ip_counts = access_df["ip"].value_counts().rename_axis("ip").reset_index(name="access_count")
    browser_counts = access_df["browser"].value_counts().rename_axis("browser").reset_index(name="count")
    timeline = access_df.groupby("hour").size().rename("requests").reset_index()
    error_timeline = error_df.groupby("hour").size().rename("errors").reset_index()

    with PdfPages(out_pdf) as pdf:
        fig = plt.figure(figsize=(11, 8.5))
        fig.suptitle("Apache Log Analysis Report", fontsize=16)
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(11,8))
        top_pages = page_counts.head(10).iloc[::-1]
        ax.barh(top_pages["page"], top_pages["access_count"])
        ax.set_title("Top pages")
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(11,8))
        top_ips = ip_counts.head(10).iloc[::-1]
        ax.barh(top_ips["ip"], top_ips["access_count"])
        ax.set_title("Top IPs")
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(11,8))
        ax.bar(browser_counts["browser"], browser_counts["count"])
        ax.set_title("Browser breakdown")
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(11,6))
        ax.plot(timeline["hour"], timeline["requests"], marker="o")
        ax.set_title("Requests per hour")
        fig.autofmt_xdate()
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(11,6))
        if len(error_timeline) > 0:
            ax.plot(error_timeline["hour"], error_timeline["errors"], marker="x")
        ax.set_title("Errors per hour")
        fig.autofmt_xdate()
        pdf.savefig(fig); plt.close(fig)

if __name__ == "__main__":
    access_df = parse_access_log(ACCESS_LOG)
    error_df = parse_error_log(ERROR_LOG)
    generate_report(access_df, error_df, PDF_OUT)

