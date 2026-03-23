# VI-DOCK Pro 3.1: API Integration Guide for AI Agents 🧬

This document provides the "rules" and protocols for an AI agent to interact with the VI-DOCK backend programmatically.

## 📡 Base URL
Depending on your deployment:
- **Local**: `http://localhost:8000`
- **Colab/Tunnel**: Use your ngrok/localtunnel URL (e.g., `https://xxxx.ngrok-free.app`)

---

## 🛠️ Step-by-Step Docking Workflow

### 1. Create a Project
Every run must belong to a project.
- **Endpoint**: `POST /projects/`
- **Payload**: `{"name": "my_experiment_01"}`

### 2. Upload Input Files
You must upload both a **Receptor** and a **Ligand** in `.pdbqt` format.
- **Endpoint**: `POST /projects/{project_name}/upload?category=receptor`
- **Endpoint**: `POST /projects/{project_name}/upload?category=ligand`
- **Method**: Multipart Form Data ([file](file:///c:/Users/arjun/OneDrive/Desktop/vi-dock-backend/Dockerfile) field)

> [!TIP]
> If you only have PDB files, use the **Conversion API** first (see below).

### 3. Calculate Grid Box (Autoboxing)
If you don't know the coordinates, the API can calculate them from the ligand.
- **Endpoint**: `POST /analysis/{project_name}/gridbox?ligand_file=ligand.pdbqt`
- **Returns**: Center X, Y, Z and Size X, Y, Z.

### 4. Submit Docking Job
- **Endpoint**: `POST /docking/{project_name}/dock`
- **Payload**:
```json
{
  "engine": "vina",
  "receptor_file": "receptor.pdbqt",
  "ligand_file": "ligand.pdbqt",
  "config": {
    "center_x": 0.0, "center_y": 0.0, "center_z": 0.0,
    "size_x": 20.0, "size_y": 20.0, "size_z": 20.0
  },
  "exhaustiveness": 8
}
```

### 5. Monitor Job & Get Results
- **Endpoint**: `GET /docking/jobs/{job_id}`
- **Status**: Poll until status is `"completed"`.
- **Results**: The response will contain a `scores` array (with affinities) and an `output_file` path.

---

## 🔄 Utility Endpoints

### PDB to PDBQT Conversion
- **Endpoint**: `POST /convert/pdb-to-pdbqt`
- **Payload**: `{"pdb_content": "...", "add_hydrogens": true}`

### Fetch from RCSB (PDB ID)
- **Endpoint**: `GET /fetch/pdb/{pdb_id}`

---

## ⚠️ Important Rules for the AI
1. **Coordinate Systems**: Ensure that the `center` coordinates provided in Step 4 are relative to the receptor's 3D space.
2. **File Formats**: AutoDock Vina REQUIRES `.pdbqt`. Do not send raw `.pdb` or `.sdf` to the `/dock` endpoint.
3. **Polling**: Do not spam the status endpoint. A 1-second interval is recommended.
4. **Project Names**: Use unique project names to avoid file overwrites.
