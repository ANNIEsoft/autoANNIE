#!/bin/bash

run=$1
processed_path=$2
output_path=$3
WHICH=$4
LAPPD_processed_path=$5
scratch_output_path=$6
lappd_filter_path=$7
mrd_filter_path=$8

IFDH="$(cd "$(dirname "$0")/../lib" && pwd)/ifdh.sh"

echo ""
echo "Copying file(s)..."
echo ""

if [ "$WHICH" == "BC" ]; then
  "${IFDH}" cp -D $output_path/BeamCluster/BeamCluster_$run.root $processed_path/
  echo ""
  ls -lrth $processed_path/BeamCluster_$run.root
  echo ""
elif [ "$WHICH" == "LAPPD" ]; then
  "${IFDH}" cp -D $output_path/BeamCluster/LAPPDBeamCluster_$run.root $LAPPD_processed_path/
  echo ""
  ls -lrth $LAPPD_processed_path/LAPPDBeamCluster_$run.root
  echo ""
  
elif [ "$WHICH" == "LAPPD_filter" ]; then
  mkdir -p $lappd_filter_path/R$run
  chmod 777 $lappd_filter_path/R$run
  "${IFDH}" cp $scratch_output_path/$run/FilteredAllLAPPDData* $lappd_filter_path/R$run/
  echo ""
  ls -lrth $lappd_filter_path/R$run/
  echo ""
elif [ "$WHICH" == "MRD_filter" ]; then
  mkdir -p $mrd_filter_path/R$run
  chmod 777 $mrd_filter_path/R$run
  "${IFDH}" cp $scratch_output_path/$run/FilteredMRDData* $mrd_filter_path/R$run/
  echo ""
  ls -lrth $mrd_filter_path/R$run/
  echo ""
fi
