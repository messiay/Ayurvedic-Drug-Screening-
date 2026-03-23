import requests

def test_pubchem_pdb():
    cid = 5281703 # Withaferin A
    # Try fetching 3D PDB
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/record/SDF/?record_type=3d"
    resp = requests.get(url)
    if resp.status_code == 200:
        print("SDF 3D found.")
        # print(resp.text[:200])
    else:
        print(f"SDF 3D NOT found. Status: {resp.status_code}")

    url_pdb = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/record/PDB/?record_type=3d"
    resp_pdb = requests.get(url_pdb)
    if resp_pdb.status_code == 200:
        print("PDB 3D found.")
    else:
        print(f"PDB 3D NOT found. Status: {resp_pdb.status_code}")

if __name__ == "__main__":
    test_pubchem_pdb()
