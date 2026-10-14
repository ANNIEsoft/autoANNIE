#!/bin/bash

APP=$1
SCRATCH=$2
BEAM_PATH=$3
BIND=$4

while read run; do

    echo ""
    echo "Running BeamFetcherV2 toolchain on run: $run"
    echo ""

    cd ${APP}
    cd configfiles/BeamFetcherV2/

    sh CreateMyList.sh $run

    cd ../../

    # enter the singularity environment
    singularity shell ${BIND} /cvmfs/singularity.opensciencegrid.org/anniesoft/toolanalysis\:latest/ << EOF

    source Setup.sh

    ./Analyse ./configfiles/BeamFetcherV2/ToolChainConfig

    exit

EOF

    cp beamfetcher_tree.root ${BEAM_PATH}/beamfetcher_${run}.root

    ls -lrth ${BEAM_PATH}/beamfetcher_${run}.root

    rm beamfetcher_tree.root

    cd ${SCRATCH}

done < "beam.list"
