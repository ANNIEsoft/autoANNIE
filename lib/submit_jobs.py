# this file produces the necessary grid submission scripts

# this script is for actually submitting the job to the FermiGrid
def submit_grid_job(run, p_start, p_end, input_path, output_path, TA_tar_name, disk_space, raw_path, trig_path, beamfetcher_path, first, final, node_loc, run_type):
    
    if first == True and final == True:
        file = open('submit_grid_job_' + run + '.sh', "w")
        logic_option = 1
    elif first == True:
        file = open('submit_grid_job_' + run + '_first.sh', "w")
        logic_option = 2
    elif final == True:
        file = open('submit_grid_job_' + run + '_final.sh', "w")
        logic_option = 3
    else:
        file = open('submit_grid_job_' + run + '.sh', "w")
        logic_option = 1

    file.write('export INPUT_PATH=' + input_path +  '\n')
    file.write('export RAWDATA_PATH=' + raw_path + run + '/ \n')
    file.write('\n\n')
    file.write('OUTPUT_FOLDER=' + output_path + run + '\n')
    file.write('mkdir -p $OUTPUT_FOLDER \n')
    file.write('\n')

    # offsite resources
    if node_loc == "OFFSITE":
        file.write('jobsub_submit --memory=4000MB --expected-lifetime=6h -G annie --disk=' + disk_space + 'GB --resource-provides=usage_model=OFFSITE --blacklist=Omaha,Swan,Wisconsin,RAL ')
    # FermiGrid
    elif node_loc == "ONSITE":
        file.write('jobsub_submit --memory=4000MB --expected-lifetime=6h -G annie --disk=' + disk_space + 'GB --resource-provides=usage_model=DEDICATED,OPPORTUNISTIC ')
    
    for i in range(int(p_start), int(p_end)+1):
        file.write('-f ${RAWDATA_PATH}/RAWDataR' + run + 'S0p' + str(i) + ' ')

    if logic_option == 2:
        grid_job = 'grid_job_' + run + '_first.sh'
        container_job = 'run_container_job_' + run + '_first.sh'
    elif logic_option == 3:
        grid_job = 'grid_job_' + run + '_final.sh'
        container_job = 'run_container_job_' + run + '_final.sh'
    else:
        grid_job = 'grid_job_' + run + '.sh'
        container_job = 'run_container_job_' + run + '.sh'

    file.write('-f ${INPUT_PATH}/' + container_job + ' ')
    file.write('-f ${INPUT_PATH}/' + TA_tar_name + ' ')
    file.write('-f ' + trig_path + 'R' + run + '_TrigOverlap.tar.gz ')
    if run_type == 'beam' or run_type == 'beam_39':
        file.write('-f ' + beamfetcher_path + 'beamfetcher_' + run + '.root ')
    file.write('-d OUTPUT $OUTPUT_FOLDER ')
    file.write('file://${INPUT_PATH}/' + grid_job + ' ' + run + '_' + str(p_start) + '_' + str(p_end) + '\n')
    file.close()

    return


# this next script executes on the grid node
def grid_job(run, user, TA_tar_name, name_TA, first, final, run_type):

    if first == True and final == True:
        file = open('grid_job_' + run + '.sh', "w")
        logic_option = 1
    elif first == True:
        file = open('grid_job_' + run + '_first.sh', "w")
        logic_option = 2
    elif final == True:
        file = open('grid_job_' + run + '_final.sh', "w")
        logic_option = 3
    else:
        file = open('grid_job_' + run + '.sh', "w")
        logic_option = 1

    file.write('#!/bin/bash \n')
    file.write('# Steven Doran \n')
    file.write('\n')

    file.write('cat <<EOF\n')
    file.write('condor   dir: $CONDOR_DIR_INPUT \n')
    file.write('process   id: $PROCESS \n')
    file.write('output   dir: $CONDOR_DIR_OUTPUT \n')
    file.write('EOF\n')
    file.write('\n')

    file.write('HOSTNAME=$(hostname -f) \n')
    file.write('GRIDUSER="' + user + '" \n')
    file.write('\n')

    file.write('# Argument passed through job submission \n')
    file.write('PART_NAME=$1 \n')
    file.write('\n')

    file.write('# Run type: ' + run_type + '\n')
    file.write('\n')

    file.write('# Create a dummy file in the output directory \n')
    file.write('DUMMY_OUTPUT_FILE=${CONDOR_DIR_OUTPUT}/${JOBSUBJOBID}_dummy_output \n')
    file.write('touch ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "This dummy file belongs to job ${PART_NAME}" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('start_time=$(date +%s)   # start time in seconds \n')
    file.write('echo "The job started at: $(date)" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')

    file.write('echo "Run type: ' + run_type + '" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')

    file.write('echo "Files present in CONDOR_INPUT:" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls -lrth $CONDOR_DIR_INPUT >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')

    file.write('# Copy datafiles \n')
    file.write('${JSB_TMP}/ifdh.sh cp -D $CONDOR_DIR_INPUT/RAWData* . \n')
    file.write('${JSB_TMP}/ifdh.sh cp -D $CONDOR_DIR_INPUT/' + TA_tar_name + ' . \n')
    if run_type == 'beam' or run_type == 'beam_39':
        file.write('${JSB_TMP}/ifdh.sh cp -D $CONDOR_DIR_INPUT/beamfetcher_' + run + '.root . \n') 
    file.write('${JSB_TMP}/ifdh.sh cp -D $CONDOR_DIR_INPUT/R' + run + '_TrigOverlap.tar.gz . \n')
    file.write('tar -xzf ' + TA_tar_name + '\n')
    file.write('tar -xzf R' + run + '_TrigOverlap.tar.gz \n')
    file.write('rm ' + TA_tar_name + '\n')
    file.write('rm R' + run + '_TrigOverlap.tar.gz\n')
    
    file.write('\n')

    file.write('# create bind mountable /tmp directory \n')
    file.write('mkdir tmp \n')
    file.write('\n')

    file.write('ls -v /srv/RAWData* >> my_files.txt \n')
    file.write('echo "Trig overlap files present:" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls -v /srv/Trig* >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    if run_type == 'beam' or run_type == 'beam_39':
        file.write('echo "BeamFetcherV2 file present:" >> ${DUMMY_OUTPUT_FILE} \n')
        file.write('ls -v /srv/beamfetcher*.root >> ${DUMMY_OUTPUT_FILE} \n')
    else:
        file.write('echo "NOT A BEAM RUN - No BeamFetcherV2 file present!" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')

    # ensure singularity is properly bind-mounted
    file.write('\n')
    file.write('echo "Make sure singularity is bind mounting correctly (ls /cvmfs/singularity)" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls /cvmfs/singularity.opensciencegrid.org >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')

    file.write('# Setup singularity container \n')
    if logic_option == 2:
        container_job = 'run_container_job_' + run + '_first.sh'
    elif logic_option == 3:
        container_job = 'run_container_job_' + run + '_final.sh'
    else:
        container_job = 'run_container_job_' + run + '.sh'

    file.write('result=$(singularity exec -B/srv:/srv,/srv/tmp:/tmp /cvmfs/singularity.opensciencegrid.org/anniesoft/toolanalysis\:latest/ $CONDOR_DIR_INPUT/' + container_job + ' $PART_NAME) \n')
    file.write('\n')

    file.write('echo "Moving the output files to CONDOR OUTPUT..." >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')

    file.write('if [ "$result" = "True" ]; then \n')
    file.write('    echo "Processed = Raw, transferring to CONDOR_DIR_OUTPUT" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('    ${JSB_TMP}/ifdh.sh cp -D /srv/logfile* $CONDOR_DIR_OUTPUT \n')
    file.write('    ${JSB_TMP}/ifdh.sh cp -D /srv/Processed* $CONDOR_DIR_OUTPUT \n')
    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':      # other source runs will not have LAPPD information
        file.write('    ${JSB_TMP}/ifdh.sh cp -D /srv/LAPPDTree*.root $CONDOR_DIR_OUTPUT \n')
        file.write('    ${JSB_TMP}/ifdh.sh cp -D /srv/offsetFitResult*.root $CONDOR_DIR_OUTPUT \n')
    file.write('else \n')
    file.write('    echo "Processed != Raw, transferring logfiles to CONDOR_DIR_OUTPUT, BUT NOT TRANSFERRING PROCESSED OR LAPPD FILES" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('    ${JSB_TMP}/ifdh.sh cp -D /srv/logfile* $CONDOR_DIR_OUTPUT \n')
    file.write('fi \n')
    file.write('\n')

    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "Input:" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls $CONDOR_DIR_INPUT >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "Output:" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls $CONDOR_DIR_OUTPUT >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "Cleaning up..." >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "srv directory:" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls -v /srv >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('rm /srv/RAWData* \n')
    file.write('rm /srv/my_files.txt \n')
    file.write('rm /srv/*_beamdb \n')          # typically this won't be here - but some of the tar folders for the overlap files contain a beamdb file as well (from old version of the tool)
    file.write('rm /srv/beamfetcher_*.root \n')
    file.write('rm -rf ' + name_TA + ' \n')
    file.write('rm /srv/Trig* \n')
    file.write('rm /srv/Processed* \n')
    file.write('rm /srv/LAPPDTree*.root \n')
    file.write('rm /srv/offsetFitResult*.root \n')
    file.write('rm /srv/grid_job*.sh /srv/*.txt \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "Any remaining contents?" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls -v /srv >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')

    file.write('\n')
    file.write('end_time=$(date +%s) \n')
    file.write('echo "Job ended at: $(date)" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('duration=$((end_time - start_time)) \n')
    file.write('echo "Script duration (s): ${duration}" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')
    
    file.write('### END ###')

    file.close()

    return


# third script actually executes the ToolChains once in the singularity environment
def run_container_job(run, name_TA, DLS, first, final, run_type):

    # must be a small run with all part files contained in a single job
    if first == True and final == True:
        file = open('run_container_job_' + run + '.sh', "w")
        logic_option = 1

    # contains the first part file
    elif first == True:
        file = open('run_container_job_' + run + '_first.sh', "w")
        logic_option = 2
    
    # contains the final part file
    elif final == True:
        file = open('run_container_job_' + run + '_final.sh', "w")
        logic_option = 3

    # contains neither (middle part files)
    else:
        file = open('run_container_job_' + run + '.sh', "w")
        logic_option = 1    # same result as if both are contained

    file.write('#!/bin/bash \n')
    file.write('# Steven Doran \n')
    file.write('\n')

    file.write('PART_NAME=$1 \n')
    file.write('\n')

    file.write('# sanity checks \n')
    file.write('touch /srv/logfile_${PART_NAME}.txt \n')
    file.write('pwd >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('ls -v >>/srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')
    file.write('\n')

    # We have to copy files to and use the correct EventBuilder toolchain (different ones for different sources)
    if run_type == 'beam' or run_type == 'beam_39':
        eventbuilder_TC = 'EventBuilderV2'
    elif run_type == "AmBe":
        eventbuilder_TC = 'EventBuilderV2_AmBe'
    elif run_type == "cosmic":
        eventbuilder_TC = 'EventBuilderV2_cosmic'
    elif run_type == "LED":
        eventbuilder_TC = 'EventBuilderV2_LED'
    elif run_type == "laser":
        eventbuilder_TC = 'EventBuilderV2_laser'

    file.write('# EventBuilding toolchain selected: ' + eventbuilder_TC + '\n')
    file.write('\n')

    file.write('# copy files \n')

    file.write('echo "contents of my_files:" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('cat /srv/my_files.txt >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('pwd >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')
    file.write('\n')

    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        file.write('\cp /srv/my_files.txt /srv/' + name_TA + '/configfiles/LAPPD_EB/ \n')
        file.write('echo "contents of my_files in the LAPPD_EB toolchain:" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('cat /srv/' + name_TA + '/configfiles/LAPPD_EB/my_files.txt >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')
    else:
        file.write('# Will not run LAPPD toolchains, as it is a ' + run_type + ' run \n')

    file.write('\cp /srv/my_files.txt /srv/' + name_TA + '/configfiles/' + eventbuilder_TC + '/ \n')
    file.write('echo "contents of my_files in the EventBuilder toolchain:" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('cat /srv/' + name_TA + '/configfiles/' + eventbuilder_TC + '/my_files.txt >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')

    if run_type == 'beam' or run_type == 'beam_39':
        file.write('\cp /srv/beamfetcher_' + run + '.root /srv/' + name_TA + '/ \n')
    
    file.write('\cp /srv/Trig* /srv/' + name_TA + '/ \n')
    file.write('echo "ToolAnalysis directory contents:" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('ls -v /srv/' + name_TA + '/ >>/srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')
    
    file.write('\n')

    file.write('# enter ToolAnalysis directory \n')
    file.write('cd ' + name_TA + '/ \n')
    file.write('echo "Are we now in the ToolAnalysis directory?" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('pwd >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')
    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        file.write('echo "LAPPD_EB Toolchain folder contents:" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('ls configfiles/LAPPD_EB/ >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "EventBuilder Toolchain folder contents:" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('ls configfiles/' + eventbuilder_TC + '/ >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')

    file.write('\n')

    # Create DaylightSavings Config for MRD
    if run_type == 'beam' or run_type == 'cosmic' or run_type == 'beam_39':
        file.write('# append MRDDataDecoder for DLS \n')
        file.write("sed -i '$ s/.*/DaylightSavingsSpring " + DLS + "/' configfiles/" + eventbuilder_TC + "/MRDDataDecoderConfig \n")
        file.write('echo "MRDDataDecoderConfig (DLS ' + DLS + ' was selected)" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('cat configfiles/' + eventbuilder_TC + '/MRDDataDecoderConfig >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')
    else:
        file.write('# Not cosmic or beam: no need to append MRDDataDecoder for DLS \n')
        file.write('echo "Not a cosmic or beam run, not appending MRDDataDecoderConfig" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "" >>/srv/logfile_${PART_NAME}.txt \n')
    
    file.write('\n')

    # Change EBSaver beam file path
    if run_type == 'beam' or run_type == 'beam_39':
        file.write('# append EBSaver with the correct beam file name \n')
        file.write('echo "OG EBSaver (incorrect BeamFetcherV2 file):" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('cat configfiles/' + eventbuilder_TC + '/EBSaverConfig >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "EBSaver after, with the correct BeamFetcherV2 file:" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write("sed -i '$ s/.*/beamInfoFileName beamfetcher_" + run + ".root/' configfiles/" + eventbuilder_TC + "/EBSaverConfig \n")
        file.write('cat configfiles/' + eventbuilder_TC + '/EBSaverConfig >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
    else:
        file.write('# No need to append EBSaver with the correct beam file name as it is a source run \n')
        file.write('echo "Not appending EBSaver as there is no beam file" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')

    file.write('\n')

    file.write('# set up paths and libraries \n')
    file.write('source Setup.sh \n')
    file.write('\n')

    # this toolchain produces an LAPPDTree.root file
    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        file.write('# Get LAPPD timing information (LAPPD_EB toolchain) \n')
        file.write('./Analyse configfiles/LAPPD_EB/ToolChainConfig  >> /srv/logfile_LAPPD_${PART_NAME}.txt 2>&1 \n')      # execute lappd timing info toolchain
        file.write('\n')

    # obtain offsets (need to make sure the right primary trigger word is used)
        if run_type == 'beam':        # PPS = 10s (default)
            if int(run) >= 5140:      # after this run, the default PPS was set to 5
                file.write('echo "Command: root -l -q offsetFit_MultipleLAPPD.cpp(LAPPDTree.root, 14, 1, 5, 0)" >> /srv/logfile_LAPPD_${PART_NAME}.txt \n')
                file.write("""root -l -q 'offsetFit_MultipleLAPPD.cpp("LAPPDTree.root", 14, 1, 5, 0)' >> /srv/logfile_LAPPD_${PART_NAME}.txt 2>&1 \n""")
            else:
                file.write('echo "Command: root -l -q offsetFit_MultipleLAPPD.cpp(LAPPDTree.root, 14, 1, 10, 0)" >> /srv/logfile_LAPPD_${PART_NAME}.txt \n')
                file.write("""root -l -q 'offsetFit_MultipleLAPPD.cpp("LAPPDTree.root", 14, 1, 10, 0)' >> /srv/logfile_LAPPD_${PART_NAME}.txt 2>&1 \n""")
        elif run_type == 'beam_39':   # PPS = 1s (run type 39)
            file.write('echo "Command: root -l -q offsetFit_MultipleLAPPD.cpp(LAPPDTree.root, 14, 1, 1, 0)" >> /srv/logfile_LAPPD_${PART_NAME}.txt \n')
            file.write('echo "*** LAPPD PPS RATIO SET TO 1s (RUN TYPE 39) ***" >> /srv/logfile_LAPPD_${PART_NAME}.txt \n')
            file.write("""root -l -q 'offsetFit_MultipleLAPPD.cpp("LAPPDTree.root", 14, 1, 1, 0)' >> /srv/logfile_LAPPD_${PART_NAME}.txt 2>&1 \n""")
        elif run_type == 'laser':
            file.write('echo "Command: root -l -q offsetFit_MultipleLAPPD.cpp(LAPPDTree.root, 47, 1, 10, 0)" >> /srv/logfile_LAPPD_${PART_NAME}.txt \n')
            file.write("""root -l -q 'offsetFit_MultipleLAPPD.cpp("LAPPDTree.root", 47, 0, 10, 0)' >> /srv/logfile_LAPPD_${PART_NAME}.txt 2>&1 \n""")
            file.write('\n')

    else:
        file.write('# Will not run LAPPD_EB or offsetFit script as it is a ' + run_type + ' run \n')

    file.write('# Run the Event Building toolchain \n')
    file.write('./Analyse configfiles/' + eventbuilder_TC + '/ToolChainConfig  >> /srv/logfile_EventBuilder_${PART_NAME}.txt 2>&1 \n')      # execute Event Building TC
    file.write('\n')
    
    file.write('pwd >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "Contents of TA after toolchain:" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('ls -lrth >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('\n')
    file.write('echo "Copying output files... ending script..." >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('\n')

    file.write('# ------------------------ #\n')
    # We need to remove "overlap" Processed files
    file.write('# copy any produced files \n')
    file.write('\n')

    # 1. Count how many RAWData files were copied to /srv/
    file.write('raw_count=$(ls /srv/RAWData* | wc -l) \n')
    file.write('echo "There were $raw_count RAWData files present" >> /srv/logfile_${PART_NAME}.txt \n')

    # 2. Count how many Processed files are present/were produced
    file.write('pro_count=$(ls ProcessedData* | wc -l) \n')
    file.write('echo "There are $pro_count ProcessedData files present" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
    file.write('\n')

    # 3. If Processed != Raw, at least one part file failed for whatever reason --> do not copy processed files (or LAPPD files) to srv/
    #    If Processed == Raw, proceed with clipping the overlap and copying
    file.write('if [ "$pro_count" -ne "$raw_count" ]; then\n')
    file.write('    echo "Mismatch detected: Processed files NOT to be copied" >> /srv/logfile_${PART_NAME}.txt\n')
    file.write('    echo "False" \n')      # passes this up the chain the grid_job.sh
    file.write('else\n')
    file.write('    echo "Counts match: Files to be copied to normal output" >> /srv/logfile_${PART_NAME}.txt\n')
    file.write('    echo "True" \n')      
    file.write('fi\n')

    file.write('\n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
    if logic_option == 2:    # first job
        file.write('echo "This is the first job! Clipping the final part file in the job..." >> /srv/logfile_${PART_NAME}.txt \n')
        file.write("FILES=$(ls Processed* | sort -V | sed '$d')\n")
        file.write('cp $FILES /srv/ \n')
        file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "Files to be copied:" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo $FILES >> /srv/logfile_${PART_NAME}.txt \n')
    elif logic_option == 3:  # final job
        file.write('echo "This is the final job! Clipping the first part file in the job..." >> /srv/logfile_${PART_NAME}.txt \n')
        file.write("FILES=$(ls Processed* | sort -V | sed '1d')\n")
        file.write('cp $FILES /srv/ \n')
        file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "Files to be copied:" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo $FILES >> /srv/logfile_${PART_NAME}.txt \n')
    else:                    # middle jobs
        file.write('echo "Clipping both the first and final part files in the job..." >> /srv/logfile_${PART_NAME}.txt \n')
        file.write("FILES=$(ls Processed* | sort -V | sed '1d;$d')\n")
        file.write('cp $FILES /srv/ \n')
        file.write('echo "" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo "Files to be copied:" >> /srv/logfile_${PART_NAME}.txt \n')
        file.write('echo $FILES >> /srv/logfile_${PART_NAME}.txt \n')
    
    file.write('\n')
    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        file.write('cp LAPPDTree.root /srv/LAPPDTree_${PART_NAME}.root \n')
        file.write('cp offsetFitResult.root /srv/offsetFitResult_${PART_NAME}.root \n')
        file.write('\n')
    file.write('# make sure any output files you want to keep are put in /srv or any subdirectory of /srv \n')
    file.write('\n')
    file.write('### END ###')

    file.close()

    return




# ------------------------------------------------ #
# BeamCluster job scripts

# submission script
def submit_BC(input_path, output_path, TA_tar_name, data_path, node_loc, lappd_pedestal_path):

    # job resources
    lifetime = str(12)       # hr
    mem = str(2000)         # MB

    # For this script, although just the laser + beam run types will need the LAPPDs (and the pedestal files),
    # we can just keep the script the same and attach them anyways. For the grid + run_container scripts we will add conditions.

    file = open(input_path + 'BeamCluster/submit_grid_job.sh', "w")

    file.write('# Job submission script for BeamClusterAnalysis toolchain\n')
    file.write('\n')

    file.write('RUN=$1\n')
    file.write('PI=$2\n')
    file.write('PF=$3\n')
    file.write('DISK_SPACE=$4\n')
    file.write('PED_YEAR=$5\n')
    file.write('\n')
    file.write('export INPUT_PATH=' + input_path + '\n')
    file.write('export OUTPUT_FOLDER=' + output_path + '$RUN\n')
    file.write('export PROCESSED_FILES_PATH=' + data_path + 'R${RUN}/\n')
    file.write('export LAPPD_PEDESTAL_PATH=' + lappd_pedestal_path + '\n')
    file.write('\n')

    file.write('echo ""\n')
    file.write('echo "submitting job..."\n')
    file.write('echo "--> This job will use ${DISK_SPACE}GB of disk space"\n')
    file.write('echo ""\n')
    file.write('\n')

    file.write('QUEUE=medium\n')
    file.write('\n')

    file.write('mkdir -p $OUTPUT_FOLDER\n')
    file.write('\n')

    file.write('# Create a list of part files to attach\n')
    file.write('PART_FILES=""\n')
    file.write('for FILE in ${PROCESSED_FILES_PATH}ProcessedData*; do\n')
    file.write('''    PART_NUM=$(echo "$FILE" | grep -oP 'S0p\K[0-9]+')\n''')
    file.write('    if [ "$PART_NUM" -ge "$PI" ] && [ "$PART_NUM" -le "$PF" ]; then\n')
    file.write('        PART_FILES="$PART_FILES -f $FILE"\n')
    file.write('    fi\n')
    file.write('done\n')
    file.write('\n')

    file.write('jobsub_submit --memory=' + mem + 'MB --expected-lifetime=' + lifetime + 'h -G annie --disk=${DISK_SPACE}GB ')

    # offsite resources
    if node_loc == "OFFSITE":
        file.write('--resource-provides=usage_model=OFFSITE --blacklist=Omaha,Swan,Wisconsin,RAL ')
    # FermiGrid
    elif node_loc == "ONSITE":
        file.write('--resource-provides=usage_model=DEDICATED,OPPORTUNISTIC ')

    # despite other run types not needing the LAPPD pedestal files (cause we aren't building LAPPD-related events), just keep it here. We won't copy it to the pwd in the next step
    file.write('$PART_FILES -f ${INPUT_PATH}/BeamCluster/run_container_job.sh -f ${INPUT_PATH}/' + TA_tar_name + ' -f ${LAPPD_PEDESTAL_PATH}/${PED_YEAR}.tar.gz ')
    file.write('-d OUTPUT $OUTPUT_FOLDER ')
    file.write('file://${INPUT_PATH}/BeamCluster/grid_job.sh BC_${RUN} ${PI} ${PF} ${PED_YEAR}\n')
    file.write('\n')

    file.write('echo "job name is: BC_${RUN} ${PI} ${PF} ${PED_YEAR}"\n')
    file.write('echo "" \n')

    file.close()

    return



# job script that will run on the cluster node
def grid_BC(user, TA_tar_name, name_TA, input_path, run_type):

    file = open(input_path + 'BeamCluster/grid_job.sh', "w")

    file.write('#!/bin/bash\n')
    file.write('# Steven Doran\n')
    file.write('\n')
    file.write('cat <<EOF\n')
    file.write('condor   dir: $CONDOR_DIR_INPUT\n')
    file.write('process   id: $PROCESS\n')
    file.write('output   dir: $CONDOR_DIR_OUTPUT\n')
    file.write('EOF\n')
    file.write('\n')

    file.write('HOSTNAME=$(hostname -f)\n')
    file.write('GRIDUSER="' + user + '"\n')
    file.write('\n')
    file.write('# Argument passed through job submission\n')
    file.write('FIRST_ARG=$1\n')
    file.write('PART_NAME=$(echo "$FIRST_ARG" | grep -oE \'[0-9]+\')\n')
    file.write('PI=$2\n')
    file.write('PF=$3\n')
    file.write('PED=$4   # LAPPD Pedestal folder\n')
    file.write('\n')

    file.write('# Create a dummy log file in the output directory\n')
    file.write('DUMMY_OUTPUT_FILE=${CONDOR_DIR_OUTPUT}/${JOBSUBJOBID}_dummy_output\n')
    file.write('touch ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "This dummy file belongs to job ${PART_NAME}_${PI}_${PF}" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('start_time=$(date +%s)   # start time in seconds \n')
    file.write('echo "The job started at: $(date)" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')

    file.write('echo "Run type: ' + run_type + '" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')
    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        file.write('# LAPPDs will be PRESENT in this job \n')
    else:
        file.write('# LAPPDs will NOT be present in this job \n')
    file.write('\n')

    file.write('echo "Files present in CONDOR_INPUT:" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('ls -lrth $CONDOR_DIR_INPUT >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')
    
    file.write('# Copy datafiles from $CONDOR_INPUT onto worker node (/srv)\n')
    file.write('${JSB_TMP}/ifdh.sh cp -D $CONDOR_DIR_INPUT/ProcessedData* .\n')
    file.write('${JSB_TMP}/ifdh.sh cp -D $CONDOR_DIR_INPUT/' + TA_tar_name + ' .\n')
    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':      # only copy LAPPD ped folder for runs where LAPPD data is built
        file.write('${JSB_TMP}/ifdh.sh cp -D $CONDOR_DIR_INPUT/${PED}.tar.gz .\n')
    file.write('\n')

    file.write('# un-tar TA\n')
    file.write('tar -xzf ' + TA_tar_name + '\n')
    file.write('rm ' + TA_tar_name + '\n')
    file.write('\n')

    if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        file.write('# un-tar LAPPD Pedestal\n')
        file.write('tar -xzf ${PED}.tar.gz\n')
        file.write('rm ${PED}.tar.gz\n')
        file.write('\n')

    file.write('# Check that there is the necessary amount of processed files present\n')
    file.write('NUM_PART_FILES=$((PF - PI + 1))\n')
    file.write('echo "There should be $NUM_PART_FILES files in this job" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('FILES_PRESENT=$(ls /srv/Processed* 2>/dev/null | wc -l)\n')
    file.write('echo "*** There are $FILES_PRESENT files here ***" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('# Exit if the number of part files doesnt match the expected count\n')
    file.write('if [ "$FILES_PRESENT" -ne "$NUM_PART_FILES" ]; then\n')
    file.write('    echo "Expected $NUM_PART_FILES files, but found $FILES_PRESENT. Creating a DANGER file and proceeding..." >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('    touch /srv/DANGER_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('    echo "" >> /srv/DANGER_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('    ls -v /srv/Processed* >> /srv/DANGER_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('fi\n')
    file.write('\n')

    file.write('echo "" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "Looks like they matched. Proceeding with the job..." >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('\n')

    file.write('# Create my_inputs.txt for toolchain\n')
    file.write('ls -v /srv/Processed* >> my_inputs.txt\n')
    file.write('\n')
    
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "Processed files present:" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('ls -v /srv/Processed* >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('\n')

    file.write('echo "Make sure singularity is bind mounting correctly (ls /cvmfs/singularity)" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('ls /cvmfs/singularity.opensciencegrid.org >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('\n')
    file.write('# Setup singularity container\n')
    file.write('singularity exec -B/srv:/srv /cvmfs/singularity.opensciencegrid.org/anniesoft/toolanalysis:latest/ $CONDOR_DIR_INPUT/run_container_job.sh $PART_NAME $PI $PF $PED\n')
    file.write('\n')
    file.write('# ------ The script run_container_job.sh will now run within singularity ------ #\n')
    file.write('\n')

    file.write('# cleanup and move files to $CONDOR_OUTPUT after leaving singularity environment\n')
    file.write('echo "Moving the output files to CONDOR OUTPUT..." >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('${JSB_TMP}/ifdh.sh cp -D /srv/logfile*.txt $CONDOR_DIR_OUTPUT     # log files\n')
    file.write('${JSB_TMP}/ifdh.sh cp -D /srv/*.ntuple.root $CONDOR_DIR_OUTPUT    # Modify: any .root files etc.. that are produced from your toolchain\n')
    #if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        #file.write('${JSB_TMP}/ifdh.sh cp -D /srv/*.lappd.root $CONDOR_DIR_OUTPUT     # LAPPD BeamCluster\n')
        #file.write('${JSB_TMP}/ifdh.sh cp -D /srv/FilteredAllLAPPDData* $CONDOR_DIR_OUTPUT    # Filtered LAPPD Data\n')
    #if run_type == 'beam' or run_type == 'cosmic' or run_type == 'beam_39':     # only cosmic and MRD runs will have MRD data streams
        #file.write('${JSB_TMP}/ifdh.sh cp -D /srv/FilteredMRDData* $CONDOR_DIR_OUTPUT    # Filtered MRD Data\n')
    file.write('\n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "Input:" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('ls $CONDOR_DIR_INPUT >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "Output:" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('ls $CONDOR_DIR_OUTPUT >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('\n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "Cleaning up..." >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('echo "srv directory:" >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('ls -v /srv >> ${DUMMY_OUTPUT_FILE}\n')
    file.write('\n')
    file.write('# make sure to clean up the files left on the worker node\n')
    file.write('rm /srv/Processed*\n')
    file.write('rm /srv/*.txt\n')
    file.write('rm /srv/*.ntuple.root\n')
    file.write('rm /srv/*.lappd.root\n')
    file.write('rm /srv/Filtered*\n')
    file.write('rm /srv/*.sh\n')
    file.write('rm -rf /srv/' + name_TA + '\n')
    file.write('rm -rf /srv/${PED} \n')
    file.write('\n')

    file.write('end_time=$(date +%s) \n')
    file.write('echo "Job ended at: $(date)" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('echo "" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('duration=$((end_time - start_time)) \n')
    file.write('echo "Script duration (s): ${duration}" >> ${DUMMY_OUTPUT_FILE} \n')
    file.write('\n')
    file.write('### END ###\n')

    file.close()

    return


# job that executes within our container
def container_BC(name_TA, input_path, run_type):

    # process is:
    #    1. run BeamClusterAnalysis toolchain over normal Processed Files (produces .ntuple.root file) (relevant for all run types)
    #    2. run LAPPDProcessedFilter to produce FilteredMRD and FilteredAllLAPPDData processed files   (only relevant for beam runs)
    #    3. run BeamClusterAnalysi over FilteredAllLAPPDData files (produces .lappd.root file)         (only relevant for beam runs)

    file = open(input_path + 'BeamCluster/run_container_job.sh', "w")

    file.write('#!/bin/bash\n')
    file.write('# Steven Doran\n')
    file.write('\n')

    file.write('FIRST_ARG=$1\n')
    file.write('PART_NAME=$(echo "$FIRST_ARG" | grep -oE \'[0-9]+\')\n')
    file.write('PI=$2\n')
    file.write('PF=$3\n')
    file.write('PED=$4   # LAPPD Pedestal folder\n')
    file.write('\n')
    
    file.write('# logfile\n')
    file.write('touch /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('pwd >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('ls -v >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('\n')

    file.write('# place the input file containing the necessary data files in the toolchain\n')
    file.write('echo "my_inputs.txt paths:" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('cat /srv/my_inputs.txt >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('rm /srv/' + name_TA + '/configfiles/BeamClusterAnalysis/my_inputs.txt\n')
    file.write('\cp /srv/my_inputs.txt /srv/' + name_TA + '/configfiles/BeamClusterAnalysis/\n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('\n')

    #if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
    #    file.write('# place the LAPPD pedestal folder in the TA folder\n')
    #    file.write('\cp -r /srv/${PED} /srv/' + name_TA + '/ \n')
    #    file.write('\n')

    file.write('# enter ToolAnalysis directory\n')
    file.write('cd ' + name_TA + '/\n')
    file.write('\n')

    file.write('# adjust TreeMaker to have the correct name and the correct run type configurations\n')
    file.write('cd configfiles/BeamClusterAnalysis\n')
    file.write('python3 config.py ${PART_NAME} ${PI} ${PF} ' + run_type + '\n')
    file.write('echo "ANNIEEventTreeMaker config:" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('cat ANNIEEventTreeMakerConfig >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('\n')

    file.write('cd ../../\n')
    file.write('\n')

    #if run_type == 'beam' or run_type == 'laser' or run_type == 'beam_39':
        # Append LAPPD Pedestal folder to Configs in LAPPDProcessedAna
    #    file.write('# append Configs for LAPPD Pedestal file \n')
    #    file.write('echo "LAPPD Pedestal arg: ${PED}" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('echo "LAPPD Pedestal folder contents (${PED}): " >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('ls ${PED} >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write("grep '^[[:space:]]*PedinputfileTXT[[:space:]]' configfiles/LAPPDProcessedAna/Configs >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n")
    #    file.write('sed -i "/^[[:space:]]*#/! s|^[[:space:]]*PedinputfileTXT[[:space:]].*|PedinputfileTXT ${PED}/P|" configfiles/LAPPDProcessedAna/Configs\n')
    #    file.write('echo "PedinputfileTXT line (changed): " >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write("grep '^[[:space:]]*PedinputfileTXT[[:space:]]' configfiles/LAPPDProcessedAna/Configs >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n")
    #    file.write('echo "" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('\n')

    file.write('# set up paths and libraries\n')
    file.write('source Setup.sh\n')
    file.write('\n')

    file.write('# Run the toolchain, and output verbose to log file\n')
    file.write('./Analyse configfiles/BeamClusterAnalysis/ToolChainConfig >> /srv/logfile_BC_${PART_NAME}_${PI}_${PF}.txt 2>&1 \n')
    file.write('\n')

    # Only run the filtering over beam runs (we only care about producing LAPPD + MRD filtered runs for beam)
    #if run_type == 'beam' or run_type == 'beam_39':
    #    file.write('# Run the event filter for the LAPPD and MRD\n')
    #    file.write('rm configfiles/LAPPDProcessedFilter/list.txt\n')
    #    file.write('\cp configfiles/BeamClusterAnalysis/my_inputs.txt configfiles/LAPPDProcessedFilter/list.txt\n')
    #    file.write('echo "configfiles/LAPPDProcessedFilter/list.txt:" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('cat configfiles/LAPPDProcessedFilter/list.txt >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('echo "" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('./Analyse configfiles/LAPPDProcessedFilter/ToolChainConfig >> /srv/logfile_Filter_${PART_NAME}_${PI}_${PF}.txt 2>&1 \n')
    #    file.write('\n')

    #    file.write('# Run BC for the filtered data\n')
    #    file.write('rm configfiles/BeamClusterAnalysis/my_inputs.txt\n')
    #    file.write('ls -v FilteredAllLAPPDData >> configfiles/BeamClusterAnalysis/my_inputs.txt\n')
    #    file.write('cd configfiles/BeamClusterAnalysis\n')
    #    file.write('python3 configLAPPD.py ${PART_NAME} ${PI} ${PF} ' + run_type + '\n')
    #    file.write('cd ../../\n')
    #    file.write('echo "File present in filtered my_inputs.txt:" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('cat configfiles/BeamClusterAnalysis/my_inputs.txt >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('echo "" >> /srv/logfile_BC_Filtered_${PART_NAME}_${PI}_${PF}.txt\n')
    #    file.write('./Analyse configfiles/BeamClusterAnalysis/ToolChainConfig >> /srv/logfile_BC_Filtered_${PART_NAME}_${PI}_${PF}.txt 2>&1 \n')
    #    file.write('\n')

    file.write('# log files\n')
    file.write('echo "" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('echo "ToolAnalysis directory contents:" >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('ls -lrth >> /srv/logfile_${PART_NAME}_${PI}_${PF}.txt\n')
    file.write('\n')

    file.write('# copy any produced files to /srv for extraction\n')
    file.write('cp *.ntuple.root /srv/\n')
    #if run_type == 'beam' or run_type == 'beam_39':
    #    file.write('cp *.lappd.root /srv/\n')
    #    file.write('cp FilteredMRDData /srv/FilteredMRDData_${PART_NAME}_${PI}_${PF}\n')
    #    file.write('cp FilteredAllLAPPDData /srv/FilteredAllLAPPDData_${PART_NAME}_${PI}_${PF}\n')
    file.write('\n')
    file.write('# make sure any output files you want to keep are put in /srv or any subdirectory of /srv\n')
    file.write('\n')
    file.write('### END ###\n')

    file.close()




