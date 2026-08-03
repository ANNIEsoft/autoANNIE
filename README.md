# autoANNIE

Scripts to Event build and create ANNIEEvent root files on the grid.

-----------------------

### Contents:

- `master_script.py` is the primary tool for running the event building proceedure (and creating the BeamClusterAnalysis ntuples).

```
autoANNIE/
├── master_script.py               # runs and executes the event building, data processing, and transferring
├── lib/                           # folder containing helper scripts
│   ├── helper_script.py
│   ├── automated_submission.py
│   ├── submit_jobs.py
│   ├── run_trig.sh
│   ├── run_beamfetcher.sh
│   ├── merge_it.sh
│   ├── ifdh.sh
│   ├── mergeBeamTrees.C
│   └── copy_grid_output.sh
├── BeamCluster/                   # staging area for grid submission scripts that are separate from the event building scripts
├── scripts/                       # standalone scripts for various tasks
│   ├── check_run_status.py        #      - output a snapshot of which runs have yet to be processed
│   ├── tarball_create_script.py   #      - tar-balls toolanalysis for grid submission
│   ├── copy_runs.py               #      - copy multiple runs from scratch to persistent, outside of the normal EventBuilding scripts
│   ├── missing_scratch.py         #      - checks how many part files are processed (in scratch)
│   ├── manual_merge_and_transfer_BC.sh # - can be used to manually merge BC files and transfer them (+ filtered files) to persistent/
│   └── is_transferred.sh          #      - checks filesize of last RAWData part files; used to make sure run is fully transferred from the DAQ
└── README.md                      
```


### Usage:

1. After cloning a copy of this repo to your user directory in ```/pnfs/annie/scratch/users/<username>/```, make sure you have the latest copy of ToolAnalysis built in ```/exp/annie/app/users/<username>/```. The scripts will first run pre processing toolchains using this directory before submitting grid jobs, so it is recommended to keep this directory present and up to date and use it exclusively for the event building procedure. 
2. The MRD subsystem records data in CDT (and is therefore daylight savings (DLS) dependent). To ensure we enable the correct DLS configuration in the `MRDDataDecoder` tool for the event building toolchain, we must first fetch and generate an SQL txt file from the DAQ's database. Create this txt file locally (based on the following instructions from Marvin: https://cdcvs.fnal.gov/redmine/projects/annie_experiment/wiki/DAQ's_DB_in_the_gpvm): 
   - From your local computer, open a terminal and establish an SSH tunneling:
     - `ssh -K -L 5433:192.168.163.21:5432 annie@annie-gw01.fnal.gov`
   - Run the sql command in another local terminal to get the DB and save it to a .txt file:
     - `echo "Select * from run order by id desc" | psql annie -h localhost -p 5433 -d rundb > ANNIE_SQL_RUNS.txt`
   - Copy it from your local computer to your scratch area:
     - ```scp ANNIE_SQL_RUNS.txt <username>@anniegpvm02.fnal.gov:/pnfs/annie/scratch/users/<username>/<repo_name>/.```
3. Tar your ToolAnalysis directory via: ```tar -czvf <tarball_name>.tar.gz -C /<path_to_user_directory> <ToolAnalysis_folder>```. Running ```python3 scripts/tarball_create_script.py``` will create the tarball for you and copy it to your `scratch` area (modify path and folder names within the script accordingly). If you tar-balled the directory manually, copy it to your scratch user directory (```/pnfs/annie/scratch/users/<username>/<repo_name>/```).
5. Edit ```master_script.py``` to reflect your username, the bind mounted folders you are using when entering the singularity container, the name of the ANNIE SQL txt file you generated, and other paths.
6. Run the the master script: ```python3 master_script.py``` and specify which mode you want to use: (1) for EventBuilder, (2) for BeamClusterAnalysis jobs, and provide the necessary user inputs when prompted.


#### scripts/ usage

* `python3 scripts/check_run_status.py`
* `python3 scripts/copy_runs.py`
* `python3 scripts/missing_scratch.py`
* `python3 scripts/tarball_create_script.py`
* `sh scripts/is_transferred.sh`
* 'sh scripts/manual_merge_and_transfer_BC.sh`

-----------------------

### Additional information

- The following scripts require modification of paths within their headers (modifying your username or the name of the ToolAnalysis directory, for example):
   * `master_script.py`
   * `scripts/copy_runs.py`
   * `scripts/check_run_status.py`
   * `scripts/missing_scratch.py`
   * `scripts/tarball_create_script.py`
   * `scripts/manual_merge_and_transfer_BC.sh`

- For the event building, the local copy of ToolAnalysis in ```/exp/annie/app/users/<username>/``` will be used to run the ```PreProcessTrigOverlap``` and ```BeamFetcherV2``` toolchains to create the necessary files prior to submitting grid jobs. This is why it is recommended to have an "event building" ToolAnalysis folder present in your `/exp/annie/app/` area.

- Given that the `MRDDataDecoder` tool is DLS-dependent, in `lib/helper_script.py` there are [DLS timestamps](https://github.com/S81D/autoANNIE/blob/8472dfb76716f23dbe6f929e2b8119fc0e6667bc/lib/helper_script.py#L95C5-L103C6) that are hardcoded. I have included the dates through 2026 - if event building is used beyond 2026, please add the 2027 dates for DLS.

- There are two options to submit runs: manaully (enter run by run) or through a list. For mass re-production of data, it is easier to populate a list named ```runs.list``` with the associated run numbers. If you elect to use the list, make sure there is a ```runs.list``` present in the working ```scratch``` directory.

- Similarily, for `scripts/copy_runs.py` you must populate a `runs.list` file containing all runs you wish to transfer from scratch to persistent.

- There is a configuration variable in `master_script.py` (`initial_submission_only`) that when set to `True`, will only submit the initial jobs (no further checking, transferring, or re-submissions). The script will exit after the initial submissions.

- No additional modifications of the ToolAnalysis directory is needed prior to tar-balling. The scripts will handle DLS, input filename modifications, LAPPD pedestal files, etc... (assuming you are using the latest event building version).

- Both the ```BeamClusterAnalysis``` and ```EventBuilding``` features of this script will submit the same tar-ball of ToolAnalysis.

- `scripts/is_transferred.sh` will display the final few RAWData part files for a given run. It takes time for the runs to be transferred from the DAQ to the gpvms. If a run is fully transferred, the final part file should be smaller than the average (~50% or so). Checking the timestamp of transfer vs when the run is complete is also a good indication; we don't want to event build a run that is only partially transferred. Usage: `python3 scripts/is_transferred.sh`

- An event building guide using ToolAnalysis can be found here: https://cdcvs.fnal.gov/redmine/projects/annie_experiment/wiki/Event_Building_with_ToolAnalysis

- A guide for grid submissions can be found here: https://cdcvs.fnal.gov/redmine/projects/annie_experiment/wiki/General_guideline_for_running_ANNIE_Singularity_Containers_on_Grid

- Running event building jobs now works on the FNAL-only nodes. More testing is needed to work out additional bugs. For now (October 2024), it is recommended to continue to run the jobs OFFSITE.

- The default LAPPD PPS for beam runs (34) was 10, before run 5140. After this run, this was changed to PPS 5. The scripts have a condition where this is hardcoded, but something to keep in mind if the PPS is changing more frequently in the future.

- Job resources have not been fully optimized. General recommendations are embedded in the code. Memory and wall time are given in `submit_jobs.py`. Disk space is estimated in `automated_submission.py`. Feel free to test and change these as needed.

-----------------------

To check on your jobs, use: ```jobsub_q -G annie --user <<username>>```

To cancel job submissions, use: ```jobsub_rm -G annie <<username>>```

To check why jobs are held, use: ```jobsub_q --hold -G annie <<username>>```
