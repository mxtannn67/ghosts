# ⚙️ Installation Guide for GHOSTS User-Sim

This guide explains how to install and run the human activity simulator.

---

## 🧱 Requirements

- Ubuntu / Debian system
- Python 3.8+
- ```bash
  - sudo apt-get install python3-tk python3-dev
- Installed GUI apps:
- ```bash
  - sudo snap install onlyoffice-desktopeditors
  - sudo apt install -y thunderbird

- Internet connection for dependencies

---

## 🧩 Setup

- ```bash
  - sudo apt install git
  - cd ~
  - git clone https://github.com/mxtannn67/ghosts.git
  - cd ghosts
  - sudo apt install python3-pip
  - pip install -r requirements.txt

---
##🧠 Configure the App
Open settings.yaml inside your project folder and adjust as needed

## 🚀 Running the Simulation
- ```bash
  - python3 main.py



📜 Viewing Logs
- ```bash
  - cat ~/.local/share/user-sim/activity.log
  - tail -f ~/.local/share/user-sim/activity.log    #view them live
  

