import requests
import time
import json
import pandas as pd
import os

# API configuration (Provided by VI-DOCK)
BASE_API_URL = os.getenv("DOCKING_API_URL", "https://isa-papua-sharing-favor.trycloudflare.com")
PUBCHEM_REST = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"

def fetch_cids_by_name(name):
    print(f"Searching PubChem for {name} derivatives...")
    url = f"{PUBCHEM_REST}/name/{name}/cids/JSON?name_type=word"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json().get('IdentifierList', {}).get('CID', [])
    except Exception as e:
        print(f"Error fetching CIDs for {name}: {e}")
    return []

def fetch_properties(cids):
    print(f"Fetching properties for {len(cids)} compounds...")
    all_props = []
    chunk_size = 50
    for i in range(0, len(cids), chunk_size):
        chunk = cids[i:i+chunk_size]
        cid_str = ",".join(map(str, chunk))
        url = f"{PUBCHEM_REST}/cid/{cid_str}/property/XLogP,MolecularFormula,CanonicalSMILES,ConnectivitySMILES,IUPACName/JSON"
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                all_props.extend(response.json().get('PropertyTable', {}).get('Properties', []))
            time.sleep(0.5)
        except Exception as e:
            print(f"Error fetching properties chunk: {e}")
    return all_props

def is_glycosylated(smiles):
    if not smiles or not isinstance(smiles, str): return False
    # Sugar patterns or high oxygen count
    sugar_patterns = ["O1C(O)C(O)C(O)C(O)C1", "O1C(CO)C(O)C(O)C(O)C1", "O[C@H]1[C@H](O)"]
    return any(p in smiles for p in sugar_patterns) or smiles.count('O') > 7

def generate_hypothesis(name, score, logp, glycosylated):
    if glycosylated:
        return f"High aqueous solubility due to glycosylation enhances bioavailability in liquid formulations while maintaining strong COX-2 binding ({score} kcal/mol)."
    return f"Optimized LogP ({logp}) balances membrane permeability and water solubility, making it ideal for rapid post-exercise absorption."

def main():
    # 1. Sourcing
    w_cids = fetch_cids_by_name("Withanolide")
    b_cids = fetch_cids_by_name("Boswellic")
    unique_cids = list(set(w_cids + b_cids))[:500]
    print(f"Found {len(unique_cids)} candidates in sourcing.")

    # 2. Properties & Filtering
    props = fetch_properties(unique_cids)
    if not props: return
    df = pd.DataFrame(props)
    smi_col = 'CanonicalSMILES' if 'CanonicalSMILES' in df.columns else 'ConnectivitySMILES'
    logp_col = 'XLogP' if 'XLogP' in df.columns else [c for c in df.columns if 'LOGP' in c.upper()][0]
    df[logp_col] = pd.to_numeric(df[logp_col], errors='coerce').fillna(4.0)
    
    filtered_df = df[df[logp_col] < 3.5].copy()
    filtered_df['Glycosylated'] = filtered_df[smi_col].apply(is_glycosylated)
    filtered_df = filtered_df.sort_values(by='Glycosylated', ascending=False)
    candidates = filtered_df.head(15).to_dict('records')
    print(f"Prioritized {len(candidates)} high-solubility candidates for sequential docking.")

    # 3. Receptor & Project Setup
    proj_name = f"HT_Sequential_{int(time.time())}"
    print(f"Starting project: {proj_name}")
    try:
        rec_fetch = requests.get(f"{BASE_API_URL}/fetch/pdb/5F19").json()
        rec_pdbqt = requests.post(f"{BASE_API_URL}/convert/pdb-to-pdbqt", json={"pdb_content": rec_fetch['pdb_content']}).json()['pdbqt_content']
        
        requests.post(f"{BASE_API_URL}/projects/", json={"name": proj_name})
        requests.post(f"{BASE_API_URL}/projects/{proj_name}/upload?category=receptor", files={'file': ('receptor.pdbqt', rec_pdbqt)})
    except Exception as e:
        print(f"Setup failed: {e}")
        return

    # 4. Docking Loop
    results = []
    for cand in candidates:
        try:
            cid = cand['CID']
            smi = cand[smi_col]
            print(f"--> Processing CID {cid}...")
            
            # SMILES to PDBQT
            conv = requests.post(f"{BASE_API_URL}/convert/smiles-to-pdbqt", json={"smiles": smi, "name": f"mol_{cid}"}).json()
            lig_pdbqt = conv['pdbqt_content']
            
            lig_file = f"lig_{cid}.pdbqt"
            requests.post(f"{BASE_API_URL}/projects/{proj_name}/upload?category=ligand", files={'file': (lig_file, lig_pdbqt)})
            
            # Grid & Dock
            job = requests.post(f"{BASE_API_URL}/docking/{proj_name}/dock", json={
                "engine": "vina",
                "receptor_file": "receptor.pdbqt",
                "ligand_file": lig_file,
                "config": {
                    "center_x": 25.6, "center_y": 54.9, "center_z": 38.9,
                    "size_x": 20, "size_y": 20, "size_z": 20
                },
                "exhaustiveness": 8
            }).json()
            
            job_id = job['job_id']
            # Poll
            for _ in range(60): 
                status = requests.get(f"{BASE_API_URL}/docking/jobs/{job_id}").json()
                if status['status'] == 'completed':
                    result_data = status.get('result', {})
                    if 'scores' in result_data and result_data['scores']:
                        score = result_data['scores'][0]['Affinity (kcal/mol)']
                        results.append({
                            "Compound Name": cand.get('IUPACName', f"Withanolide Deriv. {cid}"),
                            "PubChem CID": cid,
                            "Binding Score (kcal/mol)": score,
                            "LogP": cand[logp_col],
                            "Glycosylated": cand['Glycosylated']
                        })
                        print(f"    Done: {score} kcal/mol")
                    else:
                        print(f"    Warning: No scores found in result for CID {cid}")
                    break
                elif status['status'] == 'failed':
                    print(f"    Failed: {status.get('error')}")
                    break
                time.sleep(5)
        except Exception as e:
            print(f"    Error docking CID {cid}: {e}")

    if not results:
        print("No docking results collected.")
        return

    # 5. Reporting
    final_df = pd.DataFrame(results)
    final_df = final_df.sort_values(by='Binding Score (kcal/mol)')
    top_5 = final_df.head(5).copy()
    top_5['Hypothesis'] = top_5.apply(lambda x: generate_hypothesis(x['Compound Name'], x['Binding Score (kcal/mol)'], x['LogP'], x['Glycosylated']), axis=1)
    
    report_cols = ["Compound Name", "PubChem CID", "Binding Score (kcal/mol)", "Hypothesis"]
    report_md = top_5[report_cols].to_markdown(index=False)
    
    with open("final_docking_report.md", "w") as f:
        f.write("# Final High-Throughput Docking Screen Results\n\n")
        f.write(report_md)
    
    print("\n--- SCREEN COMPLETE ---")
    print(report_md)

if __name__ == "__main__":
    main()
