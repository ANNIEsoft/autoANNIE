# master script for automated event building runs and running the BeamClusterAnalysis toolchain to create root files containing ANNIEEvent information

# Author: Steven Doran
# Date: December 2024

import os
import glob
import time
import subprocess
from lib import helper_script as hs
from lib import submit_jobs as sj

#
#
#
#
#

'''@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''

''' Please modify the following to reflect your working directory '''

user = '<username>'

# bind mounted path for entering your container
singularity = '-B/pnfs:/pnfs,/exp/annie/app/users/' + user + '/temp_directory:/tmp,/exp/annie/data:/exp/annie/data,/exp/annie/app:/exp/annie/app'

TA_folder = 'EventBuilding/'                      # Folder that was tar-balled (Needs to be the same name as the ToolAnalysis directory in /exp/annie/app that will run TrigOverlap + BeamFetcherV2 toolchains)
TA_tar_name = 'MyToolAnalysis_grid.tar.gz'        # name of tar-ball

grid_sub_dir = 'autoANNIE/'                       # input grid
grid_output = 'output/'                           # output grid

SQL_file = 'ANNIE_SQL_RUNS.txt'                   # SQL filename

initial_submission_only = False                   # run PreProcess, BeamFetcher, submit the initial jobs and quit

clear_scratch = False                             # will prompt the user with the option to delete run folders (Processed + BeamCluster) in your scratch output (useful if re-processing runs)

'''@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'''

#
#
#
#
#

# constructed paths based on user customization and current areas of data

app_path = '/exp/annie/app/users/' + user + '/' + TA_folder                                        # working TA folder

scratch_path = '/pnfs/annie/scratch/users/' + user + '/' + grid_sub_dir                            # clone autoANNIE repository/set of grid scripts
output_path = '/pnfs/annie/scratch/users/' + user + '/' + grid_output                              # general output directory (event building jobs will be outputted directly here)
BC_scratch_output_path = output_path + 'beamcluster/'                                              # output from the BeamCluster jobs (embedded in folder above)
raw_path = '/pnfs/annie/persistent/raw/raw/'                                                       # raw data location, transferred from the DAQ
processed_path = '/pnfs/annie/persistent/processed/'                                               # general directory for "processed" data, such as BeamFetcher files, ProcessedData, etc...

data_path = processed_path + 'processed_EBV2/'                                                     # Processed Data
trig_path = '/pnfs/annie/persistent/processed/trigoverlap/'                                        # trigger overlap tar files
beamcluster_path = processed_path + 'BeamClusterTrees/'                                            # BeamCluster root files
beamfetcher_path = processed_path + 'BeamFetcherV2/'                                               # BeamFetcherV2 root files
lappd_EB_path = processed_path + 'LAPPD_EB_output/'                                                # contains two subdirectories: LAPPDTree and offsetFit
lappd_BC_path = beamcluster_path + 'LAPPDBeamClusterTrees/'                                        # filtered events w/ LAPPDs stored in root files
lappd_filter_path = processed_path + 'processed_EBV2_LAPPDFiltered/'                               # filtered, processed data w/ LAPPD events
mrd_filter_path = processed_path + 'processed_EBV2_MRDFiltered/'                                   # same, for the MRD
lappd_pedestal_path = '/pnfs/annie/persistent/processed/processingData_EBV2/LAPPD_Pedestal/'       # Pedestal files for the LAPPDs in the BeamCluster jobs


# # # # # # # # # # # # # # # # # # # # # # # # # # 
print('\n\n**********************************************************\n')
user_confirm = input('The current user is set to ' + user + ', is this correct? (y/n):      ')
if user_confirm == 'n':
    user = input('\nPlease enter the correct user name:      ')
    print('\nUser has been set to ' + user + ', locking in changes...')
    time.sleep(3)
elif user_confirm != 'y' and user_confirm != 'n':
    print('\nInvalid response - please restart script\n')
    exit()
print('\n')

which_mode = input("Event building mode (type '1') or BeamClusterAnalysis mode (type '2'):     ")
if which_mode != '1' and which_mode != '2':
    print('\nInvalid response - please restart script\n')
    exit()
print('\n')


usage_verbose = """
#########################################################################################
# ******* Event Building mode ********
# args: --step_size --runs_to_run --node_loc --source_type

# step_size   = number of part files per job for event building (recommendations below)
#                - beam/cosmic:    2+2
#                - AmBe/laser/LED: 1+2
# runs_to_run = runs you would like to event build. It will ask you to enter one at a time
# node_loc    = run OFFSITE or ONSITE (FermiGrid) jobs
# source_type = run type ("beam", "cosmic", "AmBe", "LED", "laser", "beam_39")

# Grid job specifications:
# -- lifetime: 6hr
# -- memory: 4GB
# -- disk: varies depending on number of part files, but typically between 5 and 10GB
#########################################################################################
"""

usage_verbose_BC = """
#########################################################################################
# ******* BeamCluster mode ********
# args: --runs_to_run --node_loc --source_type

# runs_to_run = runs you would like to run the BC toolchain over. It will ask you to enter one at a time
# node_loc    = run OFFSITE or ONSITE (FermiGrid) jobs
# source_type = run type ("beam", "cosmic", "AmBe", "LED", "laser")

# Grid job specifications:
# -- lifetime: 12hr
# -- memory: 2GB
# -- disk: 10GB for BC (baseline, plus more depending on number of part files)
#########################################################################################
"""

# make ifdh script executable for transfers from dCache
subprocess.run(["chmod", "+x", "lib/ifdh.sh"], check=True)

if which_mode == '1':      # Event building mode

    print(usage_verbose, '\n')

    run_type = hs.get_run_type()     # will return 'beam', 'AmBe', etc...

    # user provided arguments
    step_size = int(input('Please specify the job part file size:     '))
    resub_step_size = 1    # not provided by user - manually set for resubmissions
    which_node = int(input('\nOFFSITE (1) or ONSITE (2)  (OFFSITE is recommended):     '))
    if which_node == 1:
        node_loc = 'OFFSITE'
    elif which_node == 2:
        node_loc = 'ONSITE'
    else:
        print('\nWRONG INPUT, RE-RUN SCRIPT\n')
        exit()

    print('\n')
    runs_to_run_user = hs.get_runs_from_user()

    print('\nVetting the runs you submitted...')
    runs_to_run = []; DLS = []    # final lists to be used in event building

    # First, make sure there is RawData available for the runs the user selected
    raw_available_runs = hs.is_there_raw(runs_to_run_user, raw_path)

    # Secondly, grab DLS info from the SQL txt file
    dls_vals = hs.read_SQL(SQL_file, raw_available_runs)
    for i in range(len(raw_available_runs)):
        if dls_vals[i] != -9999:     # -9999 = runs that occured during DLS transition and were passed to the master script to be removed - this condition could probably be removed for certain source runs: TODO
            runs_to_run.append(runs_to_run_user[i])
            DLS.append(str(dls_vals[i]))


    # will clear scratch output run directories if specified by the user
    if clear_scratch:
        print('\n')
        which_one = 'Processed'    # EventBuilding
        confirm_delete = input('Would you like to delete any previous Processed output directories for the runs provided? (y/n):      ')
        if confirm_delete == 'n':
            print('\nWill not clear scratch, proceeding...')
        elif confirm_delete == 'y':
            print('\n')
            hs.clearScratch(runs_to_run, output_path, BC_scratch_output_path, which_one)
        elif user_confirm != 'y' and user_confirm != 'n':
            print('\nInvalid response - please restart script\n')
            exit()

    
    time.sleep(1)
    
    # -------------------------------------------------------------
    print('\n\n')
    print('*************************************************')
    print('        Automated EventBuilding initiated        ')
    print('*************************************************\n')
    
    print('The following arguments have been provided:\n')
    print('  - Job part file size:  ' + str(step_size))
    print('  - Job re-submission part file size:  ' + str(resub_step_size))
    print('  - Runs to run: ', runs_to_run)
    print('  - node location: ', node_loc)
    print('  - run type: ', run_type)
    print('\n')
    time.sleep(3)
    print('Locking arguments in...')
    for i in range(5):
        print(str(5-i) + '...')
        time.sleep(1)
    print('\n\nProceeding with event building...')
    time.sleep(3)
    
    # Part 1 - Initial job submission
    
    length_of_runs = []
    for i in range(len(runs_to_run)):
        list_parts = os.listdir(raw_path + runs_to_run[i] + '/')
        list_parts.sort(key=lambda file: int(file.split('p')[-1]))
        last_file = list_parts[-1]
        final_part = int(last_file.split('p')[-1])
        length_of_runs.append(final_part + 1)
    
    print('\nAvailable runs:\n', runs_to_run)
    time.sleep(3)
    
    # ---------------------------------------
    # Trigger Overlap
    print('\n\n---------------------------')
    print('Moving onto PreProcess...\n')
    time.sleep(1)
    
    # Produce trig overlap files if they havent yet been created
    for run in runs_to_run:
        hs.trig_overlap(run, trig_path, app_path, scratch_path, singularity)
    
    # ---------------------------------------
    
    # BeamFetcher
    print('\n\n---------------------------')
    print('Moving onto BeamFetcher...\n')
    time.sleep(1)

    if run_type == 'beam' or run_type == 'beam_39':
        for run in runs_to_run:
            hs.beamfetcher(run, app_path, scratch_path, singularity, beamfetcher_path)
    else:
        print('Beam run type not selected - skipping BeamFetcherV2 root file creation...\n')
    
    # ---------------------------------------
    
    
    # Now that we have the trigoverlap files + beamfetcher file produced, we can send the initial grid jobs
    print('\n***************************************************************')
    print('Submitting initial set of jobs to the grid with step size = ' + str(step_size) + '...\n')
    time.sleep(1)
    for i in range(len(runs_to_run)):
        if length_of_runs[i] < step_size:
            small_step = length_of_runs[i]
        else:
            small_step = step_size
    
        # omit the runs that have some part files in /scratch
        exists_and_contains = os.path.exists(output_path + runs_to_run[i] + "/") and any(file.startswith('Processed') and not file.endswith(".data") for file in os.listdir(output_path + runs_to_run[i] + "/"))
        if exists_and_contains == False:
            os.system('python3 lib/automated_submission.py ' + user + ' ' + runs_to_run[i] + ' n ' + str(small_step) + ' ' + DLS[i] + ' ' + TA_tar_name + ' ' + TA_folder + ' ' + scratch_path + ' ' + output_path + ' ' + raw_path + ' ' + trig_path + ' ' + beamfetcher_path + ' ' + node_loc + ' ' + run_type)   # no re-run
            time.sleep(3)
        else:
            print('\n' + runs_to_run[i] + ' processed files present in /scratch, not submitting this run in first batch...\n')
    
    print('\nAll initial jobs submitted\n')
    time.sleep(1)

    if initial_submission_only == True:     # only submit the initial jobs, then quit (no re-submission)
        print('\n***Initial submission only*** mode complete... my work here is done!\n')
        print('\nExiting...\n')
        exit()
    
    # display active jobs
    os.system('\njobsub_q -G annie --user ' + user + '\n')
    time.sleep(1)
    
    
    # -------------------------------------------------------------
    # Part 2 - Resubmission
    
    resubs = [0 for i in range(len(runs_to_run))]
    complete = 0
    
    print('\n***********************************************************\n')
    
    while complete != len(resubs):
    
        # check jobs
        active_jobs, which_runs, check = hs.my_jobs(runs_to_run, user)
    
        check_count = 0
        for i in range(len(check)):
    
            if check[i] == True and resubs[i] < 2:
                reprocess = hs.missing_scratch(runs_to_run[i], raw_path, output_path, run_type)
                time.sleep(1)
                if reprocess == True:   # if there are missing files in scratch, re-submit
                    os.system('python3 lib/automated_submission.py ' + user + ' ' + runs_to_run[i] + ' y ' + str(resub_step_size) + ' ' + DLS[i] + ' ' + TA_tar_name + ' ' + TA_folder + ' ' + scratch_path + ' ' + output_path + ' ' + raw_path + ' ' + trig_path + ' ' + beamfetcher_path + ' ' + node_loc + ' ' + run_type)
                    resubs[i] += 1
                else:                   # if there aren't any missing files, transfer
                    if resubs[i] != -1:
                        print('\n\nRun ' + runs_to_run[i] + ' is done! It was resubmitted ' + str(resubs[i]) + ' times. Initiating transfer...\n')
                        os.system('sh lib/copy_grid_output.sh ' + runs_to_run[i] + ' ' + data_path + ' ' + output_path + ' ' + lappd_EB_path + ' ' + run_type)
                        time.sleep(1)
                        hs.missing_after_transfer(runs_to_run[i], raw_path, data_path, run_type)
                        complete += 1; resubs[i] = -1
                    else:
                        print('\nRun ' + runs_to_run[i] + ' already transferred\n')
                        check_count += 1
    
            elif check[i] == True and resubs[i] == 2:    # no more jobs, but already re-submitted twice
                print('\nMax re-submissions reached for run ' + runs_to_run[i] + '! Initiating transfer...\n')
                os.system('sh lib/copy_grid_output.sh ' + runs_to_run[i] + ' ' + data_path + ' ' + output_path + ' ' + lappd_EB_path + ' ' + run_type)
                time.sleep(1)
                hs.missing_after_transfer(runs_to_run[i], raw_path, data_path, run_type)
                complete += 1; resubs[i] = -1
    
            
            else:   # still running
                check_count += 1     # how many jobs are still active
    
    
        # if all jobs are still active, wait and return to start (dont submit any BC jobs)
        if check_count == len(check):
            hs.wait(5)     # wait 5 minutes


    # ---------------------------------------
    # Finish and clean up

    time.sleep(1)
    print('\nNo jobs left! All runs', runs_to_run, 'completed!')
    print('\nCleaning up...\n')   # remove leftover files produced

    for pattern in (
        "grid_job*.sh",
        "run_container_job*.sh",
        "submit_grid_job*.sh",
        "beam.list",
        "trig.list",
    ):
        for filename in glob.glob(pattern):
            subprocess.run(["./lib/ifdh.sh", "rm", filename], check=True)

    time.sleep(1)
    print('\nExiting...\n')
    



if which_mode == '2':        # BeamCluster

    BC_job_size = 50         # how many part files per job  (500 is the recommended max)

    print(usage_verbose_BC, '\n')

    print('\n*** Please ensure the run type is the same for all runs you plan on submitting ***\n')
    run_type = hs.get_run_type()     # will return 'beam', 'AmBe', etc...

    which_node = int(input('OFFSITE (1) or ONSITE (2)  (OFFSITE is recommended):     '))
    if which_node == 1:
        node_loc = 'OFFSITE'
    elif which_node == 2:
        node_loc = 'ONSITE'
    else:
        print('\nWRONG INPUT, RE-RUN SCRIPT\n')
        exit()
    print('\n')
    runs_to_run = hs.get_runs_from_user()


    # will clear scratch output run directories if specified by the user
    if clear_scratch:
        print('\n')
        which_one = 'BC'    # BeamCluster
        confirm_delete = input('Would you like to delete any previous beamcluster output directories for the runs provided? (y/n):      ')
        if confirm_delete == 'n':
            print('\nWill not clear scratch, proceeding...')
        elif confirm_delete == 'y':
            print('\n')
            hs.clearScratch(runs_to_run, output_path, BC_scratch_output_path, which_one)
        elif user_confirm != 'y' and user_confirm != 'n':
            print('\nInvalid response - please restart script\n')
            exit()


    print('\n\n\n')
    print('*************************************************')
    print('          BeamClusterAnalysis initiated          ')
    print('*************************************************\n')
    
    print('The following argument has been provided:\n')
    print('  - Runs to run: ', runs_to_run)
    print('  - job size: ', BC_job_size)
    print('  - node location: ', node_loc)
    print('  - run type: ', run_type)
    print('\n')
    time.sleep(3)
    print('Locking arguments in...')
    for i in range(5):
        print(str(5-i) + '...')
        time.sleep(1)
    print('\n\nProceeding with BeamClusterAnalysis...')
    time.sleep(3)

    # clear any leftovers
    os.system('rm BeamCluster/submit_grid_job.sh')
    os.system('rm BeamCluster/grid_job.sh')
    os.system('rm BeamCluster/run_container_job.sh')
    os.system('rm BeamCluster/BeamCluster*.root')
    os.system('rm BeamCluster/LAPPDBeamCluster*.root')
    time.sleep(1)

    BC_resubs = [0 for i in range(len(runs_to_run))]
    complete_BC = 0      # when this value == number of runs, the while loop will complete

    # create job submission scripts  (since these scripts take args, we don't need to keep creating them for every job)
    sj.submit_BC(scratch_path, BC_scratch_output_path, TA_tar_name, data_path, node_loc, lappd_pedestal_path)
    sj.grid_BC(user, TA_tar_name, TA_folder, scratch_path, run_type)
    sj.container_BC(TA_folder, scratch_path, run_type)
    time.sleep(1)

    while complete_BC != len(BC_resubs):

        BC_active_jobs, BC_which_runs, BC_check = hs.my_jobs_BC(runs_to_run, user)
    
        check_count_BC = 0
        for i in range(len(BC_check)):
    
            # breaks the part files into N part sections
            parts_i, parts_f = hs.BC_breakup(runs_to_run[i], data_path, BC_job_size, run_type)
            n_jobs = len(parts_i)

            # Disk space for BeamCluster jobs --> feel free to increase this if needed
            disk_space_factor = str(int(((BC_job_size*8)/1000) + 8))
            
            # initial submission
            if BC_check[i] == True and BC_resubs[i] == 0:
                
                # check if all root files are present
                present = hs.check_root_scratch(runs_to_run[i],n_jobs,BC_scratch_output_path)
                present_pro = hs.check_root_pro(runs_to_run[i],beamcluster_path)
    
                # Couple of scenarios:
    
                # 1. root file is present in processed - if this is the case we are done with this run
                if present_pro == True:
                    print('\nRun ' + runs_to_run[i] + ' already present in /persistent --> skipping job submission and this run will not be transfered...\n')
                    BC_resubs[i] = -1
                    complete_BC += 1
    
                # 2. root file is not present in either processed or scratch, indicating it has never been produced.
                #    if this is the case, submit the initial job
                elif present == False and present_pro == False:
                    print('\nSubmitting BeamCluster job for Run ' + runs_to_run[i] + '...\n')

                    # grab the correct lappd pedestal folder
                    ped_folder = hs.LAPPD_pedestal(runs_to_run[i])
    
                    for j in range(n_jobs):
                        os.system('sh BeamCluster/submit_grid_job.sh ' + runs_to_run[i] + ' ' + parts_i[j] + ' ' + parts_f[j] + ' ' + disk_space_factor + ' ' + ped_folder)
                        time.sleep(1)
    
                    BC_resubs[i] += 1
                
                # 3. All root files are present in /scratch but not in /persistent
                elif present_pro == False and present == True:         
                    print('\nall .root file(s) found in /scratch output for Run ' + runs_to_run[i] + ', skipping job submission\n')
                    BC_resubs[i] = -1


                # 4. There are some root files present in scratch/ (none in persistent)
                elif present_pro == False and present == 'INCOMPLETE':

                    # grab the correct lappd pedestal folder
                    ped_folder = hs.LAPPD_pedestal(runs_to_run[i])

                    missing_chunks = hs.which_ones_to_resub_BC(runs_to_run[i],BC_scratch_output_path,parts_i,parts_f)

                    print('\nRun ' + runs_to_run[i] + ' is INCOMPLETE:')
                    for j in range(len(missing_chunks)):
                        print('  - BeamCluster_' + runs_to_run[i] + '_' + missing_chunks[j][0] + '_' + missing_chunks[j][1] + ' missing!')
                        os.system('sh BeamCluster/submit_grid_job.sh ' + runs_to_run[i] + ' ' + missing_chunks[j][0] + ' ' + missing_chunks[j][1] + ' ' + disk_space_factor + ' ' + ped_folder)
                        time.sleep(1)

                    BC_resubs[i] += 1

    
            # no active jobs but re-submitted (get 1 resubmission)
            elif BC_check[i] == True and BC_resubs[i] == 1:
                
                present = hs.check_root_scratch(runs_to_run[i],n_jobs,BC_scratch_output_path)
    
                # if none are present, resubmit all of them
                if present == False:
                    print('\nRe-submitting BeamCluster job for Run ' + runs_to_run[i] + '...\n')
                    ped_folder = hs.LAPPD_pedestal(runs_to_run[i])
                    time.sleep(1)
                    for j in range(n_jobs):
                        os.system('sh BeamCluster/submit_grid_job.sh ' + runs_to_run[i] + ' ' + parts_i[j] + ' ' + parts_f[j] + ' ' + disk_space_factor + ' ' + ped_folder)
                        time.sleep(1)
                    BC_resubs[i] += 1

                # all root files present and complete
                elif present == True:
                    print('\nBC job complete for Run ' + runs_to_run[i] + '\n')
                    BC_resubs[i] = -1

                # partial completion
                elif present == 'INCOMPLETE':
                    print('\nBC job INCOMPLETE for Run ' + runs_to_run[i])
                    ped_folder = hs.LAPPD_pedestal(runs_to_run[i])
                    missing_chunks = hs.which_ones_to_resub_BC(runs_to_run[i],BC_scratch_output_path,parts_i,parts_f)
                    for j in range(len(missing_chunks)):
                        print('  - BeamCluster_' + runs_to_run[i] + '_' + missing_chunks[j][0] + '_' + missing_chunks[j][1] + ' missing!')
                        os.system('sh BeamCluster/submit_grid_job.sh ' + runs_to_run[i] + ' ' + missing_chunks[j][0] + ' ' + missing_chunks[j][1] + ' ' + disk_space_factor + ' ' + ped_folder)
                        time.sleep(1)
                    BC_resubs[i] += 1
     
    
            elif BC_check[i] == True and BC_resubs[i] == 2:    # no more jobs, but already re-submitted twice
                print('\nMax re-submissions reached for run ' + runs_to_run[i] + ' for BC jobs! Will not transfer to /persistent\n')
                complete_BC += 1
    
            
            # actually complete, transfer
            elif BC_resubs[i] == -1:
                present = hs.check_root_pro(runs_to_run[i],beamcluster_path)
                if present == False:
    
                    # first merge the BeamCluster files into one
                    print('\nMerging BeamCluster files...\n')
                    os.system('sh lib/merge_it.sh ' + singularity + ' ' + BC_scratch_output_path + ' ' + runs_to_run[i] + ' ' + 'BC')
                    time.sleep(1)

                    # any LAPPD-related files will only be created for beam runs. We dont need LAPPD root files or filtered files for laser runs. We can just use the normal BC output.
                    if run_type == 'beam' or run_type == 'beam_39':
                        # Second, merge the LAPPDBeamCluster files into one
                        print('\nMerging LAPPDBeamCluster files...\n')
                        os.system('sh lib/merge_it.sh ' + singularity + ' ' + BC_scratch_output_path + ' ' + runs_to_run[i] + ' ' + 'LAPPD')
                        time.sleep(1)
    
                    # Then copy all the output files
                    
                    # BeamCluster
                    print('\nTransferring BeamCluster files...\n')
                    os.system('sh BeamCluster/BC_copy.sh ' + runs_to_run[i] + ' ' + beamcluster_path + ' ' + scratch_path + ' ' + 'BC' + ' ' + lappd_BC_path + ' ' + BC_scratch_output_path + ' ' + lappd_filter_path + ' ' + mrd_filter_path)
                    check_count_BC += 1
                    complete_BC += 1
                    time.sleep(1)

                    if run_type == 'beam' or run_type == 'beam_39':
                        # LAPPDBeamCluster
                        os.system('sh BeamCluster/BC_copy.sh ' + runs_to_run[i] + ' ' + beamcluster_path + ' ' + scratch_path + ' ' + 'LAPPD' + ' ' + lappd_BC_path + ' ' + BC_scratch_output_path + ' ' + lappd_filter_path + ' ' + mrd_filter_path)
                        time.sleep(1)
                    
                        # Filtered files (LAPPD + MRD)
                        print('\nTransferring Filtered datasets (MRD + LAPPD)...\n')
                        os.system('sh BeamCluster/BC_copy.sh ' + runs_to_run[i] + ' ' + beamcluster_path + ' ' + scratch_path + ' ' + 'LAPPD_filter' + ' ' + lappd_BC_path + ' ' + BC_scratch_output_path + ' ' + lappd_filter_path + ' ' + mrd_filter_path)
                        time.sleep(1)
                        os.system('sh BeamCluster/BC_copy.sh ' + runs_to_run[i] + ' ' + beamcluster_path + ' ' + scratch_path + ' ' + 'MRD_filter' + ' ' + lappd_BC_path + ' ' + BC_scratch_output_path + ' ' + lappd_filter_path + ' ' + mrd_filter_path)
                        time.sleep(1)
                    
                else:
                    print('\nRun ' + runs_to_run[i] + ' already transferred\n')
                    check_count_BC += 1
    
    
            else:   # still running
                check_count_BC += 1     # how many jobs are still active
    
    
        if check_count_BC == len(BC_check):
            hs.wait(5)     # wait 5 minutes


    print('\nNo jobs left! All runs', runs_to_run, 'completed!')
    print('\nCleaning up...\n')   # remove leftover files produced

    for pattern in (
        "BeamCluster/submit_grid_job.sh",
        "BeamCluster/grid_job.sh",
        "BeamCluster/run_container_job.sh",
        "BeamCluster/BeamCluster*.root",
        "BeamCluster/LAPPDBeamCluster*.root",
    ):
        for filename in glob.glob(pattern):
            subprocess.run(["./lib/ifdh.sh", "rm", filename], check=True)

    time.sleep(1)
    print('\nExiting...\n')
