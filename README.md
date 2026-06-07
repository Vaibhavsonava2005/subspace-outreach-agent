# 🚀 Subspace Cold Outreach Agent

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Author](https://img.shields.io/badge/Author-Vaibhav%20Sonava-blueviolet?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=for-the-badge)

> **Fully automated cold outreach pipeline** built for the **Subspace / Vocallabs** assignment.  
> Give it a domain — it finds similar companies, discovers decision-makers, enriches emails, and delivers personalized outreach. All in one command.

---

## ✨ What It Does

This agent automates the entire cold outreach workflow in a **four-stage pipeline** — no manual steps, no spreadsheets, no copy-paste. Just run it and watch.

```
python main.py --domain hubspot.com
```

That's it. The agent handles everything else.

---

## 🏗️ Architecture

```
                          ┌─────────────────────┐
                          │   Domain Input       │
                          │   (e.g. hubspot.com) │
                          └─────────┬───────────┘
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │  Stage 1: Ocean.io                    │
                │  Discover similar companies           │
                │  Input:  target domain                │
                │  Output: list of similar companies    │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │  Stage 2: Prospeo                     │
                │  Find decision-makers at each company │
                │  Input:  company domains              │
                │  Output: names + LinkedIn URLs        │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │  Stage 3: Eazyreach                   │
                │  Enrich LinkedIn profiles → emails    │
                │  Input:  LinkedIn profile URLs        │
                │  Output: verified email addresses     │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                ┌───────────────────────────────────────┐
                │  Stage 4: Brevo (Sendinblue)          │
                │  Deliver personalized cold emails     │
                │  Input:  contacts + email template    │
                │  Output: delivery confirmations       │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │   ✅ Emails Sent     │
                          │   + JSON Report      │
                          └─────────────────────┘
```

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Vaibhavsonava2005/subspace-outreach-agent.git
cd subspace-outreach-agent
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys (see the table below).

---

## 🔑 API Keys

| #  | Service       | Environment Variable | Purpose                          | Get a Key                                    |
|----|---------------|----------------------|----------------------------------|----------------------------------------------|
| 1  | **Ocean.io**  | `OCEAN_API_KEY`      | Discover similar companies       | [ocean.io](https://ocean.io)                 |
| 2  | **Prospeo**   | `PROSPEO_API_KEY`    | Find decision-makers & LinkedIn  | [prospeo.io](https://prospeo.io)             |
| 3  | **Eazyreach** | `EAZYREACH_API_KEY`  | LinkedIn → email enrichment      | [eazyreach.io](https://eazyreach.io)         |
| 4  | **Brevo**     | `BREVO_API_KEY`      | Transactional email delivery     | [brevo.com](https://www.brevo.com)           |

> **Note:** `BREVO_API_KEY` and `SENDER_EMAIL` are **required**. The pipeline will warn you if other keys are missing but will still attempt to run available stages.

---

## 🚀 Usage

### Basic run

```bash
python main.py --domain hubspot.com
```

### Dry-run mode (preview without sending)

```bash
python main.py --domain stripe.com --dry-run
```

### Custom output directory

```bash
python main.py --domain intercom.com --output results/
```

### CLI Reference

| Flag         | Required | Default   | Description                               |
|--------------|----------|-----------|-------------------------------------------|
| `--domain`   | ✅ Yes   | —         | Target company domain to prospect around  |
| `--dry-run`  | No       | `false`   | Preview pipeline without sending emails   |
| `--output`   | No       | `output/` | Directory to save JSON results            |

---

## 📂 Project Structure

```
subspace-outreach-agent/
├── main.py                  # CLI entry point with Rich TUI
├── config.py                # Configuration loader & validator
├── requirements.txt         # Pinned Python dependencies
├── .env.example             # Example environment config
├── .gitignore               # Comprehensive Python gitignore
├── README.md                # You are here
│
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py      # PipelineOrchestrator — runs all 4 stages
│   ├── exporter.py          # ResultExporter — saves JSON output
│   │
│   └── stages/
│       ├── __init__.py
│       ├── ocean.py         # Stage 1: Ocean.io API client
│       ├── prospeo.py       # Stage 2: Prospeo API client
│       ├── eazyreach.py     # Stage 3: Eazyreach API client
│       └── brevo.py         # Stage 4: Brevo email sender
│
├── output/                  # Generated results (git-ignored)
└── logs/                    # Rotating log files (git-ignored)
```

---

## 🖥️ Terminal Output

When you run the agent, you'll see:

1. **ASCII art banner** — project identity
2. **Configuration table** — which API keys are active
3. **Live progress bars** — real-time stage tracking
4. **Email draft panels** — preview every email before/after sending
5. **Summary dashboard** — companies found, contacts enriched, emails sent, timing per stage

---

## 🛡️ Design Decisions

| Decision                  | Rationale                                                         |
|---------------------------|-------------------------------------------------------------------|
| `httpx` over `requests`   | Async-ready, HTTP/2 support, modern API                           |
| `tenacity` for retries    | Decorator-based retry with exponential backoff for flaky APIs     |
| `loguru` over `logging`   | Zero-config structured logging with rotation and colorized output |
| `rich` for TUI            | Production-grade terminal UI with tables, panels, progress bars   |
| `python-dotenv` for config| 12-factor app compliance, simple `.env` file loading              |

---

## 📝 License

This project is licensed under the **MIT License**.

---

## 👤 Author

**Vaibhav Sonava**

- GitHub: [github.com/Vaibhavsonava2005](https://github.com/Vaibhavsonava2005)

---

<p align="center">
  <b>Built with ❤️ for the Subspace / Vocallabs Assignment</b><br>
  <sub>Created by Vaibhav Sonava</sub>
</p>
