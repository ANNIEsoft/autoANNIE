# autoANNIE

autoANNIE runs ANNIE processing on the Fermilab grid (jobsub_lite):
- EventBuilding (EB, mode 1): RAWData -> ProcessedData
- BeamCluster (BC, mode 2): ProcessedData -> BeamCluster ROOT trees
- Repo: github.com/ANNIEsoft/autoANNIE. Run from a clone in /pnfs/annie/scratch/users/<user>/autoANNIE/.

## 1. Layout
```
master_script.py             user settings at top; EB and BC main loops
lib/helper_script.py         get_runs_from_user, get_run_type, is_there_raw, read_SQL (DLS), trig_overlap, beamfetcher,
                             missing_scratch, missing_after_transfer (R<run>_summary.txt), my_jobs, my_jobs_BC, wait,
                             BC_breakup, check_root_scratch, check_root_pro, which_ones_to_resub_BC, LAPPD_pedestal,
                             clearScratch, ifdh_rm, jobs_gone, log_error
lib/automated_submission.py  EB: split a run into jobs, write scripts, submit; branch missing=='n' (initial) / 'y' (resub)
lib/submit_jobs.py           writes grid scripts: EB submit_grid_job / grid_job / run_container_job;
                             BC submit_BC / grid_BC / container_BC
lib/monitor_jobs.py          memory/disk monitor (thread in master_script, or standalone)
lib/copy_grid_output.sh      EB scratch -> persistent (ProcessedData, LAPPDTree, offsetFitResult); skips existing files
lib/merge_it.sh              runs lib/mergeBeamTrees.C in singularity, mv result to BeamCluster/
BeamCluster/BC_copy.sh       merged BC / LAPPDBeamCluster + FilteredAllLAPPDData / FilteredMRDData -> persistent
lib/run_trig.sh, lib/run_beamfetcher.sh   PreProcessTrigOverlap / BeamFetcherV2, run locally from app_path before EB
lib/ifdh.sh                  wrapper: setup ifdhc; exec ifdh
scripts/                     check_run_status.py, copy_runs.py, missing_scratch.py, is_transferred.sh,
                             manual_merge_and_transfer_BC.sh, tarball_create_script.py
```

## 2. Paths
- Local ToolAnalysis: `/exp/annie/app/users/<user>/<TA_folder>` (runs TrigOverlap/BeamFetcher; same tree is tarred for the grid).
- Raw: `/pnfs/annie/persistent/raw/raw/<run>/RAWDataR<run>S0p<N>`
- Scratch output: EB `/pnfs/annie/scratch/users/<user>/output/<run>/`, BC `output/beamcluster/<run>/`
- Persistent (`/pnfs/annie/persistent/processed/`): `processed_EBV2/R<run>/`, `BeamClusterTrees/`, `BeamClusterTrees/LAPPDBeamClusterTrees/`, `LAPPD_EB_output/{LAPPDTree,offsetFit}/R<run>/`, `processed_EBV2_LAPPDFiltered/`, `processed_EBV2_MRDFiltered/`, `trigoverlap/`, `BeamFetcherV2/`, `LAPPD_Pedestals_corrected/<folder>.tar.gz`
- Runs must be in `ANNIE_SQL_RUNS.txt` (made from the DAQ run DB, see README).

## 3. How EventBuilding works
- Run types: beam, beam_39 (LAPPD PPS 1), cosmic, AmBe, LED, laser. 
- MRD daylight-saving flag: `read_SQL` takes run start/stop times from `ANNIE_SQL_RUNS.txt` and compares them with DST dates hardcoded in `helper_script.py` (up to 2027).
- TrigOverlap and BeamFetcher files are made locally first if missing.
- Each job: 3 part files (beam) or 1 (others), plus 2 overlap files that are dropped after. A job returns outputs only if all its parts were processed; otherwise only logs.
- `hs.my_jobs()` runs jobsub_q (15 s wait) and a run counts as finished when it has no Idle/Running jobs. HELD jobs are NOT counted, so they don't block the loop; remove them. 
- Missing parts (`missing_scratch`) are resubmitted with step 1, at most 2 times; then `copy_grid_output.sh` transfers and `missing_after_transfer` writes `R<run>_summary.txt` (missing part list, % processed) into persistent.

## 4. How BeamCluster works
- Works on persistent `ProcessedData` in chunks of `BC_job_size` (40) files. 
- Container: BeamClusterAnalysis -> `.ntuple.root`; for beam also LAPPDProcessedFilter -> FilteredAllLAPPDData / FilteredMRDData, then BeamClusterAnalysis on the filtered file -> `.lappd.root`. 
- Pedestal tarball from `hs.LAPPD_pedestal(run)`; `PedinputfileTXT` set in LAPPDProcessedAna/Configs.
- Merge: `lib/mergeBeamTrees.C` (run by `merge_it.sh`) joins the chunk files with a fast clone (seconds) and renumbers eventNumber 0..N-1. Same for BeamCluster and LAPPDBeamCluster.
- The merged file goes to `BeamCluster/`, then `BC_copy.sh` copies it to persistent. Delete an old merged file before re-merging (dCache won't overwrite).

## 5. Memory/disk monitor (lib/monitor_jobs.py)
- query(user): one jobsub_q call for all your jobs (None if it fails). Per job, in MB:
  - mem = ResidentSetSize_RAW (fallback MemoryUsage), mem_alloc = RequestMemory
  - disk = DiskUsage_RAW, disk_alloc = RequestDisk, held = JobStatus 5
- job_name(): names jobs from their arguments
  - BC: BC_R<run>_p<a>-<b>, EB: EB_R<run>_p<a>-<b>, run key = plain run number
  - DQ: DQ_R<run>, run key = DQ_<run>; anything else: unknown
  - BC/EB must keep the plain run number, or save_run(run) finds nothing.
- Monitor(user, outdir, interval):
  - check(): every interval, prints jobs that are HELD or >= 90%, and keeps each job's peak.
  - save_run(run): writes <outdir>/<run>/MemDisk_R<run>.summary once (time range, one line per job peak/allocated, MAX line). Earlier sessions are kept.
  - stop(): runs at the end or on Ctrl-C; writes any runs not yet saved (skips unknown and DQ_*), prints the max table and memory/disk histograms.
- master_script: starts the monitor (EB after the first submission, BC before its loop), calls save_run before each transfer/merge, and stop() at the end.
- Standalone: python3 lib/monitor_jobs.py [user] -> RUNNING and HELD tables.
- Notes: values in MB (1 GB = 1024 MB); disk is current usage, the monitor keeps the max; a run row can pair memory and disk from different jobs; it sees all your jobs, not just this session's.

## 6. Resources (target 70-80% peak; verify values in code)
| | EB | BC |
|---|---|---|
| Per job | 3+2 part files (resub 1+2) | 40 processed files |
| Memory | 6000 MB + 2000 grace (submit_jobs.py) | 2000 MB + 2000 grace (submit_BC) |
| Disk | automated_submission.py, both blocks: 7.5 + 0.5*(step+2) -> 10 GB (3+2), 9 GB (1+2); AmBe 13 + 0.75*(step+2) | master_script: 12 + 0.2*BC_job_size -> 20 GB |
| Lifetime | 6 h | 12 h |
| Peak memory | ~3-4.9 GB (50-81%) | ~0.5 GB (25%, 2 GB kept as a safe minimum) |
| Peak disk | ~7-8 GB (70-80%) | Need to optimize |
- Grace/auto-release covers memory only, not disk.
- Allocation = peak / target. EB disk is set in both automated_submission.py blocks; update the master_script usage text and README if they quote numbers.
- EB memory blow-ups to ~9-10 GB are data problems (unmatched PMT data), not a reason to raise memory.
- Planned: mv instead of ifdh cp for inputs in grid_job (RAWData) and grid_BC (ProcessedData), then lower disk.
- OFFSITE is the default; ONSITE for small batches or when OFFSITE is slow or evicting.

## 7. Safety changes
- dCache (/pnfs) can't append or overwrite: remove the file first, then write. Copies to persistent use plain cp (ifdh gave 401 there).
- Before each transfer, hs.jobs_gone() waits 3 min and checks the queue again; if jobs reappeared, the transfer is postponed (jobsub_q can miss fresh jobs).
- Summary errors are logged to autoANNIE/logs/errors.log (cleared each session) instead of crashing.
- The tarball excludes .git (1.7 -> 0.6 GB). Re-tar after any ToolAnalysis change.

## 8. Diagnosing
- Hold reason: jobsub_q -G annie --jobid <id> -af HoldReason
- Exact usage: -af DiskUsage_RAW RequestDisk MemoryUsage (KB, KB, MB). Don't use plain DiskUsage (rounded up).
- Finished job: condor_history -name <jobsubNN.fnal.gov> <id> -af DiskUsage_RAW RequestDisk MemoryUsage
- Restarted job: -af NumJobStarts
- Remove all held: jobsub_rm -G annie --constraint 'JobStatus==5 && Owner=="<user>"'
- Before transfer, check part sizes: ls -l output/<run>/ | sort -k9 -V (beam parts ~130-230 MB; a few MB = bad part).

## 9. Known issues
- EB sometimes crashes at the end of a job; resubmission usually fixes it.
- BC: a run that reaches max resubmissions is counted again on every loop pass, so with 2+ runs the script can end early (other runs not merged/transferred) or never end.
  After a BC session, check every run has BeamCluster_<run>.root in persistent; merge by hand if not.
- dCache maintenance (often Wednesdays) breaks transfers: wait and retry.
- Don't run two master scripts on the same runs.

## 10. Before a big submission
1. One master script, in tmux, with output logged to a file outside /pnfs.
2. Re-tar ToolAnalysis if anything changed; check the runs are in ANNIE_SQL_RUNS.txt.
3. Remove old held jobs and old merged files in BeamCluster/.
4. Test one run after any change.
