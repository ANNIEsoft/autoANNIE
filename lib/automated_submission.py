import sys, os
import submit_jobs as sj     # other py script for generating the job submission scripts

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

user = sys.argv[1]                                            # annie username
run = sys.argv[2]                                             # run number to be processed
missing = sys.argv[3]                                         # re-run of missing files
step_size = int(sys.argv[4])                                  # how many part files per job
DLS = sys.argv[5]                                             # daylight Savings? (for the MRD)
TA_tar_name = sys.argv[6]                                     # name of toolanalysis tar-ball
name_TA = sys.argv[7]                                         # name of the TA directory (within tar-ball)
input_path = sys.argv[8]                                      # path to your grid input location (submit_job_grid.sh, run_container_job.sh, grid_job.sh and necessary submission files)
output_path = sys.argv[9]                                     # grid output location
raw_path = sys.argv[10]                                       # path to rawdata
trig_path = sys.argv[11]                                      # path to trig overlap tar balls
beamfetcher_path = sys.argv[12]                               # path to beamfetcher files
node_loc = sys.argv[13]                                       # OFFSITE or ONSITE (FermiGrid) nodes
run_type = sys.argv[14]                                       # run type (beam, AmBe, cosmic, LED, or laser)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

if run_type == 'beam' or run_type == 'beam_39':
        basename = "ProcessedData_PMTMRDLAPPD_R"
        indy = 34    # used to "hack" off the part file number below (in missing_files.append line)
elif run_type == 'AmBe' or run_type == 'LED':
    basename = 'ProcessedData_PMT_R'
    indy = 26
elif run_type == 'laser':
    basename = 'ProcessedData_PMTLAPPD_R'
    indy = 31
elif run_type == 'cosmic':
    basename = 'ProcessedData_PMTMRD_R'
    indy = 29

# sort and find the highest numbered part file from that run (need for breaking up the jobs)
all_files = os.listdir(raw_path + run + '/')
all_files.sort(key=lambda file: int(file.split('p')[-1]))
last_file = all_files[-1]
final_part = int(last_file.split('p')[-1])

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# normal event building (initial submission, not a re-run of missing files)

if missing == 'n':

    first_part = int(0)
    last_part = final_part

    # We need to break the batch into seperate jobs. Unless the batch size is evenly divisible by
    # the step size, the last job will be smaller than the other ones.

    part_list = [[], []]     # [0] = first,  [1] = final
    for i in range(first_part, last_part + 1, step_size):
            
        if i != 0:
            part_list[0].append(i-1)
        else:
            part_list[0].append(i)
        if (i+step_size) > last_part:
            if last_part < final_part:
                part_list[1].append(last_part+1)
            else:
                part_list[1].append(final_part)
        else:
            part_list[1].append(i + step_size)


    # calculate disk space requirements
    import math
    if run_type == 'beam' or run_type == 'beam_39':
        disk_space = str(math.ceil(7.5 + .5*(step_size+2)))     # 3+2 -> 10 GB (~70% peak)
    elif run_type == 'AmBe':
        disk_space = str(math.ceil(13 + .75*(step_size+2)))     # works out to around 15 GB for 2+2
    else:
        disk_space = str(math.ceil(7.5 + .5*(step_size+2)))     # Same as beam runs
    #disk_space = str(10)     # typically fine as a default for jobs with less than ~8 part files or so

    # Submit the entire batch through multiple jobs, based on the user input (above)

    first = False; final = False
    n_jobs = len(part_list[0])

    os.system('rm grid_job_' + run + '*.sh'); os.system('rm run_container_job_' + run + '*.sh'); os.system('rm submit_grid_job_' + run + '*.sh')
    for i in range(len(part_list[0])):     # loop over number of jobs

        if i == 0:               # first job
            first = True
            sh_name = 'submit_grid_job_' + run + '_first.sh'
        elif i == (n_jobs - 1):  # final job
            final = True
            sh_name = 'submit_grid_job_' + run + '_final.sh'
        else:
            sh_name = 'submit_grid_job_' + run + '.sh'
            os.system('rm grid_job_' + run + '.sh'); os.system('rm run_container_job_' + run + '.sh'); os.system('rm submit_grid_job_' + run + '.sh')

        if n_jobs == 1:    # handle weird cases of small runs with potentially only one job
            first = True; final = True
            sh_name = 'submit_grid_job_' + run + '.sh'
        
        # create the run_container_job and grid_job scripts
        sj.grid_job(run, user, TA_tar_name, name_TA, first, final, run_type)
        sj.run_container_job(run, name_TA, DLS, first, final, run_type)

        # We can then create the job_submit script that will send our job (with files) to the grid
        sj.submit_grid_job(run, part_list[0][i], part_list[1][i], input_path, output_path, TA_tar_name, disk_space, raw_path, trig_path, beamfetcher_path, first, final, node_loc, run_type)

        # Lastly, we can execute the job submission script and send the job to the grid
        os.system('sh ' + sh_name)
        print('\n# # # # # # # # # # # # # # # # # # # # #')
        print('Run ' + run + ' p' + str(part_list[0][i]) + '-' + str(part_list[1][i]) + ' sent')
        print('# # # # # # # # # # # # # # # # # # # # #\n')

        first = False; final = False



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# re-submit jobs that failed (resub step size set to 1)

if missing == 'y':
    
    # same as running find_missing_files.py
    run_number = run

    raw_data_dir = raw_path + run_number + "/"
    processed_dir = output_path + run_number + "/"

    print('\nFinding missing files in ' + str(processed_dir))

    raw_files = [file for file in os.listdir(raw_data_dir) if file.startswith("RAWDataR" + run_number)]
    processed_files = [file for file in os.listdir(processed_dir) if file.startswith(basename + run_number) and not file.endswith(".data")]
    num_raw_files = len(raw_files)
    num_processed_files = len(processed_files)

    # Find the missing processed files
    missing_files = []
    for file in raw_files:
        expected_processed_file = basename + file[8:]  # Remove "RAWDataR" prefix
        if expected_processed_file not in processed_files:
            missing_files.append(int(expected_processed_file[indy:]))

    missing_files.sort()   # put in numerical order

    print("\nNumber of raw files: ", num_raw_files)
    print("Number of processed files: ", num_processed_files)
    print("Number of missing files: ", num_raw_files-num_processed_files)
    print("Missing processed files: ", missing_files)

    print('\nResubmission step size: ' + str(step_size) + '\n')

    first_part = min(missing_files)
    last_part = max(missing_files)

    part_list = [[], []]     # [0] = first,  [1] = final
    for i in range(len(missing_files)):
            
        if missing_files[i] != 0:
            part_list[0].append(missing_files[i]-1)
        else:
            part_list[0].append(missing_files[i])
        if (missing_files[i]+step_size) > last_part:
            if last_part < final_part:
                part_list[1].append(last_part+1)
            else:
                part_list[1].append(final_part)
        else:
            part_list[1].append(missing_files[i] + step_size)


    # calculate disk space requirements
    import math
    if run_type == 'beam' or run_type == 'beam_39':
        disk_space = str(math.ceil(7.5 + .5*(step_size+2)))     # 1+2 -> 9 GB (resubmissions)
    elif run_type == 'AmBe':
        disk_space = str(math.ceil(13 + .75*(step_size+2)))     # works out to around 15 GB for 2+2
    else:
        disk_space = str(math.ceil(7.5 + .5*(step_size+2)))     # Same as beam runs    
    #disk_space = str(10)     # typically fine as a default - good for Laser single part submissions

    # Submit the entire batch through multiple jobs, based on the user input (above)

    first = False; final = False
    n_jobs = len(part_list[0])

    os.system('rm grid_job_' + run + '*.sh'); os.system('rm run_container_job_' + run + '*.sh'); os.system('rm submit_grid_job_' + run + '*.sh')
    for i in range(len(part_list[0])):     # loop over number of jobs

        if i == 0 and part_list[0][i] == 0:      # p0 and first job
            first = True
            sh_name = 'submit_grid_job_' + run + '_first.sh'
        elif (part_list[0][i]+1) == final_part:  # final part of the run
            final = True
            sh_name = 'submit_grid_job_' + run + '_final.sh'
        else:
            sh_name = 'submit_grid_job_' + run + '.sh'
            os.system('rm grid_job_' + run + '.sh'); os.system('rm run_container_job_' + run + '.sh'); os.system('rm submit_grid_job_' + run + '.sh')
        
        # create the run_container_job and grid_job scripts
        sj.grid_job(run, user, TA_tar_name, name_TA, first, final, run_type)
        sj.run_container_job(run, name_TA, DLS, first, final, run_type)

        # We can then create the job_submit script that will send our job (with files) to the grid
        sj.submit_grid_job(run, part_list[0][i], part_list[1][i], input_path, output_path, TA_tar_name, disk_space, raw_path, trig_path, beamfetcher_path, first, final, node_loc, run_type)

        # Lastly, we can execute the job submission script and send the job to the grid
        os.system('sh ' + sh_name)
        print('\n# # # # # # # # # # # # # # # # # # # # #')
        print('Run ' + run + ' p' + str(part_list[0][i]) + '-' + str(part_list[1][i]) + ' sent')
        print('# # # # # # # # # # # # # # # # # # # # #\n')

        first = False; final = False 


print('\nJobs successfully submitted!\n')
