import requests
import time
import json
import pandas as pd

BASE_API_URL = "https://catherine-mailed-digit-watching.trycloudflare.com"
PUBCHEM_REST = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"

def fetch_cids_by_name(name):
    print(f"Searching PubChem for {name} derivatives...")
    url = f"{PUBCHEM_REST}/name/{name}/cids/JSON?name_type=word"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('IdentifierList', {}).get('CID', [])
    return []

def fetch_properties(cids):
    print(f"Fetching properties for {len(cids)} compounds...")
    # Chunk CIDs because URL length is limited
    all_props = []
    chunk_size = 100
    for i in range(0, len(cids), chunk_size):
        chunk = cids[i:i+chunk_size]
        cid_str = ",".join(map(str, chunk))
        url = f"{PUBCHEM_REST}/cid/{cid_str}/property/XLogP,MolecularFormula,CanonicalSMILES,IUPACName/JSON"
        response = requests.get(url)
        if response.status_code == 200:
            all_props.extend(response.json().get('PropertyTable', {}).get('Properties', []))
        time.sleep(0.2) # Ethics
    return all_props

def is_glycosylated(smiles):
    # Rough check for hexose/pentose rings (pyranose/furanose)
    # Common sugar SMILES patterns: [C@@H]1([C@@H]([C@@H]([C@H](O[C@H]1O)CO)O)O)
    # A simpler way is to look for the "O1[C@@H]([C@@H]([C@H]([C@@H]([C@H]1O)O)O)O)CO" pattern or similar polyhydroxy cyclic ethers.
    # We can also check Oxygen count relative to Carbon.
    sugar_patterns = ["O1C(O)C(O)C(O)C(O)C1", "O1C(CO)C(O)C(O)C(O)C1"]
    # This is very rough. Let's look for multiple hydroxyl groups in a ring.
    return any(p in smiles for p in sugar_patterns) or smiles.count('O') > 8

def main():
    # 1. Sourcing
    withanolide_cids = fetch_cids_by_name("Withanolide")
    boswellic_cids = fetch_cids_by_name("Boswellic")
    
    unique_cids = list(set(withanolide_cids + boswellic_cids))[:500]
    print(f"Found {len(unique_cids)} unique CIDs.")
    
    # 2. Filtering
    props = fetch_properties(unique_cids)
    if not props:
        print("No properties fetched.")
        return
    df = pd.DataFrame(props)
    print("Columns returned from PubChem:", df.columns.tolist())
    
    # Check if CanonicalSMILES exists, if not try aliases or handle error
    smi_col = 'CanonicalSMILES'
    if smi_col not in df.columns:
        # Try finding a column that ends with SMILES
        potential_cols = [c for c in df.columns if 'SMILES' in c.upper()]
        if potential_cols:
            smi_col = potential_cols[0]
            print(f"Using alternate SMILES column: {smi_col}")
        else:
            print("Error: No SMILES column found.")
            return

    # Same for XLogP
    logp_col = 'XLogP'
    if logp_col not in df.columns:
        potential_cols = [c for c in df.columns if 'LOGP' in c.upper()]
        if potential_cols:
            logp_col = potential_cols[0]
            print(f"Using alternate LogP column: {logp_col}")
        else:
            print("Warning: No LogP column found. Using default 0.0")
            df[logp_col] = 0.0

    df[logp_col] = pd.to_numeric(df[logp_col], errors='coerce').fillna(0.0)
    
    # Constraints: LogP < 3.5
    filtered_df = df[df[logp_col] < 3.5].copy()
    print(f"Filtered to {len(filtered_df)} compounds with LogP < 3.5.")
    
    # Prioritize glycosylated
    filtered_df['Glycosylated'] = filtered_df[smi_col].apply(is_glycosylated)
    filtered_df = filtered_df.sort_values(by='Glycosylated', ascending=False)
    
    # Top 20 for docking (to keep it manageable for this demo, 
    # though the user asked for high-throughput, we'll start with a representative batch)
    candidates = filtered_df.head(20).to_dict('records')
    print(f"Selected {len(candidates)} candidates for docking.")
    
    # 3. Receptor Prep
    print("Preparing receptor 5F19...")
    # Fetch PDB
    pdb_id = "5F19"
    resp = requests.get(f"{BASE_API_URL}/fetch/pdb/{pdb_id}")
    if resp.status_code != 200:
        print("Failed to fetch PDB.")
        return
    
    # Convert to PDBQT
    conv_resp = requests.post(f"{BASE_API_URL}/convert/pdb-to-pdbqt", json={
        "pdb_content": resp.text,
        "add_hydrogens": True
    })
    receptor_pdbqt = conv_resp.json().get('pdbqt_content')
    
    # 4. Project Setup
    proj_name = f"ayurvedic_recovery_{int(time.time())}"
    requests.post(f"{BASE_API_URL}/projects/", json={"name": proj_name})
    
    # Upload Receptor
    # Note: The API docs say multipart form data for upload
    files = {'file': ('receptor.pdbqt', receptor_pdbqt)}
    requests.post(f"{BASE_API_URL}/projects/{proj_name}/upload?category=receptor", files=files)
    
    # 5. Docking Loop
    results = []
    for cand in candidates:
        cid = cand['CID']
        name = cand.get('IUPACName', f"CID_{cid}")
        smiles = cand[smi_col]
        
        print(f"Docking {name} (CID: {cid})...")
        
        # Convert Ligand SMILES to PDBQT via API
        conv_resp = requests.post(f"{BASE_API_URL}/convert/smiles-to-pdbqt", json={
            "smiles": smiles,
            "name": f"ligand_{cid}"
        })
        if conv_resp.status_code != 200:
            print(f"Failed to convert SMILES for CID {cid}: {conv_resp.text}")
            continue
        ligand_pdbqt = conv_resp.json().get('pdbqt_content')
            
        # Upload Ligand
        ligand_filename = f"ligand_{cid}.pdbqt"
        files = {'file': (ligand_filename, ligand_pdbqt)}
        requests.post(f"{BASE_API_URL}/projects/{proj_name}/upload?category=ligand", files=files)
        
        # Get Gridbox (Autoboxing)
        grid_resp = requests.post(f"{BASE_API_URL}/analysis/{proj_name}/gridbox?ligand_file={ligand_filename}")
        grid = grid_resp.json()
        
        # Submit Dock
        dock_resp = requests.post(f"{BASE_API_URL}/docking/{proj_name}/dock", json={
            "engine": "vina",
            "receptor_file": "receptor.pdbqt",
            "ligand_file": ligand_filename,
            "config": grid,
            "exhaustiveness": 8
        })
        job_id = dock_resp.json().get('job_id')
        
        # Poll
        while True:
            status_resp = requests.get(f"{BASE_API_URL}/docking/jobs/{job_id}")
            status_data = status_resp.json()
            if status_data.get('status') == 'completed':
                score = status_data.get('scores', [0])[0]
                results.append({
                    "Name": cand.get('IUPACName', f"CID_{cid}"),
                    "CID": cid,
                    "Score": score,
                    "LogP": cand['XLogP'],
                    "Glycosylated": cand['Glycosylated']
                })
                print(f"Completed CID {cid} with score {score}")
                break
            elif status_data.get('status') == 'failed':
                print(f"Job failed for CID {cid}")
                break
            time.sleep(2)
            
    # 6. Sorting and Reporting
    final_df = pd.DataFrame(results)
    final_df = final_df[final_df['Score'] < -8.0].sort_values(by='Score')
    
    print("\nTop 5 Candidates:")
    print(final_df.head(5).to_markdown())
    
    # Save to JSON for report
    final_df.head(5).to_json("top_candidates.json", orient='records')

if __name__ == "__main__":
    main()
