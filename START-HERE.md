# IncidentLens AI — Alisha ka local demo

Ye version sample incidents aur local logs ki evidence-based investigation ke liye hai. Live production infrastructure se connected nahi hai.

## Shuru kaise karein

1. PowerShell mein `C:\GenAI-Projects\AI-Incident-RCA-Agent` folder kholen.
2. `.\Launch-IncidentLens.ps1` chalayein. Window chalti rehne dein.
3. Browser mein http://127.0.0.1:8765/ kholen.
4. Band karne ke liye server wali window mein Ctrl+C karein. Saved reports delete nahi honge.

Agar port busy ho to `.\Launch-IncidentLens.ps1 -Port 8766` aur browser mein wahi port use karein. Script blocked ho to README mein existing Python se launch karne ka alternative hai; security policy badalne ki zarurat nahi.

## Demo ka flow

- INC-1001: pool saturation ke logs, evidence links aur missing cause dekhein.
- INC-1003: incomplete evidence par Low confidence dekhein.
- INC-1004: conflicting evidence dekhein.
- Local AI investigation: existing Ollama/model available ho to click karein. Tool audit mein decisions dekhein. AI tool order select karta hai; report ka analysis rules-based hai.
- Save investigation: current report ka exact snapshot save karein. Saved investigations mein reopen karein ya do reports select karke compare karein.
- Find a runbook mein `db pool exhaustion` search karein. Ranking keywords/synonyms par hai.
- Import custom logs mein title dein, `samples/demo-import.log` choose karein ya logs paste karein, phir Validate & import locally click karein. File synthetic hai; demo-placeholder real credential nahi hai.
- Export JSON/Markdown current displayed report ke liye hai. Purane saved reports automatically reanalyse nahi hote.

## Data aur control

Reports/imports `.local/incidentlens.sqlite3` mein rehte hain. Database encrypted nahi hai. Known secrets mask hote hain, lekin apne logs import se pehle review karein. Backup ke liye server band karke database ki copy apni approved local backup location mein rakhein.

Root cause “Unconfirmed” rehna expected hai jab independent causal evidence nahi ho. Confidence probability nahi hai. Automatic restart/rollback/delete available nahi hain; future destructive action ke liye exact action par explicit human approval chahiye.

## Agar problem aaye

- Page nahi khulta: launcher running hai aur browser ka port match karta hai, check karein.
- AI unavailable/fallback: normal report phir bhi kaam karega. Existing Ollama aur llama3.2:1b availability check karein; app khud install/download nahi karta.
- Import reject: UTF-8, timezone, allowed fields, 200-event/512-KB limits check karein. Message mein pipe ho to JSONL use karein.
- Save token expired: incident ko dobara select karke fresh report save karein.

Detailed input format, architecture, MCP/CLI commands aur verified limitations README.md aur VERIFICATION.md mein hain.
