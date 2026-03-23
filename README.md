# Ayurvedic Drug Screening: Autonomous Discovery Pipeline

This repository contains an autonomous high-throughput docking pipeline for identifying soluble anti-inflammatory compounds from traditional Ayurvedic sources.

## Overview
This project targets the **human COX-2 enzyme (PDB 5F19)** using a library of **Withanolides** and **Boswellic acids**. The pipeline automates compound sourcing from PubChem, physiochemical filtering for beverage compatibility (LogP < 3.5), and site-specific molecular docking at the Ser-530 active site.

## Key Features
- **Autonomous Sourcing**: Integration with PubChem PUG REST API.
- **Solubility Filtering**: Automated XLogP checking and glycosylation prioritization.
- **Precision Docking**: Site-specific targeting of the COX-2 Ser-530 pocket.
- **Reporting**: Automated generation of high-affinity candidate tables and formulation hypotheses.

## Attributions & Acknowledgments
- **Molecular Docking API**: Provided by **VI-DOCK**.
- **Co-Authorship & Pipeline Development**: Developed by **Antigravity** with the assistance of the **Gemini 3 Flash** model.
- **Primary Researcher**: Arjun Subbaraman.

## Installation & Usage
1. Clone the repository.
2. Install dependencies: `pip install requests pandas tabulate`.
3. Set your API endpoint: `set DOCKING_API_URL=https://your-api-url.com` (Windows) or `export DOCKING_API_URL=...` (Linux/Mac).
4. Run the screen: `python full_automated_screen.py`.

## Contents
- `full_automated_screen.py`: The main autonomous pipeline script.
- `white_paper.md`: Formal research paper detailing the study, methodology, and Top 10 results.
- `final_docking_report.md`: Markdown summary of docking scores and formulation hypotheses.

## License
Licensed under the **MIT License**.
