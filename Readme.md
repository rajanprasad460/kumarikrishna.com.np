Source code to maintain kumarikrishna.com.np 

Here is a clean, complete `README.md` you can directly use:

````markdown
# NEPSE Floorsheet Tracker

This project automatically scrapes NEPSE floorsheet data from `nepalstock.com`, stores it date-wise, and displays it on a static website hosted via GitHub Pages.

---

# 🚀 Overview

- Scrapes floorsheet data using Python
- Stores data as JSON (date-wise + latest)
- Displays data in browser (search + pagination)
- Updates automatically every day using GitHub Actions

---

# 🏗️ Architecture

```text
GitHub Actions (cron job)
        ↓
Runs Python scraper (scrape.py)
        ↓
Fetches NEPSE floorsheet data
        ↓
Stores JSON in /Data folder
        ↓
Commits updated data to repo
        ↓
GitHub Pages serves website
        ↓
index.html + app.js fetch & render data
````

---

# 📁 Project Structure

```text
.
├── index.html            # Frontend UI
├── app.js                # Fetch + render logic
├── scrape.py             # Floorsheet scraper
├── requirements.txt      # Python dependencies
├── Data/
│   ├── latest.json       # Latest floorsheet (used by UI)
│   └── floorsheet/
│       ├── 2026-05-12.json
│       ├── 2026-05-11.json
│       └── ...
└── .github/
    └── workflows/
        └── scrape.yml    # Automation workflow
```

---

# ⚙️ How It Works

## 1. Scraper (`scrape.py`)

* Uses NEPSE API via Python
* Downloads full floorsheet
* Cleans unnecessary fields (e.g., `securityName`)
* Saves:

```text
Data/floorsheet/YYYY-MM-DD.json
Data/latest.json
```

---

## 2. Frontend (`index.html + app.js`)

* Loads:

```text
./Data/latest.json
```

* Displays:

  * Floorsheet table
  * Search filter
  * Pagination (10 / 20 / 100 / 500 rows)

---

## 3. Automation (GitHub Actions)

Runs automatically every day.

Workflow file:

```text
.github/workflows/scrape.yml
```

Steps:

```text
1. Checkout repo
2. Install Python dependencies
3. Run scraper
4. Save updated JSON files
5. Commit and push changes
```

---

# ⏰ Schedule (Important)

GitHub uses **UTC time**.

```text
4:15 PM Nepal Time = 10:30 AM UTC
```

Cron config:

```yaml
- cron: "30 10 * * *"
```

---

# 💻 Local Development

Run a local server:

```bash
python -m http.server 8000
```

Open:

```text
http://localhost:8000
```

⚠️ Do NOT open `index.html` directly (`file://`) — JSON fetch will fail.

---

# 🌐 GitHub Pages Deployment

Enable in:

```text
Repo Settings → Pages
```

Use:

```text
Branch: main
Folder: /root
```

---

# 📦 Data Optimization

Floorsheet data is large, so we:

* Remove unnecessary fields (e.g., `securityName`)
* Optionally:

  * Shorten keys
  * Remove redundant fields
  * Compress using `.json.gz`

---

# 📊 Features

* 🔍 Search across all fields
* 📄 Pagination
* ⚡ Fast static site (no backend)
* 📅 Date-wise archive storage
* 🔄 Automatic daily updates

---

# ⚠️ Notes

* Large JSON files may slow browser
* Consider:

  * Splitting into pages
  * Using compressed files
* GitHub Actions commits only when data changes

---

# 🔮 Future Improvements

* Load data page-wise (lazy loading)
* Add charts (volume, turnover)
* Filter by symbol / broker
* Store compressed + optimized datasets

---

# 🧠 Summary

```text
Scraper → JSON → GitHub → Static Site → Browser
```

No backend. No database. Fully automated.

---

# 📜 License

This project is for educational and informational use.

```

---

If you want, next I can help you:
- make it look like a professional dashboard (charts + UI)
- or scale it to handle **very large floorsheet data efficiently** 🚀
```


