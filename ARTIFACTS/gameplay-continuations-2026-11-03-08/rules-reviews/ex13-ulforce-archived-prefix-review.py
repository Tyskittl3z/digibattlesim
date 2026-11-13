"""Archived-source replay of the saved103-command prefix; no stop retry/new play."""
import gzip,hashlib,json,shutil,sys,tarfile,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SEGMENT="ARTIFACTS/gameplay-continuations-2026-11-03-07"
RECORD=SEGMENT+"/game-0000-segment.json.gz"
ARCHIVE=SEGMENT+"/source-checkpoint.tar.gz"
MANIFEST=SEGMENT+"/source-manifest.json"
record=json.loads(gzip.decompress((ROOT/RECORD).read_bytes()))
manifest=json.loads((ROOT/MANIFEST).read_text())
with tempfile.TemporaryDirectory(prefix="digibattle-ex13-archived-prefix-") as directory:
    archived=Path(directory)
    with tarfile.open(ROOT/ARCHIVE) as tar:
        names=tar.getnames()
        assert all(n.startswith("SOURCE/") and ".." not in Path(n).parts for n in names)
        tar.extractall(archived,filter="data")
    for child in ROOT.iterdir():
        if child.name not in ("SOURCE","ARTIFACTS","RULES"):(archived/child.name).symlink_to(child,target_is_directory=child.is_dir())
    context_relative=record["replay_provenance"]["context_file"]
    context_path=archived/context_relative
    context_path.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/context_relative,context_path)
    shutil.copytree(ROOT/"RULES/matchups/123129-vs-124303",archived/"RULES/matchups/123129-vs-124303")
    archive_hashes={str(p.relative_to(archived)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((archived/"SOURCE").glob("*.py"))}
    assert all(manifest["source_sha256"][k]==v for k,v in archive_hashes.items())
    sys.path.insert(0,str(archived/"SOURCE"))
    import imported_attempts as ia
    from context_runtime import ContextRuntime
    from selected_mechanics import build_selected_registry
    from match_context import canonical,digest
    context,_,_=ia._load_context_selection(archived,record["replay_provenance"]["context_file"],
        expected_context=(record["context_id"],record["replay_provenance"]["context_file_sha256"]))
    rt=ContextRuntime(context,record["seed"],record["first"],build_selected_registry(context,archived),allow_experimental=True)
    assert canonical(ia._physical_snapshot(rt.snapshot()))==canonical(ia._physical_snapshot(record["initial"]))
    rows=[]
    for n,c in enumerate(record["commands"][:-1],1):
        assert c["status"]=="EXPERIMENTAL_RESOLVED",n
        assert canonical(ia._comparable_public_view(rt.public_view(c["seat"])))==canonical(ia._comparable_public_view(c["public_view"])),n
        result=ia._apply(rt,c["command"],c["seat"],c["args"],archived)
        assert canonical(result)==canonical(c["result"]),n
        rt.verify()
        snap=rt.snapshot()
        rows.append({"command_number":n,"public_view_match":True,"result_match":True,
            "physical_integrity_valid":True,"state_sha256":digest(snap["state"]),"rng_sha256":digest(snap["rng_state"])})
    assert len(rows)==103
    final=rt.snapshot()
    assert canonical(ia._physical_snapshot(final))==canonical(ia._physical_snapshot(record["final"]))
    assert canonical(ia._physical_snapshot(final))==canonical(ia._physical_snapshot(record["halts"][-1]["before"]))
    s=final["state"]
    assert (s["turn"],s["active"],s["phase"],s["memory"])==(8,"B","UNSUSPEND",2)
    assert len(s["pending"])==1 and s["pending"][0]["id"]=="effect-33"
    assert s["pending"][0]["trigger"]["paid_source"]=="B:EX13-069#4"
    assert s["zones"]["B"]["deck"][-1]=="B:P-138#1"
    assert s["battle"]["A"]["A:BT12-029#2"]["cards"]==["A:BT12-029#2"]
    assert len(s["battle"]["A"]["A:BT11-032#1"]["cards"])==2
    assert all(not stack["suspended"] for key,stack in s["battle"]["B"].items()
               if context.card("B",key.split(":",1)[1].split("#",1)[0]).kind=="Digimon")
    proof={"schema":"archived-source-read-only-saved-prefix-proof-v1","date":"2026-11-03",
        "status":"EXACT_SAVED_PREFIX_MATCH","certification":"NONE_SOFTWARE_PREFIX_PROOF_ONLY",
        "seed":record["seed"],"context_id":record["context_id"],"source_segment":SEGMENT,
        "record":RECORD,"record_sha256":hashlib.sha256((ROOT/RECORD).read_bytes()).hexdigest(),
        "archive":ARCHIVE,"archive_sha256":hashlib.sha256((ROOT/ARCHIVE).read_bytes()).hexdigest(),
        "archive_manifest":MANIFEST,"archive_manifest_sha256":hashlib.sha256((ROOT/MANIFEST).read_bytes()).hexdigest(),
        "archived_source_all_hashes_match_manifest":True,"archived_source_python_files":len(archive_hashes),
        "successful_commands_replayed":len(rows),"all_saved_public_views_match":True,"all_saved_results_match":True,
        "physical_integrity_valid_after_every_command":True,"cards_conserved":{"A":54,"B":54,"total":108},
        "exact_saved_final_physical_state_and_rng":True,"exact_before_halt_physical_state_and_rng":True,
        "comparison_note":"_physical_snapshot ignores execution_id and normalizes legacy resolving_option None; all state/RNG fields compared",
        "final_physical_snapshot_sha256":digest(ia._physical_snapshot(final)),
        "final_state_sha256":digest(final["state"]),"final_rng_sha256":digest(final["rng_state"]),
        "upcoming_evolution_draw_top_card":"B:P-138#1",
        "pending_stop":{"turn":8,"phase":"UNSUSPEND","active":"B","memory":2,
            "pending_id":"effect-33","effect_id":"EX13-069.unsuspend_evolve","paid_rina":"B:EX13-069#4"},
        "stop_command104_executed":False,"new_gameplay_executed":False,"source_files_edited":[],
        "full_match_credit":0,"accepted_fact_finding_credit":0,"final_evaluation_credit":0,
        "intermediate_hidden_state_note":"Public views/results saved per command; hidden intermediate state reconstructed, exact full final state/RNG compared",
        "per_command":rows,"archived_source_sha256":archive_hashes}
    (OUT/"ex13-ulforce-archived-prefix-proof.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({k:proof[k] for k in ("status","successful_commands_replayed","archived_source_all_hashes_match_manifest","exact_saved_final_physical_state_and_rng","stop_command104_executed","source_files_edited")},indent=2))
