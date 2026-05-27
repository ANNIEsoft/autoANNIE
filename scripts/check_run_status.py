import os
from glob import glob
import math

# Check run status of event building and data processing
# Author: Steven Doran

# output will be:
#         [run number] [(run type)] [total raw part files] [total processed part files] [total scratch part files] [status]
#  

# script WILL NOT display runs that do not have RAWData missing, or are below the 'min_part_size' threshold
#        --------

#
# if using the BC mode (beamcluster jobs), the output will be:
#         [run number] [status]

##########################################################################################

run_to = 5767                  # the script will show runs up to this one (set to 'current' to display latest runs)

run_back = 5300                # the script will only check runs this far back

run_type = 'beam'              # specify run type you would like to check ('beam', 'LED', 'cosmic', 'laser', 'AmBe')

min_part_size = 3              # only check for runs with atleast this many part files

check_BC = False               # True = check BeamCluster files instead


# modify accordingly
rawdata_path = '/pnfs/annie/persistent/raw/raw/'
prodata_path = '/pnfs/annie/persistent/processed/processed_EBV2/'
scratch_output = '/pnfs/annie/scratch/users/<user>/output/'          # edit accordingly

beamcluster_path = '/pnfs/annie/persistent/processed/BeamClusterTrees/'
BC_scratch_output_path = scratch_output + 'beamcluster/'
N_per_job = 50   # number of part files per beamcluster job

SQL_path = 'ANNIE_SQL_RUNS.txt'

##########################################################################################

# define color codes for text output
RESET = "\033[0m"                      # white = processed and transferred
YELLOW = "\033[93m"                    # yellow = scratch files present, but not complete
RED = "\033[91m"                       # red = run not yet processed (no scratch files either) / BC file not present in scratch but ProcessedData exists
GREEN = "\033[92m"                     # green = scratch files complete, ready to be transferred
DARK_GRAY = "\033[90m"                 # BC: Processed Data not in persistent


# from run type name, get number
def get_run_type(run_type):
    if run_type == 'beam':
        return ['3', '34', '39', '45']
    elif run_type == 'cosmic':
        return ['7', '37']
    elif run_type == 'LED':
        return ['1', '35', '46']
    elif run_type == 'AmBe':
        return ['4', '43', '42', '41', '36']    # TODO: check which ones are relevant
    elif run_type == 'laser':
        return ['8', '44', '40']


# grab the run types from the SQL file
def read_SQL(SQL_file, run_back, run_type):
    
    run_data = {}

    # check if the SQL file exists
    if not os.path.isfile(SQL_file):
        print(f"\nERROR: The SQL file '{SQL_file}' does not exist. Please follow the README and generate an SQL txt file.\nExiting...\n")
        exit()

    # read the SQL file, get the run numbers and the run type
    with open(SQL_file, 'r') as file:
        lines = file.readlines()[2:] 
        for line in lines:
            columns = [col.strip() for col in line.split('|')]
            if len(columns) > 1:
                runnum = columns[1]
                runconfig = columns[5]   # run type

            # 'current' means we don't want a "ceiling" on the runs we display
            if run_to == 'current':
                if int(runnum) >= int(run_back) and runconfig in run_type:
                    run_data[runnum] = int(runconfig) if runconfig.isdigit() else None
            else:
                if int(run_to) >= int(runnum) >= int(run_back) and runconfig in run_type:    
                    run_data[runnum] = int(runconfig) if runconfig.isdigit() else None

    return run_data


def check_run_data(sql, rawdata_path, prodata_path):

    # column header
    print(f"{'RUN':<3} {'TYPE':<2} {'RAW':<3} {'PRO':<3} {'SCRATCH':<3} STATUS")
    print('-' * 31)

    for run_number, run_type in sql.items():

        raw_run_folder = os.path.join(rawdata_path, run_number)
        processed_run_folder = os.path.join(prodata_path, f"R{run_number}")
        scratch_run_folder = os.path.join(scratch_output, run_number)

        # check if RAWDATA folder exists
        if not os.path.isdir(raw_run_folder):
            continue

        # count part files in RAWDATA
        raw_files = glob(os.path.join(raw_run_folder, f"RAWDataR{run_number}S0p*"))
        num_raw_files = len(raw_files)

        # skip the very small runs
        if num_raw_files < min_part_size:
            continue

        # check if PROCESSED folder exists
        if not os.path.isdir(processed_run_folder):

            # if its not processed, check if it exists in scratch
            if not os.path.isdir(scratch_run_folder):
                print(f"{RED}{run_number:>4} {run_type:>2} {num_raw_files:>4} {0:>4} {'':>4} NOT PROCESSED{RESET}")
                continue

            # if there are scratch files are present, count how many are complete
            scratch_files = glob(os.path.join(scratch_run_folder, f"ProcessedData*R{run_number}S0p*"))
            num_scratch_files = len(scratch_files)

            # if there are no scratch files (even if the folder exists), mark as not processed
            if num_scratch_files == 0:
                print(f"{RED}{run_number:>4} {run_type:>2} {num_raw_files:>4} {0:>4} {'':>4} NOT PROCESSED{RESET}")
                continue

            # all scratch part files are complete, ready to transfer
            if num_scratch_files == num_raw_files:
                print(f"{GREEN}{run_number:>4} {run_type:>2} {num_raw_files:>4} {0:>4} {num_scratch_files:>4} READY TO TRANSFER{RESET}")
                continue

            # if not ready to transfer, display number of scratch processed
            print(f"{YELLOW}{run_number:>4} {run_type:>2} {num_raw_files:>4} {0:>4} {num_scratch_files:>4} PARTIALLY COMPLETE{RESET}")
            continue


        # count part files in PROCESSED data if already transferred
        processed_files = glob(os.path.join(processed_run_folder, f"ProcessedData*R{run_number}S0p*"))
        num_processed_files = len(processed_files)

        print(f"{run_number:>4} {run_type:>2} {num_raw_files:>4} {num_processed_files:>4}")


def check_beamcluster(sql, rawdata_path, prodata_path, beamcluster_path, BC_scratch_output_path):

    # column header
    print(f"{'RUN':<3}  STATUS")
    print('-' * 13)

    for run_number, run_type in sql.items():

        raw_run_folder = os.path.join(rawdata_path, run_number)
        processed_run_folder = os.path.join(prodata_path, f"R{run_number}")
        scratch_BC_folder = os.path.join(BC_scratch_output_path, run_number)

        # check if RAWDATA folder exists
        if not os.path.isdir(raw_run_folder):
            continue

        # count part files
        part_files = glob(os.path.join(raw_run_folder, f"RAWDataR{run_number}S0p*"))
        num_raw_files = len(part_files)

        # skip the very small runs
        if num_raw_files < min_part_size:
            continue

        # check if ProcessedData folder exists
        if not os.path.isdir(processed_run_folder):
            print(f"{DARK_GRAY}{run_number:>4} no ProcessedData{RESET}")
            continue

        # check if beamcluster file exists in persistent
        if not os.path.exists(beamcluster_path + f"BeamCluster_{run_number}.root"):

            # if its not processed, check if it exists in scratch
            if not os.path.isdir(scratch_BC_folder):
                print(f"{RED}{run_number:>4} NOT PRESENT{RESET}")
                continue

            # if there are scratch files are present, count how many are complete
            scratch_files = glob(os.path.join(scratch_BC_folder, f"BeamCluster_{run_number}*"))
            num_scratch_files = len(scratch_files)

            # assuming the number of part files per job is N, check how many should be there
            expected_files = math.ceil(num_raw_files / N_per_job)

            # if there are no scratch files (even if the folder exists), mark as not processed
            if num_scratch_files == 0:
                print(f"{RED}{run_number:>4} NOT PRESENT{RESET}")
                continue

            # all scratch part files are complete, ready to transfer
            if num_scratch_files == expected_files:
                print(f"{GREEN}{run_number:>4} READY TO TRANSFER{RESET}")
                continue

            # if not ready to transfer, display number of scratch processed
            print(f"{YELLOW}{run_number:>4} PARTIALLY COMPLETE ({num_scratch_files}/{expected_files}){RESET}")
            continue

        # if file is transferred to persistent
        print(f"{run_number:>4} COMPLETE")

          
print('\n')
run_type_list = get_run_type(run_type)
sql = read_SQL(SQL_path, run_back, run_type_list)
if check_BC:
    check_beamcluster(sql, rawdata_path, prodata_path, beamcluster_path, BC_scratch_output_path)
else:
    check_run_data(sql, rawdata_path, prodata_path)
print('\n')

# done
