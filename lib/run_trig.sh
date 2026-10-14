#!/bin/bash

APP=$1
SCRATCH=$2
trig_path=$3
BIND=$4

while read run; do

    echo ""
    echo "Running PreProcessTrigOverlap on run: $run"

    cd ${APP}
    cd configfiles/PreProcessTrigOverlap/

    sh CreateMyList.sh $run

    cd ../../

    # enter the singularity environment
    singularity shell ${BIND} /cvmfs/singularity.opensciencegrid.org/anniesoft/toolanalysis\:latest/ << EOF

    source Setup.sh

    ./Analyse ./configfiles/PreProcessTrigOverlap/ToolChainConfig
    
    exit

EOF
    
    tar -czvf R${run}_TrigOverlap.tar.gz -C ${APP} TrigOverlap_R${run}S0p*
    
    cp R${run}_TrigOverlap.tar.gz ${trig_path}.

    ls -lrth ${trig_path}/R${run}_TrigOverlap.tar.gz

    rm TrigOverlap_R${run}S0p*

    rm R${run}_TrigOverlap.tar.gz

    cd ${SCRATCH}


done < "trig.list"
