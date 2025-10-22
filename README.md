# 👻 GHOSTS – Human Activity Simulation Framework (User-Sim Edition)

This project is a **human activity simulator** inspired by [CMU-SEI GHOSTS (Generate Human-like Operation Simulation and Traffic System)](https://github.com/cmu-sei/GHOSTS).

It automates **realistic end-user behavior** across desktop applications like:
- 🦊 Firefox (web browsing)
- ✉️ Thunderbird (email reading, link-clicking, attachment opening)
- 📝 OnlyOffice (document editing and saving)

The goal is to **mimic human workstation activity** for use in:
- Cyber range environments
- SOC / EDR testing
- Blue team and forensic simulation
- Endpoint telemetry and behavioral analysis

---

## ⚙️ Core Concept

At its core, this app uses **YAML-defined action scripts** that describe how a “digital user” behaves.  
Each action mimics human keyboard/mouse input, randomizes timing, and executes within real desktop apps.

The controller (`main.py`) handles:
1. Loading configuration (`settings.yaml`)
2. Randomly or sequentially triggering YAML-defined user actions
3. Executing steps with human-like delays and randomness
4. Logging every simulated activity to a log file

---

## 📂 Project Structure

ghosts/
├── actions/
│   ├── browse_many.yaml            # Browses multiple websites in Firefox
│   ├── click_link_email.yaml       # Opens Thunderbird → clicks hyperlink in latest email
│   ├── draft_mail.yaml             # Drafts a new email with random content
│   ├── edit_doc.yaml               # Opens & edits random OnlyOffice document
│   ├── open_attachment_email.yaml  # Opens latest email and downloads attachment
│   └── write_notes.yaml            # Creates a new notes document
│
├── modules/
│   ├── firefox/
│   │   ├── firefox.yaml
│   │   └── images/                 # Icon templates for automation
│   ├── onlyoffice/
│   │   ├── onlyoffice.yaml
│   │   └── images/
│   └── thunderbird/
│       ├── thunderbird.yaml
│       └── images/                 # Contains 'hyperlink' & 'attachment' screenshots
│
├── main.py                         # Main controller that executes YAML actions
├── settings.yaml                   # Global config (log paths, timing, random delays)
└── .gitignore


---

## 🧩 Features

- 🧍 **Humanized Behavior Simulation** – Mimics keystrokes, random delays, and window focus  
- 🔁 **Modular Actions** – Add or remove behaviors easily using YAML  
- 💻 **Cross-Application Support** – Firefox, Thunderbird, OnlyOffice  
- 🪵 **Centralized Logging** – Every step recorded in timestamped logs  
- ⏱ **Realistic Timing Engine** – Built-in random wait ranges and movement jitter  

---
