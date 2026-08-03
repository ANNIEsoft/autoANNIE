import os
import time
import pytz
import shutil
import subprocess
from datetime import datetime

# --------------------------------------------------------------- #
# Some helpful functions to call for the automated event building #


# Delete a file through ifdh (a path that is already gone is not an error)
def ifdh_rm(path):

    result = subprocess.run(["./lib/ifdh.sh", "rm", path], capture_output=True, text=True)
    if result.returncode != 0:
        output = result.stdout + result.stderr
        if 'MISSING' not in output and 'No such file' not in output:
            raise RuntimeError('ifdh rm ' + path + ' failed:\n' + output)

    return


# Ask user for runs you would like to include
def get_runs_from_user():

    runs = []
    which_option = input("Read from a list (runs.list) or enter the runs manually?\nType '1' for the list, type '2' for manual submission:   ")

    if which_option == '1':
        try:
            with open('runs.list', 'r') as file:
                for line in file:
                    run = line.strip()
                    if run:  # Ensure the line is not empty
                        runs.append(run)
            print("Runs added from runs.list")
        except FileNotFoundError:
            print("\nError: 'runs.list' file not found. Please create the list file and re-run the script.\n")
            exit()
    
    elif which_option == '2':
        print("Enter the runs you want to include. Type 'done' when you are finished.")
        while True:
            user_input = input("Enter run number: ")
            if user_input.lower() == 'done':
                break
            runs.append(user_input)

    else:
        print("\nError: please type '1' or '2'! Exiting...\n")
        exit()

    return runs


# ask the user for a run type
def get_run_type():
    run_type_list = ['beam', 'cosmic', 'AmBe', 'LED', 'laser', 'beam_39']
    print('Please select a run type from the list below:   (1, 2, 3, 4, or 5)  ')
    runtype_verbose = """
    - beam (1)
    - cosmic (2)
    - AmBe (3)
    - LED (4)
    - laser (5)
    - beam LAPPD PPS 1 (6)
    """
    print(runtype_verbose)
    run_type = int(input('->   '))
    if run_type not in [1,2,3,4,5,6]:
        print("\nWRONG INPUT! Please type '1', '2', '3', '4', '5', or '6' and RE-RUN SCRIPT\nExiting...\n")
        exit()
    else:
        print('\nYou have selected:', run_type_list[run_type-1], '(', run_type, ')\n')
        if run_type == 6:
            print('Setting LAPPD PPS ratio from the default (10) to 1\n')
        time.sleep(1)
        return run_type_list[run_type-1]


# Check if there isn't RawData for any of the runs and omit that run from the list
def is_there_raw(runs_to_run_user, raw_path):
    temp_runs = []
    for i in range(len(runs_to_run_user)):
        if os.path.isdir(raw_path + runs_to_run_user[i] + '/'):
            temp_runs.append(runs_to_run_user[i])
        else:
            print('Run ' + runs_to_run_user[i] + ' does not have any RAWData!!! Removing from the list')
    return temp_runs


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Grab SQL, extract run information, and return DLS values accordingly for the MRDDataDecoder tool
def read_SQL(SQL_file, runs):
    
    run_data = {}
    dls_values = []

    # Check if the SQL file exists
    if not os.path.isfile(SQL_file):
        print(f"\nERROR: The SQL file '{SQL_file}' does not exist. Please follow the README and generate an SQL txt file for the event building.\nExiting...\n")
        exit()

    # Set timezone for Chicago (MRD)
    chicago_timezone = pytz.timezone('America/Chicago')

    # define daylight savings periods (THIS IS SO CONFUSING)
    ### Note: We have to upddate the dst_periods manually each year based on the Day Light Saving Time as per the Chicago Time Zone. ######
    dst_periods = {
        2021: (datetime(2021, 3, 14, 2, 0, 0), datetime(2021, 11, 7, 1, 0, 0)),
        2022: (datetime(2022, 3, 13, 2, 0, 0), datetime(2022, 11, 6, 1, 0, 0)),
        2023: (datetime(2023, 3, 12, 2, 0, 0), datetime(2023, 11, 5, 1, 0, 0)),
        2024: (datetime(2024, 3, 10, 2, 0, 0), datetime(2024, 11, 3, 1, 0, 0)),
        2025: (datetime(2025, 3, 9, 2, 0, 0), datetime(2025, 11, 2, 1, 0, 0)),
        2026: (datetime(2026, 3, 8, 2, 0, 0), datetime(2026, 11, 1, 1, 0, 0))
    }

    with open(SQL_file, 'r') as file:
        lines = file.readlines()[2:] 
        for line in lines:
            columns = [col.strip() for col in line.split('|')]
            if len(columns) > 1:
                runnum = columns[1]
                runconfig = columns[5]   # run type
                start = columns[3]       # UTC start time
                stop = columns[4]        # UTC stop time

                if runnum in runs:
                    # runs after 3869 have microsecond precision in their timestamps
                    try:
                        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S.%f")
                        stop_dt = datetime.strptime(stop, "%Y-%m-%d %H:%M:%S.%f") if stop else None
                    # for earlier runs, they are recorded to the nearest second
                    except ValueError:
                        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                        stop_dt = datetime.strptime(stop, "%Y-%m-%d %H:%M:%S") if stop else None
                    
                    # Remove fractional seconds by rounding to the nearest second to make them all the same
                    run_data[runnum] = {
                        'runconfig': int(runconfig) if runconfig.isdigit() else None,
                        'start': start_dt.replace(microsecond=0),
                        'stop': stop_dt.replace(microsecond=0) if stop_dt else None
                    }


    # if run isn't in SQL txt file, force the user to update it so we have the necessary DLS information
    missing_runs = [run for run in runs if run not in run_data]
    if missing_runs:
        print(f'ERROR: The following runs were not found in the SQL text file: {", ".join(missing_runs)}\n'
              f'Please add these runs to the .txt file and re-run the script.\nExiting...\n')
        exit()


    runconfigs = [data['runconfig'] for data in run_data.values() if data['runconfig'] is not None]
    unique_runconfigs = set(runconfigs)

    beam_run_types = {39, 34, 3, 45}
    
    # Check for consistent run configurations: we dont want to process beam runs with the same grid resources
    if len(unique_runconfigs) > 1:
        if not unique_runconfigs.issubset(beam_run_types):
            print(f'ERROR: The runs have inconsistent run types: {unique_runconfigs}\n'
                  f'Please ensure all runs are the same (except for beam runs: 39, 34, or 3)')
            proceed = input("\nWould you like to continue anyway? (yes/no): ")
            if proceed.lower() != 'yes':
                print("\nExiting...\n")
                return
            

    # convert to UTC to CDT and then check if its within a DLS period
    for run, config in run_data.items():
        
        start_cdt = config['start'].astimezone(chicago_timezone)
        stop_cdt = config['stop'].astimezone(chicago_timezone) if config['stop'] else None

        # Check if the timestamps are in daylight saving time
        year = start_cdt.year
        if year in dst_periods:
            dst_start, dst_stop = dst_periods[year]
            
            # Localize the DST start and stop times to the Chicago timezone
            dst_start = chicago_timezone.localize(dst_start)
            dst_stop = chicago_timezone.localize(dst_stop)

            # local start time in a DLS period (True or False)
            in_dls_start = dst_start <= start_cdt < dst_stop
            
            if stop_cdt:                      # for stop times that aren't blank
                in_dls_stop = dst_start <= stop_cdt < dst_stop     # local stop time in a DLS period  (True or False)
            else:
                in_dls_stop = in_dls_start    # if its blank, assign it the same as the start (may be problematic but it wont happen very often)


            # Update DLS status
            if in_dls_start:                                  # if start time is in DLS
                if in_dls_stop:                               #     if stop time is in DLS
                    dls_status = 1                            #          run was during DLS
                else:                                         #     if stop time wasn't in DLS (but start was)
                    dls_status = -9999                        #          run occured during a transition period

            else:                                             # if start time was not in DLS
                if in_dls_stop:                               #     if stop time is in DLS (but start wasn't)
                    dls_status = -9999                        #          run occured during a transition period
                else:                                         #     if stop time wasn't in DLS
                    dls_status = 0                            #          run was not during DLS


        # Add DLS status to run_data
        run_data[run]['DLS'] = dls_status

        # Prompt error if the run occured during a DLS period
        if dls_status == -9999:
            print('\n\n\n########################################################################')
            print(f"\nDANGER!!! {run}: Run occurred during Daylight Saving Time transition: start ({start_cdt}) and stop ({stop_cdt}) do not match.\n")
            
            choice = input("Type (1) to exit and re-run the script with an updated list. Type (2) to proceed and manually enter the DLS variable (risky!): ")
            
            if choice == '1':
                print("\nExiting the script. Please update the list and re-run.\n")
                exit()

            elif choice == '2':
                # Prompt user to enter the DLS variable
                dls_variable = input("\nPlease enter the DLS variable (1 for in DLS, 0 for out of DLS): ")
                
                # Validate the input for the DLS variable
                if dls_variable not in ['0', '1']:
                    print("\nInvalid input. Please enter 0 or 1.\n")
                    exit()

                # Assign the user-provided DLS variable
                run_data[run]['DLS'] = int(dls_variable)
                print(f"\nManually set DLS variable for run {run} to {dls_variable}. Proceeding...\n")

            elif choice == '3':
                # Keep the DLS variable as -9999, pass to master script for removal
                print(f"\nKeeping -9999 for {run} and passing to master script. Proceeding...\n")

            else:
                print("\nInvalid choice. Please enter either 1 or 2.\n")
                exit()
        

    # output run information
    print('\n')
    print(f"Run (type) DLS")
    print('------------------')
    for run in runs:  # Iterate over the original runs list
        config = run_data[run]
        if config['DLS'] != -9999:
            print(f"{run} ({config['runconfig']}) {config['DLS']}")
        else:
            print(f"{run} ({config['runconfig']}) {config['DLS']}  --> to be removed")
        dls_values.append(config['DLS'])  # Append the DLS value in order
    
    return dls_values

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    


# Produce trigoverlap files for event building
def trig_overlap(run, trig_path, app_path, scratch_path, singularity):

    ifdh_rm('trig.list')
    os.system('echo "' + run + '" >> trig.list')

    # does the run have an overlap tar file?
    exists = os.path.isfile(trig_path + 'R' + run + '_TrigOverlap.tar.gz')
    if exists == False:
        print('\nNo trigoverlap tar file found in /persistent for ' + run + ', producing trig overlap files now...\n')
        os.system('sh lib/run_trig.sh ' + app_path + ' ' + scratch_path + ' ' + trig_path + ' ' + singularity)
    else:
        print('Trigoverlap file present in /persistent for ' + run + ', moving on...\n')

    return


# produce beamfetcher part files
def beamfetcher(run, app_path, scratch_path, singularity, beamfetcher_path):

    ifdh_rm('beam.list')

    os.system('echo "' + run + '" >> beam.list')
    
    # does the run already have a beamfetcher file?
    exists = os.path.isfile(beamfetcher_path + 'beamfetcher_' + run + '.root')
    
    if exists == False:

        print('\nNo Beamfetcher file found in /persistent for ' + run + ', producing file now...\n')
        os.system('sh lib/run_beamfetcher.sh ' + app_path + ' ' + scratch_path + ' ' + beamfetcher_path + ' ' + singularity)

    else:
        print('BeamFetcher file present in /persistent for ' + run + ', moving on...\n')

    return


# check output location for missing processed files after job submissions (in /scratch)
def missing_scratch(run_number, raw_path, output_path, run_type):
    
    raw_data_dir = raw_path + run_number + "/"
    processed_dir = output_path + run_number + "/"

    # different build types are going to create ProcessedData with different basenames
    if run_type == 'beam' or run_type == 'beam_39':
        basename = "ProcessedData_PMTMRDLAPPD_R"
    elif run_type == 'AmBe' or run_type == 'LED':
        basename = 'ProcessedData_PMT_R'
    elif run_type == 'laser':
        basename = 'ProcessedData_PMTLAPPD_R'
    elif run_type == 'cosmic':
        basename = 'ProcessedData_PMTMRD_R'

    raw_files = [file for file in os.listdir(raw_data_dir) if file.startswith("RAWDataR" + run_number)]
    processed_files = [file for file in os.listdir(processed_dir) if file.startswith(basename + run_number) and not file.endswith(".data")]

    num_raw_files = len(raw_files)
    num_processed_files = len(processed_files)

    reprocess = False
    if num_raw_files != num_processed_files:
        reprocess = True

    return reprocess


# Check if there any missing processed files in /persistent after the file transfer
def missing_after_transfer(run_number, raw_path, data_path, run_type):

    raw_data_dir = raw_path + run_number + "/"
    processed_dir = data_path + "R" + run_number + "/"

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

    # Print the results
    print("\nNumber of raw files: ", num_raw_files)
    print("Number of processed files: ", num_processed_files)
    print("Number of missing files: ", num_raw_files-num_processed_files)
    print("Missing processed files: ", missing_files)
    print("\nPercentage processed: ", round((num_processed_files/num_raw_files)*100,2), '%')
    print('\n')

    # write to run summary file
    with open('R' + run_number + '_summary.txt', 'a') as file:
        file.write('R' + run_number + ' transfer summary\n')
        file.write('\nNumber of raw files: ' + str(num_raw_files))
        file.write('\nNumber of processed files: ' + str(num_processed_files))
        file.write('\nNumber of missing files: ' + str(num_raw_files-num_processed_files))
        file.write('\nMissing processed files: ' + str(missing_files) + '\n')
        file.write('\nPercentage processed: ' + str(round((num_processed_files/num_raw_files)*100,2)) + '%')
        
    subprocess.run([
        "./lib/ifdh.sh",
        "cp",
        "R" + run_number + "_summary.txt",
        processed_dir + "."
    ], check=True)
    
    time.sleep(1)

    ifdh_rm("R" + run_number + "_summary.txt")

    return


# Query active jobs list for the user (for event building jobs)
def my_jobs(submitted_runs, user):

    ifdh_rm('current_jobs.txt')
    time.sleep(1)
    print('\nFetching active job list...')
    os.system('jobsub_q -G annie --user ' + user + ' >> current_jobs.txt')
    time.sleep(15)    # this is so long because it sometimes takes time to query job lists

    with open('current_jobs.txt', 'r') as file:
        lines = file.readlines()[:-1]

    # sometimes the .txt file contains "Attempting to get token from..." or whatever - irgnore those lines (only at the top)
    for i, line in enumerate(lines):
        if line.startswith("JOBSUBJOBID"):
            lines = lines[i:]
            break
    
    # only consider jobs that are currently running or idle
    filtered_lines = [line.strip().split() for line in lines[1:] if ('I' in line.strip().split()[-5] or 'R' in line.strip().split()[-5])]
    # only consider jobs form the list with the form: <run>_<p1>_<p2>    (isdigit() checks that the string consists of only digits and underscores)
    jobs = [line for line in filtered_lines if line[9].replace('_', '').isdigit()]
    active_jobs = len(jobs)
    print('\nThere are', active_jobs, 'jobs currently running\n')
    job_names = [row[9] for row in jobs]

    which_runs = list(set([int(job.split('_')[0]) for job in job_names]))

    print('Run number | Still running?')
    print('-------------------------------------')
    
    check = [False for i in range(len(submitted_runs))]
    for i in range(len(submitted_runs)):
        if int(submitted_runs[i]) in which_runs:
            print('  ', submitted_runs[i], '   |    yes')
        else:
            print('  ', submitted_runs[i], '   |    no')
            check[i] = True

    return active_jobs, which_runs, check


# Query BeamCluster active jobs list for the user
def my_jobs_BC(submitted_runs, user):

    ifdh_rm('current_jobs.txt')
    time.sleep(1)
    print('\nFetching active job list...')
    os.system('jobsub_q -G annie --user ' + user + ' >> current_jobs.txt')
    time.sleep(15)
    
    with open('current_jobs.txt', 'r') as file:
        lines = file.readlines()[:-1]

    # sometimes the .txt file contains "Attempting to get token from..." or whatever - irgnore those lines (only at the top)
    for i, line in enumerate(lines):
        if line.startswith("JOBSUBJOBID"):
            lines = lines[i:]
            break
    
    filtered_lines = [line.strip().split() for line in lines[1:] if ('I' in line.strip().split()[-8] or 'R' in line.strip().split()[-8]) and 'BC_' in line.strip().split()[-4]]
    jobs = [line for line in filtered_lines if line[9].startswith(f"BC_")]
    active_jobs = len(jobs)
    print('\nThere are', active_jobs, 'jobs currently running\n')
    why_r_u_running = [row[9] for row in jobs]

    which_runs = list(set([int(job.split('_')[1]) for job in why_r_u_running]))

    print('**** BeamCluster jobs ****')
    print('Run number | Still running?')
    print('-------------------------------------')
    
    check = [False for i in range(len(submitted_runs))]
    for i in range(len(submitted_runs)):
        if int(submitted_runs[i]) in which_runs:
            print('  ', submitted_runs[i], '   |    yes')
        else:
            print('  ', submitted_runs[i], '   |    no')
            check[i] = True

    return active_jobs, which_runs, check


# Tell the script to wait some amount of time
def wait(length_of_time):

    print('\n\n------------------------------------------------')
    print('Waiting for jobs to complete... going to sleep...\n')
    for i in range(length_of_time):
       print('Zzzz ... ' + str(i) + '/' + str(length_of_time) + ' minutes until my alarm goes off ... Zzzz\n')
       time.sleep(60)

    print('\nI am awake!\n')

    return


# breakup run parts into seperate jobs if the number of processed files exceeds a certain part size
def BC_breakup(run_number, data_path, part_size, run_type):

    processed_dir = data_path + "R" + run_number + "/"

    if run_type == 'beam' or run_type == 'beam_39':
        basename = "ProcessedData_PMTMRDLAPPD_R"
    elif run_type == 'laser':
        basename = 'ProcessedData_PMTLAPPD_R'
    elif run_type == 'AmBe' or run_type == 'LED':
        basename = 'ProcessedData_PMT_R'
    elif run_type == 'cosmic':
        basename = 'ProcessedData_PMTMRD_R'

    # Get the list of processed files
    processed_files = [file for file in os.listdir(processed_dir) if file.startswith(basename + run_number) and not file.endswith(".data")]

    # Count the number of processed files
    num_processed_files = len(processed_files)

    if num_processed_files <= part_size:
        return ['0'], [str(num_processed_files - 1)]
    else:
        start_indices = ['0']
        end_indices = []
        for i in range(part_size, num_processed_files, part_size):
            start_indices.append(str(i))
            end_indices.append(str(i - 1))
        end_indices.append(str(num_processed_files - 1))

        return start_indices, end_indices      # lists of starting part file and ending part file
    

# check for BC root files in /scratch
def check_root_scratch(run_number,required_count,output_path):

    file_path = output_path + run_number + '/'

    if not os.path.exists(file_path):
        return False

    root_files = [     # ignore LAPPD BC files
        file for file in os.listdir(file_path)
        if file.endswith(".ntuple.root") and "LAPPD" not in file
    ]

    if len(root_files) == required_count:   # true if all root files present
        return True
    else:
        return 'INCOMPLETE'                 # not completely done


# resubmit the missing BC root files
def which_ones_to_resub_BC(run_number,output_path,parts_i,parts_f):

    missing_chunks = []
    file_path = os.path.join(output_path, run_number)

    for pi, pf in zip(parts_i, parts_f):
        filename = f"BeamCluster_{run_number}_{pi}_{pf}.ntuple.root"
        full_path = os.path.join(file_path, filename)
        if not os.path.exists(full_path):
            missing_chunks.append((pi, pf))

    return missing_chunks


# check for BC root file in /persistent
def check_root_pro(run_number,output_path):

    name_of_file = 'BeamCluster_' + run_number
    file_path = os.path.join(output_path, f"{name_of_file}.root")

    return os.path.exists(file_path)


# attach the correct LAPPD Pedestal folder based on the year
def LAPPD_pedestal(run_number):

    # taken from Yue's README at: /pnfs/annie/persistent/processed/processed_EBV2_LAPPDFiltered/Pedestal/README

    # 2022
    if int(run_number) <= 4173:            # probably lots of data with no LAPPDs
        return '2022_LAPPD40'
    # 2023
    elif 4180 <= int(run_number) < 4763:   # no runs between 4173 and 4180
        return '2023_LAPPD40'
    # 2024
    elif int(run_number) >= 4763:          # continuing to present (November 2024)
        return '2024_LAPPD645839'
    

# clear scratch output directory (Processed + beamcluster) of old runs if reprocessing
def clearScratch(run_list, output_path, BC_scratch_output_path, which_one):
    
    for run in run_list:
        if not run or run.startswith('#'):
            continue

        if which_one == 'Processed':
            path_run = f"{output_path}/{run}"               # ProcessedData
        elif which_one == 'BC':
            path_run = f"{BC_scratch_output_path}/{run}"    # BeamCluster

        print(f"Deleting: {path_run}")

        try:
            shutil.rmtree(path_run)
        except FileNotFoundError:
            print(f"Warning: {path_run} does not exist.")
        except Exception as e:
            print(f"Error deleting {path_run}: {e}")
