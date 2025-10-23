# 🕒 Google Drive Timestamp updater

A **Python automation tool** that lets you **change the modified or created date** of files and folders in **Google Drive** using the official **Google Drive API**.

This tool is extremely useful for developers, archivists, or anyone managing old project backups or synced files who wants consistent timestamps.

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Google API Setup](#google-api-setup)
5. [Usage](#usage)
6. [Examples](#examples)
7. [Options](#options)
8. [Advantages](#advantages)
9. [Disadvantages / Limitations](#disadvantages--limitations)
10. [Example Outputs](#example-outputs)
11. [FAQ](#faq)
12. [Author](#author)
13. [License](#license)

---

## 🧭 Overview

By default, Google Drive doesn’t allow users to manually modify a file’s **upload date** or **modified time** via the web interface.

However, using the **Google Drive API**, developers can programmatically update file metadata such as:
- `modifiedTime`
- `createdTime`

This project simplifies that process into a command-line tool with:
- Recursive folder support  
- Dry-run preview mode  
- Credential-based authentication  

---

## ⚙️ Features

✅ Change file or folder `modifiedTime` and `createdTime`  
✅ Recursive mode — update all subfolders and files  
✅ Dry-run mode — preview changes without applying  
✅ Works with **Service Account credentials**  
✅ Simple one-line command execution  
✅ Cross-platform — works on Windows, macOS, and Linux  

---

## 💻 Installation

### 1️⃣ Prerequisites

- Python **3.8+**
- A Google Cloud Project with **Drive API** enabled
- Your **Service Account JSON key**

### 2️⃣ Clone the Repository

```bash
git clone https://github.com/athulcoder/gdrive-timestamp-updater.git
cd google-drive-date-modifier

```
## Install dependencies
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## example
```bash
python main.py -c service_account.json --recursive 132o7aen5Qy6OnwkWe5YiNfYxMW-ZO4Nb 2006-03-24T09:20:25.000Z

